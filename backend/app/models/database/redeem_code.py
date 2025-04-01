import uuid
from sqlmodel import Field, SQLModel


class RedeemCode(SQLModel, table=True):
    """Database model for redeem codes"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    code: str = Field(unique=True, max_length=50)
    value: int = Field(ge=50)
    is_used: bool = Field(default=False)

    def use_code(self) -> int:
        """Use the redeem code and return its value"""
        if not self.is_used:
            self.is_used = True
            return self.value
        return 0

    def delete_code(self) -> None:
        """Logic to delete the redeem code"""
        if self.is_used:
            # Logic to delete the redeem code from the database
            pass