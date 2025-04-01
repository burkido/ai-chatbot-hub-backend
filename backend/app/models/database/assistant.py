from sqlmodel import SQLModel, Field


class Assistant(SQLModel, table=True):
    """Database model for AI assistants"""
    id: int = Field(default=None, primary_key=True)
    title: str
    topic: str
    description: str
    icon_id: int