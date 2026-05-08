from dataclasses import dataclass
from typing import Any, Optional

from rapidfuzz import fuzz

from .config import NOT_REPORTED_SENTINEL, CompareConfig, FieldRule
from .normalize import (
    has_negation,
    is_not_reported,
    normalize_predictor,
    normalize_text,
    parse_sample_size,
)


@dataclass
class FieldResult:
    field: str
    agree: bool
    score: Optional[int]
    reason: str
    value_a_norm: str
    value_b_norm: str


def _normalize_for_field(field: str, value: Any) -> str:
    if field == "predictors":
        return normalize_predictor(value)
    return normalize_text(value)


def _compare_normalized_exact(field: str, a: Any, b: Any) -> FieldResult:
    na = _normalize_for_field(field, a)
    nb = _normalize_for_field(field, b)
    return FieldResult(
        field=field,
        agree=(na == nb),
        score=100 if na == nb else 0,
        reason="exact" if na == nb else "exact_mismatch",
        value_a_norm=na,
        value_b_norm=nb,
    )


def _compare_numeric_int(field: str, a: Any, b: Any) -> FieldResult:
    na = normalize_text(a)
    nb = normalize_text(b)
    a_nr = is_not_reported(a)
    b_nr = is_not_reported(b)
    if a_nr and b_nr:
        return FieldResult(field, True, 100, "both_not_reported", na, nb)
    if a_nr or b_nr:
        return FieldResult(field, False, 0, "one_not_reported", na, nb)
    try:
        ia = parse_sample_size(a)
        ib = parse_sample_size(b)
    except ValueError:
        return _compare_normalized_exact(field, a, b)
    return FieldResult(
        field=field,
        agree=(ia == ib),
        score=100 if ia == ib else 0,
        reason="numeric_eq" if ia == ib else "numeric_diff",
        value_a_norm=str(ia),
        value_b_norm=str(ib),
    )


def _compare_fuzzy(field: str, a: Any, b: Any, rule: FieldRule) -> FieldResult:
    na = normalize_text(a)
    nb = normalize_text(b)
    a_nr = is_not_reported(a)
    b_nr = is_not_reported(b)
    if a_nr and b_nr:
        return FieldResult(field, True, 100, "both_not_reported", na, nb)
    if a_nr or b_nr:
        return FieldResult(field, False, 0, "one_not_reported", na, nb)
    score = int(round(fuzz.token_sort_ratio(na, nb)))
    agree = score >= rule.threshold
    reason = f"fuzzy_{'pass' if agree else 'fail'}_{rule.threshold}"
    if rule.negation_guard and has_negation(a) != has_negation(b):
        # Informational v1 behavior: flag but don't zero the score.
        # The collaborator's confidence formula will decide how to penalize this.
        agree = False
        reason = "negation_mismatch"
    return FieldResult(
        field=field,
        agree=agree,
        score=score,
        reason=reason,
        value_a_norm=na,
        value_b_norm=nb,
    )


def compare_field(field: str, a: Any, b: Any, rule: FieldRule) -> FieldResult:
    if rule.strategy == "skip":
        return FieldResult(field, True, None, "skipped", "", "")
    if rule.strategy == "normalized_exact":
        return _compare_normalized_exact(field, a, b)
    if rule.strategy == "numeric_int":
        return _compare_numeric_int(field, a, b)
    if rule.strategy == "fuzzy":
        return _compare_fuzzy(field, a, b, rule)
    raise ValueError(f"unknown strategy: {rule.strategy}")


def _is_na_asymmetric(fr: FieldResult) -> bool:
    """True when exactly one side has a NOT_REPORTED sentinel.

    Catches both the fuzzy/numeric ``one_not_reported`` case and the
    normalized_exact case where one value is the sentinel but the other isn't.
    """
    a_na = fr.value_a_norm == NOT_REPORTED_SENTINEL
    b_na = fr.value_b_norm == NOT_REPORTED_SENTINEL
    return a_na != b_na


def _compute_confidence(
    record_a: dict,
    record_b: dict,
    field_results: list[FieldResult],
    field_weights: Optional[dict] = None,
    na_abstention_score: float = 60.0,
) -> float:
    """Weighted confidence score for a record pair.

    Design rationale:
    - Fields are weighted by clinical/analytical importance. Predictors and
      outcomes matter most; DOIs and free-text characteristics matter least.
    - When one extractor has real data and the other has NA (because it cannot
      read table images), the field gets an abstention score rather than 0.
      NA != wrong; it means "couldn't extract." Default abstention = 60.
    - Both-NA fields score 100 (either both return sentinel → exact match, or
      both-not-reported logic applies in fuzzy/numeric comparisons).

    To swap in a custom formula: replace this function body. record_a and
    record_b are available for formulas that do raw-value arithmetic.
    """
    if field_weights is None:
        field_weights = {}

    total_weight = 0.0
    weighted_sum = 0.0

    for fr in field_results:
        if fr.score is None:  # "skip" strategy
            continue
        weight = field_weights.get(fr.field, 1.0)
        score = na_abstention_score if _is_na_asymmetric(fr) else float(fr.score)
        weighted_sum += weight * score
        total_weight += weight

    return weighted_sum / total_weight if total_weight > 0 else 100.0


@dataclass
class RecordComparison:
    key: tuple
    record_a: dict
    record_b: dict
    field_results: list[FieldResult]
    confidence_score: float = 0.0

    @property
    def disagreeing_fields(self) -> list[FieldResult]:
        return [r for r in self.field_results if not r.agree]

    def passes_confidence(self, threshold: float) -> bool:
        return self.confidence_score >= threshold


def compare_records(
    record_a: dict,
    record_b: dict,
    key: tuple,
    field_rules: dict[str, FieldRule],
    field_weights: Optional[dict] = None,
    na_abstention_score: float = 60.0,
) -> RecordComparison:
    results: list[FieldResult] = []
    for field, rule in field_rules.items():
        a = record_a.get(field)
        b = record_b.get(field)
        results.append(compare_field(field, a, b, rule))
    confidence = _compute_confidence(
        record_a, record_b, results,
        field_weights=field_weights,
        na_abstention_score=na_abstention_score,
    )
    return RecordComparison(
        key=key,
        record_a=record_a,
        record_b=record_b,
        field_results=results,
        confidence_score=confidence,
    )
