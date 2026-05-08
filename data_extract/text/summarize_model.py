import os
import json
import time
from typing import List
from pathlib import Path

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv


start_time = time.time()

# Load API key from root .env
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent
ENV_PATH = ROOT_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=False)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


# ==========================================
# HYPERPARAMETER: Choose LLM Provider
# ==========================================
# Set to "google" or "openrouter" ONLY
LLM_PROVIDER = "google"

GOOGLE_MODEL = "gemini-2.5-flash"
OPENROUTER_MODEL = "anthropic/claude-sonnet-4.5"


def get_llm():
    if LLM_PROVIDER == "google":
        if not GOOGLE_API_KEY:
            raise ValueError("Missing GOOGLE_API_KEY or GEMINI_API_KEY in .env")

        return ChatGoogleGenerativeAI(
            model=GOOGLE_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=0,
        )

    if LLM_PROVIDER == "openrouter":
        if not OPENROUTER_API_KEY:
            raise ValueError("Missing OPENROUTER_API_KEY in .env")

        return ChatOpenAI(
            model=OPENROUTER_MODEL,
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            temperature=0,
        )

    raise ValueError("LLM_PROVIDER must be either 'google' or 'openrouter'")


# ==========================================
# 1. PYDANTIC SCHEMAS (Enforcing the Structure)
# ==========================================
class StudyCohortRecord(BaseModel):
    cohort_id: str = Field(description="Free text; must match cohort_id used in predictor_model_level_records. E.g., 'Tartaglia_2021_Total'")
    papers: str = Field(description="Free text; format: FirstAuthor Year")
    doi: str = Field(description="Free text; DOI or NA")
    encounters_period: str = Field(description="Free text; year range or NA")
    population_location: str = Field(description="Free text")
    data_sets: str = Field(description="Free text; database/cohort name or blank/NA")
    detailed_study_design_description: str = Field(description="MUST use controlled vocabulary for study design or 'Other: [exact text]'.")
    population_description: str = Field(description="Free text")
    cohort: str = Field(description="MUST use controlled vocabulary for cohort or 'Other: [exact text]'.")
    cohort_size_n: str = Field(description="Free text; number preferred, but keep paper wording if inconsistent")
    cohort_characteristics: str = Field(description="Free text; compact semicolon-separated summary or NA")
    cohort_characteristics_timepoint: str = Field(description="MUST use controlled vocabulary for cohort timepoint or 'Other: [exact text]'.")
    mortality_rate_percent: str = Field(description="Free text; percentage, NA, or exact paper wording")
    mortality_timepoint: str = Field(description="MUST use controlled vocabulary for mortality timepoint or 'Other: [exact text]'.")


class PredictorModelRecord(BaseModel):
    cohort_id: str = Field(description="Free text; MUST exactly match the cohort_id generated in study_cohort_level_records")
    predictors: str = Field(description="Free text; exact predictor/model/score/variable name from paper")
    timing_of_predictor_measurement: str = Field(description="MUST use controlled vocabulary for predictor measurement timing or 'Other: [exact text]'.")
    outcome: str = Field(description="MUST use controlled vocabulary for outcome or 'Other: [exact text]'.")
    model_specification: str = Field(description="MUST use controlled vocabulary for model specification or 'Other: [exact text]'.")
    effect_size_performance_and_significance: str = Field(description="Free text; preserve OR/AUC/CI/p-value/sensitivity/specificity/accuracy exactly")


class ArticleRelationalSummary(BaseModel):
    study_cohort_level_records: List[StudyCohortRecord]
    predictor_model_level_records: List[PredictorModelRecord]


# ==========================================
# 2. LLM EXTRACTION ENGINE
# ==========================================
def extract_article_data(text_content: str) -> dict:
    """Passes the combined chunk text to the LLM for structured extraction."""

    llm = get_llm()
    print(f"  → Using {LLM_PROVIDER.upper()}...")
    return _extract_with_llm(llm, text_content)


