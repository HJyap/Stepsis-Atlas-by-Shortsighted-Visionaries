import os
import re
import json
import time
from pydantic import BaseModel, Field
from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

VARIABLE_ONTOLOGY = {
    "mortality_rate": ["30-day mortality", "28-day mortality", "in-hospital mortality", "icu mortality", "1-year mortality"],
    "sofa_score": ["sofa", "p-sofa", "sequential organ failure assessment", "sofa score"],
    "age": ["age", "median age", "mean age"],
    "sample_size": ["n=", "number of patients", "total patients", "sample size"],
    "lactate": ["lactate", "serum lactate", "initial lactate", "lac"],
    "apache_ii": ["apache ii", "apache score", "acute physiology and chronic health evaluation"],
    "mechanical_ventilation": ["mechanical ventilation", "mv", "ventilator", "ventilator support"],
    "gender": ["gender", "sex", "male", "female", "man", "woman", "sex ratio", "male/female", "性别"],
    "icu_los": ["icu length of stay", "icu stay", "picu stay", "length of stay in icu", "icu los", "duration of icu stay", "icu住院天数", "picu住院天数"],
    "hospital_los": ["hospital length of stay", "hospital stay", "length of stay in hospital", "hospital los", "duration of hospitalization", "住院时间", "住院天数"],
    "septic_shock": ["septic shock", "septic shock patients", "shock", "脓毒性休克", "感染性休克"],
    "creatinine": ["creatinine", "serum creatinine", "cr", "肌酐", "血肌酐"],
    "platelets": ["platelet count", "platelets", "plt", "血小板", "血小板计数"],
    "bilirubin": ["bilirubin", "total bilirubin", "tbil", "胆红素", "总胆红素"],
    "albumin": ["albumin", "serum albumin", "alb", "白蛋白", "血清白蛋白"],
    "procalcitonin": ["procalcitonin", "pct", "降钙素原"],
    "vasopressor_use": ["vasopressor", "vasoactive agent", "vasopressor use", "vasopressor requirement", "inotrope", "norepinephrine", "dopamine", "血管活性药", "升压药"],
    "rrt_use": ["rrt", "renal replacement therapy", "dialysis", "crrt", "hemodialysis", "continuous renal replacement therapy", "肾脏替代治疗", "透析", "连续性肾脏替代治疗"],
    "sensitivity": ["sensitivity", "sn", "true positive rate", "灵敏度", "敏感性"],
    "specificity": ["specificity", "sp", "true negative rate", "特异度", "特异性"],
    "auc_value": ["auc", "area under curve", "area under the curve", "c-statistic", "roc area", "auroc"]
}

def normalize_text(text):
    if not text or text == "Not reported":
        return text
        
    text_lower = text.lower()
    
    # 🚨 List of dangerous short abbreviations that might hide in other words
    risky_abbr = ["sp", "sn", "cr", "mv", "lac", "plt", "alb", "pct", "rrt", "auc"]
    
    for standard_name, patterns in VARIABLE_ONTOLOGY.items():
        for pattern in patterns:
            if pattern in risky_abbr:
                # e.g., matches " sp " but ignores "hospital"
                if re.search(rf'\b{re.escape(pattern)}\b', text_lower):
                    return standard_name
            else:
                # Normal substring match for safe, longer phrases like "30-day mortality"
                if pattern in text_lower:
                    return standard_name
                    
    return text


class ClinicalEvidence(BaseModel):
    study: str = Field(description="Study author and year (e.g., 'Leona 2025').")
    population: str = Field(description="Patient population characteristics.")
    sample_size: str = Field(description="Sample size details (e.g., 'N=147').")
    cohort_age: str = Field(default="Not reported", description="Median/mean age of the cohort.")
    cohort_gender: str = Field(default="Not reported", description="Gender breakdown.")
    predictor: str = Field(description="The clinical variable or biomarker being measured.")
    outcome: str = Field(description="The clinical outcome being predicted.")
    timing: str = Field(description="When the predictor was measured.")
    method: str = Field(description="Statistical method used (e.g., 'ROC analysis').")
    effect_size: str = Field(description="Effect size or cutoffs (e.g., 'OR 2.5').")
    performance: str = Field(description="Performance metrics (e.g., 'AUC 0.78, p<0.001').")
    notes: str = Field(description="Relevant notes, rules, or context. If none, output 'None'.")

class ExtractionResult(BaseModel):
    evidence_list: List[ClinicalEvidence]

class Demographics(BaseModel):
    cohort_age: str = Field(description="The age of the patient cohort. If not found, output 'Not reported'.")
    cohort_gender: str = Field(description="The gender breakdown of the cohort. If not found, output 'Not reported'.")

