// Legal RAG Frontend - JavaScript

const API_BASE = 'http://localhost:8000/api';

let currentSessionId = null;
let uploadedEsempi = [];
let uploadedTemplate = null;

// ==================== INIT ====================

document.addEventListener('DOMContentLoaded', () => {
    initApp();
    setupEventListeners();
});

async function initApp() {
    // Crea sessione
    await createSession();

    // Carica stato sistema
    await checkStatus();

    // Carica lista normative
    await loadNormative();
}

// ==================== SESSION ====================

async function createSession() {
    try {
        const response = await fetch(`${API_BASE}/session/create`, {
            method: 'POST'
        });
        const data = await response.json();
        currentSessionId = data.session_id;
        console.log('Session created:', currentSessionId);
    } catch (error) {
        console.error('Error creating session:', error);
        showError('Errore creazione sessione');
    }
}

// ==================== STATUS ====================

async function checkStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        const data = await response.json();

        const statusEl = document.getElementById('status');
        statusEl.textContent = data.status === 'ready' ? ' Sistema Pronto' : '  Sistema Non Pronto';
        statusEl.className = `status ${data.status}`;

        console.log('System status:', data);
    } catch (error) {
        const statusEl = document.getElementById('status');
        statusEl.textContent = 'L Errore Connessione';
        statusEl.className = 'status error';
    }
}

async function loadNormative() {
    try {
        const response = await fetch(`${API_BASE}/normative`);
        const data = await response.json();

        const listEl = document.getElementById('normativeList');
        listEl.innerHTML = '';

        if (data.normative.length === 0) {
            listEl.innerHTML = '<p style="color: #7f8c8d;">Nessuna normativa caricata</p>';
            return;
        }

        data.normative.forEach(norm => {
            const item = document.createElement('div');
            item.className = 'normative-item';
            item.innerHTML = `
                <div class="code">${norm.codice}</div>
                <div class="filename">${norm.filename}</div>
            `;
            listEl.appendChild(item);
        });

        console.log('Normative loaded:', data.normative.length);
    } catch (error) {
        console.error('Error loading normative:', error);
    }
}

// ==================== EVENT LISTENERS ====================

function setupEventListeners() {
    // Drop zone esempi
    setupDropZone('dropZoneEsempi', 'fileInputEsempi', handleEsempiUpload);

    // Drop zone template
    setupDropZone('dropZoneTemplate', 'fileInputTemplate', handleTemplateUpload);

    // Generate button
    document.getElementById('generateBtn').addEventListener('click', handleGenerate);

    // Download button
    document.getElementById('downloadBtn').addEventListener('click', handleDownload);
}

function setupDropZone(dropZoneId, inputId, uploadHandler) {
    const dropZone = document.getElementById(dropZoneId);
    const fileInput = document.getElementById(inputId);

    // Click to select
    dropZone.addEventListener('click', () => fileInput.click());

    // File input change
    fileInput.addEventListener('change', (e) => uploadHandler(e.target.files));

    // Drag and drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        uploadHandler(e.dataTransfer.files);
    });
}

// ==================== UPLOAD HANDLERS ====================

