from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["agent"] == "Hindi Poem Writer"


def test_generate_poem_without_api_key(monkeypatch):
    from app import config
    monkeypatch.setattr(config.settings, "openai_api_key", "")
    r = client.post("/api/poems/generate", json={
        "prompt": "आशा",
        "style": "muktak",
        "emotion": "आशावादी",
        "lines": 4,
        "rhyme": "auto",
        "language": "hi"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["poem"]
    assert data["txt_url"].endswith(".txt")
    assert data["csv_url"].endswith(".csv")
