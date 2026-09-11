"""
Database setup for the AI Financial News Intelligence Platform.

Sprint 1 scope: create a SQLite engine and provide a function to
create all tables defined on the shared `Base` metadata.
"""

from pathlib import Path

from sqlalchemy import Engine, create_engine

from src.database.models import Base

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
# We build the data directory path relative to this file's location
# (rather than relative to the current working directory) so the database
# always ends up in the same place, no matter where the script is run from.
#
# This file lives at: src/database/database.py
# parents[2] walks up: database.py -> database/ -> src/ -> project root
BASE_DIR: Path = Path(__file__).resolve().parents[2]
DATA_DIR: Path = BASE_DIR / "data"
DB_PATH: Path = DATA_DIR / "news.db"

# Ensure the data/ directory exists before SQLite tries to create the file.
# SQLite will create the .db file itself, but it will NOT create missing
# parent directories, so we have to do that ourselves.
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Engine setup
# ---------------------------------------------------------------------------
# The engine is the entry point SQLAlchemy uses to talk to the database.
# We build the SQLite URL from DB_PATH so it stays consistent with the
# path logic above (no hardcoded strings duplicating the location).
DATABASE_URL: str = f"sqlite:///{DB_PATH}"

# echo=False keeps console output clean; set to True temporarily if you
# ever need to debug the raw SQL SQLAlchemy is generating.
engine: Engine = create_engine(DATABASE_URL, echo=False)


def create_tables() -> None:
    """
    Create all tables defined on Base.metadata (currently just `news`).

    This is safe to call multiple times: create_all() only creates
    tables that don't already exist, it won't overwrite existing data.
    """
    Base.metadata.create_all(engine)
    print(f"Database initialized at: {DB_PATH}")


# ---------------------------------------------------------------------------
# Allow running this module directly:
#   python -m src.database.database
# to set up the database without needing any other code.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    create_tables()