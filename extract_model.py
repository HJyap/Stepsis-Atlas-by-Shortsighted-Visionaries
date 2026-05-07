import os
import json
import time
from pydantic import BaseModel, Field
from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

# ==========================================
# 1. THE SCHEMA
# ==========================================
class ClinicalEvidence(BaseModel):
    study: str = Field(description="Study author and year (e.g., 'Leona 2025').")
    population: str = Field(description="Patient population characteristics.")
    sample_size: str = Field(description="Sample size details (e.g., 'N=147').")
    predictor: str = Field(description="The clinical variable or biomarker being measured.")
    outcome: str = Field(description="The clinical outcome being predicted.")
    timing: str = Field(description="When the predictor was measured.")
    method: str = Field(description="Statistical method used (e.g., 'ROC analysis').")
    effect_size: str = Field(description="Effect size or cutoffs (e.g., 'OR 2.5').")
    performance: str = Field(description="Performance metrics (e.g., 'AUC 0.78, p<0.001').")
    notes: str = Field(description="Relevant notes, rules, or context. If none, output 'None'.")

class ExtractionResult(BaseModel):
    evidence_list: List[ClinicalEvidence]

# ==========================================
# 2. THE EXTRACTION ENGINE
# ==========================================
def extract_sepsis_data(chunk_text):
    llm = ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=API_KEY, 
        model="nvidia/nemotron-3-super-120b-a12b:free", # Updated to the valid OpenRouter tag
        temperature=0,
        default_headers={
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Sepsis Atlas Hackathon",    
        }
    )
    
    structured_llm = llm.with_structured_output(ExtractionResult)
    
    # 🔥 HACKATHON UPGRADE: Added rules for Markdown Tables and Blank Cells
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

# ==========================================
# 3. THE BATCH PROCESSOR
# ==========================================
def build_sepsis_atlas(input_chunks_file, output_atlas_file):
    with open(input_chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    master_atlas = []
    print(f"🚀 Starting Granular Extraction on {len(chunks)} chunks...")

    for i, chunk in enumerate(chunks):
        try:
            print(f"Processing chunk {i+1}/{len(chunks)}...")
            filename = chunk["metadata"].get("source_file", "Unknown Study")
            text_with_context = f"Source Document: {filename}\n\n{chunk['chunk_text']}"
            result = extract_sepsis_data(text_with_context)
            
            if result and result.evidence_list:
                for item in result.evidence_list:
                    # Merge LLM data with Chunker metadata
                    entry = item.model_dump()
                    
                    # 🔥 NEW: Injects DOI and Section along with the other metadata
                    entry["source_info"] = {
                        "file": chunk["metadata"].get("source_file", "Unknown"),
                        "doi": chunk["metadata"].get("doi", "Not reported"),
                        "section": chunk["metadata"].get("section", "General"),
                        "page": chunk["metadata"].get("page", "Unknown"),
                        "chunk": chunk["metadata"].get("chunk_id", "Unknown")
                    }
                    master_atlas.append(entry)

                    # Print to terminal to monitor progress
                    print(f"\nStudy: {entry['study']}")
                    print(f"Predictor: {entry['predictor']}")
                    print(f"Effect Size: {entry['effect_size']}")
                    print(f"Performance: {entry['performance']}")
                    print(f"Source: {entry['source_info']['file']} (DOI: {entry['source_info']['doi']} | p.{entry['source_info']['page']})")
                    print("-" * 50)
            else:
                print(f"⏩ No relevant clinical data found in chunk {i+1}. Skipping.")
                
            time.sleep(1.5) # OpenRouter rate limit protection
                
        except Exception as e:
            print(f"❌ Error at chunk {i+1}: {e}")
            time.sleep(3) # Back off on error

    # Save final JSON for your UI/Analysis
    with open(output_atlas_file, 'w', encoding='utf-8') as f:
        json.dump(master_atlas, f, indent=4, ensure_ascii=False)
        
    print(f"🎉 SUCCESS! Saved {len(master_atlas)} extracted rows to {output_atlas_file}")

# ==========================================
# 4. RUN IT!
# ==========================================
if __name__ == "__main__":
    INPUT_FOLDER = "/Users/hongjayyap/Stepsis-Atlas-by-Shortsighted-Visionaries/chunks" 
    OUTPUT_FOLDER = "/Users/hongjayyap/Stepsis-Atlas-by-Shortsighted-Visionaries/extractions/free_models"
    
    # 🔥 HACKATHON TIME-SAVER: Choose which files to extract!
    
    # Option 1: Extract everything in the folder
    # FILES_TO_PROCESS = "ALL" 
    
    # Option 2: Extract ONLY the files in this list
    FILES_TO_PROCESS = [
        "Park_2022.json",
        "Baloch_2022.json",
        # "Besen_2016.json",
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
        # "Luo_2022.json",
        # "Ren_2022.json",
        "Roh_2019.json",
        "Schlapbach_2018.json",
        "Seymour_2016.json",
        # "Suttapanit_2022.json",
        "Tang_2025.json",
        "Tartaglia_2021.json",
        "Todi_2024.json",
        "Varga_2024.json",
        "Wang_2020.json",
        "Wang_2023.json",
        # "Wen_2019.json",
        "Zhang_2019.json",
        "Zhang_2021.json"
    ]

    # 1. Safety check: Create the extractions folder if it doesn't exist
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"📁 Created output folder: {OUTPUT_FOLDER}")

    # 2. Filter the files based on your choice above
    if FILES_TO_PROCESS == "ALL":
        json_files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith('.json')]
    else:
        # Only process the files in your list (and double check they actually exist in the folder!)
        json_files = [f for f in FILES_TO_PROCESS if os.path.exists(os.path.join(INPUT_FOLDER, f))]

    print(f"🔍 Ready to process {len(json_files)} file(s)...\n")

    # 3. Loop through your selected files
    for filename in json_files:
        input_file_path = os.path.join(INPUT_FOLDER, filename)
        output_file_path = os.path.join(OUTPUT_FOLDER, filename)
        
        print(f"==================================================")
        print(f"📄 Starting extraction for: {filename}")
        print(f"==================================================")
        
        # Call your extraction engine
        build_sepsis_atlas(input_file_path, output_file_path)
        
    print("\n🎉 BATCH EXTRACTION COMPLETE! Your selected files are ready.")