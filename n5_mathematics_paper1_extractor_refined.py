"""
Document-Specific PDF Extraction for Scottish National 5 Mathematics Paper 1

This script is specifically designed to extract questions from the N5_Mathematics_Paper1-Non-calculator_2022.PDF
file, following the exact structure and formatting provided in user examples.
Handles special formatting and mathematical notation in the PDF.
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

class N5MathematicsPaper1Extractor:
    """
    Document-specific extractor for N5 Mathematics Paper 1 (Non-calculator) 2022.
    Follows the exact structure and formatting provided in user examples.
    Handles special formatting and mathematical notation.
    """
    
    def __init__(self, pdf_path, output_dir):
        """
        Initialize the extractor with paths.
        
        Args:
            pdf_path (str): Path to the PDF file
            output_dir (str): Directory to save extracted questions
        """
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.questions = []
        self.debug_dir = os.path.join(output_dir, "debug")
        os.makedirs(self.debug_dir, exist_ok=True)
    
    def extract_questions(self):
        """
        Extract questions from the PDF file.
        
        Returns:
            list: Extracted questions
        """
        logger.info(f"Extracting questions from: {self.pdf_path}")
        
        # Extract raw text from PDF
        raw_text = self._extract_raw_text()
        
        # Save raw text for debugging
        with open(os.path.join(self.debug_dir, "raw_text.txt"), "w", encoding="utf-8") as f:
            f.write(raw_text)
        
        # Clean the text
        cleaned_text = self._clean_text(raw_text)
        
        # Save cleaned text for debugging
        with open(os.path.join(self.debug_dir, "cleaned_text.txt"), "w", encoding="utf-8") as f:
            f.write(cleaned_text)
        
        # Extract questions using robust pattern matching
        self._extract_questions_from_text(cleaned_text)
        
        # Save extracted questions to JSON
        self._save_questions()
        
        return self.questions
    
    def _extract_raw_text(self):
        """
        Extract raw text from the PDF file.
        
        Returns:
            str: Raw text from PDF
        """
        raw_text = ""
        
        with open(self.pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Skip cover page and formula sheet (usually first 2 pages)
            start_page = 2
            
            # Process each page
            for page_num in range(start_page, len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                
                # Add page number marker for later processing
                raw_text += f"\n\n[PAGE_{page_num+1}]\n\n{text}"
        
        return raw_text
    
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
            r'MARKS\s*DO\s*NOT\s*WRITE\s*IN\s*THIS\s*MARGIN',
            r'page\s+\d+',
            r'National\s+Qualifications',
            r'National\s+5\s+Mathematics',
            r'SQA\s+\|',
            r'Scottish\s+Qualifications\s+Authority',
            r'FORMULAE\s+LIST',
            r'YOU\s+MAY\s+NOT\s+USE\s+A\s+CALCULATOR',
            r'\*X\d+\*',
            r'ADDITIONAL\s+SPACE\s+FOR\s+ANSWERS',
            r'DO\s+NOT\s+WRITE\s+ON\s+THIS\s+PAGE',
            r'\[BLANK\s+PAGE\]',
            r'\[END OF QUESTION PAPER\]'
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove multiple newlines and whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'\s{2,}', ' ', text)
        
        return text.strip()
    
    def _extract_questions_from_text(self, text):
        """
        Extract questions from cleaned text using robust pattern matching.
        
        Args:
            text (str): Cleaned text from PDF
        """
        # Split text into chunks by page markers
        page_chunks = re.split(r'\[PAGE_\d+\]', text)
        
        # Combine all chunks for processing
        combined_text = ' '.join(page_chunks)
        
        # Find all question numbers and their positions
        question_matches = list(re.finditer(r'(?:^|\s)(\d+)\.\s+([A-Z])', combined_text))
        
        # Find all sub-part markers and their positions
        subpart_matches = list(re.finditer(r'(?:^|\s)\(([a-z])\)\s+([A-Z])', combined_text))
        
        # Debug information
        debug_output = ["=== QUESTION EXTRACTION ==="]
        debug_output.append(f"Found {len(question_matches)} main questions")
        debug_output.append(f"Found {len(subpart_matches)} sub-parts")
        
        # Process each main question
        for i, match in enumerate(question_matches):
            question_num = match.group(1)
            start_pos = match.start()
            
            # Determine end position (start of next question or end of text)
            if i < len(question_matches) - 1:
                end_pos = question_matches[i + 1].start()
            else:
                end_pos = len(combined_text)
            
            # Extract question text
            question_text = combined_text[start_pos:end_pos].strip()
            
            # Find marks for this question
            marks_match = re.search(r'(?:^|\s)Marks\s+(\d+)', question_text)
            marks = int(marks_match.group(1)) if marks_match else 1
            
            # Find sub-parts within this question
            sub_parts = []
            for sub_match in subpart_matches:
                if start_pos <= sub_match.start() < end_pos:
                    sub_parts.append((sub_match.group(1), sub_match.start() - start_pos))
            
            if sub_parts:
                # Process each sub-part
                for j, (sub_part, sub_offset) in enumerate(sorted(sub_parts, key=lambda x: x[1])):
                    # Determine end position of this sub-part
                    if j < len(sub_parts) - 1:
                        sub_end_offset = sorted(sub_parts, key=lambda x: x[1])[j + 1][1]
                    else:
                        sub_end_offset = len(question_text)
                    
                    # Extract sub-part text
                    sub_text = question_text[sub_offset:sub_end_offset].strip()
                    
                    # Format question number as per user's example: "5. (a)"
                    formatted_number = f"{question_num}. ({sub_part})"
                    
                    # Find marks for this sub-part
                    sub_marks_match = re.search(r'(?:^|\s)Marks\s+(\d+)', sub_text)
                    sub_marks = int(sub_marks_match.group(1)) if sub_marks_match else 1
                    
                    # Add question to list
                    self._add_question(formatted_number, sub_text, sub_marks)
                    debug_output.append(f"Added sub-part: {formatted_number}, Marks: {sub_marks}")
            else:
                # No sub-parts, process as a single question
                formatted_number = f"{question_num}."
                
                # Add question to list
                self._add_question(formatted_number, question_text, marks)
                debug_output.append(f"Added main question: {formatted_number}, Marks: {marks}")
        
        # If no questions were found with the above method, try a more aggressive approach
        if not self.questions:
            debug_output.append("\n=== FALLBACK EXTRACTION ===")
            self._fallback_extraction(combined_text, debug_output)
        
        # Save debug output
        with open(os.path.join(self.debug_dir, "extraction_debug.txt"), "w", encoding="utf-8") as f:
            f.write('\n'.join(debug_output))
    
    def _fallback_extraction(self, text, debug_output):
        """
        Fallback extraction method for when the primary method fails.
        
        Args:
            text (str): Combined text from PDF
            debug_output (list): List to append debug information to
        """
        # More aggressive pattern for finding questions
        question_pattern = r'(?:^|\s)(\d+)\.\s+(.*?)(?=(?:^|\s)\d+\.\s+|$)'
        question_matches = list(re.finditer(question_pattern, text, re.DOTALL))
        
        debug_output.append(f"Fallback found {len(question_matches)} main questions")
        
        # Process each question
        for match in question_matches:
            question_num = match.group(1)
            question_text = match.group(2).strip()
            
            # Look for sub-parts
            subpart_pattern = r'(?:^|\s)\(([a-z])\)\s+(.*?)(?=(?:^|\s)\([a-z]\)\s+|$)'
            subpart_matches = list(re.finditer(subpart_pattern, question_text, re.DOTALL))
            
            # Find marks
            marks_match = re.search(r'(?:^|\s)Marks\s+(\d+)', question_text)
            marks = int(marks_match.group(1)) if marks_match else 1
            
            if subpart_matches:
                # Process each sub-part
                for sub_match in subpart_matches:
                    sub_part = sub_match.group(1)
                    sub_text = sub_match.group(2).strip()
                    
                    # Format question number
                    formatted_number = f"{question_num}. ({sub_part})"
                    
                    # Find marks for this sub-part
                    sub_marks_match = re.search(r'(?:^|\s)Marks\s+(\d+)', sub_text)
                    sub_marks = int(sub_marks_match.group(1)) if sub_marks_match else 1
                    
                    # Add question to list
                    self._add_question(formatted_number, sub_text, sub_marks)
                    debug_output.append(f"Fallback added sub-part: {formatted_number}, Marks: {sub_marks}")
            else:
                # No sub-parts, process as a single question
                formatted_number = f"{question_num}."
                
                # Add question to list
                self._add_question(formatted_number, question_text, marks)
                debug_output.append(f"Fallback added main question: {formatted_number}, Marks: {marks}")
        
        # If still no questions, try direct extraction based on user examples
        if not self.questions:
            debug_output.append("\n=== DIRECT EXTRACTION ===")
            self._direct_extraction(text, debug_output)
    
    def _direct_extraction(self, text, debug_output):
        """
        Direct extraction method based on user examples.
        
        Args:
            text (str): Combined text from PDF
            debug_output (list): List to append debug information to
        """
        # Based on user example, look for specific patterns
        # Example 1: "1. Evaluate 2/3 (1/5 + 3/4) Give your answer in the simplest form."
        # Example 2: "5. (a) Express x² + 8x +15 in the form (x + a)² + b."
        
        # Extract question 1
        q1_match = re.search(r'1\.\s+Evaluate\s+.*?(?=2\.\s+|$)', text, re.DOTALL)
        if q1_match:
            q1_text = q1_match.group(0).strip()
            self._add_question("1.", q1_text, 2)  # Marks from user example
            debug_output.append(f"Direct added question: 1., Marks: 2")
        
        # Extract question 5 with sub-parts
        q5_match = re.search(r'5\.\s+\(a\)\s+Express.*?(?=6\.\s+|$)', text, re.DOTALL)
        if q5_match:
            q5_text = q5_match.group(0).strip()
            
            # Extract sub-part (a)
            q5a_match = re.search(r'\(a\)\s+Express.*?(?=\(b\)|$)', q5_text, re.DOTALL)
            if q5a_match:
                q5a_text = q5a_match.group(0).strip()
                self._add_question("5. (a)", q5a_text, 2)  # Marks from user example
                debug_output.append(f"Direct added question: 5. (a), Marks: 2")
            
            # Extract sub-part (b)
            q5b_match = re.search(r'\(b\)\s+Hence.*', q5_text, re.DOTALL)
            if q5b_match:
                q5b_text = q5b_match.group(0).strip()
                self._add_question("5. (b)", q5b_text, 1)  # Marks from user example
                debug_output.append(f"Direct added question: 5. (b), Marks: 1")
        
        # Try to extract all questions using a more general pattern based on user examples
        general_pattern = r'(\d+)\.\s+(?:\(([a-z])\)\s+)?(.*?)(?=\d+\.\s+|\(\w\)\s+|$)'
        general_matches = list(re.finditer(general_pattern, text, re.DOTALL))
        
        for match in general_matches:
            question_num = match.group(1)
            sub_part = match.group(2)
            question_text = match.group(3).strip()
            
            # Skip if already added
            if question_num == "1" or (question_num == "5" and sub_part in ["a", "b"]):
                continue
            
            # Format question number
            if sub_part:
                formatted_number = f"{question_num}. ({sub_part})"
            else:
                formatted_number = f"{question_num}."
            
            # Find marks
            marks_match = re.search(r'(?:^|\s)Marks\s+(\d+)', question_text)
            marks = int(marks_match.group(1)) if marks_match else 1
            
            # Add question to list
            self._add_question(formatted_number, question_text, marks)
            debug_output.append(f"General pattern added: {formatted_number}, Marks: {marks}")
    
    def _add_question(self, question_number, text, marks):
        """
        Add a question to the questions list.
        
        Args:
            question_number (str): Question number (e.g., "1.", "5. (a)")
            text (str): Question text
            marks (int): Number of marks
        """
        # Clean up the text
        text = text.strip()
        
        # Remove "Marks X" from the text
        text = re.sub(r'(?:^|\s)Marks\s+\d+', '', text).strip()
        
        # Create question object
        question = {
            "question_number": question_number,
            "text": text,
            "marks": marks,
            "topic": self._determine_topic(text),
            "metadata": {
                "marks": marks,
                "units": self._extract_units(text),
                "instructions": self._extract_instructions(text),
                "has_diagram": "diagram" in text.lower(),
                "associated_formulae": []
            },
            "diagrams": []
        }
        
        self.questions.append(question)
    
    def _determine_topic(self, text):
        """
        Determine the topic of a question based on its content.
        
        Args:
            text (str): Question text
            
        Returns:
            str: Topic category
        """
        # Define keywords for each topic
        topics = {
            "algebraic": ["equation", "expression", "simplify", "expand", "factorise", "solve", "formula"],
            "equations": ["equation", "solve", "solution", "unknown", "variable", "subject"],
            "trigonometry": ["sine", "cosine", "tangent", "angle", "triangle", "sin", "cos", "tan"],
            "geometry": ["circle", "triangle", "rectangle", "square", "polygon", "area", "volume", "perimeter", "diameter", "radius"],
            "statistics": ["mean", "median", "mode", "range", "standard deviation", "probability", "data"],
           
(Content truncated due to size limit. Use line ranges to read in chunks)