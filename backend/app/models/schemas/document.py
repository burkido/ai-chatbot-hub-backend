from typing import List
from pydantic import BaseModel


class DeleteDocumentRequest(BaseModel):
    """Schema for document deletion request"""
    document_id: str


class UploadDocumentResponse(BaseModel):
    """Schema for document upload response"""
    message: str
    document_id: str
    chunk_count: int


class DeleteDocumentResponse(BaseModel):
    """Schema for document deletion response"""
    message: str
    deleted_ids: List[str]