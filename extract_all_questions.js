// Extract all questions from the exam papers
const fs = require('fs');
const path = require('path');
const pdfParse = require('pdf-parse');

// Function to extract questions from PDF
async function extractQuestionsFromPDF(pdfPath) {
  try {
    // Read the PDF file
    const dataBuffer = fs.readFileSync(pdfPath);
    
    // Parse the PDF
    const data = await pdfParse(dataBuffer);
    
    // Get the text content
    const text = data.text;
    
    // Regular expression to identify questions
    // This pattern looks for numbered questions (e.g., "1.", "2.", etc.)
    const questionPattern = /(\d+\.)\s*(.*?)(?=\d+\.|$)/gs;
    
    // Extract questions
    const questions = [];
    let match;
    while ((match = questionPattern.exec(text)) !== null) {
      const questionNumber = match[1].trim();
      const questionText = match[2].trim();
      
      // Extract marks (if available)
      const marksPattern = /\((\d+)\s*marks?\)/i;
      const marksMatch = questionText.match(marksPattern);
      const marks = marksMatch ? parseInt(marksMatch[1]) : 1;
      
      questions.push({
        number: questionNumber,
        text: questionText,
        marks: marks
      });
    }
    
    return questions;
  } catch (error) {
    console.error('Error extracting questions:', error);
    return [];
  }
}

// Function to process all PDFs in a directory
async function processAllPDFs(directory) {
  try {
    const files = fs.readdirSync(directory);
    const pdfFiles = files.filter(file => file.toLowerCase().endsWith('.pdf'));
    
    const allQuestions = {};
    
    for (const pdfFile of pdfFiles) {
      const pdfPath = path.join(directory, pdfFile);
      console.log(`Processing ${pdfFile}...`);
      
      const questions = await extractQuestionsFromPDF(pdfPath);
      
      // Determine subject from filename
      let subject = 'Mathematics';
      if (pdfFile.includes('Applications')) {
        subject = 'Applications of Mathematics';
      }
      
      if (!allQuestions[subject]) {
        allQuestions[subject] = [];
      }
      
      allQuestions[subject] = [...allQuestions[subject], ...questions];
      
      console.log(`Extracted ${questions.length} questions from ${pdfFile}`);
    }
    
    // Save extracted questions to JSON files
    for (const subject in allQuestions) {
      const outputPath = path.join(directory, `${subject.replace(/\s+/g, '_')}_questions.json`);
      fs.writeFileSync(outputPath, JSON.stringify(allQuestions[subject], null, 2));
      console.log(`Saved ${allQuestions[subject].length} questions to ${outputPath}`);
    }
    
    return allQuestions;
  } catch (error) {
    console.error('Error processing PDFs:', error);
    return {};
  }
}

// Main function
async function main() {
  const pdfDirectory = './exam_papers';
  const allQuestions = await processAllPDFs(pdfDirectory);
  
  console.log('Question extraction complete!');
  console.log('Summary:');
  for (const subject in allQuestions) {
    console.log(`${subject}: ${allQuestions[subject].length} questions`);
  }
}

main();
