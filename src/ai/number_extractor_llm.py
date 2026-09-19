"""LLM-based extractor for 營收/淨利/年增率.

The actual model call (`llm_call`) is injected rather than hardcoded: no
backend (API key or local model) has been decided yet — see
docs/number-extraction-plan.md. Everything around that one call (prompt
construction, JSON parsing, building AnalysisResult, running the numeric
verification) is complete and tested independently of which backend gets
plugged in later.

Usage once a backend is chosen:
    from src.ai.number_extractor_llm import analyze_article

    def call_my_backend(prompt: str) -> str:
        ...  # send `prompt` to whichever API/local model, return its text

    result = analyze_article(article, llm_call=call_my_backend)
"""

import json
from collections.abc import Callable

from src.ai.number_extraction_schema import AnalysisResult, Article, NumberFact
from src.ai.number_verification import verify_growth

_PROMPT_TEMPLATE = """你是財經新聞的數字擷取助手。以下是一篇新聞的正文,每個句子前面標了句子 ID。

請找出文章中關於「營收」「淨利」的具體數字,包含年增率(如果有提到)。

規則:
- 一篇文章可能有多筆,每一筆分開輸出,不要只挑一筆。
- 只填原文明確寫出的內容;原文沒提到的欄位填 null,不要用常識推測或補值。
- 「年增」「較去年同期」這類原文用語可以正規化成 comparison_base = "去年同期",
  但如果原文完全沒有提到比較基準或期間,對應欄位就是 null。
- evidence_sentence_id 填支持這筆數字的句子 ID。
- 如果文章完全沒有營收或淨利相關的數字,回傳空的 facts 陣列。

只輸出 JSON,不要輸出其他文字,格式如下:
{{
  "facts": [
    {{
      "company": "字串或 null",
      "metric": "營收 或 淨利",
      "value": "本期數值,字串,例如 100",
      "unit": "單位,例如 億元",
      "period": "字串或 null,例如 第二季",
      "comparison_base": "字串或 null,例如 去年同期",
      "comparison_value": "比較期間的數值,字串或 null,例如 77",
      "stated_change_pct": "原文陳述的變化百分比,字串或 null,例如 30",
      "evidence_sentence_id": "句子 ID",
      "missing_reason": "如果上面有欄位是 null,簡短說明原文沒提供什麼;都齊全就填 null"
    }}
  ]
}}

文章正文:
{sentences}
"""


def _build_prompt(article: Article) -> str:
    sentences_text = "\n".join(f"[{s.sentence_id}] {s.text}" for s in article.sentences)
    return _PROMPT_TEMPLATE.format(sentences=sentences_text)


def _default_llm_call(prompt: str) -> str:
    raise NotImplementedError(
        "No LLM backend configured yet. Pass llm_call=<your function> to "
        "analyze_article(), or wire a default backend here once the team "
        "decides between a local model and an API (see docs/number-extraction-plan.md)."
    )


def analyze_article(
    article: Article,
    llm_call: Callable[[str], str] = _default_llm_call,
) -> AnalysisResult:
    """Run the LLM extractor on one article and verify any stated growth rates.

    Never raises: a broken/unconfigured backend, a timeout, or a malformed
    response all come back as status="extraction_failed" with the reason in
    error_message, so this can never be mistaken for a genuine
    "no_target_data" result.
    """
    prompt = _build_prompt(article)

    try:
        raw_response = llm_call(prompt)
    except Exception as exc:
        return AnalysisResult(status="extraction_failed", facts=[], error_message=str(exc))

    try:
        parsed = json.loads(raw_response)
        raw_facts = parsed["facts"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        return AnalysisResult(
            status="extraction_failed", facts=[],
            error_message=f"無法解析模型回傳的 JSON: {exc}",
        )

    if not raw_facts:
        return AnalysisResult(status="no_target_data", facts=[], error_message=None)

    facts: list[NumberFact] = []
    for raw in raw_facts:
        fact = NumberFact(
            company=raw.get("company"),
            metric=raw["metric"],
            value=raw.get("value"),
            unit=raw.get("unit"),
            period=raw.get("period"),
            comparison_base=raw.get("comparison_base"),
            comparison_value=raw.get("comparison_value"),
            stated_change_pct=raw.get("stated_change_pct"),
            evidence_sentence_id=raw.get("evidence_sentence_id"),
            missing_reason=raw.get("missing_reason"),
            verification="not_applicable",  # placeholder, computed next
        )
        fact.verification = verify_growth(fact)
        facts.append(fact)

    return AnalysisResult(status="extracted", facts=facts, error_message=None)
