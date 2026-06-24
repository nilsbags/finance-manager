"""SQLite persistence layer for the finance manager.

This module owns the database schema and all read/write helpers for
transactions and category rules. Connections are opened per-operation
through a context manager, which keeps things simple and safe under
Streamlit's re-run / multi-thread execution model.
"""

import os
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager

import pandas as pd

import categories

# Database file lives in the project's ``data/`` directory (gitignored).
# ``FINANCE_DB`` can override the location (useful for tests / multiple profiles).
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(_THIS_DIR), "data")
DB_PATH = os.environ.get("FINANCE_DB", os.path.join(DATA_DIR, "finance.db"))

# Default bucket for transactions that no rule has classified yet.
UNCATEGORIZED = categories.UNCATEGORIZED


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection with row access by column name.

    The connection is committed on success and always closed afterwards.
    """
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables / run migrations and seed starter rules. Idempotent."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT    NOT NULL,          -- ISO date: YYYY-MM-DD
                description TEXT    NOT NULL,
                amount      REAL    NOT NULL,          -- negative = expense
                account     TEXT    NOT NULL,
                currency    TEXT    NOT NULL DEFAULT 'EUR',
                category    TEXT    NOT NULL DEFAULT 'Uncategorized',
                subcategory TEXT    NOT NULL DEFAULT '',
                notes       TEXT    NOT NULL DEFAULT '',
                hash        TEXT    NOT NULL UNIQUE,    -- dedup fingerprint
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_tx_date     ON transactions(date);
            CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category);
            CREATE INDEX IF NOT EXISTS idx_tx_account  ON transactions(account);

            CREATE TABLE IF NOT EXISTS rules (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern     TEXT NOT NULL,             -- case-insensitive substring
                category    TEXT NOT NULL,
                subcategory TEXT NOT NULL DEFAULT '',
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS meta (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )

        # --- Lightweight migrations for databases created before subcategory.
        _ensure_column(conn, "transactions", "subcategory", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "rules", "subcategory", "TEXT NOT NULL DEFAULT ''")

    seed_starter_rules()
    _autocategorize_existing_once()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    """Add ``column`` to ``table`` if it is not already present."""
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _get_meta(key: str) -> str | None:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def _set_meta(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


# Public aliases so other modules can persist small key/value settings.
def get_meta(key: str) -> str | None:
    """Return a stored setting value, or ``None`` if unset."""
    return _get_meta(key)


def set_meta(key: str, value: str) -> None:
    """Persist a small key/value setting."""
    _set_meta(key, value)


def seed_starter_rules() -> int:
    """Seed the built-in starter rules exactly once (first run).

    Guarded by a meta flag so that a user who later deletes rules does not get
    them silently re-added. Returns the number of rules inserted.
    """
    if _get_meta("starter_rules_seeded") == "1":
        return 0
    inserted = add_rules(categories.STARTER_RULES)
    _set_meta("starter_rules_seeded", "1")
    return inserted


def reload_starter_rules() -> int:
    """Add any starter rules whose pattern is not already present. Returns count."""
    existing = {row["pattern"].lower() for row in fetch_rules()}
    missing = [r for r in categories.STARTER_RULES if r[0].lower() not in existing]
    return add_rules(missing)


def _autocategorize_existing_once() -> int:
    """One-time pass: categorize already-imported uncategorized transactions.

    Earlier versions only applied rules at import time, so databases created
    before the starter-rule set existed are full of uncategorized rows. This
    runs the rules over them exactly once (guarded by a meta flag) and only
    touches rows still in the default bucket, never manual categorizations.
    """
    if _get_meta("existing_autocat_v1") == "1":
        return 0
    # Lazy import avoids a circular dependency (rules imports database).
    import rules

    changed = rules.apply_rules_to_existing(only_uncategorized=True)
    _set_meta("existing_autocat_v1", "1")
    return changed


# --------------------------------------------------------------------------- #
# Transactions
# --------------------------------------------------------------------------- #
def insert_transactions(rows: Iterable[dict]) -> int:
    """Insert transaction rows, ignoring duplicates by ``hash``.

    Each row must contain: date, description, amount, account, currency,
    category, notes, hash. Returns the number of rows actually inserted
    (duplicates are silently skipped thanks to the UNIQUE constraint).
    """
    rows = list(rows)
    if not rows:
        return 0

    # Default subcategory to empty when callers omit it.
    for row in rows:
        row.setdefault("subcategory", "")

    with get_connection() as conn:
        before = conn.total_changes
        conn.executemany(
            """
            INSERT OR IGNORE INTO transactions
                (date, description, amount, account, currency, category, subcategory, notes, hash)
            VALUES
                (:date, :description, :amount, :account, :currency, :category, :subcategory, :notes, :hash)
            """,
            rows,
        )
        return conn.total_changes - before


def fetch_transactions(
    *,
    search: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    accounts: list[str] | None = None,
    categories: list[str] | None = None,
    subcategories: list[str] | None = None,
) -> pd.DataFrame:
    """Return transactions as a DataFrame, filtered by the given criteria."""
    clauses: list[str] = []
    params: list[object] = []

    if search:
        clauses.append("(description LIKE ? OR notes LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if start_date:
        clauses.append("date >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("date <= ?")
        params.append(end_date)
    if accounts:
        clauses.append(f"account IN ({','.join('?' * len(accounts))})")
        params.extend(accounts)
    if categories:
        clauses.append(f"category IN ({','.join('?' * len(categories))})")
        params.extend(categories)
    if subcategories:
        clauses.append(f"subcategory IN ({','.join('?' * len(subcategories))})")
        params.extend(subcategories)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = (
        "SELECT id, date, description, amount, account, currency, "
        "category, subcategory, notes "
        f"FROM transactions {where} ORDER BY date DESC, id DESC"
    )

    with get_connection() as conn:
        df = pd.read_sql_query(sql, conn, params=params)

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def update_transaction(tx_id: int, *, category: str, subcategory: str, notes: str) -> None:
    """Update the editable fields (category, subcategory, notes) of a transaction."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE transactions SET category = ?, subcategory = ?, notes = ? WHERE id = ?",
            (category, subcategory, notes, tx_id),
        )


