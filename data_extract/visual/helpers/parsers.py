# File: data_extract/visual/helpers/parsers.py

from __future__ import annotations

import json
import re
from typing import Any

from .models import (
    CombinedRecord,
    MISSING_VALUE,
    PREDICTOR_MODEL_LEVEL_FIELDS,
    STUDY_COHORT_LEVEL_FIELDS,
)


KEY_ALIASES = {
    "cohort_id": "cohort_id",
    "papers": "papers",
    "paper": "papers",
    "doi": "doi",
    "encounter_period": "encounters_period",
    "encounters_period": "encounters_period",
    "population_location": "population_location",
    "data_sets": "data_sets",
    "dataset": "data_sets",
    "datasets": "data_sets",
    "detailed_study_design_description": "detailed_study_design_description",
    "study_design": "detailed_study_design_description",
    "population_description": "population_description",
    "cohort": "cohort",
    "cohort_size_n": "cohort_size_n",
    "cohort_size": "cohort_size_n",
    "sample_size": "cohort_size_n",
    "cohort_characteristics": "cohort_characteristics",
    "cohort_characteristics_timepoint": "cohort_characteristics_timepoint",
    "mortality_rate_percent": "mortality_rate_percent",
    "mortality_rate": "mortality_rate_percent",
    "mortality_timepoint": "mortality_timepoint",

    "predictors": "predictors",
    "predictor": "predictors",
    "timing_of_predictor_measurement": "timing_of_predictor_measurement",
    "timing": "timing_of_predictor_measurement",
    "outcome": "outcome",
    "model_specification": "model_specification",
    "method": "model_specification",
    "effect_size_performance_and_significance": "effect_size_performance_and_significance",
    "effect_size_performance_significance": "effect_size_performance_and_significance",
    "effect_size": "effect_size_performance_and_significance",
    "performance": "effect_size_performance_and_significance",
}


class JSONParser:
    @staticmethod
    def strip_json_fences(text: str) -> str:
        text = text.strip()
        text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text.strip()

    @classmethod
    def parse(cls, text: str) -> Any:
        cleaned = cls.strip_json_fences(text)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        object_start = cleaned.find("{")
        object_end = cleaned.rfind("}")

        if object_start != -1 and object_end != -1 and object_end > object_start:
            possible_object = cleaned[object_start: object_end + 1]

            try:
                return json.loads(possible_object)
            except json.JSONDecodeError:
                pass

        array_start = cleaned.find("[")
        array_end = cleaned.rfind("]")

        if array_start != -1 and array_end != -1 and array_end > array_start:
            possible_array = cleaned[array_start: array_end + 1]

            try:
                return json.loads(possible_array)
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse model response as JSON:\n{text}")


class RecordNormalizer:
    @staticmethod
    def stringify_field(value: Any) -> str:
        if value is None:
            return MISSING_VALUE

        if isinstance(value, str):
            value = re.sub(r"\s+", " ", value.strip())
            return value if value else MISSING_VALUE

        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)

        return str(value)

    @staticmethod
    def normalize_key(key: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9]+", "_", str(key).strip().lower())
        normalized = normalized.strip("_")
        return KEY_ALIASES.get(normalized, normalized)

    @classmethod
    def normalize_keys(cls, row: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}

        for key, value in row.items():
            normalized_key = cls.normalize_key(key)
            normalized[normalized_key] = value

        return normalized

    @classmethod
    def normalize_row(
        cls,
        row: dict[str, Any],
        fields: list[str],
    ) -> dict[str, str]:
        row = cls.normalize_keys(row)

        return {
            field: cls.stringify_field(row.get(field, MISSING_VALUE))
            for field in fields
        }

    @staticmethod
    def row_has_content(row: dict[str, str]) -> bool:
        useful_values = [
            value
            for value in row.values()
            if value not in {"", MISSING_VALUE, "NA"}
        ]

        return bool(useful_values)

    @staticmethod
    def row_key(row: dict[str, str], fields: list[str]) -> tuple[str, ...]:
        return tuple(
            re.sub(r"\s+", " ", row.get(field, "").strip()).lower()
            for field in fields
        )

    @classmethod
    def dedupe_rows(
        cls,
        rows: list[dict[str, str]],
        fields: list[str],
    ) -> list[dict[str, str]]:
        seen: set[tuple[str, ...]] = set()
        output: list[dict[str, str]] = []

        for row in rows:
            key = cls.row_key(row, fields)

            if key in seen:
                continue

            seen.add(key)
            output.append(row)

        return output

    @staticmethod
    def coerce_record_list(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

        if isinstance(value, dict):
            return [value]

        return []

    @classmethod
    def normalize(cls, parsed_json: Any, *args: Any, **kwargs: Any) -> CombinedRecord:
        """
        Normalize model output into the two final table-shaped arrays.

        Expected final structure:
        {
          "study_cohort_level_records": [...],
          "predictor_model_level_records": [...]
        }
        """

        if isinstance(parsed_json, dict):
            study_raw = parsed_json.get("study_cohort_level_records", [])
            predictor_raw = parsed_json.get("predictor_model_level_records", [])

            # Defensive fallback if model accidentally returns one flat row.
            if not study_raw and not predictor_raw:
                normalized_keys = cls.normalize_keys(parsed_json)

                has_study_fields = any(
                    field in normalized_keys for field in STUDY_COHORT_LEVEL_FIELDS
                )
                has_predictor_fields = any(
                    field in normalized_keys for field in PREDICTOR_MODEL_LEVEL_FIELDS
                )

                if has_study_fields:
                    study_raw = [parsed_json]

                if has_predictor_fields:
                    predictor_raw = [parsed_json]

        elif isinstance(parsed_json, list):
            # Defensive fallback: treat raw lists as predictor/model records.
            study_raw = []
            predictor_raw = parsed_json

        else:
            raise ValueError("Parsed JSON must be a dict or list.")

        study_rows = [
            cls.normalize_row(row, STUDY_COHORT_LEVEL_FIELDS)
            for row in cls.coerce_record_list(study_raw)
        ]

        predictor_rows = [
            cls.normalize_row(row, PREDICTOR_MODEL_LEVEL_FIELDS)
            for row in cls.coerce_record_list(predictor_raw)
        ]

        study_rows = [
            row for row in study_rows
            if cls.row_has_content(row)
        ]

        predictor_rows = [
            row for row in predictor_rows
            if cls.row_has_content(row)
        ]

        study_rows = cls.dedupe_rows(study_rows, STUDY_COHORT_LEVEL_FIELDS)
        predictor_rows = cls.dedupe_rows(predictor_rows, PREDICTOR_MODEL_LEVEL_FIELDS)

        return CombinedRecord(
            study_cohort_level_records=study_rows,
            predictor_model_level_records=predictor_rows,
        )