"""One-off migration: add a `summary` column to the existing news table.

Safe to run multiple times: it checks PRAGMA table_info first and only runs
ALTER TABLE if the column is missing. Never touches existing rows/data.

Usage:
    python -m scripts.migrate_add_summary
"""

import sqlite3

from src.database.database import DB_PATH

TABLE_NAME = "news"
COLUMN_NAME = "summary"


def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """Check whether `column` already exists on `table`."""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def migrate() -> None:
    """Add `summary TEXT` to the news table if it doesn't already exist."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()

        if column_exists(cursor, TABLE_NAME, COLUMN_NAME):
            print(f"Column '{COLUMN_NAME}' already exists on '{TABLE_NAME}'. Nothing to do.")
            return

        cursor.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {COLUMN_NAME} TEXT")
        conn.commit()
        print(f"Added '{COLUMN_NAME} TEXT' column to '{TABLE_NAME}' table.")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()