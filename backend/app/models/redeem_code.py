from sqlmodel import Field, SQLModel, Relationship
import uuid

class RedeemCode(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    code: str = Field(unique=True, max_length=50)
    value: int = Field(ge=50)
    is_used: bool = Field(default=False)

    def use_code(self):
        if not self.is_used:
            self.is_used = True
            return self.value
        return 0

    def delete_code(self):
        if self.is_used:
            # Logic to delete the redeem code from the database
            pass

class RedeemCodesPublic(SQLModel):
    data: list[RedeemCode]
    count: int