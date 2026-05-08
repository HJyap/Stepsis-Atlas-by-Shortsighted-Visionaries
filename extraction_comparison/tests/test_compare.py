from extraction_comparison.compare import compare_field, compare_records
from extraction_comparison.config import (
    COHORT_FIELD_RULES,
    PREDICTOR_FIELD_RULES,
    CompareConfig,
)


def _cohort_record(**overrides) -> dict:
    base = {
        "cohort_id": "S 2024 Total",
        "papers": "S 2024",
        "doi": "10.0/test",
        "encounters_period": "2020-2022",
        "population_location": "Hospital A",
        "data_sets": "DS",
        "detailed_study_design_description": "Retrospective cohort study",
        "population_description": "Patients with sepsis",
        "cohort": "Total Cohort",
        "cohort_size_n": "500",
        "cohort_characteristics": "Age 65; ICU admission 30%",
        "cohort_characteristics_timepoint": "At admission",
        "mortality_rate_percent": "20%",
        "mortality_timepoint": "In-hospital mortality",
    }
    base.update(overrides)
    return base


def _predictor_record(**overrides) -> dict:
    base = {
        "cohort_id": "S 2024 Total",
        "predictors": "qSOFA",
        "timing_of_predictor_measurement": "At admission",
        "outcome": "30-day mortality",
        "model_specification": "Multivariate logistic regression",
        "effect_size_performance_and_significance": "AUC 0.75",
    }
    base.update(overrides)
    return base


class TestCompareField:
    def test_numeric_int_handles_format_diff(self):
        result = compare_field("cohort_size_n", "N=500", "500 patients", COHORT_FIELD_RULES["cohort_size_n"])
        assert result.agree

    def test_numeric_int_catches_real_diff(self):
        result = compare_field("cohort_size_n", "665", "670", COHORT_FIELD_RULES["cohort_size_n"])
        assert not result.agree
        assert result.reason == "numeric_diff"

    def test_normalized_exact_catches_effect_size_diff(self):
        result = compare_field(
            "effect_size_performance_and_significance",
            "RR 2.14 (95% CI 1.44-3.17), p<0.001",
            "RR 3.00 (95% CI 2.00-4.00), p<0.001",
            PREDICTOR_FIELD_RULES["effect_size_performance_and_significance"],
        )
        assert not result.agree
        assert result.reason == "exact_mismatch"

    def test_doi_not_reported_disagrees_with_real_doi(self):
        # normalized_exact: "NA" → sentinel, "10.1186/test" → itself → mismatch
        result = compare_field("doi", "10.1186/test", "NA", COHORT_FIELD_RULES["doi"])
        assert not result.agree
        assert result.reason == "exact_mismatch"

    def test_doi_both_not_reported_agrees(self):
        # normalized_exact: both "NA" and "Not reported" → same sentinel → exact match
        result = compare_field("doi", "NA", "Not reported", COHORT_FIELD_RULES["doi"])
        assert result.agree
        assert result.reason == "exact"

    def test_negation_guard_on_population(self):
        result = compare_field(
            "population_description",
            "Patients with sepsis",
            "Patients without sepsis",
            COHORT_FIELD_RULES["population_description"],
        )
        assert not result.agree
        assert result.reason == "negation_mismatch"

    def test_negation_does_not_zero_score(self):
        result = compare_field(
            "population_description",
            "Patients with sepsis",
            "Patients without sepsis",
            COHORT_FIELD_RULES["population_description"],
        )
        assert result.score is not None
        assert result.score > 50

    def test_predictor_alias_normalization(self):
        result = compare_field("predictors", "qSOFA", "qsofa", PREDICTOR_FIELD_RULES["predictors"])
        assert result.agree

    def test_predictor_sofa_vs_qsofa_disagree(self):
        result = compare_field("predictors", "SOFA", "qSOFA", PREDICTOR_FIELD_RULES["predictors"])
        assert not result.agree


class TestCompareRecords:
    def test_identical_cohort_records_confidence_100(self):
        config = CompareConfig()
        a = _cohort_record()
        result = compare_records(a, dict(a), ("k",), config.cohort_field_rules)
        assert result.confidence_score == 100.0
        assert result.disagreeing_fields == []

    def test_one_cohort_field_diff_flagged(self):
        config = CompareConfig()
        a = _cohort_record()
        b = _cohort_record(cohort_size_n="670")
        result = compare_records(a, b, ("k",), config.cohort_field_rules)
        assert len(result.disagreeing_fields) == 1
        assert result.disagreeing_fields[0].field == "cohort_size_n"
        assert result.confidence_score < 100.0

    def test_identical_predictor_records_confidence_100(self):
        config = CompareConfig()
        a = _predictor_record()
        result = compare_records(a, dict(a), ("k",), config.predictor_field_rules)
        assert result.confidence_score == 100.0

    def test_passes_confidence(self):
        config = CompareConfig(confidence_threshold=99.0)
        a = _predictor_record()
        b = _predictor_record(effect_size_performance_and_significance="AUC 0.99")
        result = compare_records(a, b, ("k",), config.predictor_field_rules)
        assert not result.passes_confidence(99.0)
        assert result.passes_confidence(0.0)


class TestComputeConfidence:
    def test_threshold_configurable(self):
        config = CompareConfig(confidence_threshold=75.0)
        assert config.confidence_threshold == 75.0

    def test_simple_average_formula(self):
        config = CompareConfig()
        a = _cohort_record()
        # All fields identical → confidence 100
        result = compare_records(a, dict(a), ("k",), config.cohort_field_rules)
        assert result.confidence_score == 100.0
