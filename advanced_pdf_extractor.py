#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import fitz  # PyMuPDF
import re
import json
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class AdvancedPDFExtractor:
    def __init__(self, pdf_path, output_dir):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.doc = fitz.open(pdf_path)
        self.questions = []
        self.current_question_number = None
        self.current_question_text = ""
        self.current_marks = None
        self.current_parts = []
        self.debug_output = []

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # Basic math symbol mapping (can be expanded)
        self.math_symbol_map = {
            "\uf02b": "+",
            "\uf02d": "-",
            "\uf03d": "=",
            "\uf0b1": "+/-",
            "\uf0b4": "*", # Multiplication X
            "\uf0b8": "/", # Division sign
            "\uf0e6": "(",
            "\uf0f6": ")",
            "\uf0e7": "[",
            "\uf0f7": "]",
            "\uf0e8": "{",
            "\uf0f8": "}",
            "\u00b0": " degrees", # Degree symbol
            "\u03c0": "pi", # Pi symbol
            "\u221a": "sqrt", # Square root
            "\u2013": "-", # En dash
            "\u2014": "-", # Em dash
            "\u2212": "-", # Minus sign
            # Add more mappings as needed based on observed Unicode characters
        }

    def _clean_text(self, text):
        """Cleans text by removing noise and replacing math symbols."""
        # Remove common headers/footers/noise
        noise = [
            r"DO NOT WRITE IN THIS MARGIN",
            r"MARKS",
            r"Page \d+ of \d+",
            r"\*X\d+/\d+\*",
            r"\(page \d+\)",
            r"Turn over",
            r"END OF QUESTION PAPER",
            r"FORMULAE LIST",
            r"You may NOT use a calculator",
            r"You may use a calculator",
            r"Total marks \u2013 \d+",
            r"Attempt ALL questions",
            r"National Quali\x1fcations \d+",
            r"Mathematics Paper \d \(Non-calculator\)",
            r"Mathematics Paper \d \(Calculator\)",
            r"Applications of Mathematics Paper \d",
            r"SQA",
            r"THURSDAY, \d+ MAY",
            r"FRIDAY, \d+ MAY",
            r"\d+:\d+ AM \u2013 \d+:\d+ AM",
            r"\d+:\d+ AM \u2013 \d+:\d+ PM",
            r"\d+:\d+ PM \u2013 \d+:\d+ PM",
            r"Ref: \w+",
            r"Date: \w+",
            r"Time: \w+",
            r"Duration: \w+",
            r"Instructions",
            r"Additional space for answers",
            r"Additional axes for question \d+",
            r"\[BLANK PAGE\]",
            r"DO NOT WRITE ON THIS PAGE",
        ]
        cleaned = text
        for pattern in noise:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
        
        # Replace known math Unicode characters
        for uni, replacement in self.math_symbol_map.items():
            cleaned = cleaned.replace(uni, replacement)
            
        # Replace multiple spaces/newlines with single ones
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        cleaned = re.sub(r"\n{2,}", "\n", cleaned).strip()
        
        return cleaned

    def _extract_marks(self, text):
        """Extracts marks if explicitly mentioned like [marks 2] or Marks: 2."""
        # Simple pattern for marks, might need refinement
        match = re.search(r"(?:marks?[:\s]*|\s)\[?(\d+)\]?", text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None # Default if no marks found

    def _process_block(self, block_text):
        """Processes a text block to identify questions, parts, and content."""
        lines = block_text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            cleaned_line = self._clean_text(line)
            if not cleaned_line:
                continue

            # Check for main question number (e.g., "1.", "12.")
            main_q_match = re.match(r"^(\d+)\.\s+(.*)", line)
            # Check for sub-question part (e.g., "(a)", "(b)")
            sub_q_match = re.match(r"^\((\w+)\)\s+(.*)", line)
            # Check for continued sub-question part (e.g., "15. (a)")
            continued_sub_q_match = re.match(r"^(\d+)\.\s+\((\w+)\)\s+(.*)", line)
            # Check for continued main question (e.g., "15. (continued)")
            continued_main_q_match = re.match(r"^(\d+)\.\s+\(continued\)(.*)", line, re.IGNORECASE)

            extracted_marks = self._extract_marks(line)

            if continued_sub_q_match:
                q_num = continued_sub_q_match.group(1)
                part_letter = continued_sub_q_match.group(2)
                text = continued_sub_q_match.group(3)
                self.debug_output.append(f"Detected continued sub-question: {q_num}.({part_letter})")
                if self.current_question_number and self.current_question_number.startswith(q_num + "."):
                    # Add as a new part to the current question
                    self._add_part(part_letter, text, extracted_marks)
                else:
                    # If it doesn't match current, treat as new main question (edge case)
                    self._finalize_current_question()
                    self.current_question_number = f"{q_num}."
                    self.current_question_text = "" # Reset text for main question
                    self._add_part(part_letter, text, extracted_marks)

            elif main_q_match:
                self._finalize_current_question()
                self.current_question_number = main_q_match.group(1) + "."
                self.current_question_text = self._clean_text(main_q_match.group(2))
                self.current_marks = extracted_marks # Assign marks found on the main question line
                self.current_parts = []
                self.debug_output.append(f"Detected main question: {self.current_question_number}")

            elif sub_q_match:
                if self.current_question_number:
                    part_letter = sub_q_match.group(1)
                    text = sub_q_match.group(2)
                    self._add_part(part_letter, text, extracted_marks)
                    self.debug_output.append(f"Detected sub-question: {self.current_question_number} ({part_letter})")
                else:
                    # Orphaned sub-question? Log it or handle as needed
                    self.debug_output.append(f"Warning: Orphaned sub-question found: {line}")
                    # Attempt to attach to previous or start new generic question
                    if self.questions:
                         # Heuristic: attach to the last question if it makes sense
                         last_q = self.questions[-1]
                         if not last_q.get("parts"): # Only attach if last question had no parts yet
                             part_letter = sub_q_match.group(1)
                             text = sub_q_match.group(2)
                             last_q.setdefault("parts", []).append({
                                 "part_label": part_letter,
                                 "text": self._clean_text(text),
                                 "marks": extracted_marks
                             })
                             self.debug_output.append(f"Heuristically attached orphaned part ({part_letter}) to question {last_q['question_number']}")
                         else:
                             self.debug_output.append(f"Could not attach orphaned part ({sub_q_match.group(1)}) to last question {last_q['question_number']}")
                    else:
                         self.debug_output.append(f"Could not attach orphaned part ({sub_q_match.group(1)}) - no previous question.")

            elif continued_main_q_match:
                 q_num = continued_main_q_match.group(1)
                 text = continued_main_q_match.group(2)
                 if self.current_question_number and self.current_question_number.startswith(q_num + "."):
                     self.current_question_text += " " + self._clean_text(text)
                     self.debug_output.append(f"Continued main question {q_num}.")
                 else:
                     # Doesn't match current question, maybe noise or misidentified
                     self.debug_output.append(f"Warning: Misidentified continued question: {line}")
                     if self.current_question_number:
                         self.current_question_text += " " + self._clean_text(line) # Append as regular text

            elif self.current_question_number:
                # Append line to the current question or part text
                cleaned_part = self._clean_text(line)
                if cleaned_part:
                    if self.current_parts:
                        # Append to the last part's text
                        self.current_parts[-1]["text"] += " " + cleaned_part
                        # Update marks if found on this line and part has no marks yet
                        if extracted_marks is not None and self.current_parts[-1]["marks"] is None:
                            self.current_parts[-1]["marks"] = extracted_marks
                    else:
                        # Append to the main question text
                        self.current_question_text += " " + cleaned_part
                        # Update main marks if found and no marks yet
                        if extracted_marks is not None and self.current_marks is None:
                            self.current_marks = extracted_marks
                            
    def _add_part(self, part_label, text, marks):
        """Adds a new part to the current question."""
        if not self.current_question_number:
            self.debug_output.append(f"Warning: Trying to add part ({part_label}) without a current question.")
            return
            
        cleaned_text = self._clean_text(text)
        self.current_parts.append({
            "part_label": part_label,
            "text": cleaned_text,
            "marks": marks
        })

    def _finalize_current_question(self):
        """Adds the completed current question to the list."""
        if self.current_question_number:
            # Consolidate text and clean final result
            final_text = re.sub(r"\s{2,}", " ", self.current_question_text).strip()
            for part in self.current_parts:
                part["text"] = re.sub(r"\s{2,}", " ", part["text"]).strip()
                # Remove the part label from the beginning of the text if present
                part["text"] = re.sub(f"^\({part['part_label']}\)\s*", "", part["text"]).strip()
                # If marks were None, try extracting again from the final part text
                if part["marks"] is None:
                    part["marks"] = self._extract_marks(part["text"])
                # Remove marks indication from text after extraction
                part["text"] = re.sub(r"(?:marks?[:\s]*|\s)\[?(\d+)\]?", "", part["text"], flags=re.IGNORECASE).strip()

            # Remove marks indication from main text after extraction
            if self.current_marks is None:
                 self.current_marks = self._extract_marks(final_text)
            final_text = re.sub(r"(?:marks?[:\s]*|\s)\[?(\d+)\]?", "", final_text, flags=re.IGNORECASE).strip()
            # Remove the question number from the beginning of the text if present
            final_text = re.sub(f"^{re.escape(self.current_question_number)}\s*", "", final_text).strip()

            question_data = {
                "question_number": self.current_question_number,
                "text": final_text,
                "marks": self.current_marks, # Overall marks if available
                "parts": self.current_parts,
                "metadata": {
                    "has_diagram": "diagram" in final_text.lower() or any("diagram" in p["text"].lower() for p in self.current_parts),
                    # Add other metadata extraction later (topic, units, etc.)
                },
                "diagrams": [] # Placeholder for actual diagram file paths/data
            }
            self.questions.append(question_data)
            self.debug_output.append(f"Finalized question: {self.current_question_number}")

        # Reset for next question
        self.current_question_number = None
        self.current_question_text = ""
        self.current_marks = None
        self.current_parts = []

    def extract_questions(self):
        """Extracts questions from the PDF document."""
        full_text = ""
        for page_num in range(len(self.doc)):
            page = self.doc.load_page(page_num)
            # Extract text blocks with layout preservation
            blocks = page.get_text("blocks") # list of (x0, y0, x1, y1, "text", block_no, block_type)
            blocks.sort(key=lambda b: (b[1], b[0])) # Sort blocks top-to-bottom, left-to-right
            
            page_text = ""
            for b in blocks:
                block_text = b[4] # The text content of the block
                # Simple cleaning within the block
                cleaned_block_text = block_text.replace("\n", " ").strip()
                cleaned_block_text = re.sub(r"\s{2,}", " ", cleaned_block_text)
                
                # Filter out blocks that are likely headers/footers based on position or content
                y0 = b[1]
                y1 = b[3]
                page_height = page.rect.height
                if y0 < 50 or y1 > page_height - 50: # Arbitrary margin for header/footer
                    if re.search(r"Page \d+|MARKS|DO NOT WRITE|Turn over", cleaned_block_text, re.IGNORECASE):
                         self.debug_output.append(f"Skipping potential header/footer block: {cleaned_block_text[:50]}...")
                         continue
                
                # Process the block
                self._process_block(block_text) # Use original block text with newlines for structure

        # Finalize the last question after processing all pages
        self._finalize_current_question()
        
        # Save the extracted questions
        self._save_questions()
        self._save_debug_log()

    def _save_questions(self):
        """Saves the extracted questions to a JSON file."""
        output_filename = os.path.splitext(os.path.basename(self.pdf_path))[0] + "_questions.json"
        output_path = os.path.join(self.output_dir, output_filename)
        
        # Basic validation/cleanup before saving
        valid_questions = []
        for q in self.questions:
            # Ensure text fields are not empty and question number exists
            if q.get("question_number") and (q.get("text") or q.get("parts")):
                 # Ensure parts have text
                 if q.get("parts"):
                     q["parts"] = [p for p in q["parts"] if p.get("text")]
                 # Only add if main text exists or there are valid parts
                 if q.get("text") or q.get("parts"):
                    valid_questions.append(q)
            else:
                self.debug_output.append(f"Skipping invalid question structure: {q.get('question_number')}")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(valid_questions, f, indent=2, ensure_ascii=False)
        logging.info(f"Saved {len(valid_questions)} questions to {output_path}")

    def _save_debug_log(self):
        """Saves the debug messages to a log file."""
        output_filename = os.path.splitext(os.path.basename(self.pdf_path))[0] + "_extraction_log.txt"
        output_path = os.path.join(self.output_dir, output_filename)
        with open(ou
(Content truncated due to size limit. Use line ranges to read in chunks)