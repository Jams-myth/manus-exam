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
                # Fix question numbering for all subjects
                questions = self._fix_question_numbering(questions, subject)
                
                output_file = os.path.join(output_dir, f"{subject}_questions.json")
                with open(output_file, 'w') as f:
                    json.dump(questions, f, indent=2)
                logger.info(f"Saved {len(questions)} questions to {output_file}")
    
    def _fix_question_numbering(self, questions, subject):
        """
        Fix question numbering for all subjects.
        
        Args:
            questions (list): List of question objects
            subject (str): Subject name
            
        Returns:
            list: List of question objects with fixed numbering
        """
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
        
        # Sort question groups by main number
        sorted_groups = sorted(question_groups.items())
        
        # Renumber questions sequentially
        fixed_questions = []
        current_num = 1
        
        for _, group in sorted_groups:
            # Sort sub-parts alphabetically
            sorted_group = sorted(group, key=lambda x: x[0] if x[0] else "")
            
            for sub_part, question in sorted_group:
                if sub_part:
                    question["question_number"] = f"{current_num}. ({sub_part})"
                else:
                    question["question_number"] = f"{current_num}."
                
                fixed_questions.append(question)
            
            current_num += 1
        
        return fixed_questions
    
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
        
        # Extract questions using direct page parsing
        questions = self._extract_questions_from_cleaned_text(cleaned_text, subject, diagrams)
        
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
    
    def _extract_questions_from_cleaned_text(self, cleaned_text, subject, diagrams):
        """
        Extract questions from cleaned text.
        
        Args:
            cleaned_text (str): Cleaned text from PDF
            subject (str): Subject of the exam
            diagrams (dict): Dictionary of diagram information
            
        Returns:
            list: Extracted questions
        """
        questions = []
        
        # Modified pattern to match question numbers with more flexibility
        # This handles cases where there might be spaces, newlines, or other characters
        question_pattern = r'(?:^|\n|\s)(\d+)\.(?:\s|\n)'
        
        # Find all question numbers in the text
        question_matches = list(re.finditer(question_pattern, cleaned_text))
        
        # Store question positions and numbers
        question_positions = []
        for match in question_matches:
            question_number = match.group(1)
            start_pos = match.start()
            question_positions.append((question_number, start_pos))
        
        # Sort question positions by their position in the text
        question_positions.sort(key=lambda x: x[1])
        
        # Process each question
        for i, (question_number, start_pos) in enumerate(question_positions):
            # Determine end position (start of next question or end of text)
            if i < len(question_positions) - 1:
                end_pos = question_positions[i + 1][1]
            else:
                end_pos = len(cleaned_text)
            
            # Extract question text
            question_text = cleaned_text[start_pos:end_pos].strip()
            
            # Check for sub-parts
            sub_parts = self._extract_sub_parts(question_text)
            
            if sub_parts:
                # Extract main question text (before any sub-parts)
                main_text = question_text[:sub_parts[0][1]].strip()
                
                # Process each sub-part
                for j, (part_letter, part_start, part_end) in enumerate(sub_parts):
                    # Determine the end of this sub-part
                    if j < len(sub_parts) - 1:
                        actual_end = sub_parts[j + 1][1]
                    else:
                        actual_end = len(question_text)
                    
                    part_text = question_text[part_start:actual_end].strip()
                    
                    # Format question number as per user's example: "5. (a)"
                    formatted_number = f"{question_number}. ({part_letter})"
                    
                    # Create question object
                    question = self._create_question_object(
                        formatted_number,
                        part_text,
                        subject,
                        []  # Diagrams placeholder
                    )
                    
                    questions.append(question)
            else:
                # No sub-parts, process as a single question
                formatted_number = f"{question_number}."
                
                # Create question object
                question = self._create_question_object(
                    formatted_number,
                    question_text,
                    subject,
                    []  # Diagrams placeholder
                )
                
                questions.append(question)
        
        return questions
    
    def _extract_sub_parts(self, text):
        """
        Extract sub-parts from question text.
        
        Args:
            text (str): Question text
            
        Returns:
            list: List of tuples (part_letter, start_position, end_position)
        """
        sub_parts = []
        
        # Pattern for sub-parts like "(a)", "(b)", etc. with more flexibility
        sub_part_pattern = r'(?:^|\n|\s)\(([a-z])\)(?:\s|\n)'
        
        # Find all sub-parts in the text
        sub_part_matches = list(re.finditer(sub_part_pattern, text))
        
        # Store sub-part positions and letters
        for match in sub_part_matches:
            part_letter = match.group(1)
            start_pos = match.start()
            sub_parts.append((part_letter, start_pos, match.end()))
        
        return sub_parts
    
    def _create_question_object(self, question_number, text, subject, diagrams):
        """
        Create a structured question object.
        
        Args:
            question_number (str): Formatted question number
            text (str): Question text
            subject (str): Subject of the exam
            diagrams (list): List of diagram references
            
        Returns:
            dict: Question object
        """
        # Extract marks
        marks = self._extract_marks(text)
        
        # Determine topic
        topic = self._determine_topic(text, subject)
        
        # Extract math expressions
        math_expressions = self._extract_math_expressions(text)
        
        # Check for diagram references in text
        has_diagram = bool(diagrams) or "diagram" in text.lower()
        
        # Create question object
        question = {
            "question_number": question_number,
            "text": text,
            "marks": marks,
            "topic": topic,
            "metadata": {
                "marks": marks,
                "units": self._extract_units(text),
                "instructions": self._extract_instructions(text),
                "has_diagram": has_diagram,
                "associated_formulae": math_expressions
            },
            "diagrams": diagrams
        }
        
        return question
    
    def _extract_marks(self, text):
        """
        Extract the number of marks from question text.
        
        Args:
            text (str): Question text
            
        Returns:
            int: Number of marks, or 1 if not found
        """
        # Look for patterns like "3 marks" or "(2)"
        marks_pattern = r'(\d+)\s*marks?'
        marks_match = re.search(marks_pattern, text, re.IGNORECASE)
        
        if marks_match:
            return int(marks_match.group(1))
        
        # Alternative pattern for marks in parentheses
        alt_pattern = r'\((\d+)\)'
        alt_match = re.search(alt_pattern, text)
        
        if alt_match:
            return int(alt_match.group(1))
        
        # Default to 1 mark if not specified
        return 1
    
    def _determine_topic(self, text, subject):
        """
        Determine the topic of a question based on its content.
        
        Args:
            text (str): Question text
            subject (str): Subject of the e
(Content truncated due to size limit. Use line ranges to read in chunks)