def extract_sepsis_data(chunk_text):
    llm = ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=API_KEY, 
        model="anthropic/claude-sonnet-4.6", 
        temperature=0,
        default_headers={
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Sepsis Atlas Hackathon",    
        }
    )
    
    structured_llm = llm.with_structured_output(ExtractionResult)
    
    system_prompt = """
    You are an expert AI clinical evidence assistant building a 'Sepsis Atlas'.
    Your job is to extract structured data from the provided scientific paper excerpts.
    
    CRITICAL INSTRUCTIONS:
    1. ONLY extract the primary experimental findings of the current study. DO NOT extract data, sample sizes, or outcomes from referenced literature, background studies, or the Introduction/Discussion sections if they are discussing other authors' work.
    2. DO NOT extract planned variables from the Methodology or Statistical Analysis sections. Only extract actual statistical results and confirmed findings.
    3. Only extract data explicitly stated in the text or markdown tables.
    4. If a specific field is missing or a table cell is blank, you MUST output 'Not reported'. Do not guess or infer from surrounding rows.
    5. For Markdown tables: strictly respect the rows and columns. Match the correct effect size to the correct predictor.
    6. If an abbreviation is used (e.g., 'PSV') and not defined, extract the abbreviation exactly as written.
    7. Correct obvious OCR spelling errors.
    8. If the text does not contain any clinical predictors or actual outcomes, return an empty evidence_list.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Extract the clinical evidence from this text:\n\n{text}")
    ])
    
    chain = prompt | structured_llm
    return chain.invoke({"text": chunk_text})

def extract_demographics(paper_summary_text):
    """The Fast Retroactive Extractor"""
    llm = ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=API_KEY, 
        model="anthropic/claude-sonnet-4.6", # Switched to GPT-4o-mini for better JSON Schema reliability
        temperature=0
    )
    structured_llm = llm.with_structured_output(Demographics)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Extract the overall cohort age (mean/median) and gender breakdown from the provided clinical data summary. Keep it concise. If missing, say 'Not reported'."),
        ("human", "Here is a summary of the data extracted from the paper:\n\n{text}")
    ])
    
    try:
        return (prompt | structured_llm).invoke({"text": paper_summary_text})
    except Exception as e:
        print(f"\nLLM Extraction Error: {e}\n") # Now we will see if OpenRouter fails!
        return Demographics(cohort_age="Not reported", cohort_gender="Not reported")

def build_sepsis_atlas(input_chunks_file, output_atlas_file):
    with open(input_chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    master_atlas = []
    print(f"Starting Granular Extraction on {len(chunks)} chunks...")

    for i, chunk in enumerate(chunks):
        try:
            print(f"Processing chunk {i+1}/{len(chunks)}...")
            filename = chunk["metadata"].get("source_file", "Unknown Study")
            text_with_context = f"Source Document: {filename}\n\n{chunk['chunk_text']}"
            result = extract_sepsis_data(text_with_context)
            
            if result and result.evidence_list:
                for item in result.evidence_list:
                    entry = item.model_dump()
                    
                    entry["source_info"] = {
                        "file": chunk["metadata"].get("source_file", "Unknown"),
                        "doi": chunk["metadata"].get("doi", "Not reported"),
                        "section": chunk["metadata"].get("section", "General"),
                        "page": chunk["metadata"].get("page", "Unknown"),
                        "chunk": chunk["metadata"].get("chunk_id", "Unknown")
                    }
                    master_atlas.append(entry)

                    print(f"\nStudy: {entry['study']}")
                    print(f"Predictor: {entry['predictor']}")
                    print(f"Effect Size: {entry['effect_size']}")
                    print(f"Performance: {entry['performance']}")
                    print(f"Source: {entry['source_info']['file']} (DOI: {entry['source_info']['doi']} | p.{entry['source_info']['page']})")
                    print("-" * 50)
            else:
                print(f"⏩ No relevant clinical data found in chunk {i+1}. Skipping.")
                
            time.sleep(1.5)
                
        except Exception as e:
            print(f"Error at chunk {i+1}: {e}")
            time.sleep(3)

    with open(output_atlas_file, 'w', encoding='utf-8') as f:
        json.dump(master_atlas, f, indent=4, ensure_ascii=False)
        
    print(f"SUCCESS! Saved {len(master_atlas)} extracted rows to {output_atlas_file}")

def update_sepsis_atlas_file(input_extracted_file, output_standardized_file):
    """Retroactive Ontology, Demographics & Section Tracker Update"""
    if not os.path.exists(input_extracted_file):
        print(f"⚠️  Skipping {input_extracted_file} - file not found.")
        return

    with open(input_extracted_file, 'r', encoding='utf-8') as f:
        rows = json.load(f)

    # ==========================================
    # 🔥 THE NEW SECTION TRACKER (FORWARD-FILL)
    # ==========================================
    last_known_section = "Introduction" # Default starting point
    
    for row in rows:
        source_info = row.get("source_info", {})
        current_sec = source_info.get("section", "General")
        
        # If the chunker lost the section name, replace it with our memorized one!
        if current_sec == "General" or current_sec == "Unknown" or not current_sec:
            source_info["section"] = last_known_section
        else:
            # We found a real section heading! Memorize it for the next rows.
            last_known_section = current_sec
            
        row["source_info"] = source_info # Save it back to the row
    # ==========================================

    # 1. Build the summary for the LLM
    extracted_summary_lines = []
    for r in rows:
        pop = r.get("population", "")
        sz = r.get("sample_size", "")
        pred = r.get("predictor", "")
        eff = r.get("effect_size", "")
        line = f"Pop: {pop} | N: {sz} | Predictor: {pred} | Effect: {eff}"
        extracted_summary_lines.append(line)
        
    unique_summary_lines = list(set(extracted_summary_lines))
    combined_summary_text = "\n".join(unique_summary_lines)

    # 2. Extract Age & Gender ONCE per file
    print(f"\n🧠 Searching for Demographics in {os.path.basename(input_extracted_file)}...")
    if combined_summary_text:
        demographics = extract_demographics(combined_summary_text)
        print(f"   -> Found Age: {demographics.cohort_age}")
        print(f"   -> Found Gender: {demographics.cohort_gender}")
    else:
        demographics = Demographics(cohort_age="Not reported", cohort_gender="Not reported")

    # 3. 🔥 REBUILD EACH ROW IN THE EXACT REQUESTED ORDER
    ordered_rows = []
    for row in rows:
        # To handle if 'sample_size' was temporarily turned into a dict in our last step
        original_sample = row.get("sample_size", "Not reported")
        if isinstance(original_sample, dict):
            original_sample = original_sample.get("total", "Not reported")
            
        ordered_row = {
            "study": row.get("study", "Not reported"),
            "population": row.get("population", "Not reported"),
            "sample_size": original_sample,
            "cohort_age": demographics.cohort_age,
            "cohort_gender": demographics.cohort_gender,
            "predictor": row.get("predictor", "Not reported"),
            "predictor": normalize_text(row.get("predictor", "")),
            "outcome": row.get("outcome", "Not reported"),
            "outcome": normalize_text(row.get("outcome", "")),
            "timing": row.get("timing", "Not reported"),
            "method": row.get("method", "Not reported"),
            "effect_size": row.get("effect_size", "Not reported"),
            "performance": row.get("performance", "Not reported"),
            "notes": row.get("notes", "None"),
            "source_info": row.get("source_info", {})
        }
        ordered_rows.append(ordered_row)

    # Save output using the new perfectly ordered rows
    with open(output_standardized_file, 'w', encoding='utf-8') as f:
        json.dump(ordered_rows, f, indent=4, ensure_ascii=False)
    
    print(f"✨ Saved properly ordered file: {output_standardized_file}")



if __name__ == "__main__":
    CHUNKS_FOLDER = "/Users/hongjayyap/Stepsis-Atlas-by-Shortsighted-Visionaries/chunks" 
    EXTRACTIONS_FOLDER = "/Users/hongjayyap/Stepsis-Atlas-by-Shortsighted-Visionaries/extractions"
    STANDARDIZED_FOLDER = "/Users/hongjayyap/Stepsis-Atlas-by-Shortsighted-Visionaries/standardized_extractions"
        
    os.makedirs(STANDARDIZED_FOLDER, exist_ok=True)
    os.makedirs(EXTRACTIONS_FOLDER, exist_ok=True)
    # FILES_TO_PROCESS = "ALL" 
    
    FILES_TO_PROCESS = [
        "Park_2022.json",
        "Baloch_2022.json",
        "Besen_2016.json",
        "Bidart_2024.json",
        "Cao_2021.json",
        "Chen_2021.json",
        "Cilloniz_2019.json",
        "Gai_2022.json",
        "Gai_2022_chunks.json",
        "Holanda_2020.json",
        "Kochkin_2021.json",
        "Koozi_2023.json",
        "Kozlov_2022.json",
        "Li_2020.json",
        "Li_2024.json",
        "Liu_2019.json",
        "Luo_2022.json",
        "Ren_2022.json",
        "Roh_2019.json",
        "Schlapbach_2018.json",
        "Seymour_2016.json",
        "Suttapanit_2022.json",
        "Tang_2025.json",
        "Tartaglia_2021.json",
        "Todi_2024.json",
        "Varga_2024.json",
        "Wang_2020.json",
        "Wang_2023.json",
        "Wen_2019.json",
        "Zhang_2019.json",
        "Zhang_2021.json"
    ]

    print(f"Ready to process {len(FILES_TO_PROCESS)} file(s)...\n")

    for filename in FILES_TO_PROCESS:
        print(f"==================================================")
        print(f"Processing: {filename}")
        print(f"==================================================")
        
        chunk_file = os.path.join(CHUNKS_FOLDER, filename)
        extracted_file = os.path.join(EXTRACTIONS_FOLDER, filename)
        standardized_file = os.path.join(STANDARDIZED_FOLDER, filename)
        
        # 🟢 =======================================================
        # 🟢 THE TOGGLE ZONE: Comment/Uncomment what you want to run
        # 🟢 =======================================================
        
        # OPTION A: Run the heavy extraction (Chunks -> Extractions)
        # build_sepsis_atlas(chunk_file, extracted_file)
        
        # OPTION B: Run the fast ontology/demographic update (Extractions -> Standardized)
        update_sepsis_atlas_file(extracted_file, standardized_file)
        
    print("\nBATCH PROCESSING COMPLETE!")