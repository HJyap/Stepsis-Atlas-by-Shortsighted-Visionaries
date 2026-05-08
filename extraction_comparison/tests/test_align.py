from extraction_comparison.align import align_cohorts, align_predictors, build_cohort_map


def _cohort(papers: str, data_sets: str, cohort: str, cohort_id: str = "c1") -> dict:
    return {
        "cohort_id": cohort_id,
        "papers": papers,
        "data_sets": data_sets,
        "cohort": cohort,
    }


def _predictor(cohort_id: str, predictors: str, outcome: str) -> dict:
    return {"cohort_id": cohort_id, "predictors": predictors, "outcome": outcome}


class TestAlignCohorts:
    def test_matches_same_papers_datasets_cohort(self):
        a = [_cohort("Bidart 2024", "Bidart", "Total Cohort", "Bidart 2024 Total")]
        b = [_cohort("Bidart 2024", "Bidart", "Total Cohort", "Bidart_2024_Total")]
        result = align_cohorts(a, b)
        assert len(result.matched_pairs) == 1
        assert result.only_in_a == []
        assert result.only_in_b == []

    def test_only_in_a_when_b_missing_cohort(self):
        a = [
            _cohort("S 2024", "DS", "Total Cohort"),
            _cohort("S 2024", "DS", "Survivors"),
        ]
        b = [_cohort("S 2024", "DS", "Total Cohort")]
        result = align_cohorts(a, b)
        assert len(result.matched_pairs) == 1
        assert len(result.only_in_a) == 1
        assert result.only_in_b == []

    def test_only_in_b_when_a_missing_cohort(self):
        a = [_cohort("S 2024", "DS", "Total Cohort")]
        b = [
            _cohort("S 2024", "DS", "Total Cohort"),
            _cohort("S 2024", "DS", "ICU subgroup"),
        ]
        result = align_cohorts(a, b)
        assert len(result.matched_pairs) == 1
        assert len(result.only_in_b) == 1

    def test_multiple_datasets_same_study_align_separately(self):
        a = [
            _cohort("S 2016", "UPMC", "Total Cohort"),
            _cohort("S 2016", "KPNC", "External validation cohort"),
        ]
        b = [
            _cohort("S 2016", "UPMC", "Total Cohort"),
            _cohort("S 2016", "KPNC", "External validation cohort"),
        ]
        result = align_cohorts(a, b)
        assert len(result.matched_pairs) == 2
        assert result.only_in_a == []
        assert result.only_in_b == []


class TestAlignPredictors:
    def test_aligns_via_cohort_context(self):
        """Even with different cohort_id naming, predictors align via shared
        (papers, data_sets, cohort) context resolved from cohort_map."""
        cohort_a = [_cohort("S 2024", "DS", "Total Cohort", "S 2024 Total")]
        cohort_b = [_cohort("S 2024", "DS", "Total Cohort", "S_2024_Total")]
        pred_a = [_predictor("S 2024 Total", "qSOFA", "30-day mortality")]
        pred_b = [_predictor("S_2024_Total", "qSOFA", "30-day mortality")]

        result = align_predictors(
            pred_a, pred_b,
            build_cohort_map(cohort_a),
            build_cohort_map(cohort_b),
        )
        assert len(result.matched_pairs) == 1
        assert result.only_in_a == []
        assert result.only_in_b == []

    def test_only_in_a_and_only_in_b(self):
        cohort_a = [_cohort("S 2024", "DS", "Total Cohort", "ca")]
        cohort_b = [_cohort("S 2024", "DS", "Total Cohort", "cb")]
        pred_a = [
            _predictor("ca", "qSOFA", "30-day mortality"),
            _predictor("ca", "SOFA", "In-hospital mortality"),
        ]
        pred_b = [
            _predictor("cb", "qSOFA", "30-day mortality"),
            _predictor("cb", "LODS", "In-hospital mortality"),
        ]
        result = align_predictors(
            pred_a, pred_b,
            build_cohort_map(cohort_a),
            build_cohort_map(cohort_b),
        )
        assert len(result.matched_pairs) == 1
        assert len(result.only_in_a) == 1
        assert len(result.only_in_b) == 1
