"""Text helpers shared by the article-input flow (fetched or pasted)."""

import hashlib
import re

# Zero-width characters and BOM carry no meaning in news text but break
# exact-match comparisons and later evidence highlighting.
_INVISIBLE = re.compile("[​‌‍⁠﻿]")
_BLANK_LINES = re.compile(r"\n{3,}")


def normalize_body(text: str) -> str:
    """
    Normalize article body text without changing its wording.

    Paragraphs are separated by one blank line. The function is idempotent, so
    text that was already normalized (for example a fetched body that the user
    did not edit) hashes to the same value after a round trip.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    text = _INVISIBLE.sub("", text)
    lines = [line.strip() for line in text.split("\n")]
    return _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def collapse_inline_whitespace(text: str) -> str:
    """Turn any whitespace run inside one paragraph into a single space."""
    text = text.replace("\xa0", " ")
    text = _INVISIBLE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def count_paragraphs(body: str) -> int:
    return len([p for p in body.split("\n\n") if p.strip()])


def count_chars(body: str) -> int:
    """Length in non-whitespace characters, the unit used by all body limits."""
    return len(re.sub(r"\s", "", body))


def content_hash(body: str) -> str:
    """SHA-256 of the normalized body; identifies one version of the text."""
    return hashlib.sha256(normalize_body(body).encode("utf-8")).hexdigest()
