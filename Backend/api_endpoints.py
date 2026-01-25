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
