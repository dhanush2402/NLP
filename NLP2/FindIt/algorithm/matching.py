"""
FindIt — algorithm/matching.py
NLP matching engine: Excel I/O, text preprocessing, TF-IDF, cosine similarity.
"""

import os
import re
import uuid
from datetime import datetime, date

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ─────────────────────────────────────────────
# Paths (always relative to this file's location)
# ─────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL_DIR  = os.path.join(BASE_DIR, "excel")
LOST_FILE  = os.path.join(EXCEL_DIR, "lost_items.xlsx")
FOUND_FILE = os.path.join(EXCEL_DIR, "found_items.xlsx")

# ─────────────────────────────────────────────
# Column schemas
# ─────────────────────────────────────────────
LOST_COLS = [
    "report_id", "item_category", "custom_item_name", "item_name",
    "color", "brand", "description", "location", "date_lost",
    "submission_status", "department_name", "created_at",
]

FOUND_COLS = [
    "report_id", "item_category", "custom_item_name", "item_name",
    "color", "brand", "description", "location", "date_found",
    "submission_status", "department_name", "created_at",
]

# Minimum TF-IDF cosine similarity to show a result (demo threshold)
SIMILARITY_THRESHOLD = 0.10   # 10%
TOP_N = 5                      # maximum results shown

# ─────────────────────────────────────────────
# Excel initialisation
# ─────────────────────────────────────────────

def _ensure_excel_dir() -> None:
    os.makedirs(EXCEL_DIR, exist_ok=True)


def _init_excel(filepath: str, columns: list[str]) -> None:
    """Create an empty Excel workbook with the given columns if missing."""
    _ensure_excel_dir()
    if not os.path.exists(filepath):
        df = pd.DataFrame(columns=columns)
        df.to_excel(filepath, index=False, engine="openpyxl")


def init_excel_files() -> None:
    """Initialise both Excel files. Call once at app startup."""
    _init_excel(LOST_FILE, LOST_COLS)
    _init_excel(FOUND_FILE, FOUND_COLS)


# ─────────────────────────────────────────────
# Read helpers
# ─────────────────────────────────────────────

def _safe_read(filepath: str, columns: list[str]) -> pd.DataFrame:
    """
    Read an Excel file and return a DataFrame.
    Returns an empty DataFrame with the correct columns on any failure.
    """
    try:
        df = pd.read_excel(filepath, engine="openpyxl", dtype=str)
        # Add any missing columns (schema evolution)
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        df = df[columns]  # keep only known columns, in order
        df = df.fillna("")
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=columns)
    except Exception as exc:
        raise RuntimeError(
            f"Could not read {os.path.basename(filepath)}: {exc}"
        ) from exc


def read_lost_items() -> pd.DataFrame:
    return _safe_read(LOST_FILE, LOST_COLS)


def read_found_items() -> pd.DataFrame:
    return _safe_read(FOUND_FILE, FOUND_COLS)


# ─────────────────────────────────────────────
# Write helpers
# ─────────────────────────────────────────────

def _append_row(filepath: str, columns: list[str], row: dict) -> None:
    """Append one row to an Excel file atomically (read → append → write)."""
    df = _safe_read(filepath, columns)
    new_row = {col: str(row.get(col, "")) for col in columns}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    try:
        df.to_excel(filepath, index=False, engine="openpyxl")
    except Exception as exc:
        raise RuntimeError(
            f"Failed to save report to {os.path.basename(filepath)}: {exc}"
        ) from exc


def save_lost_item(data: dict) -> str:
    """
    Persist a lost-item report. Returns the generated report_id.
    Raises RuntimeError if the write fails.
    """
    report_id = "L-" + uuid.uuid4().hex[:8].upper()
    data["report_id"] = report_id
    data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _append_row(LOST_FILE, LOST_COLS, data)
    return report_id


def save_found_item(data: dict) -> str:
    """
    Persist a found-item report. Returns the generated report_id.
    Raises RuntimeError if the write fails.
    """
    report_id = "F-" + uuid.uuid4().hex[:8].upper()
    data["report_id"] = report_id
    data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _append_row(FOUND_FILE, FOUND_COLS, data)
    return report_id


# ─────────────────────────────────────────────
# Text preprocessing
# ─────────────────────────────────────────────

def _safe_str(value) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if s.lower() in ("nan", "none", ""):
        return ""
    return s


def build_text(row: dict | pd.Series) -> str:
    """
    Combine item fields into a single normalised string for TF-IDF.
    Fields used: category, custom_item_name, item_name, color,
                 brand, description, location.
    We intentionally keep stopwords so that TF-IDF weighting handles them.
    """
    parts = [
        _safe_str(row.get("item_category", "")),
        _safe_str(row.get("custom_item_name", "")),
        _safe_str(row.get("item_name", "")),
        _safe_str(row.get("color", "")),
        _safe_str(row.get("brand", "")),
        _safe_str(row.get("description", "")),
        _safe_str(row.get("location", "")),
    ]
    combined = " ".join(p for p in parts if p)
    # collapse repeated whitespace
    return re.sub(r"\s+", " ", combined).strip().lower()


# ─────────────────────────────────────────────
# Category compatibility
# ─────────────────────────────────────────────

