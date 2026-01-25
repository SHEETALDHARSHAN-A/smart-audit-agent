const API_BASE = 'http://localhost:8000';

let currentDocument = null;
let documents = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupUploadZone();
    loadDocuments();
});

// Upload Zone Setup
function setupUploadZone() {
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');

    uploadZone.addEventListener('click', () => fileInput.click());

    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('drag-over');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('drag-over');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });
}

// Handle File Upload
async function handleFileUpload(file) {
    const progress = document.getElementById('upload-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');

    // Show progress
    progress.style.display = 'block';
    progressFill.style.width = '30%';
    progressText.textContent = 'Uploading...';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_BASE}/ingest`, {
            method: 'POST',
            body: formData
        });

        progressFill.style.width = '60%';
        progressText.textContent = 'Processing with AI...';

        if (!response.ok) throw new Error('Upload failed');

        const result = await response.json();

        progressFill.style.width = '100%';
        progressText.textContent = 'Complete!';

        setTimeout(() => {
            currentDocument = result;
            showReviewSection(file, result);
            progress.style.display = 'none';
            progressFill.style.width = '0%';
        }, 500);

    } catch (error) {
        console.error('Upload error:', error);
        alert('Error uploading file: ' + error.message);
        progress.style.display = 'none';
    }
}

// Show Review Section
async function showReviewSection(file, result) {
    document.getElementById('upload-section').style.display = 'none';
    document.getElementById('documents-section').style.display = 'none';
    document.getElementById('review-section').style.display = 'block';

    // Display file preview
    if (file.type === 'application/pdf') {
        await displayPDF(file);
    } else {
        displayImage(file);
    }

    // Set confidence badge
    const confidence = result.confidence || 0;
    const badge = document.getElementById('confidence-badge');
    badge.textContent = `${(confidence * 100).toFixed(0)}% Confidence`;
    badge.className = 'confidence-badge ';
    if (confidence >= 0.95) badge.className += 'confidence-high';
    else if (confidence >= 0.80) badge.className += 'confidence-medium';
    else badge.className += 'confidence-low';

    // Populate form
    document.getElementById('date').value = result.date || '';
    document.getElementById('invoice_no').value = result.invoice_no || '';
    document.getElementById('vendor_name').value = result.vendor_name || '';
    document.getElementById('gstin').value = result.gstin || '';
    document.getElementById('total').value = result.total || '';
    document.getElementById('tax').value = result.tax || '';

    // Line items
    const lineItemsContainer = document.getElementById('line-items');
    lineItemsContainer.innerHTML = '';

    if (result.line_items && result.line_items.length > 0) {
        result.line_items.forEach((item, index) => {
            lineItemsContainer.innerHTML += `
                <div class="line-item">
                    <input type="text" placeholder="Description" value="${item.description || ''}" data-index="${index}" data-field="description">
                    <input type="number" placeholder="Qty" value="${item.qty || ''}" data-index="${index}" data-field="qty">
                    <input type="number" placeholder="Rate" value="${item.rate || ''}" data-index="${index}" data-field="rate">
                    <input type="number" placeholder="Amount" value="${item.amount || ''}" data-index="${index}" data-field="amount">
                </div>
            `;
        });
    }

    // Setup form submit
    document.getElementById('review-form').onsubmit = (e) => {
        e.preventDefault();
        approveDocument();
    };
}

// Display PDF
async function displayPDF(file) {
    const canvas = document.getElementById('pdf-canvas');
    const ctx = canvas.getContext('2d');

    canvas.style.display = 'block';
    document.getElementById('image-preview').style.display = 'none';

    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    const page = await pdf.getPage(1);

    const viewport = page.getViewport({ scale: 1.5 });
    canvas.height = viewport.height;
    canvas.width = viewport.width;

    await page.render({ canvasContext: ctx, viewport }).promise;
}

// Display Image
function displayImage(file) {
    const img = document.getElementById('image-preview');
    const canvas = document.getElementById('pdf-canvas');

    canvas.style.display = 'none';
    img.style.display = 'block';

    const reader = new FileReader();
    reader.onload = (e) => {
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

// Approve Document
async function approveDocument() {
    const updatedData = {
        date: document.getElementById('date').value,
        invoice_no: document.getElementById('invoice_no').value,
        vendor_name: document.getElementById('vendor_name').value,
        gstin: document.getElementById('gstin').value,
        total: parseFloat(document.getElementById('total').value) || 0,
        tax: parseFloat(document.getElementById('tax').value) || 0,
        line_items: []
    };

    // Collect line items
    const lineItemInputs = document.querySelectorAll('.line-item');
    lineItemInputs.forEach(item => {
        const inputs = item.querySelectorAll('input');
        updatedData.line_items.push({
            description: inputs[0].value,
            qty: parseFloat(inputs[1].value) || 0,
            rate: parseFloat(inputs[2].value) || 0,
            amount: parseFloat(inputs[3].value) || 0
        });
    });

    try {
        const response = await fetch(`${API_BASE}/document/${currentDocument.document_id}/approve`, {
            method: 'POST'
        });

        if (response.ok) {
            alert('Document approved successfully!');
            backToUpload();
            loadDocuments();
        }
    } catch (error) {
        console.error('Approval error:', error);
        alert('Error approving document');
    }
}

// Reject Document
function rejectDocument() {
    if (confirm('Are you sure you want to reject this document?')) {
        backToUpload();
    }
}

// Back to Upload
function backToUpload() {
    document.getElementById('review-section').style.display = 'none';
    document.getElementById('upload-section').style.display = 'block';
    document.getElementById('documents-section').style.display = 'block';
    currentDocument = null;
}

// Load Documents
async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE}/documents`);
        const data = await response.json();
        documents = data.documents || [];

        updateStats();
        renderDocuments();
    } catch (error) {
        console.error('Error loading documents:', error);
    }
}

// Update Stats
function updateStats() {
    document.getElementById('total-docs').textContent = documents.length;
    const pending = documents.filter(d => d.status === 'pending_review').length;
    document.getElementById('pending-docs').textContent = pending;
}

// Render Documents
function renderDocuments() {
    const grid = document.getElementById('documents-grid');

    if (documents.length === 0) {
        grid.innerHTML = '<p style="color: var(--text-secondary)">No documents yet. Upload your first document above!</p>';
        return;
    }

    grid.innerHTML = documents.map(doc => `
        <div class="document-card" onclick="viewDocument('${doc.id}')">
            <div class="document-header">
                <span class="document-status status-${doc.status}">${doc.status.replace('_', ' ')}</span>
            </div>
            <div class="document-filename">${doc.filename}</div>
            <div class="document-meta">
                Confidence: ${(doc.result.confidence * 100).toFixed(0)}%
                ${doc.result.llm_enhanced ? ' • AI Enhanced' : ''}
            </div>
        </div>
    `).join('');
}

// View Document
async function viewDocument(docId) {
    try {
        const response = await fetch(`${API_BASE}/document/${docId}`);
        const doc = await response.json();

        // Re-fetch the file and show review
        // For now, just show alert
        alert('Document viewer coming soon! ID: ' + docId);
    } catch (error) {
        console.error('Error viewing document:', error);
    }
}

// Refresh every 10 seconds
setInterval(loadDocuments, 10000);