async function handleEsempiUpload(files) {
    const fileArray = Array.from(files);

    // Validate files
    const validFiles = fileArray.filter(f =>
        f.name.endsWith('.pdf') ||
        f.name.endsWith('.docx') ||
        f.name.endsWith('.txt')
    );

    if (validFiles.length === 0) {
        showError('Nessun file valido selezionato');
        return;
    }

    // Upload
    const formData = new FormData();
    formData.append('session_id', currentSessionId);
    validFiles.forEach(file => formData.append('files', file));

    try {
        const response = await fetch(`${API_BASE}/upload/esempio`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        uploadedEsempi.push(...data.uploaded_files);

        updateEsempiList();
        showSuccess(`${data.count} file caricati`);
    } catch (error) {
        console.error('Upload error:', error);
        showError('Errore caricamento file');
    }
}

async function handleTemplateUpload(files) {
    if (files.length === 0) return;

    const file = files[0];

    // Validate
    if (!file.name.endsWith('.docx') && !file.name.endsWith('.txt')) {
        showError('Formato template non valido');
        return;
    }

    // Upload
    const formData = new FormData();
    formData.append('session_id', currentSessionId);
    formData.append('file', file);

    try {
        const response = await fetch(`${API_BASE}/upload/template`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        uploadedTemplate = data;

        updateTemplateInfo();
        showSuccess('Template caricato');
    } catch (error) {
        console.error('Upload error:', error);
        showError('Errore caricamento template');
    }
}

// ==================== UI UPDATES ====================

function updateEsempiList() {
    const listEl = document.getElementById('esempiList');
    listEl.innerHTML = '';

    uploadedEsempi.forEach((file, index) => {
        const item = document.createElement('div');
        item.className = 'file-item';
        item.innerHTML = `
            <span class="file-name">=Ä ${file.filename}</span>
            <span class="file-size">${formatBytes(file.size)}</span>
            <button class="btn-remove" onclick="removeEsempio(${index})"></button>
        `;
        listEl.appendChild(item);
    });
}

function updateTemplateInfo() {
    const infoEl = document.getElementById('templateInfo');

    if (uploadedTemplate) {
        infoEl.innerHTML = `
            <div class="file-item">
                <span class="file-name">=Ä ${uploadedTemplate.template_file}</span>
                <span class="file-size">${formatBytes(uploadedTemplate.size)}</span>
                <button class="btn-remove" onclick="removeTemplate()"></button>
            </div>
        `;
    } else {
        infoEl.innerHTML = '';
    }
}

function removeEsempio(index) {
    uploadedEsempi.splice(index, 1);
    updateEsempiList();
}

function removeTemplate() {
    uploadedTemplate = null;
    updateTemplateInfo();
}

// ==================== GENERATE ====================

async function handleGenerate() {
    const promptEl = document.getElementById('userPrompt');
    const styleEl = document.getElementById('styleSelect');
    const btnEl = document.getElementById('generateBtn');

    const prompt = promptEl.value.trim();

    if (!prompt) {
        showError('Inserisci una richiesta');
        return;
    }

    // Disable button
    btnEl.disabled = true;
    btnEl.innerHTML = '<span class="loading"></span> Generazione in corso...';

    try {
        const response = await fetch(`${API_BASE}/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_prompt: prompt,
                session_id: currentSessionId,
                style: styleEl.value
            })
        });

        const data = await response.json();

        // Show output
        displayOutput(data);

        showSuccess('Relazione generata!');
    } catch (error) {
        console.error('Generate error:', error);
        showError('Errore generazione relazione');
    } finally {
        btnEl.disabled = false;
        btnEl.innerHTML = '<span class="btn-icon">=€</span> Genera Relazione';
    }
}

function displayOutput(data) {
    const section = document.getElementById('outputSection');
    section.style.display = 'block';

    // Confidence
    const progressBar = document.getElementById('confidenceProgress');
    const confidenceValue = document.getElementById('confidenceValue');
    const confidence = Math.round(data.confidence * 100);

    progressBar.style.width = confidence + '%';
    confidenceValue.textContent = confidence + '%';

    // Needs review
    const reviewEl = document.getElementById('needsReview');
    reviewEl.style.display = data.needs_review ? 'block' : 'none';

    // Document
    const documentEl = document.getElementById('documentOutput');
    documentEl.textContent = data.document;

    // Citations
    const citationsEl = document.getElementById('citationsList');
    citationsEl.innerHTML = '';

    data.citations.forEach(citation => {
        const item = document.createElement('div');
        item.className = 'citation-item';
        item.innerHTML = `
            <div class="source">${citation.source}</div>
            <div class="text">${citation.text.substring(0, 200)}...</div>
            <div class="score">Score: ${(citation.score * 100).toFixed(1)}%</div>
        `;
        citationsEl.appendChild(item);
    });

    // Scroll to output
    section.scrollIntoView({ behavior: 'smooth' });
}

// ==================== DOWNLOAD ====================

function handleDownload() {
    const documentEl = document.getElementById('documentOutput');
    const text = documentEl.textContent;

    // Create blob
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);

    // Download
    const a = document.createElement('a');
    a.href = url;
    a.download = `relazione_${new Date().toISOString().split('T')[0]}.txt`;
    a.click();

    URL.revokeObjectURL(url);
}

// ==================== UTILITIES ====================

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function showSuccess(message) {
    // TODO: Implement toast notification
    console.log('Success:', message);
}

function showError(message) {
    // TODO: Implement toast notification
    console.error('Error:', message);
    alert(message);
}
