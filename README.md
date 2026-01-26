# Smart Audit Agent - AI-Powered Document OCR

A high-accuracy, local document ingestion and extraction pipeline using **PaddleOCR** and **FastAPI**.

## ✨ Features

- **Local Execution** - Runs entirely on your machine, no cloud APIs required
- **Hybrid OCR Engine** - Combines multiple OCR engines for best accuracy:
  - **PaddleOCR** - Advanced layout-aware text extraction
  - **Tesseract** - Fallback OCR support
- **Image Preprocessing** - Automatic deskew, denoise, and upscaling
- **Multi-Format Support** - PDF, images, Word docs, Excel files
- **Structured Output** - JSON with dates, invoice numbers, totals, and line items
- **REST API** - FastAPI backend for easy integration

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Windows 10/11** or Windows Server
- **Visual C++ Redistributable** (for OpenCV/Paddle)

### Installation

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd Smart-Audit-Agent

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# 3. Install dependencies
pip install -r Backend\requirements.txt
```

### Running the Server

```bash
# Option 1: Double-click
run_server.bat

# Option 2: Command line
.\venv\Scripts\uvicorn Backend.app:app --reload
```

The API will be available at `http://127.0.0.1:8000`

---

## 📁 Project Structure

```
Smart-Audit-Agent/
├── Backend/
│   ├── app.py                 # FastAPI application
│   ├── pipeline/
│   │   ├── hybrid_ocr.py      # Multi-engine OCR orchestrator
│   │   ├── ocr_engine.py      # OCR processing logic
│   │   └── llm_enhancer.py    # LLM-based text enhancement
│   └── requirements.txt       # Python dependencies
├── Frontend/
│   ├── index.html             # Web interface
│   └── app.js                 # Frontend JavaScript
├── run_server.bat             # Server startup script
└── README.md
```

---

## 🔧 API Endpoints

### Upload & Process Document

```http
POST /ingest
Content-Type: multipart/form-data

file: <document file>
```

**Response:**
```json
{
  "status": "success",
  "extracted_text": "...",
  "structured_data": {
    "date": "2024-01-15",
    "invoice_number": "INV-001",
    "total": 1250.00,
    "line_items": [...]
  }
}
```

### List Documents

```http
GET /documents
```

---

## 🧠 OCR Engine Details

### Hybrid OCR Engine

The system uses a smart hybrid approach:

1. **PaddleOCR** (Primary)
   - Layout-aware text detection
   - High accuracy for printed text
   - Handles complex document structures

2. **TrOCR** (Handwriting)
   - Microsoft's transformer-based model
   - Specialized for handwritten text
   - Activated automatically when handwriting is detected

3. **Tesseract** (Fallback)
   - Traditional OCR engine
   - Used for comparison and validation

### Model Requirements

| Model | Size | Purpose |
|-------|------|---------|
| PaddleOCR | ~150 MB | Downloaded automatically |
| Tesseract | External | Optional, install separately |

---

## 📦 Deployment

### Production Deployment

1. **Install dependencies:**
   ```bash
   pip install -r Backend\requirements.txt
   ```

2. **Run with production server:**
   ```bash
   .\venv\Scripts\uvicorn Backend.app:app --host 0.0.0.0 --port 8000
   ```

### Docker (Coming Soon)

Docker configuration is planned for future releases.

---

## 🛠️ Troubleshooting



### PaddleOCR Issues

Ensure Visual C++ Redistributable is installed:
- Download from [Microsoft](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)

---

## 📄 License

[Add your license here]

---

## 🤝 Contributing

[Add contribution guidelines here]
