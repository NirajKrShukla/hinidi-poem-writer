"""Production security helpers.

For production, replace the demo bearer-token verifier with your OIDC/JWT provider
(AWS Cognito, Auth0, Azure AD B2C, etc.). The dependency is deliberately isolated.
"""
from fastapi import Header, HTTPException


def require_auth(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid access token.")
    # Integration point: validate JWT signature, issuer, audience and expiry here.
    # The current starter accepts a non-empty bearer token so local integration
    # can be tested without a specific identity provider.
    return {"sub": "authenticated-user"}


def require_admin(x_admin_token: str | None = Header(default=None)):
    if not x_admin_token:
        raise HTTPException(status_code=403, detail="Admin authorization required.")
    return True
