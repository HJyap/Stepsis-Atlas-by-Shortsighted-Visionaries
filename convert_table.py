import json
import pandas as pd
import os

# Your list of files
FILES_TO_PROCESS = [
    "Luo_2022.json",
    "Besen_2016.json",
    "Ren_2022.json",
    "Suttapanit_2022.json",
    "Wen_2019.json"
    # ... add the rest of your files here ...
]

# Directory where your JSON files are stored
# (Leave as "" if they are in the same folder as this script)
JSON_DIR = "/Users/hongjayyap/Stepsis-Atlas-by-Shortsighted-Visionaries/extractions" 

def extract_row_data(json_data, filename):
    """
    Maps the nested JSON data to flat table columns.
    Use the .get() method so the script doesn't crash if a paper is missing a specific field.
    """
    
    # Safely extract nested dictionaries if they exist
    demographics = json_data.get("patient_demographics", {})
    methodology = json_data.get("methodologies", {})
    
    # Create a single dictionary representing one row in your table
    row = {
        # Study Identification
        "Filename": filename,
        "Author (Year)": json_data.get("author_year", "Unknown"), 
        
        # Study Characteristics (Table 1 from your images)
        "Study Design": methodology.get("study_design", "N/A"),
        "Study Population": demographics.get("population_description", "N/A"),
        "Sample Size (N)": demographics.get("sample_size", "N/A"),
        "Age (Years)": demographics.get("age", "N/A"),
        "Male (%)": demographics.get("male_percentage", "N/A"),
        
        # Clinical Details & Interventions (Table 2 from your images)
        "Diagnostic Criteria": json_data.get("diagnostic_criteria", "N/A"),
        "Pathogens": json_data.get("pathogens", "N/A"),
        "Intervention/Treatment": json_data.get("intervention", "N/A"),
        "Control/Comparison": json_data.get("control", "N/A"),
        
        # Outcomes
        "Efficacy Outcomes": json_data.get("efficacy_outcomes", "N/A"),
        "Safety Outcomes": json_data.get("safety_outcomes", "N/A"),
        "Main Findings/Conclusions": json_data.get("conclusions", "N/A")
    }
    
    # Clean up lists if the JSON extracted items as arrays instead of strings
    for key, value in row.items():
        if isinstance(value, list):
            row[key] = ", ".join([str(item) for item in value])
            
    return row

def main():
    table_data = []
    
    print(f"Processing {len(FILES_TO_PROCESS)} files...")
    
    for filename in FILES_TO_PROCESS:
        filepath = os.path.join(JSON_DIR, filename)
        
        if not os.path.exists(filepath):
            print(f"Warning: Could not find {filename}. Skipping.")
            continue
            
        with open(filepath, 'r', encoding='utf-8') as file:
            try:
                data = json.load(file)
                
                # FIX: Check if the JSON is a list or a single dictionary
                if isinstance(data, list):
                    # If it's a list, loop through each item in the list
                    for item in data:
                        # Make sure the item is actually a dictionary before extracting
                        if isinstance(item, dict):
                            row_data = extract_row_data(item, filename)
                            table_data.append(row_data)
                elif isinstance(data, dict):
                    # If it's already a single dictionary, process it normally
                    row_data = extract_row_data(data, filename)
                    table_data.append(row_data)
                else:
                    print(f"Warning: {filename} contains unexpected data format.")
                    
            except json.JSONDecodeError:
                print(f"Error: {filename} is not a valid JSON file.")

    # Convert the list of dictionaries into a pandas DataFrame
    df = pd.DataFrame(table_data)
    
    # Export to CSV (Great for quick viewing or importing to other tools)
    csv_filename = "extracted_studies_summary.csv"
    df.to_csv(csv_filename, index=False, encoding='utf-8')
    print(f"\nSuccess! Data exported to {csv_filename}")
    
    # Export to Excel (Great for formatting, freezing panes, and sharing)
    excel_filename = "extracted_studies_summary.xlsx"
    df.to_excel(excel_filename, index=False)
    print(f"Success! Data exported to {excel_filename}")

if __name__ == "__main__":
    main()