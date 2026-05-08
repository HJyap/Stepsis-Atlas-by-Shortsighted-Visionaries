from collections import defaultdict
from dataclasses import dataclass

from .normalize import normalize_predictor, normalize_text


# Cohort-level alignment key: (papers, data_sets, cohort)
CohortKey = tuple[str, str, str]
# Predictor-level alignment key: (papers, data_sets, cohort, predictors, outcome)
PredictorKey = tuple[str, str, str, str, str]


def cohort_key(record: dict) -> CohortKey:
    return (
        normalize_text(record.get("papers")),
        normalize_text(record.get("data_sets")),
        normalize_text(record.get("cohort")),
    )


def predictor_key(record: dict, cohort_map: dict[str, dict]) -> PredictorKey:
    """Derive alignment key for a predictor record using its linked cohort.

    cohort_id naming differs between extractors, so we resolve the canonical
    (papers, data_sets, cohort) from the cohort_map built from the same file.
    """
    ctx = cohort_map.get(record.get("cohort_id", ""), {})
    return (
        normalize_text(ctx.get("papers")),
        normalize_text(ctx.get("data_sets")),
        normalize_text(ctx.get("cohort")),
        normalize_predictor(record.get("predictors")),
        normalize_text(record.get("outcome")),
    )


def build_cohort_map(cohort_records: list[dict]) -> dict[str, dict]:
    """Map cohort_id → cohort record dict for context lookups."""
    return {r["cohort_id"]: r for r in cohort_records}


@dataclass
class Alignment:
    matched_pairs: list[tuple]
    only_in_a: list[tuple]
    only_in_b: list[tuple]
    chunk_count_mismatches: list  # kept for API compatibility; unused in new format


def _align_records(
    records_a: list[dict],
    records_b: list[dict],
    key_fn,
) -> Alignment:
    a_by_key: dict = {}
    for r in records_a:
        k = key_fn(r)
        a_by_key[k] = r

    b_by_key: dict = {}
    for r in records_b:
        k = key_fn(r)
        b_by_key[k] = r

    matched = []
    only_a = []
    only_b = []

    for k, ra in a_by_key.items():
        if k in b_by_key:
            matched.append((k, ra, b_by_key[k]))
        else:
            only_a.append((k, ra))

    for k, rb in b_by_key.items():
        if k not in a_by_key:
            only_b.append((k, rb))

    return Alignment(
        matched_pairs=matched,
        only_in_a=only_a,
        only_in_b=only_b,
        chunk_count_mismatches=[],
    )


def align_cohorts(cohort_a: list[dict], cohort_b: list[dict]) -> Alignment:
    return _align_records(cohort_a, cohort_b, cohort_key)


def align_predictors(
    predictor_a: list[dict],
    predictor_b: list[dict],
    cohort_map_a: dict[str, dict],
    cohort_map_b: dict[str, dict],
) -> Alignment:
    def key_a(r):
        return predictor_key(r, cohort_map_a)

    def key_b(r):
        return predictor_key(r, cohort_map_b)

    a_by_key: dict = {}
    for r in predictor_a:
        a_by_key[key_a(r)] = r

    b_by_key: dict = {}
    for r in predictor_b:
        b_by_key[key_b(r)] = r

    matched = []
    only_a = []
    only_b = []

    for k, ra in a_by_key.items():
        if k in b_by_key:
            matched.append((k, ra, b_by_key[k]))
        else:
            only_a.append((k, ra))

    for k, rb in b_by_key.items():
        if k not in a_by_key:
            only_b.append((k, rb))

    return Alignment(
        matched_pairs=matched,
        only_in_a=only_a,
        only_in_b=only_b,
        chunk_count_mismatches=[],
    )


# Legacy function kept for tests that still use the old flat-record style
def align(records_a: list[dict], records_b: list[dict]) -> Alignment:
    return align_cohorts(records_a, records_b)
