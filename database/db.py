"""SQLite helpers for Spendly.

This module owns every database interaction. Route functions in
``app.py`` must not run SQL inline — they call these helpers instead.

Public API
----------
- ``get_db()``  — return a SQLite connection with FK enforcement on
  and ``row_factory`` set to ``sqlite3.Row`` for dict-like access.
- ``init_db()`` — create the ``users`` and ``expenses`` tables if
  they do not already exist.
- ``seed_db()`` — populate the demo user and 8 sample expenses for
  local development. Idempotent: a second call is a no-op.
"""

import os
import sqlite3

from werkzeug.security import generate_password_hash

# Database file lives at the project root, next to ``app.py``.
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "expense_tracker.db"
)


# ------------------------------------------------------------------ #
# Connection helper                                                    #
# ------------------------------------------------------------------ #

def get_db() -> sqlite3.Connection:
    """Return a SQLite connection wired up for the Spendly schema.

    - ``row_factory`` is set to ``sqlite3.Row`` so callers can use
      column-name access (``row["email"]``) alongside tuple indexing.
    - ``PRAGMA foreign_keys = ON`` runs on every connection because
      SQLite disables FK enforcement by default per-connection.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ------------------------------------------------------------------ #
# Schema                                                               #
# ------------------------------------------------------------------ #

def init_db() -> None:
    """Create the Spendly tables if they do not exist.

    Tables
    ------
    - ``users``    — account credentials and profile fields.
    - ``expenses`` — individual spending records, FK-linked to a user.

    All DDL uses ``IF NOT EXISTS`` so re-running ``init_db()`` against
    an existing database is a no-op.
    """
    conn = get_db()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                email         TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                amount      REAL    NOT NULL,
                category    TEXT    NOT NULL,
                date        TEXT    NOT NULL,
                description TEXT,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_expenses_user ON expenses(user_id);
            CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
            """
        )
        conn.commit()
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# Seed data                                                            #
# ------------------------------------------------------------------ #

# Fixed category list from spec §10. Used to keep the seed exhaustive
# (one expense per category) and to give callers a single source of
# truth until a categories table is introduced in a later step.
CATEGORIES = (
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
)

# Demo credentials. Email is the seed user_id=1's stable identity; the
# plain password is documented in spec §5.B and only used to derive
# the Werkzeug hash stored in the row.
DEMO_EMAIL = "demo@spendly.com"
DEMO_NAME = "Demo User"
DEMO_PASSWORD = "demo123"

# Eight sample expenses: every category from CATEGORIES appears at
# least once, with an extra Food row to round out the current month.
# Amounts are in INR; ``date`` is ISO-8601 (YYYY-MM-DD) so lexical
# sorts match chronological order.
SAMPLE_EXPENSES = (
    (250.00,  "Food",          "Lunch at the office canteen",      "2026-07-10"),
    ( 85.50,  "Transport",     "Auto rickshaw to client meeting", "2026-07-11"),
    (612.00,  "Bills",         "Weekly groceries run",            "2026-07-12"),
    (1450.00, "Bills",         "Electricity bill",                "2026-07-05"),
    (380.00,  "Health",        "Pharmacy — vitamins and first-aid", "2026-07-08"),
    (350.00,  "Entertainment", "Movie tickets",                   "2026-07-09"),
    (999.00,  "Shopping",      "T-shirt from local market",       "2026-07-13"),
    (120.00,  "Other",         "Miscellaneous cash spend",        "2026-07-14"),
)


def seed_db() -> None:
    """Insert the demo user and 8 sample expenses.

    Idempotent: returns early if the ``users`` table already contains
    any row. Re-running is a no-op, so it is safe to call on every
    app boot.
    """
    conn = get_db()
    try:
        # --- Duplicate-prevention gate -------------------------------
        # Spec §5.C requires this check before any inserts.
        if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone() is not None:
            conn.commit()
            return

        # --- Demo user -----------------------------------------------
        # INSERT OR IGNORE on the unique email column is a secondary
        # safeguard in case the gate above is bypassed (e.g. the
        # users table was populated by a different process).
        conn.execute(
            """
            INSERT OR IGNORE INTO users (id, name, email, password_hash)
            VALUES (?, ?, ?, ?)
            """,
            (
                1,
                DEMO_NAME,
                DEMO_EMAIL,
                generate_password_hash(DEMO_PASSWORD),
            ),
        )

        # --- Sample expenses -----------------------------------------
        # All linked to user_id=1 (the demo user). Plain INSERT (not
        # INSERT OR IGNORE) — the gate above guarantees a clean slate.
        conn.executemany(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            ((1, *row) for row in SAMPLE_EXPENSES),
        )

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    # Allow ``python database/db.py`` to set up a local dev database
    # in one step.
    init_db()
    seed_db()
    print(f"Initialized and seeded {DB_PATH}")
