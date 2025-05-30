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
        
        # Extract questions using regex patterns
        questions = self._extract_questions(cleaned_text, subject, diagrams)
        
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
            
            # Convert PIL image to OpenCV format
            open_cv_image = np.array(img)
            open_cv_image = open_cv_image[:, :, ::-1].copy()  # Convert RGB to BGR
            
            # In a real implementation, this would use computer vision to detect diagrams
            # For now, we'll just note that diagrams were processed
            
            # Store diagram information (placeholder)
            page_num = i + 1
            if page_num >= 3:  # Skip cover and formula pages
                # This is a placeholder. In a real implementation, we would:
                # 1. Detect diagram regions using CV
                # 2. Extract diagram images
                # 3. Associate with nearby question text
                # 4. Store references to the extracted images
                pass
        
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
            r'National\s+5\s+Mathematics',
            r'National\s+5\s+Applications\s+of\s+Mathematics',
            r'SQA\s+\|',
            r'Scottish\s+Qualifications\s+Authority',
            r'FORMULAE\s+LIST',
            r'YOU\s+MAY\s+(?:NOT\s+)?USE\s+A\s+CALCULATOR'
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove multiple newlines and whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'\s{2,}', ' ', text)
        
        return text.strip()
    
    def _extract_questions(self, text, subject, diagrams):
        """
        Extract questions from cleaned text using regex patterns.
        
        Args:
            text (str): Cleaned text
            subject (str): Subject of the exam
            diagrams (dict): Dictionary of diagram information
            
        Returns:
            list: Extracted questions
        """
        questions = []
        
        # Pattern to match main question numbers (e.g., "1.", "2.", etc.)
        main_question_pattern = r'(?:^|\n)(\d+)\.\s+(.*?)(?=(?:^|\n)\d+\.\s+|\Z)'
        
        # Find all main questions
        main_matches = re.finditer(main_question_pattern, text, re.DOTALL | re.MULTILINE)
        
        for match in main_matches:
            question_number = match.group(1)
            question_text = match.group(2).strip()
            
            # Check if the question has sub-parts
            sub_part_pattern = r'(?:^|\n)\s*\(([a-z])\)\s+(.*?)(?=(?:^|\n)\s*\([a-z]\)\s+|\Z)'
            sub_matches = re.finditer(sub_part_pattern, question_text, re.DOTALL | re.MULTILINE)
            
            sub_parts = list(sub_matches)
            
            if sub_parts:
                # Extract the main question text (before any sub-parts)
                main_text = question_text
                for sub in sub_parts:
                    # Remove sub-part text from main text
                    sub_text = sub.group(0)
                    main_text = main_text.replace(sub_text, '').strip()
                
                # Process each sub-part
                for sub in sub_parts:
                    sub_letter = sub.group(1)
                    sub_text = sub.group(2).strip()
                    
                    # Format question number as per user's example: "5. (a)"
                    formatted_number = f"{question_number}. ({sub_letter})"
                    
                    # Create question object
                    question = self._create_question_object(
                        formatted_number, 
                        sub_text,
                        subject,
                        diagrams.get(f"{question_number}.{sub_letter}", [])
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
                    diagrams.get(question_number, [])
                )
                
                questions.append(question)
        
        return questions
    
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
                "has_diagram": bool(diagrams),
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
            r'\\frac\{[^}]+\
(Content truncated due to size limit. Use line ranges to read in chunks)