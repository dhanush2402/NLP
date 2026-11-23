"""
FindIt -- ui/app.py
Streamlit front-end: homepage, lost/found forms, matching results.
"""

import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st
from datetime import date

from algorithm.matching import (
    init_excel_files,
    save_lost_item,
    save_found_item,
    read_lost_items,
    read_found_items,
    find_matches,
    SIMILARITY_THRESHOLD,
)

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="FindIt -- Lost & Found",
    page_icon="",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #f8f9fc;
    color: #1a1f36;
}

#MainMenu, footer, header { visibility: hidden; }

.block-container { max-width: 760px; padding: 2rem 1.5rem 4rem; }

.app-title {
    font-size: 2.6rem;
    font-weight: 800;
    color: #3730a3;
    letter-spacing: -1px;
    margin-bottom: 0;
}
.app-tagline {
    font-size: 1.5rem;
    font-weight: 600;
    color: #1a1f36;
    margin-top: 0.25rem;
    margin-bottom: 0.4rem;
}
.app-subtitle {
    font-size: 0.97rem;
    color: #6b7280;
    margin-bottom: 2rem;
}

.home-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 1.6rem 1.8rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.home-card h3 {
    margin: 0 0 0.4rem;
    font-size: 1.15rem;
    font-weight: 700;
    color: #1a1f36;
}
.home-card p {
    margin: 0;
    font-size: 0.9rem;
    color: #6b7280;
}

.section-header {
    font-size: 1.4rem;
    font-weight: 700;
    color: #3730a3;
    margin-bottom: 1.2rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #e0e7ff;
}

