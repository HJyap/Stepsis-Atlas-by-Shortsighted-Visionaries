# File: data_extract/visual/helpers/prompts.py

from __future__ import annotations

import json
from typing import Literal

from .models import (
    CONTROLLED_VALUES,
    PREDICTOR_MODEL_LEVEL_FIELDS,
    STUDY_COHORT_LEVEL_FIELDS,
)


class ExtractionPromptBuilder:
    @staticmethod
    def _format_table_schema() -> str:
        study_fields = ",\n        ".join(
            f'"{field}": "string"'
            for field in STUDY_COHORT_LEVEL_FIELDS
        )

        predictor_fields = ",\n        ".join(
            f'"{field}": "string"'
            for field in PREDICTOR_MODEL_LEVEL_FIELDS
        )

        return f"""{{
  "study_cohort_level_records": [
    {{
        {study_fields}
    }}
  ],
  "predictor_model_level_records": [
    {{
        {predictor_fields}
    }}
  ]
}}"""

    @staticmethod
    def _format_controlled_values() -> str:
        return json.dumps(CONTROLLED_VALUES, indent=2, ensure_ascii=False)

    @staticmethod
    def build(
        pdf_file: str,
        page_selection: int | Literal["all"],
        requested_start_page: int,
        requested_end_page: int,
        included_pages: list[int],
    ) -> str:
        included_pages_text = ", ".join(str(p) for p in included_pages) or "None"
        requested_range_text = f"{requested_start_page} through {requested_end_page}"

        if page_selection == "all":
            center_page_text = "Not applicable; all detected pages are included."
            selection_text = "ALL pages from the supplied PDF image b64 directory"
            range_rule = (
                "The attached images represent all detected pages for this PDF. "
                "Treat the complete included page set as one combined evidence chunk."
            )
        else:
            center_page_text = str(page_selection)
            selection_text = f"center-page window around page {page_selection}"
            range_rule = (
                f"The intended page window is n-2 through n+2 around center page {page_selection}. "
                "Pages that do not exist or are unavailable are omitted."
            )

        schema = ExtractionPromptBuilder._format_table_schema()
        controlled_values = ExtractionPromptBuilder._format_controlled_values()

        return f"""
You are extracting structured evidence from screenshots of a sepsis-related academic paper.

The goal is to populate exactly two spreadsheet-like tables:

1. study_cohort_level_records
2. predictor_model_level_records

Target PDF file:
{pdf_file}

Page selection mode:
{selection_text}

Center page used to form the range:
{center_page_text}

Requested extraction page range:
{requested_range_text}

Actually included pages:
{included_pages_text}

Important extraction rule:
{range_rule}

You must inspect ordinary text and visual content, including tables, plots, charts, diagrams, ROC curves, Kaplan-Meier plots, captions, labels, legends, and footnotes.

Return ONLY valid JSON.
Do not include markdown.
Do not include commentary.
Do not include explanations outside the JSON.
Do not include source_info.
Do not add extra keys.
Do not use null.
Do not use empty strings.

Return exactly this JSON structure:

{schema}

If no relevant evidence is visible on the included pages, return:

{{
  "study_cohort_level_records": [],
  "predictor_model_level_records": []
}}

Missing-value rules:
- Use "Not reported" when the paper does not report a value or the value is not visible.
- Use "NA" only when the field is genuinely not applicable.
- Preserve exact numeric values, units, confidence intervals, p-values, labels, group names, time horizons, and model names.
- Do not calculate values unless the calculated value is explicitly printed in the source.
- Do not guess.
- Do not invent values.

Controlled values and field rules:

{controlled_values}

TABLE 1: study_cohort_level_records

One object in study_cohort_level_records equals one row in the study/cohort-level table.

Create a separate study_cohort_level_record for every distinct:
- total cohort
- survivor group
- non-survivor group
- derivation cohort
- validation cohort
- training set
- testing set
- ICU subgroup
- non-ICU subgroup
- externally validated cohort
- any other analytically distinct cohort or subgroup

The columns must mean:

1. cohort_id
   - Use a concise unique row identifier.
   - Preferred format: FirstAuthor Year Dataset/Cohort/Subgroup.
   - Examples:
     - Gai 2022 Total Cohort
     - Wang 2023 MIMIC-III Training set
     - Zhang 2021 MIMIC-IV Development set, Survivors
     - Seymour 2016 UPMC ICU Validation cohort

2. papers
   - Use FirstAuthor Year.
   - Example: Gai 2022.

3. doi
   - Extract DOI if visible.

4. encounters_period
   - Extract study years, encounter years, database years, enrollment period, or collection period.

5. population_location
   - Extract hospital, city, country, region, or database location.

6. data_sets
   - Extract named database or dataset.
   - Examples: MIMIC-III, MIMIC-IV, UPMC, KPNC, ALERTS.

7. detailed_study_design_description
   - Extract concise study design.
   - Include imputation, derivation, validation, training/testing split, or prospective/retrospective status if visible.

8. population_description
   - Extract clinical population and inclusion context.
   - Example: Adult patients with Sepsis-3 admitted to ICU.

9. cohort
   - Extract the cohort/subgroup label.
   - Examples: Total Cohort, Survivors, Training set, Validation set.

10. cohort_size_n
   - Extract N for that exact cohort/subgroup.
   - Preserve paper wording if inconsistent.

11. cohort_characteristics
   - Extract compact baseline characteristics for that exact cohort/subgroup.
   - Use semicolon-separated format.
   - Include age, sex, severity scores, lactate, ventilation, comorbidities, or other characteristics if visible.
   - Do not create separate rows for each characteristic.

12. cohort_characteristics_timepoint
   - Extract when the characteristics were measured.

13. mortality_rate_percent
   - Extract mortality percentage or exact mortality count/rate for the cohort.

14. mortality_timepoint
   - Extract mortality horizon.
   - Examples: In-ICU, In-Hospital Mortality, 28-day mortality, 30-day mortality, 1-year mortality.

TABLE 2: predictor_model_level_records

One object in predictor_model_level_records equals one row in the predictor/model-level table.

Create a separate predictor_model_level_record whenever any of these changes:
- cohort_id
- predictor
- timing of predictor measurement
- outcome
- model specification
- effect size
- performance result
- p-value
- confidence interval
- cutoff

Do not merge multiple predictors into one row if they have separate ORs, AUCs, p-values, CIs, sensitivities, specificities, or model specifications.

The columns must mean:

1. cohort_id
   - Must match the related study_cohort_level_records.cohort_id when possible.
   - If the matching cohort row is not visible on these pages, still construct the best cohort_id from visible paper/cohort information.

2. predictors
   - Extract the exact predictor, score, biomarker, model, clinical variable, cutoff, or composite model.
   - Examples:
     - APACHE II score
     - SOFA score
     - Lactate
     - qSOFA
     - LDH + Age + Gender + Ethnicity + Potassium
     - Race, Age, Mechanical ventilation, Lactate, Temperature, SBP, SpO2, BUN, WBC, Ca, HR, RR, INR

3. timing_of_predictor_measurement
   - Extract when the predictor was measured.
   - Example: Within 24h of ICU admission.

4. outcome
   - Extract the predicted endpoint.
   - Examples:
     - 28-day mortality
     - In-Hospital Mortality
     - One-year mortality
     - In-hospital mortality

5. model_specification
   - Extract statistical method/model exactly and concisely.
   - Include model number, adjustment set, algorithm, comparison type, or validation type if visible.
   - Examples:
     - Univariate logistic regression (Model 1)
     - Multivariate logistic regression (Model 2)
     - ROC
     - Univariate ROC
     - XGBoost without specification/coefficients
     - Naive model, Comparison of survivors vs deaths, Univariate analysis

6. effect_size_performance_and_significance
   - Extract all reported effect/performance/significance information for that exact row.
   - Preserve OR, HR, RR, beta, CI, p-value, AUC/AUROC, sensitivity, specificity, PPV, NPV, accuracy, cut-off, calibration, NRI, IDI, and group comparison values.
   - Preferred order:
     Effect size; confidence interval; p-value; AUC/AUROC; sensitivity; specificity; accuracy; PPV; NPV; cutoff; other metrics.
   - Example:
     OR 1.449 (95% CI 1.208-1.738), p<0.001; AUC: 0.83 (95% CI 0.76-0.90)

Critical behavior:
- Extract every visible table row that matches either target table.
- Keep study/cohort rows and predictor/model rows separate.
- Do not summarize the whole paper into one row.
- Do not create baseline-characteristic records outside study_cohort_level_records.
- Do not add confidence scores.
- Do not add source_info.
- The final JSON must contain only the two arrays.
""".strip()