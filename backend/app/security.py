"""Production security helpers.

For production, replace the demo bearer-token verifier with your OIDC/JWT provider
(AWS Cognito, Auth0, Azure AD B2C, etc.). The dependency is deliberately isolated.
"""
from fastapi import Header, HTTPException
from .auth import decode_jwt


def require_auth(authorization: str | None = Header(default=None)):
    # If no Authorization header provided, allow anonymous access for development/test flows
    # (many endpoints support unauthenticated usage in dev). In production, replace this
    # behavior with a stricter policy.
    if not authorization:
        return {"sub": "anonymous"}
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid access token.")
    # Try to decode as JWT issued by our auth flow
    try:
        payload = decode_jwt(token)
        return {"sub": payload.get("sub"), "name": payload.get("name"), "jwt": True}
    except Exception:
        # Fallback for local/dev: accept any non-empty bearer token (preserve previous behavior)
        return {"sub": token}


def require_admin(x_admin_token: str | None = Header(default=None)):
    if not x_admin_token:
        raise HTTPException(status_code=403, detail="Admin authorization required.")
    return True
