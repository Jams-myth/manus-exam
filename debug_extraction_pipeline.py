"""
Debug PDF Extraction Module with Detailed Logging

This module focuses on debugging the PDF extraction process by examining
the raw text content, cleaned text, and regex matches for question segmentation.
"""

import os
import re
import json
import PyPDF2
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_extraction_pipeline(pdf_path, output_dir):
    """
    Debug the extraction pipeline with detailed logging of each step.
    
    Args:
        pdf_path (str): Path to the PDF file
        output_dir (str): Directory to save the debug output
    """
    logger.info(f"Debugging extraction pipeline for: {pdf_path}")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Get filename without extension
    filename = os.path.basename(pdf_path)
    base_name = os.path.splitext(filename)[0]
    
    # Create debug output file
    debug_file = os.path.join(output_dir, f"{base_name}_debug.txt")
    
    with open(debug_file, 'w', encoding='utf-8') as f:
        f.write(f"=== Extraction Pipeline Debug for {filename} ===\n\n")
        
        # Extract text using PyPDF2
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            f.write(f"Total Pages: {len(pdf_reader.pages)}\n\n")
            
            # Skip cover page and formula sheet (usually first 2 pages)
            start_page = 2
            
            # Process each page
            all_text = ""
            for page_num in range(start_page, len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                
                f.write(f"--- PAGE {page_num + 1} RAW TEXT ---\n\n")
                f.write(text)
                f.write("\n\n")
                
                # Add page number marker for later processing
                all_text += f"\n\n[PAGE_{page_num+1}]\n\n{text}"
            
            # Clean the text
            f.write("--- CLEANING TEXT ---\n\n")
            cleaned_text = clean_text(all_text)
            f.write(cleaned_text)
            f.write("\n\n")
            
            # Look for question numbers
            f.write("--- SEARCHING FOR MAIN QUESTIONS ---\n\n")
            main_question_pattern = r'(?:^|\n)\s*(\d+)\.\s+'
            main_matches = re.finditer(main_question_pattern, cleaned_text, re.MULTILINE)
            
            for match in main_matches:
                question_number = match.group(1)
                start_pos = match.end()
                match_text = cleaned_text[match.start():match.start()+50] + "..."  # Show context
                
                f.write(f"Found question {question_number} at position {match.start()}\n")
                f.write(f"Context: {match_text}\n\n")
            
            # Look for sub-parts
            f.write("--- SEARCHING FOR SUB-PARTS ---\n\n")
            sub_part_pattern = r'(?:^|\n)\s*\(([a-z])\)\s+'
            sub_matches = re.finditer(sub_part_pattern, cleaned_text, re.MULTILINE)
            
            for match in sub_matches:
                part_letter = match.group(1)
                start_pos = match.end()
                match_text = cleaned_text[match.start():match.start()+50] + "..."  # Show context
                
                f.write(f"Found part ({part_letter}) at position {match.start()}\n")
                f.write(f"Context: {match_text}\n\n")
    
    logger.info(f"Debug output saved to: {debug_file}")
    return debug_file

def clean_text(text):
    """
    Clean the extracted text by removing headers, footers, and other noise.
    
    Args:
        text (str): Raw extracted text
        
    Returns:
        str: Cleaned text
    """
    # Remove common headers and footers
    patterns = [
        r'MARKS\s+DO\s+NOT\s+WRITE\s+IN\s+THIS\s+MARGIN',
        r'page\s+\d+',
        r'National\s+Qualifications',
        r'National\s+5\s+Mathematics',
        r'National\s+5\s+Applications\s+of\s+Mathematics',
        r'SQA\s+\|',
        r'Scottish\s+Qualifications\s+Authority',
        r'FORMULAE\s+LIST',
        r'YOU\s+MAY\s+(?:NOT\s+)?USE\s+A\s+CALCULATOR',
        r'\*X\d+\*',
        r'ADDITIONAL\s+SPACE\s+FOR\s+ANSWERS',
        r'DO\s+NOT\s+WRITE\s+ON\s+THIS\s+PAGE',
        r'\[BLANK\s+PAGE\]'
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Remove multiple newlines and whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'\s{2,}', ' ', text)
    
    return text.strip()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python debug_extraction_pipeline.py <pdf_file> <output_directory>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2]
    
    debug_extraction_pipeline(pdf_path, output_dir)
