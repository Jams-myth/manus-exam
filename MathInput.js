/* MathInput.js - A tool for inputting mathematical symbols and expressions */

class MathInput {
  constructor(options = {}) {
    this.options = {
      targetElement: null,
      displayElement: null,
      previewElement: null,
      ...options
    };
    
    this.initialize();
  }
  
  initialize() {
    this.createToolbar();
    this.setupEventListeners();
    this.renderMathJax();
  }
  
  createToolbar() {
    const toolbar = document.createElement('div');
    toolbar.className = 'math-input-toolbar';
    toolbar.innerHTML = `
      <div class="math-input-toolbar-section">
        <button type="button" class="math-input-btn" data-action="fraction" title="Fraction">
          <span class="math-symbol">\\frac{a}{b}</span>
        </button>
        <button type="button" class="math-input-btn" data-action="squareRoot" title="Square Root">
          <span class="math-symbol">\\sqrt{x}</span>
        </button>
        <button type="button" class="math-input-btn" data-action="nthRoot" title="nth Root">
          <span class="math-symbol">\\sqrt[n]{x}</span>
        </button>
        <button type="button" class="math-input-btn" data-action="superscript" title="Superscript/Power">
          <span class="math-symbol">x^{n}</span>
        </button>
        <button type="button" class="math-input-btn" data-action="subscript" title="Subscript">
          <span class="math-symbol">x_{i}</span>
        </button>
      </div>
      <div class="math-input-toolbar-section">
        <button type="button" class="math-input-btn" data-action="pi" title="Pi">
          <span class="math-symbol">\\pi</span>
        </button>
        <button type="button" class="math-input-btn" data-action="theta" title="Theta">
          <span class="math-symbol">\\theta</span>
        </button>
        <button type="button" class="math-input-btn" data-action="infinity" title="Infinity">
          <span class="math-symbol">\\infty</span>
        </button>
        <button type="button" class="math-input-btn" data-action="plusMinus" title="Plus/Minus">
          <span class="math-symbol">\\pm</span>
        </button>
        <button type="button" class="math-input-btn" data-action="degree" title="Degree">
          <span class="math-symbol">^{\\circ}</span>
        </button>
      </div>
      <div class="math-input-toolbar-section">
        <button type="button" class="math-input-btn" data-action="lessThanEqual" title="Less Than or Equal">
          <span class="math-symbol">\\leq</span>
        </button>
        <button type="button" class="math-input-btn" data-action="greaterThanEqual" title="Greater Than or Equal">
          <span class="math-symbol">\\geq</span>
        </button>
        <button type="button" class="math-input-btn" data-action="notEqual" title="Not Equal">
          <span class="math-symbol">\\neq</span>
        </button>
        <button type="button" class="math-input-btn" data-action="approx" title="Approximately Equal">
          <span class="math-symbol">\\approx</span>
        </button>
        <button type="button" class="math-input-btn" data-action="parallel" title="Parallel">
          <span class="math-symbol">\\parallel</span>
        </button>
      </div>
      <div class="math-input-toolbar-section">
        <button type="button" class="math-input-btn" data-action="sin" title="Sine">
          <span class="math-symbol">\\sin</span>
        </button>
        <button type="button" class="math-input-btn" data-action="cos" title="Cosine">
          <span class="math-symbol">\\cos</span>
        </button>
        <button type="button" class="math-input-btn" data-action="tan" title="Tangent">
          <span class="math-symbol">\\tan</span>
        </button>
        <button type="button" class="math-input-btn" data-action="log" title="Logarithm">
          <span class="math-symbol">\\log</span>
        </button>
        <button type="button" class="math-input-btn" data-action="ln" title="Natural Logarithm">
          <span class="math-symbol">\\ln</span>
        </button>
      </div>
      <div class="math-input-toolbar-section">
        <button type="button" class="math-input-btn" data-action="mixedNumber" title="Mixed Number">
          <span class="math-symbol">a\\frac{b}{c}</span>
        </button>
        <button type="button" class="math-input-btn" data-action="vector" title="Vector">
          <span class="math-symbol">\\vec{a}</span>
        </button>
        <button type="button" class="math-input-btn" data-action="matrix2x2" title="2x2 Matrix">
          <span class="math-symbol">\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}</span>
        </button>
        <button type="button" class="math-input-btn" data-action="integral" title="Integral">
          <span class="math-symbol">\\int_{a}^{b}</span>
        </button>
        <button type="button" class="math-input-btn" data-action="sum" title="Summation">
          <span class="math-symbol">\\sum_{i=1}^{n}</span>
        </button>
      </div>
    `;
    
    // Insert toolbar before the target element
    if (this.options.targetElement) {
      this.options.targetElement.parentNode.insertBefore(toolbar, this.options.targetElement);
    }
    
    this.toolbar = toolbar;
  }
  
