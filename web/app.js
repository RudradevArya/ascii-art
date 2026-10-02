/**
 * Block Art Generator - Web UI
 * Uses Pyodide to run blockart.py in the browser
 */

let pyodide = null;
let imageData = null;

// DOM elements
const elements = {
    loadingOverlay: document.getElementById('loading-overlay'),
    loadingMessage: document.getElementById('loading-message'),
    generateBtn: document.getElementById('generate-btn'),
    btnText: document.querySelector('.btn-text'),
    btnLoading: document.querySelector('.btn-loading'),
    imageFile: document.getElementById('image-file'),
    dropZone: document.getElementById('drop-zone'),
    imagePreviewContainer: document.getElementById('image-preview-container'),
    imagePreview: document.getElementById('image-preview'),
    clearImage: document.getElementById('clear-image'),
    textContent: document.getElementById('text-content'),
    outputSection: document.getElementById('output-section'),
    artPreview: document.getElementById('art-preview'),
    snippetCode: document.getElementById('snippet-code'),
    plaintextCode: document.getElementById('plaintext-code'),
    dimensions: document.getElementById('dimensions'),
    colorsInfo: document.getElementById('colors-info'),
    errorMessage: document.getElementById('error-message'),
    mode: document.getElementById('mode'),
    cols: document.getElementById('cols'),
    colsValue: document.getElementById('cols-value'),
    crop: document.getElementById('crop'),
    fontSize: document.getElementById('font-size'),
    fontSizeValue: document.getElementById('font-size-value'),
    fgColor: document.getElementById('fg-color'),
    fgColorPicker: document.getElementById('fg-color-picker'),
    bgColor: document.getElementById('bg-color'),
    bgColorPicker: document.getElementById('bg-color-picker'),
    texture: document.getElementById('texture'),
    textureValue: document.getElementById('texture-value'),
    margin: document.getElementById('margin'),
    marginValue: document.getElementById('margin-value'),
    gamma: document.getElementById('gamma'),
    gammaValue: document.getElementById('gamma-value'),
    colorPalette: document.getElementById('color-palette'),
    invert: document.getElementById('invert'),
    dither: document.getElementById('dither'),
    label: document.getElementById('label'),
    seed: document.getElementById('seed'),
};

// State
let currentResult = null;

// Initialize Pyodide
async function initPyodide() {
    try {
        updateLoadingMessage('Loading Pyodide runtime...');
        pyodide = await loadPyodide();
        
        updateLoadingMessage('Installing Python packages...');
        await pyodide.loadPackage('micropip');
        const micropip = pyodide.pyimport('micropip');
        
        // Install required packages
        await micropip.install(['pillow', 'numpy']);
        
        updateLoadingMessage('Loading blockart module...');
        
        // Fetch the original blockart.py and the wrapper
        // Try ./blockart.py first (Cloudflare Pages with cp build), fall back to ../blockart.py (local repo root)
        const fetchBlockart = async () => {
            const paths = ['./blockart.py', '../blockart.py'];
            for (const path of paths) {
                try {
                    const response = await fetch(path);
                    if (response.ok) {
                        return response.text();
                    }
                } catch (e) {
                    // Try next path
                }
            }
            throw new Error('Could not load blockart.py from ./blockart.py or ../blockart.py');
        };
        
        const [blockartCode, wrapperCode] = await Promise.all([
            fetchBlockart(),
            fetch('blockart_web.py').then(r => r.text())
        ]);
        
        // Write blockart.py to Pyodide filesystem
        pyodide.FS.writeFile('/home/pyodide/blockart.py', blockartCode);
        
        // Run the wrapper code
        await pyodide.runPythonAsync(wrapperCode);
        
        updateLoadingMessage('Ready!');
        
        // Hide loading overlay after a brief delay
        setTimeout(() => {
            elements.loadingOverlay.classList.add('hidden');
        }, 500);
        
    } catch (error) {
        console.error('Failed to initialize Pyodide:', error);
        updateLoadingMessage(`Error: ${error.message}`);
        elements.loadingOverlay.querySelector('.loading-hint').textContent = 
            'Please refresh the page to try again.';
    }
}

function updateLoadingMessage(message) {
    elements.loadingMessage.textContent = message;
}

// Tab switching
function setupTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            
            // Update tab buttons
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Update tab content
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.getElementById(`${tab}-input`).classList.add('active');
            
            updateGenerateButton();
        });
    });
    
    // Output tabs
    document.querySelectorAll('.output-tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const output = btn.dataset.output;
            
            document.querySelectorAll('.output-tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            document.querySelectorAll('.output-content').forEach(c => c.classList.remove('active'));
            document.getElementById(`${output}-output`).classList.add('active');
        });
    });
}

