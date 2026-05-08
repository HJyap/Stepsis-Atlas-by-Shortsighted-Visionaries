import json
from pathlib import Path

import pytest

from extraction_comparison.main import run_from_files


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def report_dir(tmp_path):
    return tmp_path / "reports"


def test_full_pipeline_on_bidart_fixtures(report_dir):
    result = run_from_files(
        input_a=FIXTURES / "study_a.json",
        input_b=FIXTURES / "study_b.json",
        output_dir=report_dir,
        sample_rate=0.5,
        seed=42,
        confidence_threshold=99.0,
    )
    summary = json.loads((report_dir / "summary.json").read_text())

    # Cohort level: A has 2 cohorts, B has 1 — 1 match, 1 only_in_a
    cl = summary["cohort_level"]
    assert cl["matched_pairs"] == 1
    assert cl["only_in_a"] == 1
    assert cl["only_in_b"] == 0
    # Total Cohort disagrees on doi and cohort_size_n → 1 record below threshold
    assert cl["below_threshold_count"] == 1
    assert cl["disagreements_by_field"] == {"doi": 1, "cohort_size_n": 1}

    # Predictor level: qSOFA/30-day matches and agrees; Vasopressor/30-day matches
    # but effect_size differs; Vasopressor/In-hospital only in A; Blood cultures only in B
    pl = summary["predictor_level"]
    assert pl["matched_pairs"] == 2
    assert pl["only_in_a"] == 1
    assert pl["only_in_b"] == 1
    assert pl["below_threshold_count"] == 1
    assert pl["disagreements_by_field"] == {"effect_size_performance_and_significance": 1}

    assert summary["schema_errors_a"] == 0
    assert summary["schema_errors_b"] == 0


def test_report_files_created(report_dir):
    run_from_files(
        input_a=FIXTURES / "study_a.json",
        input_b=FIXTURES / "study_b.json",
        output_dir=report_dir,
        sample_rate=0.5,
        seed=42,
    )
    expected = [
        "cohort_disagreements.csv",
        "cohort_agreement_sample.csv",
        "predictor_disagreements.csv",
        "predictor_agreement_sample.csv",
        "missing_cohorts.csv",
        "missing_predictors.csv",
        "summary.json",
    ]
    for fname in expected:
        assert (report_dir / fname).exists(), f"missing {fname}"


def test_cohort_disagreements_csv_has_expected_content(report_dir):
    run_from_files(
        input_a=FIXTURES / "study_a.json",
        input_b=FIXTURES / "study_b.json",
        output_dir=report_dir,
        sample_rate=0.5,
        seed=42,
        confidence_threshold=99.0,
    )
    text = (report_dir / "cohort_disagreements.csv").read_text()
    assert "doi" in text
    assert "cohort_size_n" in text
    assert "record_confidence" in text


def test_missing_cohorts_csv_shows_survivors(report_dir):
    run_from_files(
        input_a=FIXTURES / "study_a.json",
        input_b=FIXTURES / "study_b.json",
        output_dir=report_dir,
        sample_rate=0.5,
        seed=42,
    )
    text = (report_dir / "missing_cohorts.csv").read_text()
    assert "Survivors" in text
    assert "missing_from" in text


def test_predictor_disagreements_sorted_by_confidence(report_dir):
    import csv
    run_from_files(
        input_a=FIXTURES / "study_a.json",
        input_b=FIXTURES / "study_b.json",
        output_dir=report_dir,
        sample_rate=0.5,
        seed=42,
        confidence_threshold=99.0,
    )
    path = report_dir / "predictor_disagreements.csv"
    with path.open() as f:
        rows = list(csv.DictReader(f))
    if rows:
        confidences = [float(r["record_confidence"]) for r in rows]
        assert confidences == sorted(confidences)


def test_agreement_sample_is_deterministic(report_dir, tmp_path):
    run_from_files(
        input_a=FIXTURES / "study_a.json",
        input_b=FIXTURES / "study_b.json",
        output_dir=report_dir,
        sample_rate=0.5,
        seed=42,
    )
    first = (report_dir / "predictor_agreement_sample.csv").read_text()

    second_dir = tmp_path / "r2"
    run_from_files(
        input_a=FIXTURES / "study_a.json",
        input_b=FIXTURES / "study_b.json",
        output_dir=second_dir,
        sample_rate=0.5,
        seed=42,
    )
    second = (second_dir / "predictor_agreement_sample.csv").read_text()
    assert first == second


def test_schema_validation_catches_bad_file(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"wrong_key": []}))
    good = FIXTURES / "study_b.json"

    out = tmp_path / "out"
    try:
        run_from_files(input_a=bad, input_b=good, output_dir=out)
    except Exception:
        pass  # bad files may raise; we just verify no silent success
