from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import json
import os

import pymupdf4llm
from langchain_text_splitters import MarkdownHeaderTextSplitter


import pymupdf4llm
from langchain_text_splitters import MarkdownHeaderTextSplitter

def process_sepsis_paper_markdown(pdf_path):
    # 1. Convert PDF directly to Markdown (preserves tables and columns!)
    md_text = pymupdf4llm.to_markdown(pdf_path)
    
    # 2. Define headers we want to split on
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    
    # 3. Chunk the document semantically based on its sections
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(md_text)
    
    # 4. Add Hackathon-required Traceability Metadata
    for chunk in md_header_splits:
        chunk.metadata['source_file'] = pdf_path
        # You now have metadata like: {"source_file": "paper1.pdf", "Header 2": "Results"}
        
    return md_header_splits

# Run it
chunks = process_sepsis_paper_markdown("sample_sepsis_study.pdf")
print(f"Created {len(chunks)} smart chunks. First chunk metadata: {chunks[0].metadata}")
    
    
    