// Image handling
function setupImageHandling() {
    // Click to browse
    elements.dropZone.addEventListener('click', () => {
        elements.imageFile.click();
    });
    
    // File input change
    elements.imageFile.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleImageFile(e.target.files[0]);
        }
    });
    
    // Drag and drop
    elements.dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        elements.dropZone.classList.add('drag-over');
    });
    
    elements.dropZone.addEventListener('dragleave', () => {
        elements.dropZone.classList.remove('drag-over');
    });
    
    elements.dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        elements.dropZone.classList.remove('drag-over');
        
        if (e.dataTransfer.files.length > 0) {
            handleImageFile(e.dataTransfer.files[0]);
        }
    });
    
    // Clear image
    elements.clearImage.addEventListener('click', () => {
        clearImage();
    });
}

function handleImageFile(file) {
    if (!file.type.startsWith('image/')) {
        showError('Please select an image file (PNG, JPG, WebP)');
        return;
    }
    
    const reader = new FileReader();
    reader.onload = (e) => {
        imageData = new Uint8Array(e.target.result);
        
        // Show preview
        const blob = new Blob([imageData], { type: file.type });
        elements.imagePreview.src = URL.createObjectURL(blob);
        elements.dropZone.style.display = 'none';
        elements.imagePreviewContainer.classList.remove('hidden');
        
        updateGenerateButton();
    };
    reader.readAsArrayBuffer(file);
}

function clearImage() {
    imageData = null;
    elements.imageFile.value = '';
    elements.imagePreview.src = '';
    elements.dropZone.style.display = 'block';
    elements.imagePreviewContainer.classList.add('hidden');
    updateGenerateButton();
}

// Options handling
function setupOptions() {
    // Range inputs with value display
    const rangeInputs = [
        { input: elements.cols, display: elements.colsValue },
        { input: elements.fontSize, display: elements.fontSizeValue },
        { input: elements.texture, display: elements.textureValue },
        { input: elements.margin, display: elements.marginValue },
        { input: elements.gamma, display: elements.gammaValue },
    ];
    
    rangeInputs.forEach(({ input, display }) => {
        input.addEventListener('input', () => {
            display.textContent = input.value;
        });
    });
    
    // Mode toggle - show/hide relevant options
    elements.mode.addEventListener('change', () => {
        const isMask = elements.mode.value === 'mask';
        
        document.querySelectorAll('.mask-option').forEach(el => {
            el.classList.toggle('hidden', !isMask);
        });
        
        document.querySelectorAll('.tone-option').forEach(el => {
            el.classList.toggle('hidden', isMask);
        });
    });
    
    // Color picker sync
    elements.fgColorPicker.addEventListener('input', () => {
        elements.fgColor.value = elements.fgColorPicker.value;
    });
    
    elements.bgColorPicker.addEventListener('input', () => {
        elements.bgColor.value = elements.bgColorPicker.value;
    });
    
    // Text input sync
    elements.textContent.addEventListener('input', () => {
        updateGenerateButton();
    });
}

function updateGenerateButton() {
    const isImageTab = document.querySelector('.tab-btn.active').dataset.tab === 'image';
    const hasInput = isImageTab ? imageData !== null : elements.textContent.value.trim() !== '';
    
    elements.generateBtn.disabled = !hasInput || !pyodide;
}

// Generate art
async function generateArt() {
    hideError();
    
    const isImageTab = document.querySelector('.tab-btn.active').dataset.tab === 'image';
    
    // Show loading state
    elements.btnText.classList.add('hidden');
    elements.btnLoading.classList.remove('hidden');
    elements.generateBtn.disabled = true;
    
    try {
        const options = {
            cols: parseInt(elements.cols.value),
            mode: elements.mode.value,
            crop: elements.crop.value,
            margin: parseFloat(elements.margin.value),
            fg: elements.fgColor.value || null,
            bg: elements.bgColor.value || null,
            texture: parseFloat(elements.texture.value),
            invert: elements.invert.checked,
            gamma: parseFloat(elements.gamma.value),
            dither: elements.dither.checked,
            color: parseInt(elements.colorPalette.value),
            font_size: parseFloat(elements.fontSize.value),
            seed: parseInt(elements.seed.value),
            label: elements.label.value || 'Block art',
        };
        
        let result;
        
        if (isImageTab) {
            // Process image
            result = await processImage(imageData, options);
        } else {
            // Process text
            const text = elements.textContent.value;
            result = await processText(text, options);
        }
        
        currentResult = result;
        displayResult(result);
        
    } catch (error) {
        console.error('Generation error:', error);
        showError(`Failed to generate art: ${error.message}`);
    } finally {
        // Reset button state
        elements.btnText.classList.remove('hidden');
        elements.btnLoading.classList.add('hidden');
        updateGenerateButton();
    }
}

