"""Streamlit entry point for the local-first personal spending tracker.

Run from the project root with:

    streamlit run app/main.py

Streamlit automatically discovers the sibling ``pages/`` directory and builds
the multipage navigation in the sidebar.
"""

import streamlit as st

import database

st.set_page_config(
    page_title="Finance Manager",
    page_icon="💸",
    layout="wide",
)

# Ensure the schema exists before any page tries to read or write.
database.init_db()

st.title("💸 Finance Manager")
st.caption("A local-first personal spending tracker. Your data never leaves this machine.")

count = database.count_transactions()
col1, col2 = st.columns(2)
col1.metric("Transactions stored", f"{count:,}")
col2.metric("Database", "data/finance.db")

st.markdown(
    """
### How to use

1. **📊 Dashboard** — overview: a gradient chart of spendings vs. earnings
   (switch between This month / 3M / 6M / 1Y / YTD) plus headline totals.
2. **🛒 Spendings** — the same gradient chart, then spending broken down by
   category, by month and by merchant.
3. **💰 Earnings** — the same gradient chart, then earnings by category, by
   month and by source.
4. **🔁 Monthly subscriptions** — detects recurring monthly charges so you can
   spot and cancel what you no longer use.
5. **📂 Transactions** — drill into a category → subcategory and edit inline.
6. **📥 Import** — upload a bank CSV and map its columns. Duplicate rows are
   skipped automatically, so re-importing the same file is safe.
7. **⚙️ Rules** — define rules like *description contains "BILLA" → Groceries*
   that auto-categorize transactions on import.

Use the sidebar to navigate between pages.

---

**Conventions**

- A **negative amount** is treated as an *expense*; a **positive amount** as *income*.
- Amounts are aggregated **per currency** so different currencies are never mixed.
- Everything runs locally on SQLite — no external APIs or network calls.
"""
)

if count == 0:
    st.info("No transactions yet. Head to the **Import** page to load a CSV file.")
