from typing import Optional
from pydantic import BaseModel, Field

class DeleteDocumentRequest(BaseModel):
    document_id: str