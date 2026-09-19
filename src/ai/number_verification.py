"""Deterministic cross-check for a NumberFact's stated change percentage.

This never needs a model call: if both the current-period value and the
comparison-period value are on the fact, we can just do the arithmetic and
see whether it matches what the article claims. This is what should catch
an LLM confidently stating "年增30%" when the two numbers it also extracted
don't actually support that.
"""

from typing import Literal

from src.ai.number_extraction_schema import NumberFact

# Rounding in the original text ("年增約30%") means an exact match is the
# wrong bar — see docs/number-extraction-plan.md's Day 1 decision table.
DEFAULT_TOLERANCE_PCT = 0.5


def verify_growth(fact: NumberFact, tolerance_pct: float = DEFAULT_TOLERANCE_PCT) -> Literal["consistent", "inconsistent", "not_applicable"]:
    """Check fact.stated_change_pct against (value - comparison_value) / comparison_value.

    Returns "not_applicable" whenever there isn't enough data to check —
    never guesses a missing number just to produce a verdict.
    """
    if fact.value is None or fact.comparison_value is None or fact.stated_change_pct is None:
        return "not_applicable"

    try:
        current = float(fact.value.replace(",", ""))
        base = float(fact.comparison_value.replace(",", ""))
        stated_pct = float(fact.stated_change_pct.replace(",", "").replace("%", ""))
    except ValueError:
        # Value wasn't actually numeric (e.g. extractor put garbage in a
        # numeric field) — that's a data problem, not something to verify.
        return "not_applicable"

    if base == 0:
        return "not_applicable"

    calculated_pct = (current - base) / base * 100

    if abs(calculated_pct - stated_pct) <= tolerance_pct:
        return "consistent"
    return "inconsistent"
