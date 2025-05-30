// JavaScript for handling all questions and mathematical input
document.addEventListener('DOMContentLoaded', function() {
    // Load questions from JSON file
    loadQuestions();
    
    // Initialize pagination
    initPagination();
    
    // Initialize math input tools
    initMathInput();
});

// Global variables
let allQuestions = [];
let currentQuestions = [];
let currentPage = 1;
const questionsPerPage = 5;

// Load questions from JSON file
function loadQuestions() {
    // Determine which subject to load based on the current page
    const subject = window.location.pathname.includes('mathematics') ? 'Mathematics' : 'Applications_of_Mathematics';
    const url = `/static/data/${subject}_questions.json`;
    
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            allQuestions = data;
            currentQuestions = [...allQuestions];
            
            // Update question navigation
            updateQuestionNavigation();
            
            // Display first page of questions
            displayQuestions();
        })
        .catch(error => {
            console.error('Error loading questions:', error);
            document.getElementById('questions-container').innerHTML = 
                `<div class="error-message">Error loading questions. Please try again later.</div>`;
        });
}

// Update question navigation with question numbers
function updateQuestionNavigation() {
    const navigationContainer = document.getElementById('question-navigation');
    navigationContainer.innerHTML = '<h3>Jump to Question:</h3><div class="question-numbers">';
    
    // Create a button for each main question number
    const questionNumbers = new Set();
    allQuestions.forEach(question => {
        // Extract main question number (e.g., "5." from "5. (a)")
        const mainNumber = question.question_number.split('.')[0];
        questionNumbers.add(mainNumber);
    });
    
    // Sort question numbers numerically
    const sortedNumbers = Array.from(questionNumbers).sort((a, b) => parseInt(a) - parseInt(b));
    
    // Create buttons
    sortedNumbers.forEach(number => {
        navigationContainer.innerHTML += `<button onclick="jumpToQuestion(${number})">${number}</button>`;
    });
    
    navigationContainer.innerHTML += '</div>';
}

// Jump to a specific question
function jumpToQuestion(questionNumber) {
    // Filter questions to show only those with the selected main number
    const filteredQuestions = allQuestions.filter(question => {
        const mainNumber = question.question_number.split('.')[0];
        return mainNumber === questionNumber.toString();
    });
    
    // Update current questions and display
    currentQuestions = filteredQuestions;
    currentPage = 1;
    displayQuestions();
    updatePagination();
}

// Filter questions by topic
function filterByTopic(topic) {
    if (topic === 'all') {
        currentQuestions = [...allQuestions];
    } else {
        currentQuestions = allQuestions.filter(question => question.topic === topic);
    }
    
    currentPage = 1;
    displayQuestions();
    updatePagination();
}

// Display current page of questions
function displayQuestions() {
    const container = document.getElementById('questions-container');
    container.innerHTML = '';
    
    const startIndex = (currentPage - 1) * questionsPerPage;
    const endIndex = Math.min(startIndex + questionsPerPage, currentQuestions.length);
    
    if (currentQuestions.length === 0) {
        container.innerHTML = '<div class="no-questions">No questions match your criteria. Try a different filter.</div>';
        return;
    }
    
    for (let i = startIndex; i < endIndex; i++) {
        const question = currentQuestions[i];
        
        // Create question element
        const questionElement = document.createElement('div');
        questionElement.className = 'question-card';
        questionElement.id = `question-${i}`;
        
        // Format question text (handle special characters and math notation)
        let formattedText = question.text;
        
        // Create question HTML
        questionElement.innerHTML = `
            <div class="question-header">
                <h3>Question ${question.question_number}</h3>
                <span class="marks">${question.marks} mark${question.marks !== 1 ? 's' : ''}</span>
            </div>
            <div class="question-content">
                <p>${formattedText}</p>
                ${question.metadata.has_diagram ? '<div class="diagram-placeholder">Diagram available in original paper</div>' : ''}
            </div>
            <div class="answer-section">
                <h4>Your Answer:</h4>
                <div class="math-input-container" id="math-input-${i}">
                    <div class="math-input-toolbar"></div>
                    <div class="math-input-field" contenteditable="true" data-question-id="${i}"></div>
                </div>
                <div class="working-space">
                    <h4>Working Space:</h4>
                    <textarea placeholder="Show your calculations here..."></textarea>
                </div>
                <button class="submit-btn" onclick="submitAnswer(${i})">Submit Answer</button>
                <div class="feedback" id="feedback-${i}"></div>
            </div>
        `;
        
        container.appendChild(questionElement);
    }
    
    // Initialize math input for new questions
    initMathInputForCurrentQuestions();
}

// Initialize pagination
function initPagination() {
    const paginationContainer = document.getElementById('pagination');
    
    paginationContainer.innerHTML = `
        <button id="prev-page" onclick="prevPage()" disabled>Previous</button>
        <span id="page-info">Page 1 of 1</span>
        <button id="next-page" onclick="nextPage()">Next</button>
    `;
    
    updatePagination();
}

// Update pagination controls
function updatePagination() {
    const totalPages = Math.ceil(currentQuestions.length / questionsPerPage);
    
    document.getElementById('page-info').textContent = `Page ${currentPage} of ${totalPages}`;
    document.getElementById('prev-page').disabled = currentPage === 1;
    document.getElementById('next-page').disabled = currentPage === totalPages;
}

// Go to previous page
function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        displayQuestions();
        updatePagination();
        window.scrollTo(0, 0);
    }
}