async function processImage(imageBytes, options) {
    // Convert Uint8Array to Python bytes
    const optionsJson = JSON.stringify(options);
    
    pyodide.globals.set('_image_bytes', imageBytes);
    pyodide.globals.set('_options_json', optionsJson);
    
    const resultJson = await pyodide.runPythonAsync(`
import json
_options = json.loads(_options_json)
# Filter out None values
_options = {k: v for k, v in _options.items() if v is not None}
_result = process_image(bytes(_image_bytes), **_options)
json.dumps(_result)
`);
    
    return JSON.parse(resultJson);
}

async function processText(text, options) {
    const optionsJson = JSON.stringify(options);
    
    pyodide.globals.set('_text', text);
    pyodide.globals.set('_options_json', optionsJson);
    
    const resultJson = await pyodide.runPythonAsync(`
import json
_options = json.loads(_options_json)
# Filter out None values
_options = {k: v for k, v in _options.items() if v is not None}
_result = process_text(_text, **_options)
json.dumps(_result)
`);
    
    return JSON.parse(resultJson);
}

function displayResult(result) {
    // Show output section
    elements.outputSection.classList.remove('hidden');
    
    // Update dimensions info
    elements.dimensions.textContent = `${result.cols} × ${result.rows} characters`;
    elements.colorsInfo.textContent = `Background: ${result.bg}, ${Object.keys(result.palette).length} color(s)`;
    
    // Render preview
    elements.artPreview.innerHTML = result.snippet_html;
    
    // Show code
    elements.snippetCode.textContent = result.snippet_html;
    elements.plaintextCode.textContent = result.art_txt;
    
    // Scroll to output
    elements.outputSection.scrollIntoView({ behavior: 'smooth' });
}

// Copy and download functions
function setupOutputActions() {
    document.getElementById('copy-snippet').addEventListener('click', () => {
        if (currentResult) {
            copyToClipboard(currentResult.snippet_html, 'HTML snippet copied!');
        }
    });
    
    document.getElementById('copy-plaintext').addEventListener('click', () => {
        if (currentResult) {
            copyToClipboard(currentResult.art_txt, 'Plain text copied!');
        }
    });
    
    document.getElementById('download-snippet').addEventListener('click', () => {
        if (currentResult) {
            downloadFile('snippet.html', currentResult.snippet_html, 'text/html');
        }
    });
    
    document.getElementById('download-preview').addEventListener('click', () => {
        if (currentResult) {
            downloadFile('preview.html', currentResult.preview_html, 'text/html');
        }
    });
    
    document.getElementById('download-plaintext').addEventListener('click', () => {
        if (currentResult) {
            downloadFile('art.txt', currentResult.art_txt, 'text/plain');
        }
    });
}

async function copyToClipboard(text, successMessage) {
    try {
        await navigator.clipboard.writeText(text);
        showTemporaryMessage(successMessage);
    } catch (error) {
        showError('Failed to copy to clipboard');
    }
}

function downloadFile(filename, content, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function showTemporaryMessage(message) {
    // Create a temporary toast notification
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        left: 50%;
        transform: translateX(-50%);
        background: var(--success);
        color: white;
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        font-size: 0.875rem;
        z-index: 1000;
        animation: fadeInOut 2s ease forwards;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        document.body.removeChild(toast);
    }, 2000);
}

// Add animation keyframes
const style = document.createElement('style');
style.textContent = `
@keyframes fadeInOut {
    0% { opacity: 0; transform: translateX(-50%) translateY(20px); }
    20% { opacity: 1; transform: translateX(-50%) translateY(0); }
    80% { opacity: 1; transform: translateX(-50%) translateY(0); }
    100% { opacity: 0; transform: translateX(-50%) translateY(-20px); }
}
`;
document.head.appendChild(style);

// Error handling
function showError(message) {
    elements.errorMessage.textContent = message;
    elements.errorMessage.classList.remove('hidden');
}

function hideError() {
    elements.errorMessage.classList.add('hidden');
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    setupImageHandling();
    setupOptions();
    setupOutputActions();
    
    elements.generateBtn.addEventListener('click', generateArt);
    
    // Start loading Pyodide
    initPyodide();
});
