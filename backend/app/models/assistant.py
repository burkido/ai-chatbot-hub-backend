from sqlmodel import SQLModel, Field

class Assistant(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    title: str
    topic: str
    description: str
    icon_id: int