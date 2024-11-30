from pydantic import BaseModel
from sqlmodel import Field

class DeleteDocumentRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    source: str | None = Field(default=None, min_length=1, max_length=255)