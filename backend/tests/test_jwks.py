import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch

client = TestClient(app)


def test_jwks_proxy_and_metrics(monkeypatch):
    # Mock the external JWKS response
    fake_jwks = {"keys": [{"kid": "abc","kty":"RSA","n":"test","e":"AQAB"}]}

    class FakeResp:
        status_code = 200
        headers = {'Cache-Control': 'max-age=60'}
        def json(self):
            return fake_jwks

    with patch('requests.get') as mock_get:
        mock_get.return_value = FakeResp()
        r = client.get('/.well-known/jwks')
        assert r.status_code == 200
        assert r.json() == fake_jwks

        # metrics endpoint should exist and show misses >= 1 after proxy
        m = client.get('/admin/jwks/metrics')
        assert m.status_code == 200
        assert 'hits' in m.json() and 'misses' in m.json()

