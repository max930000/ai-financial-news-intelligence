"""Shared data structures for the "新聞數字放大鏡" feature.

Two boundaries meet here:
  Article        -- yan's full-text extraction module produces this
  AnalysisResult -- hw453's AI analysis function produces this

Both sides import from this file instead of each defining their own shape,
so the two modules can be built in parallel and still connect on day one.
See docs/number-extraction-plan.md for the task breakdown and timeline.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Sentence(BaseModel):
    sentence_id: str
    text: str


class Article(BaseModel):
    """Output of yan's "url -> full text" extraction module."""

    url: str
    title: str
    published_at: datetime | None
    fetched_at: datetime
    content: str                  # 正文全文
    sentences: list[Sentence]     # 句子切分 + ID,證據句用 sentence_id 指回這裡


class NumberFact(BaseModel):
    """One extracted number. An article can yield zero, one, or several of
    these — don't pick "the one that matters" and drop the rest."""

    company: str | None
    metric: str                   # e.g. "營收", "淨利" — not the vague "獲利"
    value: str | None             # 本期數值,例如 "100"
    unit: str | None              # e.g. "億元", "%"
    period: str | None            # e.g. "第二季"
    comparison_base: str | None   # e.g. "去年同期"
    comparison_value: str | None  # 比較期間的本期同單位數值,例如 "77"(去年同期營收)
    stated_change_pct: str | None # 原文陳述的變化百分比,例如 "30"(年增30%)
    evidence_sentence_id: str | None   # points back into Article.sentences

    missing_reason: str | None
    # Set whenever a field above is missing and the source text just
    # doesn't say it — explain why, don't guess a plausible-looking value.

    verification: Literal["consistent", "inconsistent", "not_applicable"]
    # Only computable when both `value` and `comparison_value` are present.
    # If the source only states a percentage with no comparison_value to
    # check it against, this must be "not_applicable" — never invent a
    # base value just to produce a verdict.
    # When there's enough data to check (e.g. both the current and the
    # comparison-period value are present), verify the stated change
    # against (current - base) / base. "not_applicable" when there isn't
    # enough data to check at all.


class AnalysisResult(BaseModel):
    """Output of hw453's AI analysis function, given one Article."""

    status: Literal["extracted", "no_target_data", "extraction_failed"]
    # "extracted": found >=1 fact. "no_target_data": ran fine, nothing to
    # extract. "extraction_failed": the call/parse itself broke — never
    # report this as "no_target_data", or a broken extractor looks correct.

    facts: list[NumberFact]         # non-empty iff status == "extracted"
    error_message: str | None        # set iff status == "extraction_failed"
