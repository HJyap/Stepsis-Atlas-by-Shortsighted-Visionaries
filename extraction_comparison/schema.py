from pydantic import BaseModel, ConfigDict
from typing import Optional


class CohortRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cohort_id: str
    papers: str
    doi: Optional[str] = None
    encounters_period: Optional[str] = None
    population_location: Optional[str] = None
    data_sets: Optional[str] = None
    detailed_study_design_description: Optional[str] = None
    population_description: Optional[str] = None
    cohort: Optional[str] = None
    cohort_size_n: Optional[str] = None
    cohort_characteristics: Optional[str] = None
    cohort_characteristics_timepoint: Optional[str] = None
    mortality_rate_percent: Optional[str] = None
    mortality_timepoint: Optional[str] = None


class PredictorRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cohort_id: str
    predictors: str
    timing_of_predictor_measurement: Optional[str] = None
    outcome: Optional[str] = None
    model_specification: Optional[str] = None
    effect_size_performance_and_significance: Optional[str] = None


class StudyFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_cohort_level_records: list[CohortRecord]
    predictor_model_level_records: list[PredictorRecord]
