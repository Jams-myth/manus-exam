"""
PDF Extraction Module for Scottish National 5 Exam Papers

This module is responsible for extracting content from Scottish National 5 exam papers,
including questions, marking schemes, and visual elements.
"""

import os
import re
import PyPDF2
import pytesseract
from pdf2image import convert_from_path
import cv2
import numpy as np
from PIL import Image
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFExtractor:
    """
    Main class for extracting content from Scottish National 5 exam papers.
    """
    
    def __init__(self, pdf_path):
        """
        Initialize the PDF extractor with the path to the PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file to be processed
        """
        self.pdf_path = pdf_path
        self.pdf_name = os.path.basename(pdf_path)
        self.is_marking_instruction = "mi_" in self.pdf_name.lower()
        self.pages = []
        self.images = []
        self.extracted_text = []
        self.questions = []
        self.marking_schemes = []
        self.diagrams = []
        
        logger.info(f"Initializing PDF extractor for {self.pdf_name}")
        
    def extract_content(self):
        """
        Extract all content from the PDF file.
        
        Returns:
            dict: Dictionary containing extracted questions, marking schemes, and diagrams
        """
        logger.info(f"Starting content extraction for {self.pdf_name}")
        
        # Extract text using PyPDF2
        self._extract_text_with_pypdf()
        
        # Convert PDF to images for OCR and diagram extraction
        self._convert_pdf_to_images()
        
        # Extract text using OCR for better accuracy
        self._extract_text_with_ocr()
        
        # Identify questions or marking schemes based on file type
        if self.is_marking_instruction:
            self._extract_marking_schemes()
        else:
            self._extract_questions()
            self._extract_diagrams()
        
        return {
            "questions": self.questions,
            "marking_schemes": self.marking_schemes,
            "diagrams": self.diagrams
        }
    
    def _extract_text_with_pypdf(self):
        """Extract text from PDF using PyPDF2."""
        logger.info(f"Extracting text with PyPDF2 from {self.pdf_name}")
        
        try:
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                self.pages = []
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    self.pages.append({
                        'page_num': page_num + 1,
                        'text': text
                    })
                    
                logger.info(f"Extracted text from {len(self.pages)} pages with PyPDF2")
        except Exception as e:
            logger.error(f"Error extracting text with PyPDF2: {str(e)}")
            raise
    
    def _convert_pdf_to_images(self):
        """Convert PDF pages to images for OCR and diagram extraction."""
        logger.info(f"Converting PDF to images for {self.pdf_name}")
        
        try:
            # Convert PDF to images
            self.images = convert_from_path(
                self.pdf_path,
                dpi=300,  # Higher DPI for better quality
                fmt='jpg'
            )
            logger.info(f"Converted {len(self.images)} pages to images")
        except Exception as e:
            logger.error(f"Error converting PDF to images: {str(e)}")
            raise
    
    def _extract_text_with_ocr(self):
        """Extract text from PDF images using OCR."""
        logger.info(f"Extracting text with OCR from {self.pdf_name}")
        
        self.extracted_text = []
        
        for i, image in enumerate(self.images):
            try:
                # Convert PIL Image to numpy array for OpenCV
                img_np = np.array(image)
                
                # Convert to grayscale
                gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                
                # Apply threshold to get black and white image
                _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
                
                # Perform OCR
                text = pytesseract.image_to_string(binary)
                
                self.extracted_text.append({
                    'page_num': i + 1,
                    'text': text
                })
                
                logger.info(f"Extracted OCR text from page {i+1}")
            except Exception as e:
                logger.error(f"Error extracting OCR text from page {i+1}: {str(e)}")
                self.extracted_text.append({
                    'page_num': i + 1,
                    'text': ""
                })
    
    def _extract_questions(self):
        """Extract questions from the exam paper."""
        logger.info(f"Extracting questions from {self.pdf_name}")
        
        self.questions = []
        
        # Combine text from both extraction methods for better results
        combined_text = []
        for i in range(len(self.pages)):
            page_text = self.pages[i]['text']
            if i < len(self.extracted_text):
                ocr_text = self.extracted_text[i]['text']
                # Use the longer text as it likely contains more information
                if len(ocr_text) > len(page_text):
                    combined_text.append(ocr_text)
                else:
                    combined_text.append(page_text)
            else:
                combined_text.append(page_text)
        
        # Join all pages into one text for easier processing
        full_text = "\n".join(combined_text)
        
        # Regular expression to find questions
        # Pattern looks for question numbers followed by text
        # More specific pattern to better identify question boundaries
        question_pattern = r'(?:^|\n)(\d+\.)\s*((?:.+\n?)+?)(?=(?:^|\n)\d+\.\s*|\Z)'
        
        # Find all matches
        matches = re.findall(question_pattern, full_text, re.DOTALL)
        
        for match in matches:
            question_num = match[0].strip()
            question_text = match[1].strip()
            
            # Extract marks information
            marks_pattern = r'(\d+)\s*marks?'
            marks_match = re.search(marks_pattern, question_text, re.IGNORECASE)
            
            # If not found in question text, try looking for marks in parentheses or at end of line
            if not marks_match:
                alt_marks_pattern = r'\((\d+)(?:\s*marks?)?\)'
                marks_match = re.search(alt_marks_pattern, question_text, re.IGNORECASE)
            
            marks = int(marks_match.group(1)) if marks_match else None
            
            self.questions.append({
                'question_num': question_num,
                'text': question_text,
                'marks': marks
            })
        
        logger.info(f"Extracted {len(self.questions)} questions")
    
    def _extract_marking_schemes(self):
        """Extract marking schemes from the marking instructions."""
        logger.info(f"Extracting marking schemes from {self.pdf_name}")
        
        self.marking_schemes = []
        
        # Combine text from both extraction methods
        combined_text = []
        for i in range(len(self.pages)):
            page_text = self.pages[i]['text']
            if i < len(self.extracted_text):
                ocr_text = self.extracted_text[i]['text']
                if len(ocr_text) > len(page_text):
                    combined_text.append(ocr_text)
                else:
                    combined_text.append(page_text)
            else:
                combined_text.append(page_text)
        
        # Join all pages into one text
        full_text = "\n".join(combined_text)
        
        # Look for question numbers and associated marking criteria
        # This pattern is more complex for marking instructions
        question_pattern = r'(?:Question|Max mark)\s+(\d+).*?(?:(\d+)\s*marks?|\((\d+)\))'
        
        # Find all matches
        matches = re.finditer(question_pattern, full_text, re.DOTALL)
        
        for match in matches:
            question_num = match.group(1).strip()
            
            # Get the text following this match until the next question or end
            start_pos = match.end()
            next_match = re.search(r'Question\s+\d+', full_text[start_pos:], re.DOTALL)
            
            if next_match:
                end_pos = start_pos + next_match.start()
                scheme_text = full_text[start_pos:end_pos]
            else:
                scheme_text = full_text[start_pos:]
            
            # Clean up the text
            scheme_text = scheme_text.strip()
            
            # Extract marking criteria
            criteria_pattern = r'[•●]\s*(\d+)\s+(.*?)(?=[•●]|\Z)'
            criteria_matches = re.findall(criteria_pattern, scheme_text, re.DOTALL)
            
            criteria = []
            for c_match in criteria_matches:
                criteria.append({
                    'points': c_match[0],
                    'description': c_match[1].strip()
                })
            
            self.marking_schemes.append({
                'question_num': question_num,
                'text': scheme_text,
                'criteria': criteria
            })
        
        logger.info(f"Extracted {len(self.marking_schemes)} marking schemes")
    
    def _extract_diagrams(self):
        """Extract diagrams and visual elements from the exam paper."""
        logger.info(f"Extracting diagrams from {self.pdf_name}")
        
        self.diagrams = []
        
        for i, image in enumerate(self.images):
            try:
                # Convert PIL Image to numpy array for OpenCV
                img_np = np.array(image)
                
                # Convert to grayscale
                gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                
                # Apply threshold to get black and white image
                _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
                
                # Find contours
                contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Filter contours by size to find potential diagrams
                for j, contour in enumerate(contours):
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Filter out small contours and full-page contours
                    if (w > 100 and h > 100 and w < img_np.shape[1] * 0.9 and h < img_np.shape[0] * 0.9):
                        # Extract the region of interest
                        roi = img_np[y:y+h, x:x+w]
                        
                        # Convert back to PIL Image
                        diagram_img = Image.fromarray(roi)
                        
                        # Save diagram information
                        self.diagrams.append({
                            'page_num': i + 1,
                            'position': (x, y, w, h),
                            'image': diagram_img
                        })
                
                logger.info(f"Processed page {i+1} for diagrams")
            except Exception as e:
                logger.error(f"Error extracting diagrams from page {i+1}: {str(e)}")
        
        logger.info(f"Extracted {len(self.diagrams)} potential diagrams")

    def save_extracted_content(self, output_dir):
        """
        Save extracted content to the specified directory.
        
        Args:
            output_dir (str): Directory to save extracted content
        """
        logger.info(f"Saving extracted content to {output_dir}")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Save questions to text file
        if self.questions:
            questions_file = os.path.join(output_dir, f"{self.pdf_name}_questions.txt")
            with open(questions_file, 'w') as f:
                for q in self.questions:
                    f.write(f"Question {q['question_num']}\n")
                    f.write(f"Marks: {q['marks']}\n")
                    f.write(f"{q['text']}\n\n")
            logger.info(f"Saved questions to {questions_file}")
        
        # Save marking schemes to text file
        if self.marking_schemes:
            schemes_file = os.path.join(output_dir, f"{self.pdf_name}_marking_schemes.txt")
            with open(schemes_file, 'w') as f:
                for scheme in self.marking_schemes:
                    f.write(f"Question {scheme['question_num']}\n")
                    f.write(f"{scheme['text']}\n")
                    f.write("Criteria:\n")
                    for criterion in scheme.get('criteria', []):
                        f.write(f"• {criterion['points']} - {criterion['description']}\n")
                    f.write("\n")
            logger.info(f"Saved marking schemes to {schemes_file}")
        
        # Save diagrams as images
        if self.diagrams:
            diagrams_dir = os.path.join(output_dir, f"{self.pdf_name}_diagrams")
            os.makedirs(diagrams_dir, exist_ok=True)
            
            for i, diagram in enumerate(self.diagrams):
                img_path = os.path.join(diagrams_dir, f"diagram_{diagram['page_num']}_{i+1}.jpg")
                diagram['image'].save(img_path)
            
            logger.info(f"Saved {len(self.diagrams)} diagrams to {diagrams_dir}")
        
        return {
            "questions_file": questions_file if self.questions else None,
            "schemes_file": schemes_file if self.marking_schemes else None,
            "diagrams_dir": diagrams_dir if self.diagrams else None
        }


def process_pdf(pdf_path, output_dir=None):
    """
    Process a PDF file and extract its content.
    
    Args:
        pdf_path (str): Path to the PDF file
        output_dir (str, optional): Directory to save extracted content
    
    Returns:
        dict: Dictionary containing extracted content
    """
    extractor = PDFExtractor(pdf_path)
    content = extractor.extract_content()
    
    if output_dir:
        extractor.save_extracted_content(output_dir)
    
    return content


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pdf_extractor.py <pdf_path> [output_dir]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    
    process_pdf(pdf_path, output_dir)
