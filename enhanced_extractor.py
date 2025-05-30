"""
Advanced PDF Extraction Module for Scottish National 5 Exam Papers

This module implements a comprehensive approach to extract questions, diagrams,
mathematical notation, and metadata from Scottish National 5 exam papers.

Based on detailed guidance for handling:
- Question numbering and structure (main questions and sub-parts)
- Mathematical notation and formulas
- Diagrams and images
- Metadata extraction
"""

import os
import re
import json
import PyPDF2
from pathlib import Path
import logging
import cv2
import numpy as np
from pdf2image import convert_from_path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedPDFExtractor:
    """
    Advanced PDF extractor for Scottish National 5 exam papers.
    Handles question extraction, structure, math notation, and diagrams.
    """
    
    def __init__(self):
        """Initialize the PDF extractor with default settings."""
        self.current_paper = None
        self.calculator_allowed = None
        self.questions = {}  # Dictionary to store questions by subject
        self.images = []
        self.page_images = []
        
    def extract_from_directory(self, input_dir, output_dir):
        """
        Process all PDF files in a directory and extract questions.
        
        Args:
            input_dir (str): Directory containing PDF files
            output_dir (str): Directory to save extracted questions
        """
        logger.info(f"Processing PDFs from directory: {input_dir}")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize questions dictionary
        self.questions = {
            "Mathematics": [],
            "Applications_of_Mathematics": []
        }
        
        # Process each PDF file
        for filename in os.listdir(input_dir):
            if filename.endswith('.PDF') or filename.endswith('.pdf'):
                pdf_path = os.path.join(input_dir, filename)
                
                # Skip marking instruction files
                if filename.startswith('mi_'):
                    logger.info(f"Skipping marking instruction file: {filename}")
                    continue
                
                # Determine subject from filename
                subject = self._determine_subject(filename)
                if not subject:
                    logger.warning(f"Could not determine subject for {filename}, skipping")
                    continue
                
                # Extract questions from the PDF
                extracted_questions = self.extract_from_pdf(pdf_path, subject)
                
                # Add extracted questions to the appropriate subject
                self.questions[subject].extend(extracted_questions)
                
                logger.info(f"Extracted {len(extracted_questions)} questions from {filename}")
        
        # Save extracted questions to JSON files by subject
        for subject, questions in self.questions.items():
            if questions:
                output_file = os.path.join(output_dir, f"{subject}_questions.json")
                with open(output_file, 'w') as f:
                    json.dump(questions, f, indent=2)
                logger.info(f"Saved {len(questions)} questions to {output_file}")
    
    def extract_from_pdf(self, pdf_path, subject):
        """
        Extract questions from a single PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
            subject (str): Subject of the exam (Mathematics or Applications of Mathematics)
            
        Returns:
            list: Extracted questions
        """
        logger.info(f"Extracting questions from: {pdf_path}")
        
        # Set current paper information
        self.current_paper = os.path.basename(pdf_path)
        
        # Convert PDF pages to images for OCR and diagram extraction
        self.page_images = convert_from_path(pdf_path, dpi=300)
        
        # Process images for potential diagrams
        diagrams = self._process_images_for_diagrams(pdf_path)
        
        # Extract text using PyPDF2
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Determine if calculator is allowed from first page
            first_page_text = pdf_reader.pages[0].extract_text()
            self.calculator_allowed = "You may use a calculator" in first_page_text
            
            # Skip cover page and formula sheet (usually first 2 pages)
            start_page = 2
            
            # Process each page
            all_text = ""
            for page_num in range(start_page, len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                
                # Add page number marker for later processing
                all_text += f"\n\n[PAGE_{page_num+1}]\n\n{text}"
        
        # Clean the text
        cleaned_text = self._clean_text(all_text)
        
        # Create debug output directory
        debug_dir = os.path.join(os.path.dirname(pdf_path), "debug")
        os.makedirs(debug_dir, exist_ok=True)
        
        # Save cleaned text for debugging
        debug_file = os.path.join(debug_dir, f"{os.path.basename(pdf_path)}_cleaned.txt")
        with open(debug_file, 'w') as f:
            f.write(cleaned_text)
        
        # Use enhanced hierarchical extraction with debugging
        questions = self._enhanced_hierarchical_extraction(cleaned_text, subject, diagrams, debug_dir, pdf_path)
        
        return questions
    
    def _process_images_for_diagrams(self, pdf_path):
        """
        Process PDF pages to identify and extract potential diagrams.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            dict: Dictionary mapping question numbers to diagram information
        """
        diagrams = {}
        
        # Process each page image
        for i, img in enumerate(self.page_images):
            logger.info(f"Processed page {i+1} for diagrams")
            
            # In a real implementation, this would use computer vision to detect diagrams
            # For now, we'll just note that diagrams were processed
            
        return diagrams
    
    def _clean_text(self, text):
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
            r'\[BLANK\s+PAGE\]',
            r'\[Turn over\]',
            r'\[END OF QUESTION PAPER\]'
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove multiple newlines and whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'\s{2,}', ' ', text)
        
        return text.strip()
    
    def _enhanced_hierarchical_extraction(self, cleaned_text, subject, diagrams, debug_dir, pdf_path):
        """
        Enhanced hierarchical extraction with improved debugging and validation.
        
        Args:
            cleaned_text (str): Cleaned text from PDF
            subject (str): Subject of the exam
            diagrams (dict): Dictionary of diagram information
            debug_dir (str): Directory for debug output
            pdf_path (str): Path to the original PDF file
            
        Returns:
            list: Extracted questions
        """
        questions = []
        debug_output = []
        
        # First pass: Find all main questions with more robust pattern
        # This pattern looks for question numbers at the start of lines or after clear breaks
        main_question_pattern = r'(?:^|\n|\s)(\d+)\.(?:\s|\n)'
        main_matches = list(re.finditer(main_question_pattern, cleaned_text))
        
        debug_output.append(f"=== MAIN QUESTION MATCHES ===")
        for match in main_matches:
            context = cleaned_text[max(0, match.start()-20):min(len(cleaned_text), match.end()+50)]
            debug_output.append(f"Question {match.group(1)} at position {match.start()}: {context}")
        
        # If no main questions found, try alternative patterns
        if not main_matches:
            debug_output.append("No main questions found with primary pattern, trying alternatives...")
            
            # Alternative patterns that might match question numbers
            alt_patterns = [
                r'(?:^|\n)(\d+)\s*\.',  # Number at start of line with possible space before dot
                r'(?:^|\n)\s*(\d+)\.',  # Number with leading whitespace at start of line
                r'(?<=\n)(\d+)\.'       # Number after newline
            ]
            
            for pattern in alt_patterns:
                alt_matches = list(re.finditer(pattern, cleaned_text))
                if alt_matches:
                    debug_output.append(f"Found {len(alt_matches)} matches with alternative pattern: {pattern}")
                    main_matches = alt_matches
                    break
        
        # If still no main questions found, return empty list
        if not main_matches:
            debug_output.append("ERROR: No main questions could be identified with any pattern.")
            
            # Save debug output
            debug_file = os.path.join(debug_dir, f"{os.path.basename(pdf_path)}_extraction_debug.txt")
            with open(debug_file, 'w') as f:
                f.write('\n'.join(debug_output))
            
            return questions
        
        # Process each main question
        for i, match in enumerate(main_matches):
            question_number = match.group(1)
            start_pos = match.start()
            
            # Determine end position (start of next main question or end of text)
            if i < len(main_matches) - 1:
                end_pos = main_matches[i + 1].start()
            else:
                end_pos = len(cleaned_text)
            
            # Extract main question text
            main_question_text = cleaned_text[start_pos:end_pos].strip()
            
            debug_output.append(f"\n=== MAIN QUESTION {question_number} ===")
            debug_output.append(f"Text: {main_question_text[:100]}...")
            
            # Second pass: Find all sub-parts within this main question
            sub_part_pattern = r'(?:^|\n|\s)\(([a-z])\)(?:\s|\n)'
            sub_matches = list(re.finditer(sub_part_pattern, main_question_text))
            
            debug_output.append(f"Found {len(sub_matches)} sub-parts")
            
            if sub_matches:
                # Process each sub-part
                for j, sub_match in enumerate(sub_matches):
                    part_letter = sub_match.group(1)
                    sub_start_pos = sub_match.start()
                    
                    # Determine end position of this sub-part
                    if j < len(sub_matches) - 1:
                        sub_end_pos = sub_matches[j + 1].start()
                    else:
                        sub_end_pos = len(main_question_text)
                    
                    # Extract sub-part text
                    sub_part_text = main_question_text[sub_start_pos:sub_end_pos].strip()
                    
                    # Format question number as per user's example: "5. (a)"
                    formatted_number = f"{question_number}. ({part_letter})"
                    
                    debug_output.append(f"  Sub-part {part_letter}: {formatted_number}")
                    debug_output.append(f"  Text: {sub_part_text[:50]}...")
                    
                    # Create question object
                    question = self._create_question_object(
                        formatted_number,
                        sub_part_text,
                        subject,
                        []  # Diagrams placeholder
                    )
                    
                    questions.append(question)
            else:
                # No sub-parts, process as a single question
                formatted_number = f"{question_number}."
                
                debug_output.append(f"No sub-parts, treating as single question: {formatted_number}")
                
                # Create question object
                question = self._create_question_object(
                    formatted_number,
                    main_question_text,
                    subject,
                    []  # Diagrams placeholder
                )
                
                questions.append(question)
        
        # Save debug output
        debug_file = os.path.join(debug_dir, f"{os.path.basename(pdf_path)}_extraction_debug.txt")
        with open(debug_file, 'w') as f:
            f.write('\n'.join(debug_output))
        
        # Validate and fix question numbering
        questions = self._validate_and_fix_numbering(questions, debug_dir, pdf_path)
        
        return questions
    
    def _validate_and_fix_numbering(self, questions, debug_dir, pdf_path):
        """
        Validate and fix question numbering to ensure sequential numbers and correct sub-parts.
        
        Args:
            questions (list): List of question objects
            debug_dir (str): Directory for debug output
            pdf_path (str): Path to the original PDF file
            
        Returns:
            list: List of question objects with fixed numbering
        """
        debug_output = ["=== QUESTION NUMBERING VALIDATION ==="]
        
        # Group questions by their main number
        question_groups = {}
        
        for question in questions:
            # Extract main number and sub-part
            parts = re.match(r'(\d+)\.(?:\s*\(([a-z])\))?', question["question_number"])
            if parts:
                main_num = int(parts.group(1))
                sub_part = parts.group(2) if parts.group(2) else ""
                
                if main_num not in question_groups:
                    question_groups[main_num] = []
                
                question_groups[main_num].append((sub_part, question))
                debug_output.append(f"Question {question['question_number']} -> Main: {main_num}, Sub: {sub_part}")
            else:
                debug_output.append(f"WARNING: Could not parse question number: {question['question_number']}")
        
        # Check for zero or missing main numbers
        if 0 in question_groups:
            debug_output.append(f"WARNING: Found {len(question_groups[0])} questions with main number 0")
            
            # If we have zero-numbered questions but no proper main numbers, 
            # try to infer main numbers from context
            if len(question_groups) <= 1:
                debug_output.append("Attempting to infer main numbers from context...")
                
                # Create new questions with inferred numbers
                fixed_questions = []
                current_num = 1
                
                for sub_part, question in sorted(question_groups[0], key=lambda x: x[0] if x[0] else ""):
 
(Content truncated due to size limit. Use line ranges to read in chunks)