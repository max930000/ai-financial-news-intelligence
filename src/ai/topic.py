"""
Pydantic response models for the FastAPI layer (Sprint 3 Step 2).

These are pure output schemas: they describe what the API returns,
and are built directly from the existing `News` ORM model via
`from_attributes` — no new DB concepts introduced here.
"""

"""Zero-shot topic classification for financial news articles."""

from functools import lru_cache

from transformers import pipeline

CATEGORIES = [
    "Markets",
    "Economy",
    "Companies",
    "Banking",
    "Technology",
    "Cryptocurrency",
    "Energy",
    "Politics & Regulation",
]

MODEL_NAME = "facebook/bart-large-mnli"


@lru_cache(maxsize=1)
def _get_classifier():
    """Load and cache the zero-shot-classification pipeline (CPU only)."""
    return pipeline("zero-shot-classification", model=MODEL_NAME, device=-1)


def classify_topic(text: str) -> dict:
    """Classify a news text into one of the predefined financial categories.

    Args:
        text: Combined title/description/content of a news article.

    Returns:
        dict: {"category": str | None, "score": float}
    """
    if not text or not text.strip():
        return {"category": None, "score": 0.0}

    classifier = _get_classifier()
    result = classifier(text, candidate_labels=CATEGORIES, multi_label=False)

    return {
        "category": result["labels"][0],
        "score": round(float(result["scores"][0]), 4),
    }