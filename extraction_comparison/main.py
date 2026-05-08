import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from .align import (
    Alignment,
    align_cohorts,
    align_predictors,
    build_cohort_map,
)
from .compare import RecordComparison, compare_records
from .config import CompareConfig
from .report import build_summary, write_reports
from .sample import sample_agreements
from .schema import StudyFile


IGNORED_JSON_FILES = {
    "controlled_values.json",
    "extraction_results.json",
}


@dataclass
class ComparisonResult:
    comparisons: list[RecordComparison]
    alignment: Alignment
    sampled: list[RecordComparison]
    schema_errors_a: list[dict] = field(default_factory=list)
    schema_errors_b: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


@dataclass
class StudyComparisonResult:
    cohort: ComparisonResult
    predictor: ComparisonResult
    schema_errors_a: list[dict] = field(default_factory=list)
    schema_errors_b: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def _parse_study_file(raw: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Validate a study file dict, return cohort_records, predictor_records, errors."""
    errors: list[dict] = []
    cohort_records: list[dict] = []
    predictor_records: list[dict] = []

    try:
        sf = StudyFile.model_validate(raw)
    except ValidationError as e:
        errors.append({"level": "file", "errors": e.errors()})
        return cohort_records, predictor_records, errors

    for r in sf.study_cohort_level_records:
        cohort_records.append(r.model_dump())

    for r in sf.predictor_model_level_records:
        predictor_records.append(r.model_dump())

    return cohort_records, predictor_records, errors


def load_study_file(path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """Load a study JSON file. Returns cohort_records, predictor_records, errors."""
    raw = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(raw, dict):
        raise ValueError(
            f"{path} must contain a JSON object with "
            "study_cohort_level_records and predictor_model_level_records"
        )

    return _parse_study_file(raw)


def _run_level_comparison(
    records_a: list[dict],
    records_b: list[dict],
    alignment: Alignment,
    field_rules: dict,
    field_weights: dict,
    config: CompareConfig,
    schema_errors_a: list[dict],
    schema_errors_b: list[dict],
    confidence_threshold: float,
) -> ComparisonResult:
    comparisons: list[RecordComparison] = []

    for k, ra, rb in alignment.matched_pairs:
        comparisons.append(
            compare_records(
                ra,
                rb,
                k,
                field_rules,
                field_weights=field_weights,
                na_abstention_score=config.na_abstention_score,
            )
        )

    passing = [
        c for c in comparisons
        if c.passes_confidence(confidence_threshold)
    ]

    sampled = sample_agreements(
        passing,
        rate=config.sample_rate,
        seed=config.seed,
    )

    return ComparisonResult(
        comparisons=comparisons,
        alignment=alignment,
        sampled=sampled,
        schema_errors_a=schema_errors_a,
        schema_errors_b=schema_errors_b,
        summary={},
    )


def compare_study_files(
    cohort_a: list[dict],
    cohort_b: list[dict],
    predictor_a: list[dict],
    predictor_b: list[dict],
    config: Optional[CompareConfig] = None,
) -> StudyComparisonResult:
    """
    Compare two study files at cohort and predictor level.

    No disk I/O. Accepts already-parsed and validated record dicts.
    """
    if config is None:
        config = CompareConfig()

    cohort_alignment = align_cohorts(cohort_a, cohort_b)

    cohort_map_a = build_cohort_map(cohort_a)
    cohort_map_b = build_cohort_map(cohort_b)

    predictor_alignment = align_predictors(
        predictor_a,
        predictor_b,
        cohort_map_a,
        cohort_map_b,
    )

    cohort_result = _run_level_comparison(
        records_a=cohort_a,
        records_b=cohort_b,
        alignment=cohort_alignment,
        field_rules=config.cohort_field_rules,
        field_weights=config.cohort_field_weights,
        config=config,
        schema_errors_a=[],
        schema_errors_b=[],
        confidence_threshold=config.confidence_threshold,
    )

    predictor_result = _run_level_comparison(
        records_a=predictor_a,
        records_b=predictor_b,
        alignment=predictor_alignment,
        field_rules=config.predictor_field_rules,
        field_weights=config.predictor_field_weights,
        config=config,
        schema_errors_a=[],
        schema_errors_b=[],
        confidence_threshold=config.confidence_threshold,
    )

    summary = build_summary(
        cohort_result=cohort_result,
        predictor_result=predictor_result,
        confidence_threshold=config.confidence_threshold,
    )

    cohort_result.summary = summary
    predictor_result.summary = summary

    return StudyComparisonResult(
        cohort=cohort_result,
        predictor=predictor_result,
        summary=summary,
    )


def run_from_files(
    input_a: Path,
    input_b: Path,
    output_dir: Optional[Path] = None,
    sample_rate: float = 0.05,
    seed: int = 42,
    confidence_threshold: float = 80.0,
) -> StudyComparisonResult:
    """Load two study JSON files, compare, and optionally write reports."""
    config = CompareConfig(
        sample_rate=sample_rate,
        seed=seed,
        confidence_threshold=confidence_threshold,
    )

    cohort_a, predictor_a, errors_a = load_study_file(input_a)
    cohort_b, predictor_b, errors_b = load_study_file(input_b)

    result = compare_study_files(
        cohort_a=cohort_a,
        cohort_b=cohort_b,
        predictor_a=predictor_a,
        predictor_b=predictor_b,
        config=config,
    )

    result.schema_errors_a = errors_a
    result.schema_errors_b = errors_b

    if output_dir is not None:
        write_reports(output_dir, result)

    return result


def _json_files_by_name(directory: Path) -> dict[str, Path]:
    """
    Return all JSON files in a directory, excluding known metadata/control files.
    """
    return {
        f.name: f
        for f in sorted(directory.glob("*.json"))
        if f.name not in IGNORED_JSON_FILES
    }


def run_from_dirs(
    dir_a: Path,
    dir_b: Path,
    output_dir: Path,
    sample_rate: float = 0.05,
    seed: int = 42,
    confidence_threshold: float = 80.0,
) -> int:
    """
    Compare all JSON files that share the exact same filename across two directories.

    Ignored files:
    - controlled_values.json
    - extraction_results.json
    """
    files_a = _json_files_by_name(dir_a)
    files_b = _json_files_by_name(dir_b)

    paired = sorted(set(files_a) & set(files_b))
    only_a = sorted(set(files_a) - set(files_b))
    only_b = sorted(set(files_b) - set(files_a))

    print(
        f"Found {len(paired)} matching file(s), "
        f"{len(only_a)} only in A, {len(only_b)} only in B.\n"
    )

    if only_a:
        print("Only in A (no match):", ", ".join(only_a))

    if only_b:
        print("Only in B (no match):", ", ".join(only_b))

    if only_a or only_b:
        print()

    schema_errors_total = 0

    for name in paired:
        study_out = output_dir / name.replace(".json", "")

        print(f"--- {name} ---")

        result = run_from_files(
            input_a=files_a[name],
            input_b=files_b[name],
            output_dir=study_out,
            sample_rate=sample_rate,
            seed=seed,
            confidence_threshold=confidence_threshold,
        )

        print(json.dumps(result.summary, indent=2, ensure_ascii=False))

        schema_errors_total += (
            len(result.schema_errors_a)
            + len(result.schema_errors_b)
        )

    return 1 if schema_errors_total else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare study extraction JSON files."
    )

    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--sample-rate", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--confidence-threshold", type=float, default=80.0)

    # Single-file mode
    parser.add_argument("--input-a", type=Path)
    parser.add_argument("--input-b", type=Path)

    # Directory mode
    parser.add_argument("--dir-a", type=Path)
    parser.add_argument("--dir-b", type=Path)

    args = parser.parse_args(argv)

    if args.dir_a and args.dir_b:
        return run_from_dirs(
            dir_a=args.dir_a,
            dir_b=args.dir_b,
            output_dir=args.output_dir,
            sample_rate=args.sample_rate,
            seed=args.seed,
            confidence_threshold=args.confidence_threshold,
        )

    if args.input_a and args.input_b:
        result = run_from_files(
            input_a=args.input_a,
            input_b=args.input_b,
            output_dir=args.output_dir,
            sample_rate=args.sample_rate,
            seed=args.seed,
            confidence_threshold=args.confidence_threshold,
        )

        print(f"Reports written to {args.output_dir}")
        print(json.dumps(result.summary, indent=2, ensure_ascii=False))

        schema_errors = (
            len(result.schema_errors_a)
            + len(result.schema_errors_b)
        )

        return 1 if schema_errors else 0

    parser.error("Provide either --input-a/--input-b or --dir-a/--dir-b.")


if __name__ == "__main__":
    sys.exit(main())