def _categories_compatible(query_cat: str, candidate_cat: str) -> bool:
    """
    Returns True when the two categories are compatible enough to compare.

    Rules:
    - Exact match → always compatible.
    - Either is "Other" → compatible (rely on text similarity to distinguish).
    - Different known categories → incompatible (filter out).
    """
    q = query_cat.strip().lower()
    c = candidate_cat.strip().lower()
    if q == c:
        return True
    if q == "other" or c == "other":
        return True
    return False


# ─────────────────────────────────────────────
# TF-IDF + cosine similarity matching
# ─────────────────────────────────────────────

def find_matches(query: dict, candidates_df: pd.DataFrame) -> list[dict]:
    """
    Given a query report dict and a DataFrame of opposite-type reports,
    return a ranked list of matching records (dicts) with a 'similarity'
    key (float, 0–100), filtered by category compatibility and the
    SIMILARITY_THRESHOLD.

    Returns an empty list when no suitable matches are found.
    """
    if candidates_df is None or candidates_df.empty:
        return []

    # ── category filter ──────────────────────────────────────────────────
    query_cat = _safe_str(query.get("item_category", ""))
    compatible_rows = candidates_df[
        candidates_df["item_category"].apply(
            lambda c: _categories_compatible(query_cat, _safe_str(c))
        )
    ].copy()

    if compatible_rows.empty:
        return []

    # ── build text representations ────────────────────────────────────────
    query_text = build_text(query)
    candidate_texts = compatible_rows.apply(build_text, axis=1).tolist()

    # Guard: if query text is empty after preprocessing
    if not query_text.strip():
        return []

    # ── TF-IDF vectorisation ─────────────────────────────────────────────
    corpus = [query_text] + candidate_texts
    try:
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            lowercase=True,
            strip_accents="unicode",
            min_df=1,
        )
        tfidf_matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        # Empty vocabulary (e.g. all texts are stop-words only)
        return []

    # ── cosine similarity ─────────────────────────────────────────────────
    query_vec = tfidf_matrix[0]
    candidate_vecs = tfidf_matrix[1:]
    similarities = cosine_similarity(query_vec, candidate_vecs).flatten()

    # ── assemble results ──────────────────────────────────────────────────
    results = []
    for idx, score in enumerate(similarities):
        if score < SIMILARITY_THRESHOLD:
            continue
        record = compatible_rows.iloc[idx].to_dict()
        record["similarity"] = round(float(score) * 100, 1)
        results.append(record)

    # Sort descending, return top N
    results.sort(key=lambda r: r["similarity"], reverse=True)
    return results[:TOP_N]


# ─────────────────────────────────────────────
# Sample data loader (one-time, for testing)
# ─────────────────────────────────────────────

SAMPLE_FOUND = [
    {
        "item_category":    "Water Bottle",
        "custom_item_name": "",
        "item_name":        "Milton Water Bottle",
        "color":            "Blue",
        "brand":            "Milton",
        "description":      "Blue stainless-steel bottle with a black lid and a small scratch near the bottom.",
        "location":         "Central Library, second floor",
        "date_found":       "2026-10-27",
        "submission_status": "Submitted to Lost and Found Office",
        "department_name":  "",
    },
    {
        "item_category":    "Laptop Charger / Adapter",
        "custom_item_name": "",
        "item_name":        "Dell Laptop Charger",
        "color":            "Black",
        "brand":            "Dell",
        "description":      "Black Dell 65W USB-C laptop charger with a frayed cable near the brick.",
        "location":         "Computer Lab, Room 204",
        "date_found":       "2026-10-25",
        "submission_status": "Not submitted to a department",
        "department_name":  "",
    },
    {
        "item_category":    "College ID Card",
        "custom_item_name": "",
        "item_name":        "Student ID Card",
        "color":            "White",
        "brand":            "",
        "description":      "White college ID card with a blue lanyard holder attached. Found near the canteen.",
        "location":         "College Canteen",
        "date_found":       "2026-10-28",
        "submission_status": "Submitted to College Security",
        "department_name":  "",
    },
]

SAMPLE_LOST = [
    {
        "item_category":    "Water Bottle",
        "custom_item_name": "",
        "item_name":        "Blue Water Bottle",
        "color":            "Blue",
        "brand":            "Milton",
        "description":      "I lost my blue Milton bottle with a black cap and a scratch near the bottom.",
        "location":         "College library, second floor",
        "date_lost":        "2026-10-27",
        "submission_status": "Not submitted to a department",
        "department_name":  "",
    },
    {
        "item_category":    "Keys",
        "custom_item_name": "",
        "item_name":        "Key Ring with 3 Keys",
        "color":            "Silver",
        "brand":            "",
        "description":      "Silver key ring with three keys and a small red tag attached. Lost somewhere in the main block.",
        "location":         "Main Block corridor",
        "date_lost":        "2026-10-26",
        "submission_status": "Submitted to College Office",
        "department_name":  "",
    },
]


def load_sample_data() -> tuple[int, int]:
    """
    Insert sample records into the Excel files ONLY if they are empty.
    Returns (lost_added, found_added) counts.
    """
    lost_added = found_added = 0

    lost_df = read_lost_items()
    if lost_df.empty:
        for record in SAMPLE_LOST:
            save_lost_item(dict(record))
            lost_added += 1

    found_df = read_found_items()
    if found_df.empty:
        for record in SAMPLE_FOUND:
            save_found_item(dict(record))
            found_added += 1

    return lost_added, found_added
