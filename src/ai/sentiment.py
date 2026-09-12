from functools import lru_cache

from transformers import pipeline


MODEL_NAME = "ProsusAI/finbert"


@lru_cache(maxsize=1)
def get_sentiment_model():
    """
    Load FinBERT once and reuse it.
    """
    return pipeline(
        "text-classification",
        model=MODEL_NAME,
        tokenizer=MODEL_NAME,
        device=-1,  # CPU
    )


def analyze_sentiment(text: str) -> dict:
    """
    Analyze financial-news sentiment.

    Returns:
        {
            "label": "positive" | "negative" | "neutral",
            "score": 0.0 ~ 1.0
        }
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty.")

    classifier = get_sentiment_model()

    result = classifier(
        text.strip(),
        truncation=True,
        max_length=512,
    )[0]

    return {
        "label": result["label"].lower(),
        "score": round(float(result["score"]), 4),
    }