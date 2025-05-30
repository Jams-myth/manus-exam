"""
Advanced PDF Extraction Module for Scottish National 5 Exam Papers - Final Version

This module provides sophisticated extraction of questions from exam papers,
ensuring complete questions are captured with proper structure, metadata,
and associated diagrams according to the user's guide.
"""

import os
import re
import json
import logging
import PyPDF2
from pdf2image import convert_from_path
import cv2
import numpy as np
from PIL import Image
import pytesseract

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedQuestionExtractor:
    """
    Advanced extractor for capturing complete questions with proper structure and metadata.
    """
    
    def __init__(self, pdf_paths, output_dir):
        """
        Initialize the advanced question extractor.
        
        Args:
            pdf_paths (list): List of paths to PDF files to be processed
            output_dir (str): Directory to save extracted questions
        """
        self.pdf_paths = pdf_paths
        self.output_dir = output_dir
        self.questions = {}
        self.diagrams = {}
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"Initialized advanced question extractor for {len(pdf_paths)} PDF files")
    
    def extract_all_questions(self):
        """
        Extract questions from all PDF files.
        
        Returns:
            dict: Dictionary containing extracted questions by subject
        """
        for pdf_path in self.pdf_paths:
            self._extract_questions_from_pdf(pdf_path)
        
        # Post-process all questions to fix numbering
        self._post_process_all_questions()
        
        # Save questions to JSON files
        self._save_questions_to_json()
        
        return self.questions
    
    def _extract_questions_from_pdf(self, pdf_path):
        """
        Extract questions from a single PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
        """
        logger.info(f"Extracting questions from {os.path.basename(pdf_path)}")
        
        # Determine subject from filename
        subject = "Mathematics"
        if "Applications" in pdf_path:
            subject = "Applications of Mathematics"
        
        # Skip marking instruction files for now
        if "mi_" in os.path.basename(pdf_path).lower():
            logger.info(f"Skipping marking instruction file: {os.path.basename(pdf_path)}")
            return
        
        # Initialize subject in questions dictionary if not exists
        if subject not in self.questions:
            self.questions[subject] = []
        
        # Extract text and images from PDF
        pdf_text, pdf_images = self._extract_content_from_pdf(pdf_path)
        
        # Extract diagrams from images
        self._extract_diagrams_from_images(pdf_path, pdf_images)
        
        # Extract questions using advanced pattern matching
        extracted_questions = self._extract_questions_from_text(pdf_text, pdf_path)
        
        # Associate diagrams with questions
        self._associate_diagrams_with_questions(extracted_questions, pdf_path)
        
        # Add extracted questions to the subject
        self.questions[subject].extend(extracted_questions)
        
        logger.info(f"Extracted {len(extracted_questions)} questions from {os.path.basename(pdf_path)}")
    
    def _extract_content_from_pdf(self, pdf_path):
        """
        Extract text and images from a PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            tuple: (extracted_text, page_images)
        """
        try:
            # Extract text using PyPDF2
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_by_page = []
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    text_by_page.append({
                        'page_num': page_num + 1,
                        'text': text
                    })
            
            # Convert PDF to images for OCR and diagram extraction
            images = convert_from_path(
                pdf_path,
                dpi=300,  # Higher DPI for better quality
                fmt='jpg'
            )
            
            return text_by_page, images
            
        except Exception as e:
            logger.error(f"Error extracting content from PDF: {str(e)}")
            return [], []
    
    def _extract_diagrams_from_images(self, pdf_path, images):
        """
        Extract diagrams from PDF page images.
        
        Args:
            pdf_path (str): Path to the PDF file
            images (list): List of page images
        """
        pdf_name = os.path.basename(pdf_path)
        self.diagrams[pdf_name] = []
        
        for i, image in enumerate(images):
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
                        diagram_id = f"diagram_{i+1}_{j+1}"
                        self.diagrams[pdf_name].append({
                            'id': diagram_id,
                            'page_num': i + 1,
                            'position': (x, y, w, h),
                            'image': diagram_img,
                            'associated_question': None  # Will be filled later
                        })
                
                logger.info(f"Processed page {i+1} for diagrams")
            except Exception as e:
                logger.error(f"Error extracting diagrams from page {i+1}: {str(e)}")
        
        logger.info(f"Extracted {len(self.diagrams[pdf_name])} potential diagrams from {pdf_name}")
    
    def _extract_questions_from_text(self, text_by_page, pdf_path):
        """
        Extract questions from text using advanced pattern matching.
        
        Args:
            text_by_page (list): List of dictionaries with page number and text
            pdf_path (str): Path to the PDF file
            
        Returns:
            list: List of extracted questions
        """
        questions = []
        
        # Combine text from all pages with page markers
        full_text = ""
        for page in text_by_page:
            full_text += f"\n===== PAGE {page['page_num']} =====\n{page['text']}\n"
        
        # Remove headers, footers, and irrelevant sections
        full_text = self._clean_headers_footers(full_text)
        
        # First pass: identify question boundaries
        # This pattern looks for numbered questions (e.g., "1.", "2.", etc.)
        # and captures everything until the next question number or end of text
        pattern = r'(\d+)\.\s*((?:(?!\n\d+\.).)+)'
        
        # Find all matches
        matches = re.findall(pattern, full_text, re.DOTALL)
        
        # Process each question
        for match in matches:
            question_num = match[0].strip()
            # Remove leading zeros from question number
            question_num = str(int(question_num))
            question_text = match[1].strip()
            
            # Skip questions with very short text (likely false positives)
            if len(question_text) < 10:
                continue
                
            # Check for multi-part questions (a), (b), etc.
            parts = self._extract_question_parts(question_num, question_text)
            
            if parts:
                # Add each part as a separate question
                for part in parts:
                    questions.append(part)
            else:
                # Clean up the question text
                question_text = self._clean_question_text(question_text)
                
                # Split text at next question number if it exists
                next_q_match = re.search(r'\s+\d+\.\s+[A-Z]', question_text)
                if next_q_match:
                    question_text = question_text[:next_q_match.start()]
                
                # Extract metadata
                metadata = self._extract_metadata(question_text)
                
                # Create question object
                question = {
                    "question_number": f"{question_num}.",
                    "text": question_text,
                    "marks": metadata.get('marks', 1),
                    "topic": self._determine_topic(question_text),
                    "metadata": metadata,
                    "diagrams": [],  # Will be filled later
                    "has_diagram_reference": "diagram" in question_text.lower() or "figure" in question_text.lower()
                }
                
                questions.append(question)
        
        # Handle multi-page questions (look for "continued" markers)
        questions = self._handle_multi_page_questions(questions)
        
        # Post-process questions to fix any remaining issues
        questions = self._post_process_questions(questions)
        
        # Second pass: clean up question text to remove other question numbers
        for question in questions:
            question["text"] = self._remove_other_question_references(question["text"])
        
        return questions
    
    def _extract_question_parts(self, question_num, question_text):
        """
        Extract parts from multi-part questions.
        
        Args:
            question_num (str): Question number
            question_text (str): Question text
            
        Returns:
            list: List of question parts or None if not a multi-part question
        """
        # Improved pattern to match question parts like (a), (b), etc.
        part_pattern = r'\(([a-z])\)(.*?)(?=\([a-z]\)|$)'
        parts = re.findall(part_pattern, question_text, re.DOTALL)
        
        if not parts:
            return None
        
        question_parts = []
        
        for part_letter, part_text in parts:
            # Clean up the part text
            part_text = self._clean_question_text(part_text)
            
            # Skip empty or very short parts (likely false positives)
            if len(part_text) < 5:
                continue
            
            # Extract metadata
            metadata = self._extract_metadata(part_text)
            
            # Create question part object
            question_part = {
                "question_number": f"{question_num}.({part_letter})",
                "text": part_text,
                "marks": metadata.get('marks', 1),
                "topic": self._determine_topic(part_text),
                "metadata": metadata,
                "diagrams": [],  # Will be filled later
                "has_diagram_reference": "diagram" in part_text.lower() or "figure" in part_text.lower()
            }
            
            question_parts.append(question_part)
        
        return question_parts
    
    def _handle_multi_page_questions(self, questions):
        """
        Handle questions that span multiple pages.
        
        Args:
            questions (list): List of extracted questions
            
        Returns:
            list: List of questions with multi-page questions merged
        """
        merged_questions = []
        i = 0
        
        while i < len(questions):
            current = questions[i]
            
            # Check if the next question is a continuation
            if i + 1 < len(questions) and "continued" in questions[i + 1].get("text", "").lower():
                # Merge the continuation with the current question
                current["text"] += "\n" + questions[i + 1]["text"]
                i += 2  # Skip the continuation
            else:
                merged_questions.append(current)
                i += 1
        
        return merged_questions
    
    def _post_process_questions(self, questions):
        """
        Post-process questions to fix any remaining issues.
        
        Args:
            questions (list): List of extracted questions
            
        Returns:
            list: List of post-processed questions
        """
        processed_questions = []
        
        for question in questions:
            # Fix question text by removing any trailing question numbers
            text = question["text"]
            
            # Remove trailing question numbers (e.g., "... 3.")
            text = re.sub(r'\s+\d+\.\s*$', '', text)
            
            # Remove trailing marks indicators
            text = re.sub(r'\s+\d+\s*MARKS.*$', '', text)
            
            # Remove "DO NOT WRITE IN THIS MARGIN"
            text = re.sub(r'DO NOT WRITE IN THIS MARGIN', '', text)
            
            # Split text at next question number if it exists
            next_q_match = re.search(r'\s+\d+\.\s+[A-Z]', text)
            if next_q_match:
                text = text[:next_q_match.start()]
            
            # Update the question text
            question["text"] = text.strip()
            
            # Add to processed questions
            processed_questions.append(question)
        
        return processed_questions
    
    def _post_process_all_questions(self):
        """
        Post-process all questions to fix numbering and other issues.
        """
        for subject, questions in self.questions.items():
            # Sort questions by number
            questions.sort(key=lambda q: self._question_sort_key(q["question_number"]))
            
            # Fix question numbering
            current_main_num = 0
            current_parts = {}
            
            for i, question in enumerate(questions):
                num = question["question_number"]
                
                # Check if it's a part question (e.g., "1.(a)")
                if "(" in num:
                    main_num = num.split(".")[0]
                    part = num.split("(")[1].rstrip(")")
                    
                    # If we've moved to a new main question number
                    if int(main_num) != current_main_num:
                        current_main_num = int(main_num)
                        current_parts = {}
                    
                    # Assign sequential part letter if this part has been seen before
                    if part in current_parts:
                        current_parts[part] += 1
                        part_letter = chr(ord('a') + current_parts[part])
                    else:
                        current_parts[part] = 0
                        part_l
(Content truncated due to size limit. Use line ranges to read in chunks)