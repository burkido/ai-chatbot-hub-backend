import random
import string

from fastapi.testclient import TestClient

from app.core.config import settings


def random_lower_string() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=32))


def random_email() -> str:
    return f"{random_lower_string()}@{random_lower_string()}.com"


def get_superuser_token_headers(client: TestClient) -> dict[str, str]:
    print("FIRST_SUPERUSER", settings.FIRST_SUPERUSER)
    print("FIRST_SUPERUSER_PASSWORD", settings.FIRST_SUPERUSER_PASSWORD)
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    tokens = r.json()
    print("auth utils", tokens)
    a_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {a_token}"}
    print("auth utils", headers)
    return headers
