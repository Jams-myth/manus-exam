"""
Debug PDF Extraction Module for Scottish National 5 Exam Papers

This module focuses on debugging the PDF extraction process by examining
the raw text content extracted from the PDFs before any processing.
"""

import os
import PyPDF2
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_pdf_extraction(pdf_path, output_dir):
    """
    Extract raw text from PDF and save to a text file for debugging.
    
    Args:
        pdf_path (str): Path to the PDF file
        output_dir (str): Directory to save the extracted text
    """
    logger.info(f"Debugging PDF extraction for: {pdf_path}")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Get filename without extension
    filename = os.path.basename(pdf_path)
    base_name = os.path.splitext(filename)[0]
    
    # Extract text using PyPDF2
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        
        # Create output file
        output_file = os.path.join(output_dir, f"{base_name}_raw_text.txt")
        
        with open(output_file, 'w', encoding='utf-8') as out_file:
            # Write header
            out_file.write(f"=== Raw Text Extraction from {filename} ===\n\n")
            out_file.write(f"Total Pages: {len(pdf_reader.pages)}\n\n")
            
            # Process each page
            for page_num, page in enumerate(pdf_reader.pages):
                out_file.write(f"--- PAGE {page_num + 1} ---\n\n")
                
                try:
                    text = page.extract_text()
                    out_file.write(text)
                except Exception as e:
                    out_file.write(f"ERROR extracting text: {str(e)}")
                
                out_file.write("\n\n")
        
        logger.info(f"Raw text extraction saved to: {output_file}")
        
        return output_file

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python debug_pdf_extraction.py <pdf_file> <output_directory>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2]
    
    debug_pdf_extraction(pdf_path, output_dir)
