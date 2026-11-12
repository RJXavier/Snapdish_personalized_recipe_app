import os
import sys
import tempfile
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVER_DIR))

# Every test run uses its own throw-away SQLite database and upload folder.
_tmp = Path(tempfile.mkdtemp(prefix="recipe_app_test_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_tmp / 'test.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(_tmp / "uploads")
os.environ["JWT_SECRET_KEY"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client():
    import load_json
    from core.mysql import SessionLocal
    from main import app

    db = SessionLocal()
    try:
        load_json.seed(db)
        load_json.ensure_demo_user(db)
    finally:
        db.close()
    return TestClient(app)


def signup_and_login(client, username, preferences=("No Shrimp",), password="secret123"):
    response = client.post("/auth/signup", json={
        "username": username,
        "nickname": f"{username} nick",
        "email": f"{username}@example.com",
        "password": password,
        "gender": "Other",
        "birthday": "1995-03-14",
        "food_preferences": list(preferences),
    })
    assert response.json()["code"] == 0, response.json()
    token = client.post("/auth/login", json={"username": username, "password": password}) \
        .json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
