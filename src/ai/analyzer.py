"""Reusable AI analyzer for financial news."""

from src.ai.sentiment import analyze_sentiment
from src.ai.summarizer import (
    is_title_description_consistent,
    summarize_news,
)
from src.ai.topic import classify_topic


def _build_text(
    title: str,
    description: str | None = None,
    content: str | None = None,
) -> str:
    parts = [title, description, content]

    return " ".join(
        part.strip()
        for part in parts
        if part and part.strip()
    )


def _build_summary(
    title: str,
    description: str | None = None,
) -> str | None:
    if not description or not description.strip():
        return None

    if not is_title_description_consistent(title, description):
        return None

    return summarize_news(description)


def analyze_text(
    title: str,
    description: str | None = None,
    content: str | None = None,
    language: str | None = None,
    *,
    run_sentiment: bool = True,
    run_topic: bool = True,
    run_summary: bool = True,
) -> dict:
    """Run selected AI tasks on financial news."""

    text = _build_text(title, description, content)

    if not text:
        raise ValueError("No text available for analysis.")

    result = {
        "sentiment": None,
        "sentiment_score": None,
        "category": None,
        "summary": None,
    }

    if run_sentiment:
        sentiment_result = analyze_sentiment(text)
        result["sentiment"] = sentiment_result.get("label")
        result["sentiment_score"] = sentiment_result.get("score")

    if run_topic:
        topic_result = classify_topic(text)
        result["category"] = topic_result.get("category")

    if run_summary:
        if language == "en":
            result["summary"] = _build_summary(title, description)
        else:
            result["summary"] = None

    return result