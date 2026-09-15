"""Text summarization for financial news articles."""

import re
from functools import lru_cache

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

MODEL_NAME = "sshleifer/distilbart-cnn-12-6"

# Keep the input bounded so CPU inference stays fast; summarization models
# don't need the full article body to produce a good short summary.
MAX_INPUT_CHARS = 3000

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "by", "at", "as", "it", "its", "this",
    "that", "from", "be", "has", "have", "had", "will", "would", "could",
    "after", "over", "into", "about", "says", "said", "new", "will",
}


def _significant_words(text: str) -> set[str]:
    """Lowercase, strip punctuation, and drop stopwords/very short tokens."""
    words = re.findall(r"[a-zA-Z']+", text.lower())
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def is_title_description_consistent(title: str | None, description: str | None, min_overlap: int = 1) -> bool:
    """Cheap heuristic check for whether a title and description share topic words.

    Intentionally simple (word-overlap, no embeddings/NLP model): meant only
    to catch obviously mismatched RSS entries (e.g. title about story A,
    description about unrelated story B), not to do real semantic matching.
    """
    if not title or not description:
        return False

    title_words = _significant_words(title)
    desc_words = _significant_words(description)

    if not title_words or not desc_words:
        return False

    return len(title_words & desc_words) >= min_overlap


@lru_cache(maxsize=1)
def _get_model_and_tokenizer():
    """Load and cache the summarization model + tokenizer (CPU only).

    Loaded directly via AutoModelForSeq2SeqLM/AutoTokenizer instead of
    pipeline("summarization", ...): transformers v5 removed the
    "summarization" pipeline task alias, so calling pipeline() with that
    task name raises `KeyError: Unknown task summarization`. Loading the
    model and tokenizer directly sidesteps that alias entirely and works
    the same way regardless of transformers version.
    """
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
    model.to("cpu")
    model.eval()
    return model, tokenizer


def summarize_news(text: str) -> str:
    """Generate a short summary suitable for a dashboard card.

    Args:
        text: Combined title/description/content of a news article.

    Returns:
        str: A short summary, or "" if the input is empty/whitespace-only.
    """
    if not text or not text.strip():
        return ""

    cleaned = text.strip()[:MAX_INPUT_CHARS]
    model, tokenizer = _get_model_and_tokenizer()

    inputs = tokenizer(
        cleaned,
        return_tensors="pt",
        truncation=True,
        max_length=1024,
    )

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_length=60,
            min_length=15,
            num_beams=4,
            do_sample=False,
        )

    summary = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    return summary.strip()