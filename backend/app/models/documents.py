from typing import Optional
from pydantic import BaseModel, Field

class DeleteDocumentRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)