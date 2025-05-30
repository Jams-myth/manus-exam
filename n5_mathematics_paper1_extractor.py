"""
Document-Specific PDF Extraction for Scottish National 5 Mathematics Paper 1

This script is specifically designed to extract questions from the N5_Mathematics_Paper1-Non-calculator_2022.PDF
file, following the exact structure and formatting provided in user examples.
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
        
        # Extract questions using pattern matching
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
            r'MARKS\s+DO\s+NOT\s+WRITE\s+IN\s+THIS\s+MARGIN',
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
            r'\[Turn over\]',
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
        Extract questions from cleaned text using pattern matching.
        
        Args:
            text (str): Cleaned text from PDF
        """
        # Split text into lines for processing
        lines = text.split('\n')
        
        # Initialize variables
        current_question = None
        current_text = ""
        current_marks = 0
        in_question = False
        debug_output = []
        
        # Process each line
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and page markers
            if not line or line.startswith('[PAGE_'):
                continue
            
            # Check for main question pattern (e.g., "1. Evaluate")
            main_match = re.match(r'^(\d+)\.\s+(.*)', line)
            
            # Check for sub-part pattern (e.g., "(a) Express x²...")
            sub_match = re.match(r'^\(([a-z])\)\s+(.*)', line)
            
            # Check for marks pattern (e.g., "Marks 2")
            marks_match = re.match(r'^Marks\s+(\d+)', line)
            
            if main_match:
                # If we were already processing a question, save it
                if in_question and current_question:
                    self._add_question(current_question, current_text, current_marks)
                    debug_output.append(f"Added question: {current_question}")
                
                # Start new main question
                current_question = f"{main_match.group(1)}."
                current_text = main_match.group(2)
                current_marks = 0
                in_question = True
                debug_output.append(f"\nFound main question: {current_question}")
                
            elif sub_match and in_question:
                # If we were already processing a question, save it
                if current_question:
                    self._add_question(current_question, current_text, current_marks)
                    debug_output.append(f"Added question: {current_question}")
                
                # Extract main number from current question
                main_num = re.match(r'(\d+)\.', current_question).group(1)
                
                # Start new sub-part
                current_question = f"{main_num}. ({sub_match.group(1)})"
                current_text = sub_match.group(2)
                current_marks = 0
                debug_output.append(f"Found sub-part: {current_question}")
                
            elif marks_match:
                # Found marks for current question
                current_marks = int(marks_match.group(1))
                debug_output.append(f"Found marks: {current_marks}")
                
            elif in_question:
                # Append to current question text
                current_text += " " + line
        
        # Add the last question if there is one
        if in_question and current_question:
            self._add_question(current_question, current_text, current_marks)
            debug_output.append(f"Added final question: {current_question}")
        
        # Save debug output
        with open(os.path.join(self.debug_dir, "extraction_debug.txt"), "w", encoding="utf-8") as f:
            f.write('\n'.join(debug_output))
    
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
            "fractions": ["fraction", "simplest form", "evaluate", "simplify"]
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
            r'(Show that[^.]*\.)',
            r'(Evaluate[^.]*\.)',
            r'(Sketch[^.]*\.)',
            r'(Change[^.]*\.)',
            r'(State[^.]*\.)'
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
    
    def _save_questions(self):
        """
        Save extracted questions to JSON file.
        """
        output_file = os.path.join(self.output_dir, "Mathematics_questions.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.questions, f, indent=2)
        
        logger.info(f"Saved {len(self.questions)} questions to {output_file}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python n5_mathematics_paper1_extractor.py <pdf_file> <output_directory>")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    output_dir = sys.argv[2]
    
    extractor = N5MathematicsPaper1Extractor(pdf_file, output_dir)
    extractor.extract_questions()
