# 🔍 FindIt — NLP-Based Lost & Found Matching System

A simple college project that helps students **report lost or found items** and uses
**Natural Language Processing (NLP)** to find potentially matching reports.

---

## What FindIt Does

- Students submit a lost-item report **or** a found-item report through a web form.
- Reports are saved permanently to Excel files (`lost_items.xlsx` / `found_items.xlsx`).
- After submission, FindIt compares the new report against all opposite-type reports
  using **TF-IDF vectorisation** and **cosine similarity**.
- The most textually similar reports are displayed, ranked from highest to lowest.

---

## Two Main User Flows

### 1 — I Lost an Item
1. Click **I Lost an Item** on the homepage.
2. Fill in the form (category, color, description, location, date lost).
3. Click **Submit Lost Item**.
4. FindIt saves your report to `excel/lost_items.xlsx`.
5. FindIt searches `excel/found_items.xlsx` for similar reports.
6. Matching found items are displayed with a Text Similarity percentage.

### 2 — I Found an Item
1. Click **I Found an Item** on the homepage.
2. Fill in the form (category, color, description, location, date found).
3. Click **Submit Found Item**.
4. FindIt saves your report to `excel/found_items.xlsx`.
5. FindIt searches `excel/lost_items.xlsx` for similar reports.
6. Matching lost items are displayed with a Text Similarity percentage.

---

## How the NLP Matching Works

### Step 1 – Text Preparation
FindIt combines the key text fields from each report into one string:
> category + custom name + item name + color + brand + description + location

The string is lowercased and whitespace-normalised.

### Step 2 – Category Compatibility Filter
Only reports with a compatible item category are compared.
Exact category matches are preferred. Reports marked **Other** are always compared
using text content instead of being discarded.

### Step 3 – TF-IDF Vectorisation
`TfidfVectorizer` from scikit-learn converts the text of the query report and all
compatible candidate reports into numerical vectors.

- `ngram_range=(1, 2)` captures both single words and two-word phrases.
- Words that appear in many reports receive a lower weight (IDF effect).
- Rare, distinctive words (like brand names) receive a higher weight.

### Step 4 – Cosine Similarity
The angle between the query vector and each candidate vector is measured.
A score of **1.0** means identical text; **0.0** means completely unrelated.

```
Text Similarity (%) = cosine_similarity × 100
```

The displayed percentage measures **textual overlap**, not a guarantee that the
two reports refer to the same physical item.

### Step 5 – Ranking and Threshold
- Candidates scoring below **10%** (the demo threshold) are not shown.
- Up to **5** results are displayed, sorted from highest to lowest similarity.

---

## Excel Storage

| File | Purpose | Key columns |
|------|---------|-------------|
| `excel/lost_items.xlsx`  | All lost-item reports  | report_id, item_category, item_name, color, brand, description, location, date_lost, submission_status, department_name, created_at |
| `excel/found_items.xlsx` | All found-item reports | report_id, item_category, item_name, color, brand, description, location, date_found, submission_status, department_name, created_at |

Both files are **created automatically** when the app starts for the first time.
Records are **appended** — existing data is never deleted.

---

## Project Structure

```
FindIt/
├── ui/
│   └── app.py              ← Streamlit UI (forms, results, CSS)
├── algorithm/
│   ├── __init__.py
│   └── matching.py         ← NLP engine + Excel I/O
├── excel/
│   ├── lost_items.xlsx     ← Auto-created
│   └── found_items.xlsx    ← Auto-created
├── requirements.txt
└── README.md
```

---

## Setup & Run (Windows)

```bash
# 1. Navigate to the FindIt folder
cd path\to\FindIt

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate it
.venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the app
streamlit run ui/app.py
```

The browser will open automatically at `http://localhost:8501`.

> **Excel files are created automatically** inside the `excel/` folder on first run.
> You do not need to create them manually.

---

## Sample Data (Testing)

Click the **"Load sample data for testing"** expander on the homepage to insert
fictional records. Sample data is only inserted when the Excel files are empty,
so it will not duplicate on repeated clicks.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `streamlit` | Web UI framework |
| `pandas` | DataFrame manipulation & Excel I/O |
| `openpyxl` | Excel file engine |
| `scikit-learn` | TF-IDF vectorisation + cosine similarity |

All other functionality uses the Python standard library (`os`, `re`, `uuid`, `datetime`).

---

*FindIt — NLP AAT Project | Built with Python, Streamlit, and scikit-learn*
