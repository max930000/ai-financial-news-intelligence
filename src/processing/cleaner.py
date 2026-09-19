"""Prepare plain-text articles for paragraph-level evidence citations.

Never split on punctuation, summarize, truncate, or strip HTML here. The caller
supplies extracted plain text. Preserve the exact input separately from the
paragraph view so evidence can always be checked against the original article.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Literal

ParagraphMode = Literal["blank_lines", "line_breaks"]
PREPARATION_VERSION = "paragraphs-v1"


@dataclass(frozen=True)
class Paragraph:
    id: str
    text: str


@dataclass(frozen=True)
class PreparedArticle:
    title: str
    original_text: str
    document_id: str
    paragraph_mode: ParagraphMode
    paragraphs: tuple[Paragraph, ...]
    preparation_version: str = PREPARATION_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def prepare_article(
    title: str,
    content: str,
    paragraph_mode: ParagraphMode = "blank_lines",
) -> PreparedArticle:
    """Number paragraphs without treating wrapped lines as sentence boundaries.

    blank_lines: blank lines delimit paragraphs; single newlines stay inside them.
    line_breaks: every newline delimits a paragraph, for upstream paragraph joins.
    Neither mode infers missing boundaries. An unbroken body is one paragraph.
    """
    if not title.strip():
        raise ValueError("請提供新聞標題。")
    if not content.strip():
        raise ValueError("請提供完整內文。")
    if paragraph_mode not in ("blank_lines", "line_breaks"):
        raise ValueError("不支援的分段方式。")

    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    separator = r"\n[^\S\n]*\n(?:[^\S\n]*\n)*" if paragraph_mode == "blank_lines" else r"\n+"
    parts = [part.strip() for part in re.split(separator, normalized) if part.strip()]
    paragraphs = tuple(Paragraph(f"P{index:03d}", part) for index, part in enumerate(parts, 1))
    fingerprint = json.dumps(
        [PREPARATION_VERSION, title, content, paragraph_mode], ensure_ascii=False
    ).encode("utf-8")
    return PreparedArticle(
        title=title,
        original_text=content,
        document_id=hashlib.sha256(fingerprint).hexdigest(),
        paragraph_mode=paragraph_mode,
        paragraphs=paragraphs,
    )


def resolve_evidence(
    article: PreparedArticle, document_id: str, paragraph_ids: list[str]
) -> list[Paragraph]:
    """Resolve citations only against the exact prepared version.

    Valid IDs establish citation existence, not semantic support for a claim.
    Empty evidence is allowed (e.g. insufficient information); unknown or stale
    citations reject the entire result instead of silently dropping evidence.
    """
    if document_id != article.document_id:
        raise ValueError("文章版本不符，請使用本次處理的 document_id。")
    lookup = {paragraph.id: paragraph for paragraph in article.paragraphs}
    if any(paragraph_id not in lookup for paragraph_id in paragraph_ids):
        raise ValueError("引用包含不存在的段落編號。")
    return [lookup[paragraph_id] for paragraph_id in dict.fromkeys(paragraph_ids)]
