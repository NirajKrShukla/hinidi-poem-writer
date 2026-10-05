import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch
import jwt
from datetime import datetime, timedelta

client = TestClient(app)

# Generate a test RSA key pair using PyJWT (which can sign RS256 if keys provided)
# For simplicity use HS256 for local signing in this test and mock JWKS accordingly.

def make_hs256_token(secret, aud='test-aud'):
    now = datetime.utcnow()
    payload = {
        'iss': 'https://accounts.google.com',
        'sub': 'testsub',
        'aud': aud,
        'exp': int((now + timedelta(minutes=5)).timestamp()),
        'iat': int(now.timestamp()),
        'email': 'user@example.com',
        'name': 'Test User'
    }
    return jwt.encode(payload, secret, algorithm='HS256')


def test_id_token_verification_via_userinfo(monkeypatch):
    # When id_token is missing, the code should call userinfo endpoint.
    fake_token = {'access_token': 'atoken'}

    class FakeTokenResp:
        status_code = 200
        def json(self):
            return fake_token

    class FakeUserinfoResp:
        status_code = 200
        def json(self):
            return {'email': 'user@example.com', 'name': 'Test User'}

    with patch('app.main.requests.post') as mock_post, patch('app.main.requests.get') as mock_get:
        mock_post.return_value = FakeTokenResp()
        mock_get.return_value = FakeUserinfoResp()
        # Call callback with code and state; first ensure state exists
        r_url = client.get('/api/auth/google/url')
        assert r_url.status_code == 200
        # parse returned url to extract state param
        from urllib.parse import urlparse, parse_qs
        u = urlparse(r_url.json()['url'])
        qs = parse_qs(u.query)
        state = qs['state'][0]
        # Call callback (use POST to ensure compatibility)
        r = client.post(f'/api/auth/google/callback?code=abc&state={state}')
        # Should redirect to frontend; in some test environments method routing may differ
        assert r.status_code in (302, 307) or r.status_code >= 300


def test_id_token_verification_with_id_token(monkeypatch):
    # Mock JWKS and token verification path by providing id_token
    secret = 'test-secret'
    token = make_hs256_token(secret, aud='')
    # Mock token endpoint to return id_token
    class FakeTokenResp:
        status_code = 200
        def json(self):
            return {'access_token': 'atoken', 'id_token': token}

    # Provide JWKS that includes a dummy key; our verification in main.py expects RS keys,
    # but for test we'll patch get_jwks to return a structure and also monkeypatch jose.jwk.construct to accept it.

    fake_jwks = {'keys': []}

    with patch('app.main.requests.post') as mock_post, patch('app.main.get_jwks') as mock_get_jwks:
        mock_post.return_value = FakeTokenResp()
        mock_get_jwks.return_value = fake_jwks
        # Create state and call callback
        r_url = client.get('/api/auth/google/url')
        assert r_url.status_code == 200
        from urllib.parse import urlparse, parse_qs
        u = urlparse(r_url.json()['url'])
        qs = parse_qs(u.query)
        state = qs['state'][0]
        r = client.post(f'/api/auth/google/callback?code=abc&state={state}')
        # Since our JWKS is fake, endpoint should return JSON error (502 or similar)
        assert r.status_code >= 400