.result-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-left: 4px solid #4f46e5;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.result-card .score-badge {
    display: inline-block;
    background: #eef2ff;
    color: #3730a3;
    font-weight: 700;
    font-size: 1.1rem;
    border-radius: 8px;
    padding: 0.2rem 0.8rem;
    margin-bottom: 0.6rem;
}
.result-card .item-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #1a1f36;
    margin-bottom: 0.4rem;
}
.result-card .meta {
    font-size: 0.85rem;
    color: #6b7280;
    margin-bottom: 0.25rem;
}
.result-card .desc {
    font-size: 0.9rem;
    color: #374151;
    margin-top: 0.5rem;
    margin-bottom: 0.4rem;
}
.status-chip {
    display: inline-block;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 0.18rem 0.7rem;
    border-radius: 999px;
    margin-top: 0.4rem;
}
.chip-lost  { background: #fee2e2; color: #991b1b; }
.chip-found { background: #dcfce7; color: #166534; }

.no-match {
    background: #f0f4ff;
    border: 1px solid #c7d2fe;
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    text-align: center;
    color: #3730a3;
    font-size: 0.97rem;
}
.no-match h4 { margin-bottom: 0.4rem; font-size: 1.1rem; color: #312e81; }

.success-box {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 10px;
    padding: 0.9rem 1.2rem;
    color: #166534;
    font-size: 0.93rem;
    margin-bottom: 1rem;
}

.divider { border: none; border-top: 1px solid #e5e7eb; margin: 1.5rem 0; }

div.stButton > button { border-radius: 10px; font-weight: 600; }
label { font-weight: 500 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CATEGORIES = [
    "Water Bottle", "Bag / Backpack", "Laptop Charger / Adapter",
    "College ID Card", "Earbuds / Earphones", "Wallet / Purse",
    "Keys", "Books / Notebooks", "Umbrella", "Spectacles",
    "USB Drive", "Calculator", "Stationery", "Clothing", "Other",
]

COLORS = [
    "Black", "Blue", "White", "Red", "Grey", "Green",
    "Brown", "Silver", "Pink", "Yellow", "Multicolor", "Other",
]

DEPT_OPTIONS = [
    "Not submitted to a department",
    "Submitted to Lost and Found Office",
    "Submitted to College Security",
    "Submitted to College Office",
    "Submitted to Other Department",
]

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@st.cache_resource
def _startup():
    init_excel_files()
    return True

_startup()

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "home"
if "results" not in st.session_state:
    st.session_state.results = []
if "submitted_type" not in st.session_state:
    st.session_state.submitted_type = ""
if "report_id" not in st.session_state:
    st.session_state.report_id = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def go(page: str):
    st.session_state.page = page


def _result_card(record: dict, kind: str):
    score  = record.get("similarity", 0)
    name   = record.get("item_name", "") or record.get("custom_item_name", "") or "-"
    cat    = record.get("item_category", "-")
    color  = record.get("color", "-")
    brand  = record.get("brand", "")
    desc   = record.get("description", "-")
    loc    = record.get("location", "-")
    rid    = record.get("report_id", "-")
    status = record.get("submission_status", "")
    dept   = record.get("department_name", "")

    if kind == "found":
        date_label = "Date Found"
        date_val   = record.get("date_found", "-")
        chip_html  = '<span class="status-chip chip-found">Found</span>'
    else:
        date_label = "Date Lost"
        date_val   = record.get("date_lost", "-")
        chip_html  = '<span class="status-chip chip-lost">Lost</span>'

    brand_row = f'<div class="meta">Brand / Model: <b>{brand}</b></div>' if brand else ""
    dept_row  = ""
    if status and status != "Not submitted to a department":
        dept_info = f" - {dept}" if dept else ""
        dept_row  = f'<div class="meta">Submitted to: <b>{status.replace("Submitted to ", "")}{dept_info}</b></div>'

    st.markdown(f"""
<div class="result-card">
  <div class="score-badge">{score:.1f}% Text Similarity</div>
  <div class="item-title">{name}</div>
  <div class="meta">Category: <b>{cat}</b></div>
  <div class="meta">Color: <b>{color}</b></div>
  {brand_row}
  <div class="desc">{desc}</div>
  <div class="meta">Location: <b>{loc}</b></div>
  <div class="meta">{date_label}: <b>{date_val}</b></div>
  <div class="meta">Report ID: <code>{rid}</code></div>
  {dept_row}
  {chip_html}
</div>
""", unsafe_allow_html=True)


def _validate_form(category, custom_name, item_name, color, description,
                   location, date_val, dept_status, dept_name_field):
    errors = []
    if not category:
        errors.append("Please select an item category.")
    if category == "Other" and not custom_name.strip():
        errors.append("Please enter the custom item name (category is Other).")
    if not item_name.strip():
        errors.append("Please enter the item name / title.")
    if not color:
        errors.append("Please select the primary color.")
    if not description.strip():
        errors.append("Please enter a description.")
    elif len(description.strip()) < 15:
        errors.append("Description must be at least 15 characters.")
    if not location.strip():
        errors.append("Please enter the location.")
    if not date_val:
        errors.append("Please select the date.")
    if dept_status == "Submitted to Other Department" and not dept_name_field.strip():
        errors.append("Please enter the department name (you selected 'Other Department').")
    return errors


# ---------------------------------------------------------------------------
# Page: Home
# ---------------------------------------------------------------------------

def page_home():
    st.markdown('<div class="app-title">FindIt</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-tagline">Lost Something? Let\'s Find It.</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="app-subtitle">Report lost or found belongings and use NLP to discover similar item reports.</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
<div class="home-card">
  <h3>I Lost an Item</h3>
  <p>Report an item you lost and search for similar found items.</p>
</div>
""", unsafe_allow_html=True)
        if st.button("I Lost an Item", key="btn_lost", use_container_width=True, type="primary"):
            go("lost")
            st.rerun()

    with col2:
        st.markdown("""
<div class="home-card">
  <h3>I Found an Item</h3>
  <p>Report an item you found and check whether someone has reported it missing.</p>
</div>
""", unsafe_allow_html=True)
        if st.button("I Found an Item", key="btn_found", use_container_width=True, type="primary"):
            go("found")
            st.rerun()


# ---------------------------------------------------------------------------
# Page: Lost Item Form
# ---------------------------------------------------------------------------

def page_lost():
    if st.button("Back to Home", key="back_lost"):
        go("home")
        st.rerun()

    st.markdown('<div class="section-header">Report a Lost Item</div>', unsafe_allow_html=True)
    st.caption("Fill in as many details as possible to improve matching accuracy.")

    with st.form("lost_form", clear_on_submit=False):
        category = st.selectbox("Item Category *", [""] + CATEGORIES, key="l_cat")

        custom_name = ""
        if category == "Other":
            custom_name = st.text_input("Custom Item Name *", placeholder="e.g. Thermos Flask", key="l_custom")

        item_name = st.text_input("Item Name / Title *", placeholder="e.g. Blue Milton Water Bottle", key="l_name")
        color     = st.selectbox("Primary Color *", [""] + COLORS, key="l_color")
        brand     = st.text_input("Brand or Model (optional)", placeholder="e.g. Milton, Dell, Apple", key="l_brand")
        desc      = st.text_area(
            "Detailed Description *",
            placeholder="Describe the item - markings, size, condition, distinctive features...",
            height=110, key="l_desc",
        )
        location  = st.text_input("Location Lost *", placeholder="e.g. Central Library, 2nd floor", key="l_loc")
        date_lost = st.date_input(
            "Approximate Date Lost *",
            value=date.today(), max_value=date.today(), key="l_date",
        )

        st.markdown("---")
        st.markdown("**Submission Status** *(optional - have you reported this to any college department?)*")
        dept_status = st.selectbox("", DEPT_OPTIONS, key="l_dept_status", label_visibility="collapsed")
        dept_name = ""
        if dept_status == "Submitted to Other Department":
            dept_name = st.text_input("Department Name *", placeholder="e.g. Sports Office", key="l_dept_name")

        submitted = st.form_submit_button("Submit Lost Item", use_container_width=True, type="primary")

    if submitted:
        errors = _validate_form(category, custom_name, item_name, color, desc,
                                location, date_lost, dept_status, dept_name)
        if errors:
            for e in errors:
                st.error(e)
        else:
            data = {
                "item_category":     category,
                "custom_item_name":  custom_name.strip(),
                "item_name":         item_name.strip(),
                "color":             color,
                "brand":             brand.strip(),
                "description":       desc.strip(),
                "location":          location.strip(),
                "date_lost":         str(date_lost),
                "submission_status": dept_status,
                "department_name":   dept_name.strip(),
            }
            with st.spinner("Saving report and searching for matches..."):
                try:
                    report_id = save_lost_item(data)
                except RuntimeError as e:
                    st.error(str(e))
                    st.stop()
                try:
                    found_df = read_found_items()
                    matches  = find_matches(data, found_df)
                except Exception as e:
                    st.warning(f"Report saved but matching failed: {e}")
                    matches = []

            st.session_state.results        = matches
            st.session_state.submitted_type = "lost"
            st.session_state.report_id      = report_id
            go("results")
            st.rerun()


# ---------------------------------------------------------------------------
# Page: Found Item Form
# ---------------------------------------------------------------------------

def page_found():
    if st.button("Back to Home", key="back_found"):
        go("home")
        st.rerun()

    st.markdown('<div class="section-header">Report a Found Item</div>', unsafe_allow_html=True)
    st.caption("Fill in as many details as possible to improve matching accuracy.")

    with st.form("found_form", clear_on_submit=False):
        category = st.selectbox("Item Category *", [""] + CATEGORIES, key="f_cat")

        custom_name = ""
        if category == "Other":
            custom_name = st.text_input("Custom Item Name *", placeholder="e.g. Thermos Flask", key="f_custom")

        item_name = st.text_input("Item Name / Title *", placeholder="e.g. Red Umbrella", key="f_name")
        color     = st.selectbox("Primary Color *", [""] + COLORS, key="f_color")
        brand     = st.text_input("Brand or Model (optional)", placeholder="e.g. Samsung, HP, Nike", key="f_brand")
        desc      = st.text_area(
            "Detailed Description *",
            placeholder="Describe the item - markings, size, condition, distinctive features...",
            height=110, key="f_desc",
        )
        location  = st.text_input("Location Found *", placeholder="e.g. Computer Lab, Room 204", key="f_loc")
        date_found = st.date_input(
            "Approximate Date Found *",
            value=date.today(), max_value=date.today(), key="f_date",
        )

        st.markdown("---")
        st.markdown("**Submission Status** *(have you submitted this item to any college department?)*")
        dept_status = st.selectbox("", DEPT_OPTIONS, key="f_dept_status", label_visibility="collapsed")
        dept_name = ""
        if dept_status == "Submitted to Other Department":
            dept_name = st.text_input("Department Name *", placeholder="e.g. Sports Office", key="f_dept_name")

        submitted = st.form_submit_button("Submit Found Item", use_container_width=True, type="primary")

    if submitted:
        errors = _validate_form(category, custom_name, item_name, color, desc,
                                location, date_found, dept_status, dept_name)
        if errors:
            for e in errors:
                st.error(e)
        else:
            data = {
                "item_category":     category,
                "custom_item_name":  custom_name.strip(),
                "item_name":         item_name.strip(),
                "color":             color,
                "brand":             brand.strip(),
                "description":       desc.strip(),
                "location":          location.strip(),
                "date_found":        str(date_found),
                "submission_status": dept_status,
                "department_name":   dept_name.strip(),
            }
            with st.spinner("Saving report and searching for matches..."):
                try:
                    report_id = save_found_item(data)
                except RuntimeError as e:
                    st.error(str(e))
                    st.stop()
                try:
                    lost_df = read_lost_items()
                    matches = find_matches(data, lost_df)
                except Exception as e:
                    st.warning(f"Report saved but matching failed: {e}")
                    matches = []

            st.session_state.results        = matches
            st.session_state.submitted_type = "found"
            st.session_state.report_id      = report_id
            go("results")
            st.rerun()


# ---------------------------------------------------------------------------
# Page: Results
# ---------------------------------------------------------------------------

def page_results():
    submitted_type = st.session_state.submitted_type
    matches        = st.session_state.results
    report_id      = st.session_state.report_id

    kind_label = "Lost Item" if submitted_type == "lost" else "Found Item"
    st.markdown(f"""
<div class="success-box">
<b>{kind_label} report saved successfully.</b>&nbsp; Report ID: <code>{report_id}</code>
</div>
""", unsafe_allow_html=True)

    if submitted_type == "lost":
        heading     = "Potential Found Items"
        result_kind = "found"
    else:
        heading     = "Potential Lost Items"
        result_kind = "lost"

    st.markdown(f'<div class="section-header">{heading}</div>', unsafe_allow_html=True)
    st.caption(
        f"Results are ranked by Text Similarity (TF-IDF cosine similarity x 100). "
        f"Only results above the {int(SIMILARITY_THRESHOLD * 100)}% demo threshold are shown. "
        "This score measures textual overlap - it is not a guarantee that these reports "
        "refer to the same physical item."
    )

    if matches:
        for record in matches:
            _result_card(record, result_kind)
    else:
        st.markdown("""
<div class="no-match">
  <h4>No matching reports found yet.</h4>
  <p>Your report has been saved. Check again later when another matching item is reported.</p>
</div>
""", unsafe_allow_html=True)

    st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back to Home", key="results_home", use_container_width=True):
            go("home")
            st.rerun()
    with col2:
        label = "Report Another Lost Item" if submitted_type == "lost" else "Report Another Found Item"
        dest  = "lost" if submitted_type == "lost" else "found"
        if st.button(label, key="results_again", use_container_width=True):
            go(dest)
            st.rerun()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

page = st.session_state.page

if page == "home":
    page_home()
elif page == "lost":
    page_lost()
elif page == "found":
    page_found()
elif page == "results":
    page_results()
else:
    go("home")
    st.rerun()
