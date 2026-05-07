from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

# ==========================================
# 1. THE NEW, GRANULAR SCHEMA
# ==========================================
class ClinicalEvidence(BaseModel):
    study: str = Field(description="Study author and year (e.g., 'Leona 2025').")
    population: str = Field(description="Patient population characteristics (e.g., 'Abdominal sepsis after surgery').")
    sample_size: str = Field(description="Sample size details (e.g., 'N=147 ED; N=238 ICU; N=123 survivors').")
    predictor: str = Field(description="The clinical variable or biomarker being measured.")
    outcome: str = Field(description="The clinical outcome being predicted.")
    timing: str = Field(description="When the predictor was measured.")
    method: str = Field(description="Statistical method used (e.g., 'ROC analysis', 'Multivariable logistic regression').")
    effect_size: str = Field(description="Effect size or cutoffs (e.g., 'Cutoff 0.8x10^9', 'OR 2.5').")
    performance: str = Field(description="Performance metrics (e.g., 'AUC 0.78 (95% CI 0.72-0.93), Sens 0.9, Spec 0.8, p<0.001').")
    notes: str = Field(description="Any additional relevant notes, rules, or context (e.g., 'Youden rule used'). If none, output 'None'.")

class ExtractionResult(BaseModel):
    evidence_list: List[ClinicalEvidence]

# ==========================================
# 2. THE EXTRACTION FUNCTION
# ==========================================
def extract_sepsis_data_granular(chunk_text):
    llm = ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=API_KEY, 
        model="anthropic/claude-sonnet-4.6", 
        temperature=0
    )
    
    structured_llm = llm.with_structured_output(ExtractionResult)
    
    system_prompt = """
    You are an expert AI clinical evidence assistant building a 'Sepsis Atlas'.
    Extract structured data from the provided scientific paper excerpts.
    
    CRITICAL INSTRUCTIONS:
    1. Only extract data explicitly stated in the text.
    2. If a specific field is missing, you MUST output 'Not reported'. Do not guess.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Extract the clinical evidence from this text:\n\n{text}")
    ])
    
    chain = prompt | structured_llm
    return chain.invoke({"text": chunk_text})

# ==========================================
# 3. CUSTOM FORMATTER TO MATCH YOUR TARGET
# ==========================================
def print_as_text_block(evidence_item, metadata):
    # We build the "Source" line by combining the LLM's chunk metadata
    source_line = f"{metadata.get('source_file', 'Unknown')} (p.{metadata.get('page', 'X')}) - {metadata.get('chunk_id', '')}"
    
    formatted_block = f"""
Study: {evidence_item.study}
Population: {evidence_item.population}
Sample Size: {evidence_item.sample_size}
Predictor: {evidence_item.predictor}
Outcome: {evidence_item.outcome}
Timing: {evidence_item.timing}
Method: {evidence_item.method}
Effect Size: {evidence_item.effect_size}
Performance: {evidence_item.performance}
Notes: {evidence_item.notes}
Source: {source_line}
--------------------------------------------------"""
    print(formatted_block)

# ==========================================
# 4. TEST IT OUT
# ==========================================
if __name__ == "__main__":
    test_chunk = """
    In a recent 2025 study by Leona et al. investigating abdominal sepsis after surgery in Japan, 
    we evaluated 238 ICU patients and 147 ED patients (123 survivors). Lymphocyte count was measured 
    within the first 24h after diagnosis. ROC analysis for 28-day mortality showed that using a cutoff 
    of 0.8x10^9, the performance was strong (AUC 0.78, 95% CI 0.72-0.93, Sens 0.9, Spec 0.8, p<0.001). 
    Optimal thresholds were determined using the Youden rule.
    """
    
    # Simulating the metadata we get from your chunker script
    mock_metadata = {
        "source_file": "Leona_2025.pdf",
        "page": 4,
        "chunk_id": "page_4_p_2"
    }
    
    result = extract_sepsis_data_granular(test_chunk)
    
    for item in result.evidence_list:
        print_as_text_block(item, mock_metadata)
  
    
    
