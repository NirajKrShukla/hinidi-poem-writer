import pytest
import random
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_signup_and_login_cycle():
    # Signup with a random mobile to avoid collisions
    mobile = str(random.randint(9000000000, 9999999999))
    payload = {
        "first_name": "Test",
        "last_name": "User",
        "mobile": mobile,
        "dob": "1990-01-01",
        "email": f"test-{mobile}@example.com",
        "password": "password123"
    }
    r = client.post('/api/auth/signup', json=payload)
    assert r.status_code == 200
    data = r.json()
    assert 'token' in data

    # Login with same credentials
    r2 = client.post('/api/auth/login', json={'mobile': mobile, 'password': 'password123'})
    assert r2.status_code == 200
    data2 = r2.json()
    assert 'token' in data2


def test_login_invalid_credentials():
    r = client.post('/api/auth/login', json={'mobile': '0001112223', 'password': 'nope'})
    assert r.status_code == 401

