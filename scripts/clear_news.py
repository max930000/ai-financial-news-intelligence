"""One-off utility: clear all rows from the news table.

Deletes all data in `news` but keeps the table schema and the database
file itself intact (equivalent to SQL DELETE, not DROP TABLE).

Usage:
    python -m scripts.clear_news
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.database import engine
from src.database.models import News


def clear_news() -> None:
    """Delete all rows from the news table and report how many were removed."""
    with Session(engine) as session:
        count_before = session.scalar(select(func.count()).select_from(News))
        print(f"目前新聞筆數：{count_before}")

        session.query(News).delete()
        session.commit()

        print(f"已清除 {count_before} 筆新聞")


if __name__ == "__main__":
    clear_news()