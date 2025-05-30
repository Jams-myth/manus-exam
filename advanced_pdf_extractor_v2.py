#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import fitz  # PyMuPDF
import re
import json
import os
import logging
import hashlib

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
        self.current_question_diagrams = []
        self.debug_output = []
        self.image_output_dir = os.path.join(self.output_dir, "images")

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        if not os.path.exists(self.image_output_dir):
            os.makedirs(self.image_output_dir)
        
        # Basic math symbol mapping (can be expanded)
        # Note: This is very basic and won't handle complex structures like fractions well.
        # A proper Math OCR solution would be needed for full accuracy.
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
            "\u00b0": "°", # Degree symbol
            "\u03c0": "π", # Pi symbol
            "\u221a": "√", # Square root
            "\u2013": "-", # En dash
            "\u2014": "-", # Em dash
            "\u2212": "-", # Minus sign
            # Ligatures (common in PDFs)
            "\ufb01": "fi",
            "\ufb02": "fl",
            # Add more mappings as needed based on observed Unicode characters
        }

    def _clean_text(self, text):
        """Cleans text by removing noise and replacing math symbols."""
        # Remove specific noise patterns first
        noise = [
            r"\*X\d+/\d+\*", # Remove codes like *X847750103*
            r"DO NOT WRITE IN THIS MARGIN",
            r"Page \d+ of \d+",
            r"\(page \d+\)",
            r"^\[?Turn over\]?$", # Match 'Turn over' only if it's the whole line
            r"^\[?END OF QUESTION PAPER\]?$",
            r"^\[?FORMULAE LIST\]?$",
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
            r"^\[BLANK PAGE\]$",
            r"^\[?DO NOT WRITE ON THIS PAGE\]?$",
            r"^MARKS$", # Remove MARKS only if it's the whole line
        ]
        cleaned = text
        for pattern in noise:
            # Use re.MULTILINE to handle patterns matching whole lines
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.MULTILINE).strip()
        
        # Replace known math Unicode characters / ligatures
        for uni, replacement in self.math_symbol_map.items():
            cleaned = cleaned.replace(uni, replacement)
            
        # Replace multiple spaces/newlines with single ones
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        cleaned = re.sub(r"\n{2,}", "\n", cleaned).strip()
        
        return cleaned

    def _extract_marks(self, text):
        """Extracts marks specifically looking for patterns like Marks: 2 or [2] at the end."""
        # Look for 'Marks X' or '[X]' at the end of the string/line, possibly preceded by whitespace.
        # This is stricter to avoid capturing numbers within the text.
        match = re.search(r"(?:marks?[:\s]*|\s)\[?(\d+)\]?\s*$", text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None # Default if no marks found

    def _process_block(self, block_text, page_num):
        """Processes a text block to identify questions, parts, and content."""
        lines = block_text.strip().split("\n")
        current_line_index = 0
        while current_line_index < len(lines):
            line = lines[current_line_index].strip()
            current_line_index += 1
            
            if not line:
                continue

            # Try extracting marks from the raw line first
            extracted_marks = self._extract_marks(line)
            # Clean the line *after* trying to extract marks from the end
            cleaned_line = self._clean_text(line)
            
            if not cleaned_line:
                continue

            # Check for main question number (e.g., "1.", "12.")
            main_q_match = re.match(r"^(\d+)\.\s+(.*)", cleaned_line)
            # Check for sub-question part (e.g., "(a)", "(b)")
            sub_q_match = re.match(r"^\((\w+)\)\s+(.*)", cleaned_line)
            # Check for continued sub-question part (e.g., "15. (a)") - less likely with block processing
            continued_sub_q_match = re.match(r"^(\d+)\.\s+\((\w+)\)\s+(.*)", cleaned_line)
            # Check for continued main question (e.g., "15. (continued)")
            continued_main_q_match = re.match(r"^(\d+)\.\s+\(continued\)(.*)", cleaned_line, re.IGNORECASE)

            if continued_sub_q_match:
                q_num = continued_sub_q_match.group(1)
                part_letter = continued_sub_q_match.group(2)
                text = continued_sub_q_match.group(3).strip()
                self.debug_output.append(f"Detected continued sub-question: {q_num}.({part_letter})")
                if self.current_question_number and self.current_question_number == f"{q_num}.":
                    self._add_part(part_letter, text, extracted_marks)
                else:
                    # If it doesn't match current, treat as new main question (edge case)
                    self._finalize_current_question()
                    self.current_question_number = f"{q_num}."
                    self.current_question_text = "" # Reset text for main question
                    self._add_part(part_letter, text, extracted_marks)

            elif main_q_match:
                q_num_str = main_q_match.group(1)
                text = main_q_match.group(2).strip()
                # Check if this is a continuation marker like "15. (continued)"
                if text.lower() == "(continued)":
                     if self.current_question_number == f"{q_num_str}.":
                         self.debug_output.append(f"Ignoring explicit continuation marker for question {q_num_str}.")
                         continue # Skip this line, it's just a marker
                     else:
                         self.debug_output.append(f"Warning: Misplaced continuation marker for question {q_num_str}.")
                         # Fall through to treat as potential new question if needed
                
                # Finalize previous before starting new
                self._finalize_current_question()
                self.current_question_number = q_num_str + "."
                self.current_question_text = text
                self.current_marks = extracted_marks # Assign marks found on the main question line
                self.current_parts = []
                self.current_question_diagrams = []
                self.debug_output.append(f"Detected main question: {self.current_question_number}")

            elif sub_q_match:
                if self.current_question_number:
                    part_letter = sub_q_match.group(1)
                    text = sub_q_match.group(2).strip()
                    self._add_part(part_letter, text, extracted_marks)
                    self.debug_output.append(f"Detected sub-question: {self.current_question_number} ({part_letter})")
                else:
                    self.debug_output.append(f"Warning: Orphaned sub-question found: {cleaned_line}")
                    # Heuristic: If there's a previous question, try attaching
                    if self.questions:
                        last_q = self.questions[-1]
                        part_letter = sub_q_match.group(1)
                        text = sub_q_match.group(2).strip()
                        # Check if this part logically follows the last question's parts
                        last_part_label = last_q.get("parts", [])[-1]["part_label"] if last_q.get("parts") else None
                        if last_part_label and ord(part_letter) == ord(last_part_label) + 1:
                             last_q.setdefault("parts", []).append({
                                 "part_label": part_letter,
                                 "text": text,
                                 "marks": extracted_marks
                             })
                             self.debug_output.append(f"Heuristically attached orphaned part ({part_letter}) to question {last_q['question_number']}")
                        else:
                             self.debug_output.append(f"Could not attach orphaned part ({part_letter}) to last question {last_q['question_number']}")
                    else:
                         self.debug_output.append(f"Could not attach orphaned part ({part_letter}) - no previous question.")

            elif continued_main_q_match:
                 q_num = continued_main_q_match.group(1)
                 text = continued_main_q_match.group(2).strip()
                 if self.current_question_number and self.current_question_number == f"{q_num}.":
                     # Append text only if it's not empty
                     if text:
                         self.current_question_text += " " + text
                     self.debug_output.append(f"Continued main question {q_num}.")
                 else:
                     self.debug_output.append(f"Warning: Misidentified continued question: {cleaned_line}")
                     if self.current_question_number and text:
                         self.current_question_text += " " + text # Append as regular text

            elif self.current_question_number:
                # Append line to the current question or part text
                if cleaned_line:
                    if self.current_parts:
                        # Append to the last part's text
                        self.current_parts[-1]["text"] += " " + cleaned_line
                        # Update marks if found on this line and part has no marks yet
                        if extracted_marks is not None and self.current_parts[-1]["marks"] is None:
                            self.current_parts[-1]["marks"] = extracted_marks
                    else:
                        # Append to the main question text
                        self.current_question_text += " " + cleaned_line
                        # Update main marks if found and no marks yet
                        if extracted_marks is not None and self.current_marks is None:
                            self.current_marks = extracted_marks
            # else: # Text before the first question number is ignored
            #    self.debug_output.append(f"Ignoring text before first question: {cleaned_line[:50]}...")
                            
    def _add_part(self, part_label, text, marks):
        """Adds a new part to the current question."""
        if not self.current_question_number:
            self.debug_output.append(f"Warning: Trying to add part ({part_label}) without a current question.")
            return
            
        cleaned_text = self._clean_text(text) # Clean the incoming text as well
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
            final_parts = []
            total_part_marks = 0
            valid_parts_exist = False
            for part in self.current_parts:
                part_text = re.sub(r"\s{2,}", " ", part["text"]).strip()
                # Remove the part label from the beginning of the text if present
                part_text = re.sub(f"^\({part['part_label']}\)\s*", "", part_text, flags=re.IGNORECASE).strip()
                
                # If marks were None, try extracting again from the final part text
                part_marks = part["marks"]
                if part_marks is None:
                    part_marks = self._extract_marks(part_text)
                
                # Remove marks indication from text after extraction
                part_text = re.sub(r"(?:marks?[:\s]*|\s)\[?(\d+)\]?\s*$", "", part_text, flags=re.IGNORECASE).strip()
                
                if part_text: # Only add part if it has text content
                    final_parts.append({
                        "part_label": part["part_label"],
                        "text": part_text,
                        "marks": part_marks
                    })
                    if part_marks is not None:
                        total_part_marks += part_marks
                    valid_parts_exist = True
                else:
                    self.debug_output.append(f"Skipping empty part {part['part_label']} for question {self.current_question_number}")

            # Remove marks indication from main text after extraction
            final_marks = self.current_marks
            if final_marks is None:
                 final_marks = self._extract_marks(final_text)
            final_text = re.sub(r"(?:marks?[:\s]*|\s)\[?(\d+)\]?\s*$", "", final_text, flags=re.IGNORECASE).strip()
            
            # Remove the question number from the beginning of the text if present
            final_text = re.sub(f"^{re.escape(self.current_question_number)}\s*", "", final_text).strip()

            # If main marks are missing but parts have marks, sum them up (optional)
            # if final_marks is None and total_part_marks > 0:
            #     final_marks = total_part_marks
            #     self.debug_output.append(f"Calculated total marks {final_marks} from parts for question {self.current_question_number}")

            # Only add the question if it has main text or valid parts
            if final_text or valid_parts_exist:
                question_data = {
                    "question_number": self.current_question_number,
                    "text": final_text,
                    "marks": final_marks, # Overall marks if available
                    "parts": final_parts,
                    "metadata": {
                        "has_diagram": "diagram" in final_text.lower() or any("diagram" in p["text"].lower() for p in final_parts),
                        # Add other metadata extraction later (topic, units, etc.)
                    },
                    "diagrams": self.current_question_diagrams # Store associated diagrams
                }
                self.questions.append(question_data)
                self.debug_output.append(f"Finalized question: {self.current_question_number} with {len(final_parts)} parts.")
            else:
                 self.debug_output.append(f"Skipping question {self.current_question_number} due to empty content.")

        # Reset for next question
        self.current_question_number = None
        self.current_question_text = ""
        self.current_marks = None
        self.current_parts = []
        self.current_question_diagrams = [] # Reset diagrams for the next question

    def _extract_images(self, page_num, page):
        """Extracts images from a page and saves them."""
        image_list = page.get_images(full=True)
        extracted_diagrams = []
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = self.doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            # Create a unique filename based on page, index, and content hash
            img_hash = hashlib.md5(image_bytes).hexdigest()[:8]
            image_filename = f"page{page_num + 1}_img{img_index + 1}_{img_hash}.{image_ext}"
            image_path = os.path.join(self.image_output_dir, image_filename)
            
            with open(image_path, "wb") as img_file:
                img_file.write(image_bytes)
            self.debug_output.append(f"Saved image {image_filename}")
            extracted_diagrams.append(image_filename)
            
        return extracted_diagrams

    def extract_questions(self):
        """Extracts questions from the PDF document."""
        for page_num in range(len(self.doc)):
            page = self.doc.load_page(page_num)
            self.debug_output.append(f"--- Processing Page {page_num + 1} ---")
            
            # Extract images first and store them temporarily
            page_diagrams = self._extract_images(page_num, page)
            # Associate diagrams with the question being processed on this page
            # Simple approach: assume diagrams belong to the question starting/continuing on this page
            if self.current_question_number:
                 self.current_question_diagrams.extend(page_diagrams)
            else:
                 # If no question active, maybe store globally? Or associate later? 
                 # For now, let's assume they belong to the *next* question found.
                 self._pending_diagrams = page_diagrams 

            # Extract text blocks with layout preservation
            blocks = page.get_text("blocks") # list of (x0, y0, x1, y1, "text", block_no, block_type)
            blocks.sort(key=lambda b: (b[1], b[0])) # Sort blocks top-to-bottom, left-to-right
            
            for b in blocks:
                block_text = b[4] # The text content of the block
                block_type = b[6] # Type of block (0 for text, 1 for image)
                
                if block_type == 0: # Process text blocks
                    # Filter out blocks that are likely headers/footers based on position
                    y0 = b[1]
                    y1 = b[3]
                    page_height = page.rect.height
                    if y0 < 50 or y1 > page_height - 50: # Arbitrary margin for header/footer
                        cleaned_for_check = self._clean_text(block_text)
                        # Process the block text for logging - replace newlines with spaces
                        block_text_for_log = block_text[:50].replace("\n", " ")
                        if not cleaned_for_check or re.search(r"Page \d+|MARKS|DO NOT WRITE|Turn over", cleaned_for_check, re.IGNORECASE):
                             self.debug_output.append(f"Skipping potential header/footer block: {block_text_for_log}...")
                             continue
                    
                    # If we found a new question and had pending diagrams, associate them now
                    if self.current_question_number is None and hasattr(self, '_pending_diagrams'):
                         self.current_question_diagrams = self._pending_diagrams
                         del self._pending_diagrams # Clear pending
                         
                    # Process the text block
                    self._process_block(block_text, page_num)
                # else: # Ignore image blocks in text processing loop (handled by _extract_images)
                #    pass

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
        final_question_list = []
        # Merge continued questions (like Q15 split across pages)
        merged_questions = {}
        for q in self.questions:
            q_num = q["question_number"]
            if q_num in merged_questions:
                # Merge parts and text
                merged_questions[q_num]["text"] += " " + q["text"]
                merged_questions[q_num]["parts"].extend(q["parts"])
                merged_questions[q_num]["diagrams"].extend(q["diagrams"])
                # Update marks if the first one was null
                if merged_questions[q_num]["marks"] is None:
                    merged_questions[q_num]["marks"] = q["marks"]
                # Update metadata (e.g., has_diagram)
                merged_questions[q_num]["metadata"]["has_diagram"] = merged_questions[q_num]["metadata"]["has_diagram"] or q["metadata"]["has_diagram"]
                self.debug_output.append(f"Merged question {q_num}")
            else:
                merged_questions[q_num] = q
        
        self.questions = list(merged_questions.values())

        for q in self.questions:
            # Ensure text fields are not empty and question number exists
            if q.get("question_number") and (q.get("text") or q.get("parts")):
                 # Ensure parts have text
                 if q.get("parts"):
                     q["parts"] = [p for p in q["parts"] if p.get("text")]
                 # Only add if main text exists or there are valid parts
                 if q.get("text") or q.get("parts"):
                    # Clean up final text fields one last time
                    q["text"] = re.sub(r"\s{2,}", " ", q["text"]).strip()
                    if q.get("parts"):
                        for p in q["parts"]:
                            p["text"] = re.sub(r"\s{2,}", " ", p["text"]).strip()
                    # Remove duplicates in diagrams list
                    q["diagrams"] = sorted(list(set(q["diagrams"])))
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
        with open(output_path, "w", encoding="utf-8") as f:
            for line in self.debug_output:
                f.write(line + "\n")
        logging.info(f"Saved extraction log to {output_path}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract questions from SQA National 5 Maths PDF exam papers.")
    parser.add_argument("pdf_file", help="Path to the PDF exam paper.")
    parser.add_argument("output_dir", help="Directory to save the extracted JSON questions and log file.")
    
    args = parser.parse_args()

    if not os.path.exists(args.pdf_file):
        print(f"Error: PDF file not found at {args.pdf_file}")
        exit(1)

    extractor = AdvancedPDFExtractor(args.pdf_file, args.output_dir)
    extractor.extract_questions()