  setupEventListeners() {
    if (!this.toolbar || !this.options.targetElement) return;
    
    // Add click event listeners to all toolbar buttons
    const buttons = this.toolbar.querySelectorAll('.math-input-btn');
    buttons.forEach(button => {
      button.addEventListener('click', (e) => {
        const action = button.getAttribute('data-action');
        this.performAction(action);
      });
    });
    
    // Add input event listener to target element
    this.options.targetElement.addEventListener('input', () => {
      this.updatePreview();
    });
    
    // Add keyboard shortcuts for common math symbols
    this.options.targetElement.addEventListener('keydown', (e) => {
      // Ctrl+/ for fraction
      if (e.ctrlKey && e.key === '/') {
        e.preventDefault();
        this.performAction('fraction');
      }
      // Ctrl+R for square root
      else if (e.ctrlKey && e.key === 'r') {
        e.preventDefault();
        this.performAction('squareRoot');
      }
      // Ctrl+^ for superscript
      else if (e.ctrlKey && e.key === '^') {
        e.preventDefault();
        this.performAction('superscript');
      }
    });
  }
  
  performAction(action) {
    if (!this.options.targetElement) return;
    
    const input = this.options.targetElement;
    const cursorPos = input.selectionStart;
    const textBefore = input.value.substring(0, cursorPos);
    const textAfter = input.value.substring(cursorPos);
    
    let insertText = '';
    let cursorOffset = 0;
    
    switch (action) {
      case 'fraction':
        insertText = '\\frac{}{}'
        cursorOffset = -3;
        break;
      case 'squareRoot':
        insertText = '\\sqrt{}';
        cursorOffset = -1;
        break;
      case 'nthRoot':
        insertText = '\\sqrt[]{}'
        cursorOffset = -1;
        break;
      case 'superscript':
        insertText = '^{}';
        cursorOffset = -1;
        break;
      case 'subscript':
        insertText = '_{}';
        cursorOffset = -1;
        break;
      case 'pi':
        insertText = '\\pi';
        break;
      case 'theta':
        insertText = '\\theta';
        break;
      case 'infinity':
        insertText = '\\infty';
        break;
      case 'plusMinus':
        insertText = '\\pm';
        break;
      case 'degree':
        insertText = '^{\\circ}';
        break;
      case 'lessThanEqual':
        insertText = '\\leq';
        break;
      case 'greaterThanEqual':
        insertText = '\\geq';
        break;
      case 'notEqual':
        insertText = '\\neq';
        break;
      case 'approx':
        insertText = '\\approx';
        break;
      case 'parallel':
        insertText = '\\parallel';
        break;
      case 'sin':
        insertText = '\\sin';
        break;
      case 'cos':
        insertText = '\\cos';
        break;
      case 'tan':
        insertText = '\\tan';
        break;
      case 'log':
        insertText = '\\log';
        break;
      case 'ln':
        insertText = '\\ln';
        break;
      case 'mixedNumber':
        insertText = '\\;\\frac{}{}';
        cursorOffset = -4;
        break;
      case 'vector':
        insertText = '\\vec{}';
        cursorOffset = -1;
        break;
      case 'matrix2x2':
        insertText = '\\begin{pmatrix} & \\\\ & \\end{pmatrix}';
        cursorOffset = -20;
        break;
      case 'integral':
        insertText = '\\int_{}^{}';
        cursorOffset = -3;
        break;
      case 'sum':
        insertText = '\\sum_{}^{}';
        cursorOffset = -3;
        break;
      default:
        return;
    }
    
    // Insert the text at cursor position
    input.value = textBefore + insertText + textAfter;
    
    // Set cursor position
    const newCursorPos = cursorPos + insertText.length + cursorOffset;
    input.setSelectionRange(newCursorPos, newCursorPos);
    
    // Focus back on the input
    input.focus();
    
    // Update preview
    this.updatePreview();
  }
  
