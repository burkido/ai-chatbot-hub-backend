from pydantic import BaseModel
from sqlmodel import Field

class DeleteDocumentRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)