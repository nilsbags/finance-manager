# 💸 Finance Manager

A small, **local-first** personal spending tracker. Import bank-account CSV
files, categorize transactions, and view monthly spending summaries — all on
your own machine. **No external APIs, no network calls, no cloud.**

Built with Python, [Streamlit](https://streamlit.io/), SQLite, pandas and Plotly.

---

## Features

- **CSV import** — upload a CSV, map your columns (date, description, amount,
  account, currency), and store rows in SQLite. Re-importing the same file is
  safe: duplicates are detected via a hash of date + amount + description +
  account.
- **Transaction management** — searchable, filterable table with inline editing
  of **category** and **notes**.
- **Hierarchical categories** — a built-in taxonomy of top-level **categories**
  and **subcategories** (e.g. *Transport › Fuel*, *Food & Drink › Groceries*).
- **Category rules** — e.g. *description contains "BILLA" → Food & Drink ›
  Groceries*. A comprehensive **starter rule set** ships with the app and is
  seeded automatically, so common merchants (Shell, Uber, Amazon, Netflix, …)
  are categorized on import. Rules are re-runnable on demand.
- **Monthly subscriptions** — automatically detects recurring monthly charges
  (by cadence + consistent amounts, plus subscription-type categories), lists
  them with monthly/yearly cost in EUR, and highlights the biggest so you can
  cancel what you don't use.
- **Dashboard** — a quick overview with big **this-month** numbers (spendings,
  earnings, net, savings rate) each compared to last month, a month-over-month
  comparison chart, the spendings-vs-earnings trend, and category splits.
- **Spendings / Earnings** — each leads with a gradient area chart (spendings or
  earnings only), switchable between **This month / 3M / 6M / 1Y / YTD**, with
  account & currency filters, followed by breakdowns by category, by month and
  by merchant/source.
- **Private by design** — your data lives only in `data/finance.db` (gitignored).

---

## Setup

Requires **Python 3.12+** (the code uses modern syntax such as the `type`
statement from [PEP 695](https://peps.python.org/pep-0695/) and `X | None`
union types). Developed and tested against **Python 3.14**.

```bash
# 1. Clone and enter the project
cd finance-manager

# 2. Create and activate a virtual environment
python3.14 -m venv .venv         # or any python >= 3.12
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app/main.py
```

Streamlit opens the app in your browser (usually <http://localhost:8501>).

---

## Quick start

1. Open the **📥 Import** page and upload `sample_data/transactions.csv`
   (or your own bank export).
2. Confirm the column mapping — the app auto-detects common column names — and
   click **Import transactions**.
3. Open **⚙️ Rules** and add a rule, e.g. contains `BILLA` → `Groceries`,
   then **Apply rules to existing transactions**.
4. Explore the **📊 Dashboard** and edit individual rows under **📂 Transactions**.

---

## Categories & rules

Categories are organised as **category › subcategory** (the full taxonomy lives
in `app/categories.py` and is shown on the **Categories & Rules** page). On first
run the app seeds a large **starter rule set** that maps common merchants to a
category and subcategory automatically during import.

- **Drill down** on the **Transactions** page: click a category bar to expand it
  into subcategories, click a subcategory, and the editable table below narrows
  to exactly those transactions. A breadcrumb steps back up.
- Edit a transaction's category/subcategory inline on the **Transactions** page.
- Add your own rules, or re-load the starter rules, on the **Categories & Rules**
  page; use **Apply rules now** to re-categorize uncategorized transactions.
- Anything no rule matches stays **Uncategorized** until you tag it.

## Conventions

- **Negative amount = expense, positive amount = income.** The dashboard's
  "spending" figures sum the negative amounts (shown as positive).
- Amounts are aggregated **per currency** by default. A combined **"All → EUR"**
  option in every currency picker converts USD/AED/etc. into EUR using **manual
  exchange rates** (no external API) that you can edit inline under
  *💱 Conversion rates*.
- European number/date formats are supported via import options
  (comma decimal separator, day-first dates).

---

## Project structure

```
finance-manager/
├── README.md
├── requirements.txt
├── .gitignore
├── data/                      # SQLite database (created on first run, gitignored)
├── sample_data/
│   └── transactions.csv       # example data to try the app
└── app/
    ├── main.py                # Streamlit entry point + overview
    ├── database.py            # schema, migrations, transaction/rule CRUD
    ├── importer.py            # CSV parsing, column mapping, dedup hashing
    ├── categories.py          # taxonomy, colours, starter rule set
    ├── money.py               # manual FX rates + combined "All → EUR" view
    ├── subscriptions.py       # recurring monthly-charge detection
    ├── rules.py               # category rule engine (category + subcategory)
    ├── charts.py              # period switcher, gradient, sunburst/treemap helpers
    └── pages/
        ├── 1_Dashboard.py             # overview: KPIs + monthly comparison + sunbursts
        ├── 2_Spendings.py             # cumulative chart + category/subcategory treemap
        ├── 3_Earnings.py              # cumulative chart + category/subcategory treemap
        ├── 4_Monthly_Subscriptions.py # detected recurring subscriptions + savings
        ├── 5_Transactions.py          # drill-down explorer + editable table
        ├── 6_Import.py                # upload + map columns + import
        └── 7_Rules.py                 # categories & rules management hub
```

---

## Data & privacy

All transactions are stored in `data/finance.db` on your machine. That file is
listed in `.gitignore` and is **never** committed. To start fresh, simply delete
it — the schema is recreated automatically on the next run.