// Go to next page
function nextPage() {
    const totalPages = Math.ceil(currentQuestions.length / questionsPerPage);
    if (currentPage < totalPages) {
        currentPage++;
        displayQuestions();
        updatePagination();
        window.scrollTo(0, 0);
    }
}

// Initialize math input for current questions
function initMathInputForCurrentQuestions() {
    const startIndex = (currentPage - 1) * questionsPerPage;
    const endIndex = Math.min(startIndex + questionsPerPage, currentQuestions.length);
    
    for (let i = startIndex; i < endIndex; i++) {
        const container = document.getElementById(`math-input-${i}`);
        if (container) {
            initMathInputForContainer(container, i);
        }
    }
}

// Initialize math input for a specific container
function initMathInputForContainer(container, questionId) {
    const toolbar = container.querySelector('.math-input-toolbar');
    const inputField = container.querySelector('.math-input-field');
    
    // Create toolbar buttons
    toolbar.innerHTML = `
        <button type="button" data-action="fraction">a/b</button>
        <button type="button" data-action="sqrt">√</button>
        <button type="button" data-action="power">x²</button>
        <button type="button" data-action="pi">π</button>
        <button type="button" data-action="theta">θ</button>
        <button type="button" data-action="plusminus">±</button>
        <button type="button" data-action="infinity">∞</button>
    `;
    
    // Add event listeners to toolbar buttons
    toolbar.querySelectorAll('button').forEach(button => {
        button.addEventListener('click', function() {
            const action = this.getAttribute('data-action');
            insertMathSymbol(inputField, action);
        });
    });
    
    // Add event listener to input field
    inputField.addEventListener('keydown', function(e) {
        // Handle keyboard shortcuts
        if (e.ctrlKey || e.metaKey) {
            switch (e.key) {
                case 'f':
                    e.preventDefault();
                    insertMathSymbol(this, 'fraction');
                    break;
                case 'r':
                    e.preventDefault();
                    insertMathSymbol(this, 'sqrt');
                    break;
                case 'p':
                    e.preventDefault();
                    insertMathSymbol(this, 'power');
                    break;
            }
        }
    });
}

// Insert math symbol into input field
function insertMathSymbol(inputField, action) {
    let html = '';
    
    switch (action) {
        case 'fraction':
            html = '<div class="math-fraction"><div class="math-numerator" contenteditable="true"></div><div class="math-denominator" contenteditable="true"></div></div>';
            break;
        case 'sqrt':
            html = '<span class="math-sqrt">√<span class="math-sqrt-content" contenteditable="true"></span></span>';
            break;
        case 'power':
            html = '<span class="math-power"><span class="math-base" contenteditable="true"></span><sup class="math-exponent" contenteditable="true"></sup></span>';
            break;
        case 'pi':
            html = '<span class="math-symbol">π</span>';
            break;
        case 'theta':
            html = '<span class="math-symbol">θ</span>';
            break;
        case 'plusminus':
            html = '<span class="math-symbol">±</span>';
            break;
        case 'infinity':
            html = '<span class="math-symbol">∞</span>';
            break;
    }
    
    // Insert at cursor position
    const selection = window.getSelection();
    const range = selection.getRangeAt(0);
    
    // Create a temporary div to hold the HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    
    // Insert the HTML
    range.deleteContents();
    
    // Insert all nodes from the temporary div
    const fragment = document.createDocumentFragment();
    let child;
    while (child = tempDiv.firstChild) {
        fragment.appendChild(child);
    }
    
    range.insertNode(fragment);
    
    // Move cursor to appropriate position
    if (action === 'fraction') {
        const numerator = inputField.querySelector('.math-numerator');
        if (numerator) {
            placeCursorAt(numerator);
        }
    } else if (action === 'sqrt') {
        const content = inputField.querySelector('.math-sqrt-content');
        if (content) {
            placeCursorAt(content);
        }
    } else if (action === 'power') {
        const base = inputField.querySelector('.math-base');
        if (base) {
            placeCursorAt(base);
        }
    } else {
        // Move cursor after the inserted symbol
        const newRange = document.createRange();
        newRange.setStartAfter(range.startContainer.childNodes[range.startOffset - 1]);
        newRange.collapse(true);
        
        selection.removeAllRanges();
        selection.addRange(newRange);
    }
}

// Place cursor at the specified element
function placeCursorAt(element) {
    const range = document.createRange();
    range.setStart(element, 0);
    range.collapse(true);
    
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    
    element.focus();
}

// Submit answer for a question
function submitAnswer(questionId) {
    const inputField = document.querySelector(`#math-input-${questionId} .math-input-field`);
    const feedbackElement = document.getElementById(`feedback-${questionId}`);
    
    // Get answer from input field
    const answer = inputField.innerHTML.trim();
    
    if (!answer) {
        feedbackElement.innerHTML = '<div class="error">Please enter an answer.</div>';
        return;
    }
    
    // In a real implementation, this would validate the answer against the correct solution
    // For now, just provide generic feedback
    feedbackElement.innerHTML = `
        <div class="success">
            <h4>Feedback:</h4>
            <p>Your answer has been submitted. In a real exam, you would receive marks based on your working and final answer.</p>
            <p>Remember to show all your working steps to maximize your marks.</p>
        </div>
    `;
}

// Initialize math input tools
function initMathInput() {
    // This function is called once on page load
    // Individual math inputs are initialized when questions are displayed
}
