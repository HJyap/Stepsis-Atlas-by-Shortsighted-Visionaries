import csv
import json
from pathlib import Path
from typing import Any


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _cohort_source_columns(record: dict) -> dict[str, Any]:
    return {
        "papers": record.get("papers"),
        "data_sets": record.get("data_sets"),
        "cohort": record.get("cohort"),
        "cohort_id": record.get("cohort_id"),
    }


def _predictor_source_columns(record: dict) -> dict[str, Any]:
    return {
        "cohort_id": record.get("cohort_id"),
        "predictors": record.get("predictors"),
        "outcome": record.get("outcome"),
    }


def _build_disagreement_rows(comparisons, confidence_threshold: float, source_fn) -> list[dict]:
    from .compare import RecordComparison
    flagged = [c for c in comparisons if not c.passes_confidence(confidence_threshold)]
    flagged.sort(key=lambda c: (c.confidence_score, c.key))
    rows: list[dict] = []
    for cmp in flagged:
        base = source_fn(cmp.record_a or cmp.record_b)
        confidence = round(cmp.confidence_score, 2)
        for fr in cmp.disagreeing_fields:
            rows.append({
                **base,
                "record_confidence": confidence,
                "field": fr.field,
                "value_a": cmp.record_a.get(fr.field),
                "value_b": cmp.record_b.get(fr.field),
                "value_a_norm": fr.value_a_norm,
                "value_b_norm": fr.value_b_norm,
                "score": fr.score,
                "reason": fr.reason,
            })
    return rows


def _build_agreement_sample_rows(sampled, source_fn) -> list[dict]:
    rows: list[dict] = []
    for cmp in sampled:
        base = source_fn(cmp.record_a)
        confidence = round(cmp.confidence_score, 2)
        for fr in cmp.field_results:
            rows.append({
                **base,
                "record_confidence": confidence,
                "field": fr.field,
                "value_a": cmp.record_a.get(fr.field),
                "value_b": cmp.record_b.get(fr.field),
                "score": fr.score,
                "reason": fr.reason,
            })
    return rows


def _build_all_scores_rows(
    comparisons, confidence_threshold: float, source_fn
) -> list[dict]:
    """One row per matched pair, sorted by confidence ascending.

    Includes every pair regardless of threshold — useful for seeing the full
    distribution and calibrating the threshold.
    """
    rows = []
    for cmp in sorted(comparisons, key=lambda c: c.confidence_score):
        rows.append({
            **source_fn(cmp.record_a),
            "confidence_score": round(cmp.confidence_score, 2),
            "passes_threshold": cmp.passes_confidence(confidence_threshold),
        })
    return rows


def _build_missing_rows(alignment, source_fn) -> list[dict]:
    rows: list[dict] = []
    for _, rec in alignment.only_in_a:
        rows.append({
            **source_fn(rec),
            "missing_from": "B",
            "full_record_json": json.dumps(rec, ensure_ascii=False),
        })
    for _, rec in alignment.only_in_b:
        rows.append({
            **source_fn(rec),
            "missing_from": "A",
            "full_record_json": json.dumps(rec, ensure_ascii=False),
        })
    return rows


def build_summary(
    cohort_result,
    predictor_result,
    confidence_threshold: float,
) -> dict:
    def _level_stats(result):
        flagged = [c for c in result.comparisons if not c.passes_confidence(confidence_threshold)]
        field_counts: dict[str, int] = {}
        for c in flagged:
            for fr in c.disagreeing_fields:
                field_counts[fr.field] = field_counts.get(fr.field, 0) + 1
        if result.comparisons:
            mean_conf = sum(c.confidence_score for c in result.comparisons) / len(result.comparisons)
        else:
            mean_conf = 0.0
        return {
            "matched_pairs": len(result.alignment.matched_pairs),
            "only_in_a": len(result.alignment.only_in_a),
            "only_in_b": len(result.alignment.only_in_b),
            "below_threshold_count": len(flagged),
            "mean_confidence_score": round(mean_conf, 2),
            "disagreements_by_field": field_counts,
            "agreement_sample_size": len(result.sampled),
        }

    return {
        "confidence_threshold": confidence_threshold,
        "cohort_level": _level_stats(cohort_result),
        "predictor_level": _level_stats(predictor_result),
        "schema_errors_a": len(getattr(cohort_result, "schema_errors_a", [])),
        "schema_errors_b": len(getattr(cohort_result, "schema_errors_b", [])),
    }


def write_reports(output_dir: Path, result) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    threshold = result.summary.get("confidence_threshold", 99.0)

    _write_csv(
        output_dir / "cohort_disagreements.csv",
        _build_disagreement_rows(result.cohort.comparisons, threshold, _cohort_source_columns),
    )
    _write_csv(
        output_dir / "cohort_agreement_sample.csv",
        _build_agreement_sample_rows(result.cohort.sampled, _cohort_source_columns),
    )
    _write_csv(
        output_dir / "predictor_disagreements.csv",
        _build_disagreement_rows(result.predictor.comparisons, threshold, _predictor_source_columns),
    )
    _write_csv(
        output_dir / "predictor_agreement_sample.csv",
        _build_agreement_sample_rows(result.predictor.sampled, _predictor_source_columns),
    )
    _write_csv(
        output_dir / "missing_cohorts.csv",
        _build_missing_rows(result.cohort.alignment, _cohort_source_columns),
    )
    _write_csv(
        output_dir / "missing_predictors.csv",
        _build_missing_rows(result.predictor.alignment, _predictor_source_columns),
    )
    _write_csv(
        output_dir / "cohort_confidence_scores.csv",
        _build_all_scores_rows(result.cohort.comparisons, threshold, _cohort_source_columns),
    )
    _write_csv(
        output_dir / "predictor_confidence_scores.csv",
        _build_all_scores_rows(result.predictor.comparisons, threshold, _predictor_source_columns),
    )

    (output_dir / "summary.json").write_text(
        json.dumps(result.summary, indent=2, ensure_ascii=False)
    )

    if result.schema_errors_a or result.schema_errors_b:
        (output_dir / "schema_errors.json").write_text(
            json.dumps(
                {"a": result.schema_errors_a, "b": result.schema_errors_b},
                indent=2,
                ensure_ascii=False,
            )
        )
