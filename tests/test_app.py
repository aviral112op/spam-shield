import os

import pytest

# Point the app at a separate test database before it is imported
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    pytest.skip("Set TEST_DATABASE_URL to run these tests", allow_module_level=True)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from fastapi.testclient import TestClient  # noqa: E402

import app.main as main  # noqa: E402
from app.db import Base, engine  # noqa: E402


class FakeClassifier:
    """Stands in for the Hugging Face model so tests are fast and offline."""

    model_name = "fake"

    def predict(self, texts):
        out = []
        for t in texts:
            spam = "prize" in t.lower()
            out.append({"label": "spam" if spam else "ham", "is_spam": spam, "confidence": 0.9})
        return out


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "SpamClassifier", FakeClassifier)
    Base.metadata.drop_all(engine)
    with TestClient(main.app) as c:
        yield c


def register(client, email="user@example.com", password="password123"):
    return client.post("/auth/register", json={"email": email, "password": password})


def test_pages_redirect_based_on_login(client):
    assert client.get("/", follow_redirects=False).headers["location"] == "/login"
    assert client.get("/login").status_code == 200
    register(client)
    assert client.get("/login", follow_redirects=False).headers["location"] == "/"
    assert client.get("/").status_code == 200


def test_register_login_logout(client):
    assert register(client).status_code == 201
    assert register(client).status_code == 409
    assert client.get("/auth/me").json()["email"] == "user@example.com"

    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401

    bad = client.post("/auth/login", json={"email": "user@example.com", "password": "wrongpass1"})
    assert bad.status_code == 401
    good = client.post("/auth/login", json={"email": "USER@example.com", "password": "password123"})
    assert good.status_code == 200
    assert client.get("/auth/me").status_code == 200


def test_register_validation(client):
    assert register(client, email="not-an-email").status_code == 422
    assert register(client, password="short").status_code == 422


def test_predict_requires_login(client):
    assert client.post("/predict", json={"text": "hello"}).status_code == 401
    assert client.get("/history").status_code == 401


def test_predict_and_history(client):
    register(client)
    r = client.post("/predict", json={"text": "Claim your PRIZE now"})
    assert r.json() == {"label": "spam", "is_spam": True, "confidence": 0.9}
    client.post("/predict/batch", json={"texts": ["see you at lunch", "free prize"]})

    history = client.get("/history").json()
    assert [h["label"] for h in history] == ["spam", "ham", "spam"]

    # Another user doesn't see this history
    client.post("/auth/logout")
    register(client, email="other@example.com")
    assert client.get("/history").json() == []


def test_predict_eml(client):
    register(client)
    plain = b"Subject: You won a prize\r\nContent-Type: text/plain\r\n\r\nClaim it today.\r\n"
    html = (
        b"Subject: Lunch\r\nContent-Type: text/html\r\n\r\n"
        b"<html><style>p{}</style><p>See you at noon &amp; bring notes</p></html>\r\n"
    )
    empty = b"Content-Type: text/plain\r\n\r\n"
    files = [
        ("files", ("a.eml", plain, "message/rfc822")),
        ("files", ("b.eml", html, "message/rfc822")),
        ("files", ("c.eml", empty, "message/rfc822")),
    ]
    results = client.post("/predict/eml", files=files).json()["results"]

    assert results[0]["subject"] == "You won a prize"
    assert results[0]["prediction"]["label"] == "spam"
    assert results[1]["prediction"]["label"] == "ham"
    assert results[2]["error"] == "Email has no text"
    assert len(client.get("/history").json()) == 2
