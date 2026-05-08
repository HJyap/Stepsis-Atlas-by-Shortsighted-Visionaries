from dataclasses import dataclass, field
from typing import Literal


NOT_REPORTED_SENTINEL = "__NOT_REPORTED__"

NOT_REPORTED_VARIANTS = {
    "",
    "not reported",
    "nr",
    "n/a",
    "na",
    "none",
    "null",
    "--",
    "-",
    "n.r.",
    "not available",
    "not stated",
    "not specified",
    "unknown",
}

NEGATION_TOKENS = {
    "not",
    "non",
    "without",
    "no",
    "absence",
    "negative",
    "never",
}


Strategy = Literal["normalized_exact", "fuzzy", "numeric_int", "skip"]


@dataclass
class FieldRule:
    strategy: Strategy
    threshold: int = 0
    negation_guard: bool = False


# Field rules for cohort-level records
COHORT_FIELD_RULES: dict[str, FieldRule] = {
    "papers": FieldRule(strategy="normalized_exact"),
    "doi": FieldRule(strategy="normalized_exact"),
    "encounters_period": FieldRule(strategy="normalized_exact"),
    "population_location": FieldRule(strategy="fuzzy", threshold=88),
    "data_sets": FieldRule(strategy="normalized_exact"),
    "detailed_study_design_description": FieldRule(strategy="fuzzy", threshold=88),
    "population_description": FieldRule(strategy="fuzzy", threshold=92, negation_guard=True),
    "cohort": FieldRule(strategy="fuzzy", threshold=88),
    "cohort_size_n": FieldRule(strategy="numeric_int"),
    "cohort_characteristics": FieldRule(strategy="fuzzy", threshold=85),
    "cohort_characteristics_timepoint": FieldRule(strategy="normalized_exact"),
    "mortality_rate_percent": FieldRule(strategy="normalized_exact"),
    "mortality_timepoint": FieldRule(strategy="fuzzy", threshold=88),
}

# Field rules for predictor-level records
PREDICTOR_FIELD_RULES: dict[str, FieldRule] = {
    "predictors": FieldRule(strategy="normalized_exact"),
    "timing_of_predictor_measurement": FieldRule(strategy="normalized_exact"),
    "outcome": FieldRule(strategy="fuzzy", threshold=92, negation_guard=True),
    "model_specification": FieldRule(strategy="fuzzy", threshold=88),
    "effect_size_performance_and_significance": FieldRule(strategy="normalized_exact"),
}

# Score used when one extractor has real data and the other has NA.
# Not 0 (wrong) and not 100 (agree) — it means "couldn't extract, unknown."
# Set higher (80) because extractors without image capability genuinely cannot
# extract table data — penalising this as hard disagreement (0) is unfair.
NA_ABSTENTION_SCORE: float = 80.0

# Field weights for confidence calculation — higher = counts more toward confidence.
# Raised:  stable reliable fields (papers, cohort, cohort_size_n, data_sets, encounters_period)
# Lowered: noisy or inconsistent fields (cohort_characteristics, mortality_rate_percent,
#          mortality_timepoint, population_location) — these legitimately differ between
#          extractors due to format choices or image-extraction limitations, not errors.
COHORT_FIELD_WEIGHTS: dict[str, float] = {
    "papers": 1.5,         # stable identifier — always agrees for same study
    "doi": 0.3,            # low importance; often NA in image-limited extractors
    "encounters_period": 0.9,   # stable when present; often both NA
    "population_location": 0.5,  # often NA in B — abstention handles it
    "data_sets": 1.2,      # stable — same dataset name across extractors
    "detailed_study_design_description": 1.0,
    "population_description": 1.5,  # critical — defines who was studied
    "cohort": 1.3,         # stable — same cohort label within a study
    "cohort_size_n": 2.0,  # most reliable numeric field; directly from the paper
    "cohort_characteristics": 0.4,  # very noisy free text — each extractor picks different facts
    "cohort_characteristics_timepoint": 0.7,
    "mortality_rate_percent": 0.5,  # format is highly inconsistent (%, fraction, raw counts)
    "mortality_timepoint": 0.6,  # extractors legitimately choose different timepoints
}

PREDICTOR_FIELD_WEIGHTS: dict[str, float] = {
    "predictors": 2.0,     # critical — defines what is being tested
    "timing_of_predictor_measurement": 0.8,
    "outcome": 2.0,        # critical — defines what is being predicted
    "model_specification": 1.0,
    "effect_size_performance_and_significance": 1.5,  # critical — the actual result
}

PREDICTOR_ALIASES: dict[str, str] = {
    "apache 2": "apache ii",
    "apache2": "apache ii",
    "apache 3": "apache iii",
    "apache3": "apache iii",
    "psofa": "p-sofa",
    "p sofa": "p-sofa",
    "pediatric sofa": "p-sofa",
    "prism iii 24": "prism iii",
    "prism 3": "prism iii",
    "prism3": "prism iii",
    "qsofa": "qsofa",
    "quick sofa": "qsofa",
    "quick-sofa": "qsofa",
}


@dataclass
class CompareConfig:
    cohort_field_rules: dict[str, FieldRule] = field(
        default_factory=lambda: dict(COHORT_FIELD_RULES)
    )
    predictor_field_rules: dict[str, FieldRule] = field(
        default_factory=lambda: dict(PREDICTOR_FIELD_RULES)
    )
    cohort_field_weights: dict[str, float] = field(
        default_factory=lambda: dict(COHORT_FIELD_WEIGHTS)
    )
    predictor_field_weights: dict[str, float] = field(
        default_factory=lambda: dict(PREDICTOR_FIELD_WEIGHTS)
    )
    predictor_aliases: dict[str, str] = field(
        default_factory=lambda: dict(PREDICTOR_ALIASES)
    )
    na_abstention_score: float = NA_ABSTENTION_SCORE
    sample_rate: float = 0.05
    seed: int = 42
    confidence_threshold: float = 80.0
