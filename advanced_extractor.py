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
        self.questions = []
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
        
        # Process each PDF file
        for filename in os.listdir(input_dir):
            if filename.endswith('.PDF') or filename.endswith('.pdf'):
                pdf_path = os.path.join(input_dir, filename)
                
                # Determine subject from filename
                subject = self._determine_subject(filename)
                if not subject:
                    logger.warning(f"Could not determine subject for {filename}, skipping")
                    continue
                
                # Extract questions from the PDF
                self.extract_from_pdf(pdf_path, subject)
                
                # Save extracted questions to JSON
                output_file = os.path.join(output_dir, f"{subject}_questions.json")
                self.save_to_json(output_file)
                
                logger.info(f"Processed {filename}, extracted {len(self.questions)} questions")
                
                # Reset for next file
                self.questions = []
                self.images = []
                self.page_images = []
    
    def extract_from_pdf(self, pdf_path, subject):
        """
        Extract questions from a single PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
            subject (str): Subject of the exam (Mathematics or Applications of Mathematics)
        """
        logger.info(f"Extracting questions from: {pdf_path}")
        
        # Set current paper information
        self.current_paper = os.path.basename(pdf_path)
        
        # Convert PDF pages to images for OCR and diagram extraction
        self.page_images = convert_from_path(pdf_path, dpi=300)
        
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
        
        # Process the extracted text to identify questions
        self._process_text(all_text, subject)
    
    def _process_text(self, text, subject):
        """
        Process the extracted text to identify and structure questions.
        
        Args:
            text (str): Extracted text from the PDF
            subject (str): Subject of the exam
        """
        # Remove headers and footers
        text = self._remove_headers_footers(text)
        
        # Split text into potential question blocks
        # Look for patterns like "1.", "2.", etc. at the beginning of lines
        question_pattern = r'(?:\n|\A)(\d+)\.\s'
        question_blocks = re.split(question_pattern, text)
        
        # The first element is text before the first question, discard if not relevant
        if not re.match(r'^\d+$', question_blocks[0]):
            question_blocks = question_blocks[1:]
        
        # Process question blocks in pairs (number and content)
        for i in range(0, len(question_blocks), 2):
            if i+1 < len(question_blocks):
                question_number = question_blocks[i]
                question_content = question_blocks[i+1]
                
                # Process the question content
                self._process_question(question_number, question_content, subject)
    
    def _process_question(self, number, content, subject):
        """
        Process a single question block to extract question parts and metadata.
        
        Args:
            number (str): Question number
            content (str): Question content text
            subject (str): Subject of the exam
        """
        # Clean up the content
        content = content.strip()
        
        # Check if the question has parts (a), (b), etc.
        parts_pattern = r'(?:\n|\A)\s*\(([a-z])\)\s'
        if re.search(parts_pattern, content):
            # Split into parts
            parts_blocks = re.split(parts_pattern, content)
            
            # The first element is text before the first part
            main_text = parts_blocks[0].strip()
            
            # Process each part
            for j in range(1, len(parts_blocks), 2):
                if j+1 < len(parts_blocks):
                    part_letter = parts_blocks[j]
                    part_content = parts_blocks[j+1].strip()
                    
                    # Create a formatted question number (e.g., "5.(a)")
                    formatted_number = f"{number}.({part_letter})"
                    
                    # Extract marks, topic, and other metadata
                    marks = self._extract_marks(part_content)
                    topic = self._determine_topic(part_content, subject)
                    
                    # Extract any diagrams or images
                    diagrams = self._extract_diagrams(number, part_letter)
                    
                    # Extract math expressions
                    math_expressions = self._extract_math_expressions(part_content)
                    
                    # Create question object
                    question = {
                        "question_number": formatted_number,
                        "text": part_content,
                        "marks": marks,
                        "topic": topic,
                        "metadata": {
                            "marks": marks,
                            "units": self._extract_units(part_content),
                            "instructions": self._extract_instructions(part_content),
                            "has_diagram": len(diagrams) > 0,
                            "associated_formulae": math_expressions
                        },
                        "diagrams": diagrams
                    }
                    
                    self.questions.append(question)
        else:
            # No parts, process as a single question
            # Extract marks, topic, and other metadata
            marks = self._extract_marks(content)
            topic = self._determine_topic(content, subject)
            
            # Extract any diagrams or images
            diagrams = self._extract_diagrams(number)
            
            # Extract math expressions
            math_expressions = self._extract_math_expressions(content)
            
            # Create question object
            question = {
                "question_number": f"{number}.",
                "text": content,
                "marks": marks,
                "topic": topic,
                "metadata": {
                    "marks": marks,
                    "units": self._extract_units(content),
                    "instructions": self._extract_instructions(content),
                    "has_diagram": len(diagrams) > 0,
                    "associated_formulae": math_expressions
                },
                "diagrams": diagrams
            }
            
            self.questions.append(question)
    
    def _remove_headers_footers(self, text):
        """
        Remove standard headers and footers from the extracted text.
        
        Args:
            text (str): Extracted text from the PDF
            
        Returns:
            str: Text with headers and footers removed
        """
        # Remove common headers and footers
        patterns = [
            r'MARKS\s+DO\s+NOT\s+WRITE\s+IN\s+THIS\s+MARGIN',
            r'page\s+\d+',
            r'National\s+5\s+Mathematics',
            r'National\s+5\s+Applications\s+of\s+Mathematics',
            r'SQA\s+\|',
            r'Scottish\s+Qualifications\s+Authority',
            r'FORMULAE\s+LIST',
            r'YOU\s+MAY\s+(?:NOT\s+)?USE\s+A\s+CALCULATOR'
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove page markers (but keep track of them for diagram extraction)
        text = re.sub(r'\[PAGE_\d+\]', '', text)
        
        # Remove multiple newlines and whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'\s{2,}', ' ', text)
        
        return text.strip()
    
    def _extract_marks(self, text):
        """
        Extract the number of marks from question text.
        
        Args:
            text (str): Question text
            
        Returns:
            int: Number of marks, or None if not found
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
            subject (str): Subject of the exam
            
        Returns:
            str: Topic category
        """
        # Define keywords for each topic
        topics = {
            "algebraic": ["equation", "expression", "simplify", "expand", "factorise", "solve"],
            "equations": ["equation", "solve", "solution", "unknown", "variable"],
            "trigonometry": ["sine", "cosine", "tangent", "angle", "triangle", "sin", "cos", "tan"],
            "geometry": ["circle", "triangle", "rectangle", "square", "polygon", "area", "volume", "perimeter"],
            "statistics": ["mean", "median", "mode", "range", "standard deviation", "probability", "data"]
        }
        
        # Check for topic keywords in the text
        for topic, keywords in topics.items():
            for keyword in keywords:
                if re.search(r'\b' + keyword + r'\b', text, re.IGNORECASE):
                    return topic
        
        # Default to "other" if no specific topic is identified
        return "other"
    
    def _extract_units(self, text):
        """
        Extract units from question text.
        
        Args:
            text (str): Question text
            
        Returns:
            str: Units, or empty string if not found
        """
        # Common units in mathematics questions
        units_pattern = r'(?:cm|m|km|g|kg|s|h|min|°|degrees|radians|litres|L|ml)'
        units_match = re.search(units_pattern, text, re.IGNORECASE)
        
        if units_match:
            return units_match.group(0)
        
        return ""
    
    def _extract_instructions(self, text):
        """
        Extract instructions from question text.
        
        Args:
            text (str): Question text
            
        Returns:
            str: Instructions, or empty string if not found
        """
        # Look for common instruction phrases
        instruction_patterns = [
            r'(Calculate[^.]*\.)',
            r'(Find[^.]*\.)',
            r'(Determine[^.]*\.)',
            r'(Express[^.]*\.)',
            r'(Solve[^.]*\.)',
            r'(Simplify[^.]*\.)',
            r'(Expand[^.]*\.)',
            r'(Factorise[^.]*\.)',
            r'(Write down[^.]*\.)',
            r'(Show that[^.]*\.)'
        ]
        
        for pattern in instruction_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        # If no specific instruction is found, return the first sentence
        first_sentence = re.match(r'([^.]*\.)', text)
        if first_sentence:
            return first_sentence.group(1).strip()
        
        return ""
    
    def _extract_diagrams(self, question_number, part_letter=None):
        """
        Extract diagrams associated with a question.
        
        Args:
            question_number (str): Question number
            part_letter (str, optional): Part letter for sub-questions
            
        Returns:
            list: List of diagram references
        """
        # In a real implementation, this would extract and save diagrams
        # For now, return empty list as placeholder
        return []
    
    def _extract_math_expressions(self, text):
        """
        Extract mathematical expressions from question text.
        
        Args:
            text (str): Question text
            
        Returns:
            list: List of mathematical expressions
        """
        # In a real implementation, this would use specialized math OCR
        # For now, use simple regex to identify potential math expressions
        math_patterns = [
            r'\b\w+\s*=\s*[\w\d\+\-\*\/\^\(\)]+',  # Equations like "y = 2x + 3"
            r'\\frac\{[^}]+\}\{[^}]+\}',  # LaTeX fractions
            r'\b\w+\^[0-9]+',  # Exponents like "x^2"
            r'\\sqrt\{[^}]+\}'  # Square roots
        ]
        
        expressions = []
        for pattern in math_patterns:
            matches = re.findall(pattern, text)
            expressions.extend(matches)
        
        return expressions
    
    def _determine_subject(self, filename):
        """
        Determine the subject from the filename.
        
        Args:
            filename (str): PDF filename
            
        Returns:
            str: Subject name or None if not determined
        """
        if "Mathematics_Paper" in filename or "Mathematics-Paper" in filename:
            return "Mathematics"
        elif "Applications-of-Mathematics" in filename or "Applications_of_Mathematics" in filename:
            return "Applications_of_Mathematics"
        else:
  
(Content truncated due to size limit. Use line ranges to read in chunks)