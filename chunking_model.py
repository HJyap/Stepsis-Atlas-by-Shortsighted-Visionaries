import fitz 
import json
import os
import re
import pandas as pd
import pymupdf4llm
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

def process_sepsis_by_paragraph(pdf_path, output_json_path, doi="Not reported"):
    text_with_metadata = []
    
    if not os.path.exists(pdf_path):
        print(f"❌ Error: Could not find '{pdf_path}'. Make sure it is in the same folder!")
        return []

    doc = fitz.open(pdf_path)
    
    for page_num, page in enumerate(doc):
        # 🔥 THE SECRET WEAPON: Extract by "blocks" to natively handle multi-column layouts!
        blocks = page.get_text("blocks")
        
        page_text_blocks = []
        for block in blocks:
            # block[6] identifies the type of content (0 = text, 1 = image)
            # We only want text blocks, completely ignoring images and background noise
            if block[6] == 0:
                block_text = block[4].strip()
                
                if block_text:
                    # Cleanup: Fix mid-sentence breaks within the specific block
                    cleaned_block = block_text.replace('\n', ' ')
                    page_text_blocks.append(cleaned_block)
        
        if page_text_blocks:
            # Reconstruct the page text by joining the blocks with actual paragraph breaks
            reconstructed_page = '\n\n'.join(page_text_blocks)
            
            # 🔥 ACADEMIC CLEANER: Remove citation brackets like [1], [12-15], [1, 2]
            reconstructed_page = re.sub(r'\[\d+(?:-\d+)?(?:,\s*\d+)*\]', '', reconstructed_page)
            
            # Remove any lingering double spaces left behind by the deleted citations
            reconstructed_page = re.sub(r'\s{2,}', ' ', reconstructed_page).strip()
            
            text_with_metadata.append({
                "text": reconstructed_page,
                "metadata": {
                    "source_file": os.path.basename(pdf_path),
                    "doi": doi,
                    "page": page_num + 1
                }
            })
            
    # Close the document
    doc.close()
                
    # 3. Configure the Splitter for Paragraphs
    paragraph_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500, 
        chunk_overlap=200, 
        separators=["\n\n", "(?<=\\. )", "\n", " "],
        keep_separator=False
    )
    
    # 4. Apply the split and keep the traceability metadata
    final_chunks = []
    for item in text_with_metadata:
        chunks = paragraph_splitter.split_text(item["text"])
        for i, chunk_text in enumerate(chunks):
            # Ignore tiny fragments or blank chunks
            if len(chunk_text.strip()) > 10:
                final_chunks.append({
                    "chunk_text": chunk_text.strip(),
                    "metadata": {
                        **item["metadata"],
                        "chunk_id": f"page_{item['metadata']['page']}_p_{i+1}"
                    }
                })
            
    # 5. Save the chunks to a JSON file
    with open(output_json_path, 'w', encoding='utf-8') as json_file:
        json.dump(final_chunks, json_file, indent=4, ensure_ascii=False)
        
    return final_chunks

def process_sepsis_markdown(pdf_path, output_json_path, doi="Not reported"):
    if not os.path.exists(pdf_path):
        print(f"❌ Error: Could not find '{pdf_path}'.")
        return []

    # 1. 🔥 THE FIX: Convert to Markdown page-by-page to keep track of page numbers!
    md_pages = pymupdf4llm.to_markdown(pdf_path, page_chunks=True)

    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    
    # 2000 chars ensures we don't chop tables in half
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000, 
        chunk_overlap=200
    )

    final_chunks = []
    chunk_counter = 1
    
    # 2. Loop through each page individually
    for index, page_data in enumerate(md_pages):
        # Extract the markdown text
        md_text = page_data["text"]
        
        # We manually calculate the exact page number (index starts at 0, so we add 1)
        page_num = index + 1
        
        # Clean up the citations [1], [1-3]
        md_text = re.sub(r'\[\d+(?:-\d+)?(?:,\s*\d+)*\]', '', md_text)

        # Split by headers within this specific page
        md_header_splits = markdown_splitter.split_text(md_text)

        for split in md_header_splits:
            # Split into chunks of 2000 characters
            chunks = text_splitter.split_text(split.page_content)
            
            for chunk_text in chunks:
                if len(chunk_text.strip()) > 10:
                    final_chunks.append({
                        "chunk_text": chunk_text.strip(),
                        "metadata": {
                            "source_file": os.path.basename(pdf_path),
                            "doi": doi,
                            "page": page_num,  # 🎯 INJECTED PAGE NUMBER HERE!
                            "section": split.metadata.get("Header 2", "General"),
                            "chunk_id": f"page_{page_num}_chunk_{chunk_counter}" # Updated ID
                        }
                    })
                    chunk_counter += 1

    # Save to JSON
    with open(output_json_path, 'w', encoding='utf-8') as json_file:
        json.dump(final_chunks, json_file, indent=4, ensure_ascii=False)
        
    return final_chunks

if __name__ == "__main__":
    INPUT_FOLDER = "/Users/hongjayyap/Stepsis-Atlas-by-Shortsighted-Visionaries/articles"  
    OUTPUT_FOLDER = "/Users/hongjayyap/Stepsis-Atlas-by-Shortsighted-Visionaries/chunks"
    EXCEL_FILE = os.path.join(INPUT_FOLDER, "Sepsis3_papers.xlsx")
    
    print("📊 Loading DOI metadata from Excel...")
    try:
        df = pd.read_excel(EXCEL_FILE)
        # Create a dictionary mapping like: {'Baloch_2022.pdf': '10.7759/cureus.21055'}
        doi_lookup = dict(zip(df['File name'], df['doi']))
        print(f"✅ Loaded {len(doi_lookup)} DOI mappings.")
    except Exception as e:
        print(f"⚠️ Warning: Could not load Excel file. Error: {e}")
        doi_lookup = {}

    print("-" * 40)
    
    # 1. Safety check: Create the 'chunks' folder if it doesn't exist yet!
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"📁 Created output folder: {OUTPUT_FOLDER}")

    # 2. Loop through every file in the articles folder
    for filename in os.listdir(INPUT_FOLDER):
        # Only process PDF files
        if filename.lower().endswith(".pdf"):
            input_pdf_path = os.path.join(INPUT_FOLDER, filename)
            
            base_name = os.path.splitext(filename)[0]
            
            output_json_path = os.path.join(OUTPUT_FOLDER, f"{base_name}.json")
            
            file_doi = doi_lookup.get(filename, "Not reported")
            
            print(f"🚀 Reading '{filename}' (DOI: {file_doi})...")
            
            chunks = process_sepsis_markdown(input_pdf_path, output_json_path, doi=file_doi)
            
            if chunks:
                print(f"✅ Success: {len(chunks)} chunks saved to '{base_name}.json'")
                print("-" * 40)
            else:
                print(f"⚠️ Warning: No chunks extracted from '{filename}'.")
                print("-" * 40)
                
    print("🎉 ALL ARTICLES PROCESSED! Your chunks are ready for extraction.")
