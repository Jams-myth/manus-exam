"""
Manual Question Extraction and Numbering for Scottish National 5 Exam Papers

This script implements a direct line-by-line approach to extract questions from
Scottish National 5 exam papers, with explicit mapping of sub-parts to their
parent question numbers.
"""

import os
import re
import json
import PyPDF2
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ManualQuestionExtractor:
    """
    Manual question extractor for Scottish National 5 exam papers.
    Uses direct line-by-line processing with explicit mapping of sub-parts.
    """
    
    def __init__(self):
        """Initialize the extractor."""
        self.questions = {}
    
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
            subject (str): Subject of the exam
            
        Returns:
            list: Extracted questions
        """
        logger.info(f"Extracting questions from: {pdf_path}")
        
        # Extract text using PyPDF2
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
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
        
        # Create debug directory
        debug_dir = os.path.dirname(pdf_path)
        os.makedirs(os.path.join(debug_dir, "debug"), exist_ok=True)
        
        # Save cleaned text for debugging
        with open(os.path.join(debug_dir, "debug", f"{os.path.basename(pdf_path)}_cleaned.txt"), "w") as f:
            f.write(cleaned_text)
        
        # Manual line-by-line extraction
        questions = self._manual_line_extraction(cleaned_text, subject, pdf_path)
        
        return questions
    
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
    
    def _manual_line_extraction(self, cleaned_text, subject, pdf_path):
        """
        Extract questions using a manual line-by-line approach with explicit mapping.
        
        Args:
            cleaned_text (str): Cleaned text from PDF
            subject (str): Subject of the exam
            pdf_path (str): Path to the original PDF file
            
        Returns:
            list: Extracted questions
        """
        questions = []
        debug_output = ["=== MANUAL LINE-BY-LINE EXTRACTION ==="]
        
        # Split text into lines for processing
        lines = cleaned_text.split('\n')
        
        # Initialize variables
        current_main_num = None
        current_question_text = ""
        current_sub_part = None
        in_question = False
        
        # Process each line
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Skip page markers
            if line.startswith('[PAGE_'):
                continue
            
            # Check for main question number pattern (e.g., "1.", "2.")
            main_match = re.match(r'^(\d+)\.\s', line)
            if main_match:
                # If we were already processing a question, save it
                if in_question and current_question_text:
                    question_number = f"{current_main_num}."
                    if current_sub_part:
                        question_number = f"{current_main_num}. ({current_sub_part})"
                    
                    question = self._create_question_object(
                        question_number,
                        current_question_text,
                        subject
                    )
                    questions.append(question)
                    debug_output.append(f"Added question: {question_number}")
                
                # Start new main question
                current_main_num = main_match.group(1)
                current_question_text = line
                current_sub_part = None
                in_question = True
                debug_output.append(f"\nFound main question: {current_main_num}")
                
            # Check for sub-part pattern (e.g., "(a)", "(b)")
            elif in_question and re.match(r'^\([a-z]\)', line):
                # If we were already processing a sub-part, save it
                if current_sub_part and current_question_text:
                    question_number = f"{current_main_num}. ({current_sub_part})"
                    
                    question = self._create_question_object(
                        question_number,
                        current_question_text,
                        subject
                    )
                    questions.append(question)
                    debug_output.append(f"Added sub-part: {question_number}")
                
                # Start new sub-part
                current_sub_part = re.match(r'^\(([a-z])\)', line).group(1)
                current_question_text = line
                debug_output.append(f"Found sub-part: {current_sub_part}")
                
            # Check for continued question pattern (e.g., "4. (continued)")
            elif re.match(r'^\d+\.\s+\(continued\)', line):
                # This is a continuation of a main question, not a new question
                current_question_text += " " + line
                debug_output.append(f"Found continuation line: {line}")
                
            # Otherwise, append to current question text
            elif in_question:
                current_question_text += " " + line
        
        # Add the last question if there is one
        if in_question and current_question_text:
            question_number = f"{current_main_num}."
            if current_sub_part:
                question_number = f"{current_main_num}. ({current_sub_part})"
            
            question = self._create_question_object(
                question_number,
                current_question_text,
                subject
            )
            questions.append(question)
            debug_output.append(f"Added final question: {question_number}")
        
        # Save debug output
        debug_dir = os.path.join(os.path.dirname(pdf_path), "debug")
        with open(os.path.join(debug_dir, f"{os.path.basename(pdf_path)}_manual_extraction.txt"), "w") as f:
            f.write('\n'.join(debug_output))
        
        # If we didn't extract any questions with the line-by-line approach,
        # fall back to a more aggressive pattern-based approach
        if not questions:
            logger.warning(f"Line-by-line extraction failed for {pdf_path}, using fallback method")
            questions = self._fallback_extraction(cleaned_text, subject, pdf_path)
        
        # Ensure sequential numbering
        questions = self._ensure_sequential_numbering(questions, pdf_path)
        
        return questions
    
    def _fallback_extraction(self, cleaned_text, subject, pdf_path):
        """
        Fallback extraction method using aggressive pattern matching.
        
        Args:
            cleaned_text (str): Cleaned text from PDF
            subject (str): Subject of the exam
            pdf_path (str): Path to the original PDF file
            
        Returns:
            list: Extracted questions
        """
        questions = []
        debug_output = ["=== FALLBACK EXTRACTION ==="]
        
        # Find all potential question numbers and sub-parts
        main_matches = list(re.finditer(r'(?:^|\n|\s)(\d+)\.(?:\s|\n)', cleaned_text))
        sub_matches = list(re.finditer(r'(?:^|\n|\s)\(([a-z])\)(?:\s|\n)', cleaned_text))
        
        # If no main questions found, create artificial ones
        if not main_matches:
            debug_output.append("No main questions found, creating artificial ones")
            
            # Create questions with sequential numbering
            for i, sub_match in enumerate(sub_matches):
                # Group sub-parts into main questions (e.g., 3 sub-parts per main question)
                main_num = (i // 3) + 1
                sub_part = sub_match.group(1)
                
                # Extract text from this sub-part to the next one or end of text
                start_pos = sub_match.start()
                if i < len(sub_matches) - 1:
                    end_pos = sub_matches[i + 1].start()
                else:
                    end_pos = len(cleaned_text)
                
                question_text = cleaned_text[start_pos:end_pos].strip()
                question_number = f"{main_num}. ({sub_part})"
                
                question = self._create_question_object(
                    question_number,
                    question_text,
                    subject
                )
                questions.append(question)
                debug_output.append(f"Created artificial question: {question_number}")
        else:
            # Process each main question
            for i, main_match in enumerate(main_matches):
                main_num = main_match.group(1)
                start_pos = main_match.start()
                
                # Determine end position (start of next main question or end of text)
                if i < len(main_matches) - 1:
                    end_pos = main_matches[i + 1].start()
                else:
                    end_pos = len(cleaned_text)
                
                # Extract main question text
                main_text = cleaned_text[start_pos:end_pos].strip()
                
                # Find sub-parts within this main question
                sub_parts = []
                for sub_match in sub_matches:
                    if start_pos <= sub_match.start() < end_pos:
                        sub_parts.append((sub_match.group(1), sub_match.start() - start_pos))
                
                if sub_parts:
                    # Process each sub-part
                    for j, (sub_part, sub_offset) in enumerate(sub_parts):
                        # Determine end position of this sub-part
                        if j < len(sub_parts) - 1:
                            sub_end_offset = sub_parts[j + 1][1]
                        else:
                            sub_end_offset = len(main_text)
                        
                        # Extract sub-part text
                        sub_text = main_text[sub_offset:sub_end_offset].strip()
                        question_number = f"{main_num}. ({sub_part})"
                        
                        question = self._create_question_object(
                            question_number,
                            sub_text,
                            subject
                        )
                        questions.append(question)
                        debug_output.append(f"Added sub-part: {question_number}")
                else:
                    # No sub-parts, process as a single question
                    question_number = f"{main_num}."
                    
                    question = self._create_question_object(
                        question_number,
                        main_text,
                        subject
                    )
                    questions.append(question)
                    debug_output.append(f"Added main question: {question_number}")
        
        # Save debug output
        debug_dir = os.path.join(os.path.dirname(pdf_path), "debug")
        with open(os.path.join(debug_dir, f"{os.path.basename(pdf_path)}_fallback_extraction.txt"), "w") as f:
            f.write('\n'.join(debug_output))
        
        return questions
    
    def _ensure_sequential_numbering(self, questions, pdf_path):
        """
        Ensure sequential numbering of questions.
        
        Args:
            questions (list): List of question objects
            pdf_path (str): Path to the original PDF file
            
        Returns:
            list: List of question
(Content truncated due to size limit. Use line ranges to read in chunks)