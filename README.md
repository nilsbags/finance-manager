# 💸 Finance Manager

A small, **local-first** personal spending tracker. Import bank-account CSV
files, categorize transactions, and view monthly spending summaries — all on
your own machine. **No external APIs, no network calls, no cloud.**

Built with [Next.js](https://nextjs.org/) (App Router, TypeScript), SQLite
(better-sqlite3), Tailwind CSS and [ECharts](https://echarts.apache.org/).

---

## Features

- **CSV import** — upload a CSV, map your columns (date, description, amount,
  account, currency), and store rows in SQLite. Re-importing the same file is
  safe: duplicates are detected via a hash of date + amount + description +
  account.
- **Balance-based income recovery** — if your export has a running **balance**
  column, the importer can recover money that the statement only reflects as a
  balance jump (incoming transfers, interest, fees) rather than as its own line
  item. The net unlisted movement is reconstructed **per account and month** and
  added as a synthetic entry — positive months as income, negative as an outflow.
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
  earnings, net, savings rate) each compared to last month, the **current
  balance** shown in EUR/USD/AED, a month-over-month comparison chart, the
  spendings-vs-earnings trend, and category splits.
- **Spendings / Earnings** — each leads with a gradient area chart (spendings or
  earnings only), switchable between **This month / 3M / 6M / 1Y / YTD**, with
  account & currency filters, followed by breakdowns by category, by month and
  by merchant/source.
- **Dark mode by default** — toggle to light mode from the sidebar; the choice
  is remembered locally.
- **Private by design** — your data lives only in `data/finance.db` (gitignored).

---

## Setup

Requires **Node.js 20+**.

```bash
# 1. Clone and enter the project
cd finance-manager

# 2. Install dependencies
npm install

# 3. Run the dev server (opens on the Dashboard by default)
npm run dev
```

Open <http://localhost:3000> in your browser. For a production build:

```bash
npm run build && npm start
```

The SQLite database is created automatically at `data/finance.db` on first
run; set the `FINANCE_DB` environment variable to use a different file
(useful for tests / multiple profiles).

> **Migrating from the Python/Streamlit version?** Nothing to do — the schema
> and dedup hashes are unchanged, so the app picks up your existing
> `data/finance.db` (transactions, rules, balances, FX rates) as-is.

---

## Quick start

1. Open the **📥 Import** page and upload `sample_data/transactions.csv`
   (or your own bank export).
2. Confirm the column mapping — the app auto-detects common column names — and
   click **Import transactions**.
3. Open **⚙️ Rules** and add a rule, e.g. contains `BILLA` → `Groceries`,
   then **Apply rules now**.
4. Explore the **📊 Dashboard** and edit individual rows under **📂 Transactions**.

---

## Categories & rules

Categories are organised as **category › subcategory** (the full taxonomy lives
in `src/lib/categories.ts` and is shown on the **Categories & Rules** page). On
first run the app seeds a large **starter rule set** that maps common merchants
to a category and subcategory automatically during import.

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
├── package.json
├── next.config.ts
├── .gitignore
├── data/                      # SQLite database (created on first run, gitignored)
├── sample_data/
│   └── transactions.csv       # example data to try the app
└── src/
    ├── lib/                   # framework-free core logic
    │   ├── db.ts              # schema, migrations, transaction/rule CRUD (server-only)
    │   ├── categories.ts      # taxonomy, colours, starter rule set
    │   ├── rules.ts           # category rule engine (category + subcategory)
    │   ├── csv.ts             # CSV value parsing + column auto-detection
    │   ├── importer.ts        # row normalisation, dedup hashing, balance recovery
    │   ├── money.ts           # manual FX rates + combined "All → EUR" views
    │   ├── subscriptions.ts   # recurring monthly-charge detection
    │   ├── analytics.ts       # period ranges, time-series bucketing, groupings
    │   └── format.ts          # number formatting + shared colours
    ├── components/
    │   ├── charts/            # ECharts wrappers (gradient area, sunburst, treemap, bars)
    │   ├── OverviewSection.tsx# shared period/account/currency controls + chart
    │   ├── FlowPage.tsx       # the shared Spendings/Earnings page body
    │   ├── RatesEditor.tsx    # manual FX-rate editor
    │   ├── Sidebar.tsx        # navigation
    │   ├── useFinanceData.ts  # client data hook (transactions + rates)
    │   └── ui.tsx             # small UI kit (cards, metrics, inputs, tabs, …)
    └── app/
        ├── page.tsx           # 📊 Dashboard (KPIs, comparison, sunbursts)
        ├── spendings/         # 🛒 cumulative chart + category/subcategory treemap
        ├── earnings/          # 💰 cumulative chart + category/subcategory treemap
        ├── subscriptions/     # 🔁 detected recurring subscriptions + savings
        ├── transactions/      # 📂 drill-down explorer + editable table
        ├── import/            # 📥 upload + map columns + import
        ├── rules/             # ⚙️ categories & rules management hub
        └── api/               # transactions, import, rules, rates, balances
```

---

## Data & privacy

All transactions are stored in `data/finance.db` on your machine. That file is
listed in `.gitignore` and is **never** committed. To start fresh, simply delete
it — the schema is recreated automatically on the next run.
