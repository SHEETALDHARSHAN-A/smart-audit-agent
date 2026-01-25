from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import shutil
import os
import uuid
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from pipeline.preprocessor import ImagePreprocessor
from pipeline.hybrid_ocr import HybridOCREngine  # Updated to hybrid
from pipeline.extractor import FieldExtractor
from pipeline.validator import DataValidator
from pipeline.llm_enhancer import LLMEnhancer

app = FastAPI(title="Smart Audit Agent OCR API")
logger = logging.getLogger("uvicorn")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Pipeline Components
preprocessor = ImagePreprocessor()
ocr_engine = HybridOCREngine()  # Now using hybrid OCR
extractor = FieldExtractor()
validator = DataValidator()
llm_enhancer = LLMEnhancer()  # New: LLM enhancement

TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

# Store documents in memory (in production, use a database)
documents_db = {}

@app.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """
    Upload a document (image) and get extracted structured data.
    """
    try:
        # 1. Save File Locally
        file_ext = file.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(TEMP_DIR, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File saved to {file_path}")

        # 2. Pre-processing (for images only, hybrid OCR handles other formats)
        processed_path = file_path
        
        # Only preprocess image files
        if file_ext.lower() in ['png', 'jpg', 'jpeg', 'tiff', 'bmp']:
            try:
                processed_img = preprocessor.preprocess(file_path)
                processed_path = preprocessor.save_temp_image(processed_img, file_path)
                logger.info(f"Image preprocessed: {processed_path}")
            except Exception as e:
                logger.error(f"Preprocessing failed: {e}")
                processed_path = file_path

        # 3. Hybrid OCR Execution (handles PDF, DOCX, XLSX, images, etc.)
        text_blocks = ocr_engine.get_text_blocks(processed_path)
        combined_text = " ".join([block["text"] for block in text_blocks])
        logger.info(f"OCR Complete. Extracted {len(combined_text)} characters.")

        # 4. Field Extraction
        extracted_data = extractor.extract_fields(combined_text, text_blocks)

        # 5. LLM Enhancement (NEW)
        llm_result = llm_enhancer.enhance_extraction(combined_text, extracted_data)
        
        # Use LLM result if available and has higher confidence
        if llm_result.get("enhanced"):
            final_data = llm_result["data"]
            confidence = llm_result["confidence"]
        else:
            final_data = extracted_data
            confidence = 0.7

        # 6. Validation
        final_result = validator.validate(final_data)
        
        # Add confidence and metadata
        final_result["confidence"] = confidence
        final_result["llm_enhanced"] = llm_result.get("enhanced", False)
        final_result["meta"] = {
            "num_blocks": len(text_blocks),
            "original_filename": file.filename,
            "file_type": file_ext
        }
        
        # Store in documents DB with ID
        doc_id = str(uuid.uuid4())
        documents_db[doc_id] = {
            "id": doc_id,
            "filename": file.filename,
            "result": final_result,
            "status": "approved" if confidence >= 0.95 else "pending_review",
            "file_path": file_path
        }
        
        final_result["document_id"] = doc_id
        final_result["status"] = documents_db[doc_id]["status"]

        return final_result

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def health_check():
    return {"status": "ok", "service": "Smart Audit Agent OCR"}

@app.get("/documents")
async def list_documents():
    """Get all documents with their review status"""
    return {"documents": list(documents_db.values())}

@app.get("/document/{doc_id}")
async def get_document(doc_id: str):
    """Get specific document details"""
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    return documents_db[doc_id]

@app.put("/document/{doc_id}")
async def update_document(doc_id: str, updated_data: dict):
    """Update document with human corrections"""
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    documents_db[doc_id]["result"] = updated_data
    documents_db[doc_id]["status"] = "reviewed"
    logger.info(f"Document {doc_id} updated with corrections")
    
    return {"message": "Document updated", "document": documents_db[doc_id]}

@app.post("/document/{doc_id}/approve")
async def approve_document(doc_id: str):
    """Mark document as approved"""
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    documents_db[doc_id]["status"] = "approved"
    logger.info(f"Document {doc_id} approved")
    
    return {"message": "Document approved", "document": documents_db[doc_id]}

# Mount static files for frontend
app.mount("/", StaticFiles(directory="../Frontend", html=True), name="frontend")