def set_category(tx_id: int, category: str, subcategory: str = "") -> None:
    """Set category (and subcategory) of a transaction (used by the rules engine)."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE transactions SET category = ?, subcategory = ? WHERE id = ?",
            (category, subcategory, tx_id),
        )


def distinct_values(column: str) -> list[str]:
    """Return sorted distinct non-empty values for a whitelisted column."""
    if column not in {"account", "category", "subcategory", "currency"}:
        raise ValueError(f"Column not allowed: {column}")
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT DISTINCT {column} FROM transactions "
            f"WHERE {column} != '' ORDER BY {column}"
        ).fetchall()
    return [r[0] for r in rows]


def count_transactions() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]


def delete_all_transactions() -> int:
    """Delete every transaction. Returns the number of rows removed."""
    with get_connection() as conn:
        before = conn.total_changes
        conn.execute("DELETE FROM transactions")
        return conn.total_changes - before


# --------------------------------------------------------------------------- #
# Rules
# --------------------------------------------------------------------------- #
def add_rule(pattern: str, category: str, subcategory: str = "") -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO rules (pattern, category, subcategory) VALUES (?, ?, ?)",
            (pattern.strip(), category.strip(), subcategory.strip()),
        )


def add_rules(rules: Iterable[tuple[str, str, str]]) -> int:
    """Bulk-insert ``(pattern, category, subcategory)`` rules. Returns count."""
    rules = list(rules)
    if not rules:
        return 0
    payload = [(p.strip(), c.strip(), s.strip()) for p, c, s in rules]
    with get_connection() as conn:
        before = conn.total_changes
        conn.executemany(
            "INSERT INTO rules (pattern, category, subcategory) VALUES (?, ?, ?)",
            payload,
        )
        return conn.total_changes - before


def delete_rule(rule_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))


def delete_all_rules() -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM rules")


def count_rules() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0]


def fetch_rules() -> list[sqlite3.Row]:
    """Return rules ordered so the oldest (most specific by intent) win first."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, pattern, category, subcategory FROM rules ORDER BY id ASC"
        ).fetchall()
