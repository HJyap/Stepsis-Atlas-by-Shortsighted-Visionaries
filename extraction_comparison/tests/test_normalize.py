import pytest

from extraction_comparison.config import NOT_REPORTED_SENTINEL
from extraction_comparison.normalize import (
    has_negation,
    is_not_reported,
    normalize_predictor,
    normalize_study_key,
    normalize_text,
    parse_sample_size,
)


class TestNormalizeText:
    def test_lowercase_and_strip(self):
        assert normalize_text("  Hello  World  ") == "hello world"

    def test_collapses_internal_whitespace(self):
        assert normalize_text("a    b\tc\nd") == "a b c d"

    def test_normalizes_em_dash_to_hyphen(self):
        assert normalize_text("0.76–0.86") == "0.76-0.86"

    def test_normalizes_curly_quotes(self):
        assert normalize_text("it’s") == "it's"

    def test_strips_trailing_punctuation(self):
        assert normalize_text("Hello.") == "hello"
        assert normalize_text("Hello,") == "hello"

    def test_none_becomes_sentinel(self):
        assert normalize_text(None) == NOT_REPORTED_SENTINEL

    def test_empty_string_becomes_sentinel(self):
        assert normalize_text("") == NOT_REPORTED_SENTINEL

    @pytest.mark.parametrize(
        "value",
        ["Not reported", "NR", "n/a", "N/A", "--", "Not Available", "Unknown"],
    )
    def test_not_reported_variants(self, value):
        assert normalize_text(value) == NOT_REPORTED_SENTINEL


class TestIsNotReported:
    @pytest.mark.parametrize(
        "value",
        [None, "", "Not reported", "NR", "n/a", "--", "  Not Reported  "],
    )
    def test_recognizes_not_reported(self, value):
        assert is_not_reported(value)

    def test_real_value_is_not_not_reported(self):
        assert not is_not_reported("N=286")


class TestParseSampleSize:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("N=72", 72),
            ("n = 72", 72),
            ("72 patients", 72),
            ("N=286", 286),
            ("n=1,234", 1234),
            ("Sample of 50", 50),
        ],
    )
    def test_parses_various_formats(self, value, expected):
        assert parse_sample_size(value) == expected

    def test_returns_none_for_not_reported(self):
        assert parse_sample_size("Not reported") is None
        assert parse_sample_size(None) is None

    def test_raises_when_no_number(self):
        with pytest.raises(ValueError):
            parse_sample_size("no number here")


class TestNormalizePredictor:
    def test_strips_score_word(self):
        assert normalize_predictor("APACHE II score") == "apache ii"

    def test_alias_psofa(self):
        assert normalize_predictor("p-SOFA") == "p-sofa"
        assert normalize_predictor("pSOFA") == "p-sofa"
        assert normalize_predictor("p sofa") == "p-sofa"

    def test_alias_apache(self):
        assert normalize_predictor("APACHE 2") == "apache ii"
        assert normalize_predictor("APACHE II") == "apache ii"

    def test_distinguishes_apache_ii_from_apache_iii(self):
        assert normalize_predictor("APACHE II") != normalize_predictor("APACHE III")

    def test_prism_aliases(self):
        assert normalize_predictor("PRISM III 24") == "prism iii"
        assert normalize_predictor("PRISM III") == "prism iii"


class TestNormalizeStudyKey:
    def test_handles_et_al_variants(self):
        a = normalize_study_key("Gai et al. 2021")
        b = normalize_study_key("Gai et al., 2021")
        c = normalize_study_key("Gai 2021")
        assert a == b == c

    def test_baloch_variants(self):
        assert normalize_study_key("Baloch et al. 2022") == normalize_study_key("Baloch, 2022")


class TestHasNegation:
    @pytest.mark.parametrize(
        "value",
        [
            "Patients without sepsis",
            "Non-survivors",
            "non-mortality",
            "no improvement",
            "Absence of fever",
        ],
    )
    def test_detects_negation(self, value):
        assert has_negation(value)

    @pytest.mark.parametrize(
        "value",
        [
            "Patients with sepsis",
            "Survivors",
            "30-day mortality",
            "Mortality",
            None,
        ],
    )
    def test_no_false_positives(self, value):
        assert not has_negation(value)
