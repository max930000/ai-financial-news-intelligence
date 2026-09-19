"""Storage for confirmed article inputs (see models.Article)."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import Article


class ArticleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, article_id: int) -> Article | None:
        return self.session.get(Article, article_id)

    def save_confirmed(
        self,
        *,
        url: str | None,
        title: str,
        source: str | None,
        published_at: datetime | None,
        fetched_at: datetime | None,
        body: str,
        content_hash: str,
        input_origin: str,
        fetch_failure_reason: str | None,
    ) -> tuple[Article, bool]:
        """
        Store a confirmed input. Returns (article, created).

        Confirming the same url + title + body again returns the existing row
        instead of adding a duplicate, so repeated clicks (and later, repeated
        analysis) never multiply work on identical input.
        """
        statement = select(Article).where(
            Article.url.is_(None) if url is None else Article.url == url,
            Article.title == title,
            Article.content_hash == content_hash,
        )
        existing = self.session.execute(statement).scalars().first()
        if existing is not None:
            return existing, False

        article = Article(
            url=url,
            title=title,
            source=source,
            published_at=_naive_utc(published_at),
            fetched_at=_naive_utc(fetched_at),
            body=body,
            content_hash=content_hash,
            input_origin=input_origin,
            fetch_failure_reason=fetch_failure_reason,
        )
        self.session.add(article)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return article, True


def _naive_utc(value: datetime | None) -> datetime | None:
    """SQLite drops time zones; store UTC wall-clock like the rest of the app."""
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)