  updatePreview() {
    if (!this.options.targetElement || !this.options.previewElement) return;
    
    const latex = this.options.targetElement.value;
    
    // Wrap the LaTeX in math delimiters if not already present
    let displayLatex = latex;
    if (!displayLatex.startsWith('$$') && !displayLatex.startsWith('\\[') && 
        !displayLatex.startsWith('$') && !displayLatex.startsWith('\\(')) {
      displayLatex = '$$' + displayLatex + '$$';
    }
    
    this.options.previewElement.innerHTML = displayLatex;
    
    // Trigger MathJax to render the preview
    this.renderMathJax();
  }
  
  renderMathJax() {
    if (window.MathJax && this.options.previewElement) {
      MathJax.typesetPromise([this.options.previewElement]).catch(function (err) {
        console.log('Error rendering MathJax:', err);
      });
    }
  }
}

// CSS for the Math Input Toolbar
const mathInputStyles = `
.math-input-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 10px;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: #f8f9fa;
}

.math-input-toolbar-section {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-right: 10px;
  margin-bottom: 5px;
}

.math-input-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 36px;
  padding: 0 8px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  background-color: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.math-input-btn:hover {
  background-color: #e9ecef;
  border-color: #adb5bd;
}

.math-input-btn:active {
  background-color: #dee2e6;
  transform: translateY(1px);
}

.math-input-preview {
  margin-top: 10px;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  min-height: 40px;
  background-color: #f8f9fa;
}

.math-preview-container {
  padding: 10px;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  background-color: #f8f9fa;
  min-height: 40px;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .math-input-toolbar {
    flex-direction: column;
  }
  
  .math-input-toolbar-section {
    margin-right: 0;
    margin-bottom: 8px;
  }
}
`;

// Add styles to document
function addMathInputStyles() {
  const styleElement = document.createElement('style');
  styleElement.textContent = mathInputStyles;
  document.head.appendChild(styleElement);
}

// Initialize MathInput on page load
document.addEventListener('DOMContentLoaded', function() {
  addMathInputStyles();
  
  // Find all elements with data-math-input attribute
  const mathInputElements = document.querySelectorAll('[data-math-input]');
  
  mathInputElements.forEach(element => {
    const inputId = element.id;
    const previewId = element.getAttribute('data-math-preview');
    
    if (inputId && previewId) {
      const previewElement = document.getElementById(previewId);
      
      if (previewElement) {
        new MathInput({
          targetElement: element,
          previewElement: previewElement
        });
      }
    }
  });
});

// Function to initialize MathInput for dynamically added elements
function initializeMathInput() {
  // Find all elements with data-math-input attribute that don't have a toolbar yet
  const mathInputElements = document.querySelectorAll('[data-math-input]:not(.math-input-initialized)');
  
  mathInputElements.forEach(element => {
    const inputId = element.id;
    const previewId = element.getAttribute('data-math-preview');
    
    if (inputId && previewId) {
      const previewElement = document.getElementById(previewId);
      
      if (previewElement) {
        new MathInput({
          targetElement: element,
          previewElement: previewElement
        });
        
        // Mark as initialized
        element.classList.add('math-input-initialized');
      }
    }
  });
}

// Export the initialization function for use in other scripts
window.initializeMathInput = initializeMathInput;
