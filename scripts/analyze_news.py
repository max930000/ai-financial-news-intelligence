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

from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.ai.sentiment import analyze_sentiment
from src.ai.summarizer import is_title_description_consistent, summarize_news
from src.ai.topic import classify_topic
from src.database.database import engine
from src.database.models import News

AI_MODEL_LABEL = "finbert+bart-large-mnli+distilbart-cnn-12-6"


def _build_text(news: News) -> str:
    """Combine title, description, and content into one text blob for AI analysis."""
    parts = [news.title, news.description, news.content]
    return " ".join(p for p in parts if p)


def _build_summary(news: News) -> str | None:
    """Summarize a news row from its `description` only, with a data-quality guard.

    Summary input is `description` (not title/content): RSS descriptions are
    usually already a compressed blurb, so the summarizer just tightens it
    further. Mixing in the title risks the model picking the wrong focus
    when title and description describe different stories (a known issue
    with some RSS sources).

    Returns None (leaving `news.summary` empty) when:
      - description is missing/blank
      - title and description don't share any significant words, which
        usually means the RSS entry itself is mismatched — summarizing it
        would just be a confident-sounding summary of the wrong story.
    """
    if not news.description or not news.description.strip():
        print(f"[SKIP-SUMMARY] id={news.id} no description, summary left empty")
        return None

    if not is_title_description_consistent(news.title, news.description):
        print(f"[SKIP-SUMMARY] id={news.id} title/description mismatch, summary left empty")
        return None

    return summarize_news(news.description)


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
    """Fill in whichever of sentiment/category/summary is missing on one News row.

    Fields that are already populated are left untouched, so re-running this
    script never redoes work that was already done in a previous run.
    """
    text = _build_text(news)  # raises nothing itself; may be empty
    
    if news.sentiment is None:
        sentiment_result = analyze_sentiment(text)  # raises ValueError if text is empty
        news.sentiment = sentiment_result.get("label")
        news.sentiment_score = sentiment_result.get("score")

    if news.category is None:
        topic_result = classify_topic(text)
        news.category = topic_result.get("category")

    if news.summary is None:
        news.summary = _build_summary(news)

    

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