def _extract_with_llm(llm, text_content: str) -> dict:
    """Helper function to extract data using the provided LLM."""

    structured_llm = llm.with_structured_output(ArticleRelationalSummary)

    system_prompt = """
    You are an expert clinical data extractor. Your job is to extract study and predictive model data from the provided clinical paper excerpts and format them into a relational database schema.

    CRITICAL INSTRUCTIONS:
    1. For the `cohort_id`, generate a unique ID (e.g., "Author_Year_CohortName") and use it consistently across both tables to link predictors to their cohort.
    2. YOU MUST strictly use the following controlled vocabularies where applicable. If the text does not match perfectly, use the "Other: [exact text]" format.

    CONTROLLED VOCABULARIES:
    - detailed_study_design_description: ["Prospective observational study", "Retrospective cohort study", "Retrospective cohort; Multiple imputation of missing data", "Retrospective cohort; Internal validation; Multiple imputation of missing data", "Retrospective cohort study; development and validation", "Retrospective cohort study; internal split into training and testing sets", "Case-control study", "Prospective cohort study", "External validation study", "Not reported", "Other: [exact text]"]
    - cohort: ["Total Cohort", "Overall cohort", "Survivors", "Non-survivors", "Training set", "Testing set", "Development set", "Validation set", "Derivation cohort", "ICU Validation cohort", "External validation cohort", "non-ICU", "ICU", "Other: [exact text]"]
    - cohort_characteristics_timepoint: ["Within 24h of ICU admission", "Within 24 hours of ICU admission", "At ICU admission", "First ICU day", "Within 48h of ICU admission", "Within 24h of hospital admission", "At hospital admission", "At ED admission", "Maximum value from 48h before to 24h after infection onset", "Baseline", "During ICU stay", "Not reported", "Other: [exact text]"]
    - mortality_timepoint: ["In-ICU", "ICU mortality", "In-Hospital Mortality", "In-hospital mortality", "Hospital mortality", "28-day mortality", "30-day mortality", "60-day mortality", "90-day mortality", "1-year mortality", "One-year mortality", "NA", "Not reported", "Other: [exact text]"]
    - timing_of_predictor_measurement: ["Within 24h of ICU admission", "Within 24 hours of ICU admission", "At ICU admission", "First ICU day", "Within 48h of ICU admission", "At ED admission", "Within 24h of ED admission", "At hospital admission", "Within 24h of hospital admission", "Maximum score from 48h before to 24h after infection onset", "Assessed in window from 48h before to 24h after infection onset", "Baseline", "During ICU stay", "Not reported", "Other: [exact text]"]
    - outcome: ["ICU mortality", "In-ICU mortality", "In-Hospital Mortality", "In-hospital mortality", "Hospital mortality", "28-day mortality", "30-day mortality", "60-day mortality", "90-day mortality", "One-year mortality", "1-year mortality", "Sepsis diagnosis", "Septic shock", "Organ dysfunction", "AKI", "ICU length of stay", "Hospital length of stay", "Not reported", "Other: [exact text]"]
    - model_specification: ["Univariate logistic regression", "Univariate logistic regression (Model 1)", "Multivariate logistic regression", "Multivariable logistic regression", "Multivariate logistic regression (Model 2)", "Multivariable logistic regression (Model I)", "Multivariable logistic regression (Model II)", "Multivariable logistic regression (Model III)", "ROC", "Univariate ROC", "ROC analysis", "ROC for Logistic multivariable regression", "Nomogram", "Nomogram, Multivariable logistic regression", "XGBoost", "XGBoost without specification", "XGBoost without specification/coefficients", "Naive model, Comparison of survivors vs deaths, Univariate analysis", "Group comparison", "Sub-cohort mortality", "Not reported", "Other: [exact text]"]
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Extract the relational clinical evidence from the following chunks of a paper:\n\n{text}")
    ])

    chain = prompt | structured_llm
    result = chain.invoke({"text": text_content})
    return result.model_dump()


# ==========================================
# 3. DATA PROCESSING SCRIPT
# ==========================================
def process_chunks_to_relational_db(input_mapping_file, chunks_dir, output_dir):
    """Reads the mapping file, concatenates required chunks per article, and extracts data."""

    os.makedirs(output_dir, exist_ok=True)

    with open(input_mapping_file, "r", encoding="utf-8") as f:
        mapping_data = json.load(f)

    # Group the chunks by article
    articles_map = {}

    for item in mapping_data:
        source_json = item["source_json"]
        chunk_id = item["chunk_id"]

        if source_json not in articles_map:
            articles_map[source_json] = set()

        articles_map[source_json].add(chunk_id)

    print(f"🚀 Found {len(articles_map)} unique articles to process.\n")

    for source_json, required_chunk_ids in articles_map.items():
        chunk_file_path = os.path.join(chunks_dir, source_json)

        if not os.path.exists(chunk_file_path):
            print(f"⚠️ Warning: Could not find chunk file {chunk_file_path}. Skipping.")
            continue

        with open(chunk_file_path, "r", encoding="utf-8") as f:
            all_chunks = json.load(f)

        # Combine text from targeted chunks
        combined_text = f"--- SOURCE: {source_json} ---\n\n"

        for chunk in all_chunks:
            if chunk.get("metadata", {}).get("chunk_id") in required_chunk_ids:
                combined_text += f"[{chunk['metadata']['section']} - Page {chunk['metadata']['page']}]\n"
                combined_text += chunk.get("chunk_text", "") + "\n\n"

        if not combined_text.strip():
            print(f"⚠️ No matching chunk text found for {source_json}. Skipping.")
            continue

        print(f"🧠 Extracting relational data for {source_json} using {LLM_PROVIDER.upper()}...")

        try:
            extracted_json = extract_article_data(combined_text)

            # Save the resulting JSON file
            output_filename = source_json.replace("_chunks.json", ".json")
            output_path = os.path.join(output_dir, output_filename)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(extracted_json, f, indent=4, ensure_ascii=False)

            print(f"✨ Saved: {output_filename}")

        except Exception as e:
            print(f"❌ Error processing {source_json}: {e}")

    print("\n🎉 ALL ARTICLES PROCESSED SUCCESSFULLY!")


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # ==========================================
    # USER'S SPECIFIC DIRECTORY PATHS
    # ==========================================

    INPUT_MAPPING = os.path.abspath(os.path.join(BASE_DIR, "../extract_input.json"))
    CHUNKS_DIRECTORY = os.path.abspath(os.path.join(BASE_DIR, "./chunks"))
    OUTPUT_DIRECTORY = os.path.abspath(os.path.join(BASE_DIR, "../text_extract_output"))

    process_chunks_to_relational_db(
        INPUT_MAPPING,
        CHUNKS_DIRECTORY,
        OUTPUT_DIRECTORY,
    )

    print("--- %s seconds ---" % (time.time() - start_time))