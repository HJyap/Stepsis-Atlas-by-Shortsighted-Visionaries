# File: data_extract/visual/helpers/models.py

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

MISSING_VALUE = "Not reported"
NA_VALUE = "NA"


STUDY_COHORT_LEVEL_FIELDS = [
    "cohort_id",
    "papers",
    "doi",
    "encounters_period",
    "population_location",
    "data_sets",
    "detailed_study_design_description",
    "population_description",
    "cohort",
    "cohort_size_n",
    "cohort_characteristics",
    "cohort_characteristics_timepoint",
    "mortality_rate_percent",
    "mortality_timepoint",
]


PREDICTOR_MODEL_LEVEL_FIELDS = [
    "cohort_id",
    "predictors",
    "timing_of_predictor_measurement",
    "outcome",
    "model_specification",
    "effect_size_performance_and_significance",
]


CONTROLLED_VALUES = {
    "study_cohort_level_records": {
        "cohort_id": "Free text; must match cohort_id used in predictor_model_level_records",
        "papers": "Free text; format: FirstAuthor Year",
        "doi": "Free text; DOI, NA, or Not reported",
        "encounters_period": "Free text; year range, NA, or Not reported",
        "population_location": "Free text",
        "data_sets": "Free text; database/cohort name, NA, or Not reported",
        "detailed_study_design_description": [
            "Prospective observational study",
            "Prospective cohort study",
            "Retrospective cohort study",
            "Retrospective cohort; Multiple imputation of missing data",
            "Retrospective cohort; Internal validation; Multiple imputation of missing data",
            "Retrospective cohort study; development and validation",
            "Retrospective cohort study; internal split into training and testing sets",
            "Case-control study",
            "External validation study",
            "Not reported",
            "Other: [exact text]",
        ],
        "population_description": "Free text",
        "cohort": [
            "Total Cohort",
            "Overall cohort",
            "Survivors",
            "Non-survivors",
            "Training set",
            "Testing set",
            "Development set",
            "Validation set",
            "Derivation cohort",
            "ICU Validation cohort",
            "External validation cohort",
            "non-ICU",
            "ICU",
            "NA",
            "Not reported",
            "Other: [exact text]",
        ],
        "cohort_size_n": "Free text; number preferred, but preserve paper wording if inconsistent",
        "cohort_characteristics": "Free text; compact semicolon-separated summary, NA, or Not reported",
        "cohort_characteristics_timepoint": [
            "Within 24h of ICU admission",
            "Within 24 hours of ICU admission",
            "At ICU admission",
            "First ICU day",
            "Within 48h of ICU admission",
            "Within 24h of hospital admission",
            "At hospital admission",
            "At ED admission",
            "Maximum value from 48h before to 24h after infection onset",
            "Baseline",
            "During ICU stay",
            "NA",
            "Not reported",
            "Other: [exact text]",
        ],
        "mortality_rate_percent": "Free text; percentage, NA, Not reported, or exact paper wording",
        "mortality_timepoint": [
            "In-ICU",
            "ICU mortality",
            "In-Hospital Mortality",
            "In-hospital mortality",
            "Hospital mortality",
            "28-day mortality",
            "30-day mortality",
            "60-day mortality",
            "90-day mortality",
            "1-year mortality",
            "One-year mortality",
            "NA",
            "Not reported",
            "Other: [exact text]",
        ],
    },
    "predictor_model_level_records": {
        "cohort_id": "Free text; must match study_cohort_level_records.cohort_id when possible",
        "predictors": "Free text; exact predictor/model/score/variable name from paper",
        "timing_of_predictor_measurement": [
            "Within 24h of ICU admission",
            "Within 24 hours of ICU admission",
            "At ICU admission",
            "First ICU day",
            "Within 48h of ICU admission",
            "At ED admission",
            "Within 24h of ED admission",
            "At hospital admission",
            "Within 24h of hospital admission",
            "Maximum score from 48h before to 24h after infection onset",
            "Assessed in window from 48h before to 24h after infection onset",
            "Baseline",
            "During ICU stay",
            "NA",
            "Not reported",
            "Other: [exact text]",
        ],
        "outcome": [
            "ICU mortality",
            "In-ICU mortality",
            "In-Hospital Mortality",
            "In-hospital mortality",
            "Hospital mortality",
            "28-day mortality",
            "30-day mortality",
            "60-day mortality",
            "90-day mortality",
            "One-year mortality",
            "1-year mortality",
            "Sepsis diagnosis",
            "Septic shock",
            "Organ dysfunction",
            "AKI",
            "ICU length of stay",
            "Hospital length of stay",
            "NA",
            "Not reported",
            "Other: [exact text]",
        ],
        "model_specification": [
            "Univariate logistic regression",
            "Univariate logistic regression (Model 1)",
            "Multivariate logistic regression",
            "Multivariable logistic regression",
            "Multivariate logistic regression (Model 2)",
            "Multivariable logistic regression (Model I)",
            "Multivariable logistic regression (Model II)",
            "Multivariable logistic regression (Model III)",
            "ROC",
            "Univariate ROC",
            "ROC analysis",
            "ROC for Logistic multivariable regression",
            "Nomogram",
            "Nomogram, Multivariable logistic regression",
            "XGBoost",
            "XGBoost without specification",
            "XGBoost without specification/coefficients",
            "Naive model, Comparison of survivors vs deaths, Univariate analysis",
            "Group comparison",
            "Sub-cohort mortality",
            "NA",
            "Not reported",
            "Other: [exact text]",
        ],
        "effect_size_performance_and_significance": (
            "Free text; preserve OR/AUC/CI/p-value/sensitivity/specificity/accuracy exactly"
        ),
    },
}


class StrictStringModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def coerce_to_nonempty_string(cls, value: object) -> str:
        if value is None:
            return MISSING_VALUE

        if isinstance(value, str):
            value = value.strip()
            return value if value else MISSING_VALUE

        return str(value)


class StudyCohortLevelRecord(StrictStringModel):
    cohort_id: str = Field(default=MISSING_VALUE)
    papers: str = Field(default=MISSING_VALUE)
    doi: str = Field(default=MISSING_VALUE)
    encounters_period: str = Field(default=MISSING_VALUE)
    population_location: str = Field(default=MISSING_VALUE)
    data_sets: str = Field(default=MISSING_VALUE)
    detailed_study_design_description: str = Field(default=MISSING_VALUE)
    population_description: str = Field(default=MISSING_VALUE)
    cohort: str = Field(default=MISSING_VALUE)
    cohort_size_n: str = Field(default=MISSING_VALUE)
    cohort_characteristics: str = Field(default=MISSING_VALUE)
    cohort_characteristics_timepoint: str = Field(default=MISSING_VALUE)
    mortality_rate_percent: str = Field(default=MISSING_VALUE)
    mortality_timepoint: str = Field(default=MISSING_VALUE)


class PredictorModelLevelRecord(StrictStringModel):
    cohort_id: str = Field(default=MISSING_VALUE)
    predictors: str = Field(default=MISSING_VALUE)
    timing_of_predictor_measurement: str = Field(default=MISSING_VALUE)
    outcome: str = Field(default=MISSING_VALUE)
    model_specification: str = Field(default=MISSING_VALUE)
    effect_size_performance_and_significance: str = Field(default=MISSING_VALUE)


class CombinedRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_cohort_level_records: list[StudyCohortLevelRecord] = Field(default_factory=list)
    predictor_model_level_records: list[PredictorModelLevelRecord] = Field(default_factory=list)


class ChunkMetadata(BaseModel):
    author: str = Field(description="Author of the source document")
    source: str = Field(description="Source identifier for tracing")
    chunk_id: int = Field(description="Unique identifier for the chunk")


class RetrievedChunk(BaseModel):
    content: str = Field(description="The actual text content of the chunk")
    relevance_score: float = Field(description="Similarity score to query, 0-1")
    metadata: ChunkMetadata = Field(description="Metadata about the chunk")


class RAGToolResult(BaseModel):
    chunks: list[RetrievedChunk] = Field(description="List of retrieved chunks")
    total_retrieved: int = Field(description="Number of chunks retrieved")
    query: str = Field(description="Original query used for retrieval")