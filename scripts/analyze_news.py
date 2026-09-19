"""Orchestration script: run AI sentiment + topic + summary analysis on news.

This script does NOT implement any model logic itself. It only:
  1. fetches news rows missing at least one AI field (sentiment/category/summary)
  2. calls src.ai.sentiment.analyze_sentiment() for sentiment (if missing)
  3. calls src.ai.topic.classify_topic() for topic classification (if missing)
  4. calls src.ai.summarizer.summarize_news() for a short summary (if missing)
  5. writes the results back onto the News row

Rows are matched per-field, not per-row: if a news item already has
sentiment/category from an earlier run but is missing `summary`, this
script only fills in the summary and leaves sentiment/category untouched.

Interfaces this script relies on (confirmed against the actual project code):
  - src.ai.sentiment.analyze_sentiment(text: str) -> dict
      returns {"label": "positive"|"negative"|"neutral", "score": float}
      raises ValueError if text is empty
  - src.ai.topic.classify_topic(text: str) -> dict
      returns {"category": str | None, "score": float}
  - src.ai.summarizer.summarize_news(text: str) -> str
      returns "" if text is empty
  - src.database.database.engine (SQLAlchemy Engine)
  - src.database.models.News has: id, title, description, content,
      sentiment, sentiment_score, category, summary, ai_model, analyzed_at
"""

import sys
from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.ai.analyzer import analyze_text
from src.database.database import engine
from src.database.models import News

# Windows consoles often default to a legacy codepage (e.g. cp950) that can't
# encode every character our summaries may contain (e.g. em dashes, smart
# quotes). Without this, print() can raise UnicodeEncodeError, which gets
# caught by the per-article try/except below and misreported as an analysis
# failure even though the DB write already succeeded.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AI_MODEL_LABEL = "finbert+bart-large-mnli+distilbart-cnn-12-6"

def _get_pending_news(session) -> list[News]:
    """Fetch news rows missing sentiment, category, and/or summary.

    Using OR (not just `analyzed_at IS NULL`) so rows already analyzed in an
    earlier sprint, but missing a field added later (e.g. summary), get
    picked up and backfilled instead of being skipped forever.
    """
    return (
        session.query(News)
        .filter(
            or_(
                News.sentiment.is_(None),
                News.category.is_(None),
                News.summary.is_(None),
            )
        )
        .all()
    )


def analyze_single_news(news: News) -> None:
    result = analyze_text(
        title=news.title,
        description=news.description,
        content=news.content,
        language=news.language,
        run_sentiment=news.sentiment is None,
        run_topic=news.category is None,
        run_summary=news.summary is None,
    )

    if news.sentiment is None:
        news.sentiment = result["sentiment"]
        news.sentiment_score = result["sentiment_score"]

    if news.category is None:
        news.category = result["category"]

    if news.summary is None:
        news.summary = result["summary"]

    news.ai_model = AI_MODEL_LABEL
    news.analyzed_at = datetime.now(timezone.utc)
    
def run_analysis() -> None:
    """Analyze all unanalyzed news rows, committing after each successful update.

    A failure on a single article is logged and skipped so the whole batch
    is never aborted.
    """
    with Session(engine) as session:
        news_list = _get_pending_news(session)
        print(f"Found {len(news_list)} news item(s) with missing AI fields.")

        for news in news_list:
            try:
                analyze_single_news(news)
                session.commit()
                summary_preview = (news.summary or "")[:60]
                print(
                    f"[OK] id={news.id} sentiment={news.sentiment} "
                    f"({news.sentiment_score}) category={news.category} "
                    f"summary={summary_preview!r}"
                )
            except Exception as exc:
                session.rollback()
                print(f"[ERROR] id={news.id} failed: {exc}")
                continue


if __name__ == "__main__":
    run_analysis()