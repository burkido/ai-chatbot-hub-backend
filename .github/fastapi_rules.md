# FastAPI Project Structure & Best Practices

## 1. General Structure
- The **`src/`** directory is the highest-level directory for the application.
- Each **domain module** (e.g., `auth`, `aws`, `posts`) is a self-contained package with:
  - `router.py` – API endpoints
  - `schemas.py` – Pydantic models
  - `models.py` – Database models
  - `service.py` – Business logic
  - `dependencies.py` – Router dependencies
  - `constants.py` – Module-specific constants and error codes
  - `config.py` – Module-specific configuration (e.g., environment variables)
  - `utils.py` – Helper functions (e.g., response formatting, external API calls)
  - `exceptions.py` – Module-specific exceptions

---

## 2. Project Root
- `src/main.py` is the **entry point**, responsible for initializing the FastAPI app.
- `src/config.py` contains **global configuration** (e.g., database connection, app settings).
- `src/models.py` defines **global database models**, used across multiple modules.
- `src/exceptions.py` defines **global exception handlers**.
- `src/database.py` handles **database connection setup**.
- `src/pagination.py` contains **global utilities** (e.g., pagination handling).

---

## 3. Module-Level Guidelines
Each module (`auth`, `aws`, `posts`) should follow the same structure and guidelines:

### 3.1 `router.py` (API Endpoints)
- Defines **routes and dependencies** and registers them to the FastAPI app.
- **Example:**
  ```python
  from fastapi import APIRouter, Depends
  from src.auth.schemas import UserCreate, UserResponse
  from src.auth.service import AuthService

  router = APIRouter()

  @router.post("/register", response_model=UserResponse)
  def register(user: UserCreate, service: AuthService = Depends()):
      return service.register_user(user)
  ```

---

### 3.2 `schemas.py` (Pydantic Models)
- Defines **input validation** and **output serialization**.
- **Example:**
  ```python
  from pydantic import BaseModel

  class UserCreate(BaseModel):
      email: str
      password: str

  class UserResponse(BaseModel):
      id: int
      email: str
  ```

---

### 3.3 `models.py` (Database Models)
- Defines **SQLAlchemy models** for the database.
- **Example:**
  ```python
  from sqlalchemy import Column, Integer, String
  from src.database import Base

  class User(Base):
      __tablename__ = "users"
      id = Column(Integer, primary_key=True, index=True)
      email = Column(String, unique=True, index=True)
      password_hash = Column(String)
  ```

---

### 3.4 `service.py` (Business Logic)
- Implements **module-specific logic**.
- **Example:**
  ```python
  from sqlalchemy.orm import Session
  from src.auth.models import User
  from src.auth.schemas import UserCreate
  from src.auth.utils import hash_password

  class AuthService:
      def __init__(self, db: Session):
          self.db = db

      def register_user(self, user_data: UserCreate):
          hashed_pw = hash_password(user_data.password)
          user = User(email=user_data.email, password_hash=hashed_pw)
          self.db.add(user)
          self.db.commit()
          return user
  ```

---

### 3.5 `dependencies.py` (Router Dependencies)
- Manages **shared dependencies**.
- **Example:**
  ```python
  from fastapi import Depends
  from sqlalchemy.orm import Session
  from src.database import get_db

  def get_auth_service(db: Session = Depends(get_db)):
      return AuthService(db)
  ```

---

### 3.6 `constants.py` (Module Constants & Error Codes)
- Stores **fixed values and error messages**.
- **Example:**
  ```python
  ACCESS_TOKEN_EXPIRE_MINUTES = 30
  ERROR_USER_NOT_FOUND = "User not found"
  ```

---

### 3.7 `config.py` (Module Configurations)
- Stores **module-specific configurations**.
- **Example:**
  ```python
  import os

  AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
  AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
  ```

---

### 3.8 `utils.py` (Helper Functions)
- Contains **non-business logic functions**.
- **Example:**
  ```python
  from passlib.context import CryptContext

  pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

  def hash_password(password: str) -> str:
      return pwd_context.hash(password)
  ```

---

### 3.9 `exceptions.py` (Module Exceptions)
- Stores **module-specific custom exceptions**.
- **Example:**
  ```python
  class UserNotFoundException(Exception):
      def __init__(self, message="User not found"):
          self.message = message
          super().__init__(self.message)
  ```

---

## 4. Cross-Module Imports
- Always **import with explicit module paths**.
- **Good Practice:**
  ```python
  from src.auth.service import AuthService
  ```
- **Avoid:**
  ```python
  from .service import AuthService  # ❌ Bad Practice
  ```

---

## 5. Global Configurations
- `src/config.py` centralizes **app-wide settings**.
- **Example:**
  ```python
  import os

  DATABASE_URL = os.getenv("DATABASE_URL")
  SECRET_KEY = os.getenv("SECRET_KEY")
  DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
  ```

---

## 6. Best Practices for Testing
- Place **unit tests under `tests/`**.
- Use **pytest**.
- **Example:**
  ```python
  from fastapi.testclient import TestClient
  from src.main import app

  client = TestClient(app)

  def test_register_user():
      response = client.post("/auth/register", json={"email": "test@example.com", "password": "123456"})
      assert response.status_code == 200
  ```

---

## 7. Logging & Error Handling
- Use `logging.ini` for structured logging.
- Centralize error handling in `src/exceptions.py`.

---

## Final Notes
✅ **Organized structure**: Each module is self-contained.
✅ **Explicit imports**: Avoid circular dependencies.
✅ **Separation of concerns**: Keep business logic (`service.py`) separate from API handlers (`router.py`).
✅ **Security & best practices**: Use **hashing for passwords**, **structured error handling**, and **explicit database models**.

