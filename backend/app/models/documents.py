from typing import Optional, List
from pydantic import BaseModel, Field

class DeleteDocumentRequest(BaseModel):
    document_id: str

class UploadDocumentResponse(BaseModel):
    message: str
    document_id: str
    chunk_count: int

class DeleteDocumentResponse(BaseModel):
    message: str
    deleted_ids: List[str]