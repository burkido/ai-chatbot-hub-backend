from sqlmodel import SQLModel, Field
import uuid

class Token(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    application_id: str
    is_premium: bool = False
    remaining_credit: int

class RefreshTokenRequest(SQLModel):
    refresh_token: str

class TokenPayload(SQLModel):
    sub: str | None = None
    app: str | None = None  # Stores application_id

class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)
    application_id: uuid.UUID