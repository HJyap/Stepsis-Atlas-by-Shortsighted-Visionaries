import json
from pathlib import Path

import pytest

from extraction_comparison.config import CompareConfig
from extraction_comparison.main import compare_study_files, run_from_files


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def bidart_data():
    a = json.loads((FIXTURES / "study_a.json").read_text())
    b = json.loads((FIXTURES / "study_b.json").read_text())
    return (
        a["study_cohort_level_records"],
        a["predictor_model_level_records"],
        b["study_cohort_level_records"],
        b["predictor_model_level_records"],
    )


import pytest


class TestCompareStudyFiles:
    def test_returns_study_comparison_result(self, bidart_data):
        from extraction_comparison.main import StudyComparisonResult
        ca, pa, cb, pb = bidart_data
        result = compare_study_files(ca, cb, pa, pb)
        assert isinstance(result, StudyComparisonResult)

    def test_produces_same_summary_as_run_from_files(self, bidart_data, tmp_path):
        ca, pa, cb, pb = bidart_data
        in_memory = compare_study_files(ca, cb, pa, pb)
        from_files = run_from_files(
            input_a=FIXTURES / "study_a.json",
            input_b=FIXTURES / "study_b.json",
            output_dir=None,
        )
        assert in_memory.summary == from_files.summary

    def test_no_files_written_when_no_output_dir(self, bidart_data, tmp_path):
        ca, pa, cb, pb = bidart_data
        compare_study_files(ca, cb, pa, pb)
        assert list(tmp_path.iterdir()) == []

    def test_run_from_files_no_output_dir(self):
        result = run_from_files(
            input_a=FIXTURES / "study_a.json",
            input_b=FIXTURES / "study_b.json",
            output_dir=None,
        )
        assert result.summary["cohort_level"]["matched_pairs"] == 1
        assert result.summary["predictor_level"]["matched_pairs"] == 2

    def test_custom_confidence_threshold(self, bidart_data):
        ca, pa, cb, pb = bidart_data
        # At threshold 0, everything passes — nothing below threshold
        config = CompareConfig(confidence_threshold=0.0)
        result = compare_study_files(ca, cb, pa, pb, config=config)
        assert result.summary["cohort_level"]["below_threshold_count"] == 0
        assert result.summary["predictor_level"]["below_threshold_count"] == 0

    def test_self_compare_produces_confidence_100(self, bidart_data):
        ca, pa, cb, pb = bidart_data
        result = compare_study_files(ca, ca, pa, pa)
        assert result.summary["cohort_level"]["mean_confidence_score"] == 100.0
        assert result.summary["predictor_level"]["mean_confidence_score"] == 100.0
        assert result.summary["cohort_level"]["below_threshold_count"] == 0
