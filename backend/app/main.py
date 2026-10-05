from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi import Request

from .config import settings
from .models import PoemRequest, PoemResponse, TTSRequest, VideoResponse
from .services import PoemService, ElevenLabsService, CartoonService, VideoService
from .security import require_auth
from fastapi.responses import RedirectResponse
import requests
from .auth import create_jwt
from jose import JWTError, jwt as jose_jwt
from urllib.parse import urlencode
from .db import get_conn
import uuid
from .db import create_user, get_user_by_email, get_user_by_mobile, verify_password, save_state, pop_state
from .rate_limit import SimpleRateLimiter
from .media_scan import validate_upload
from .audit import audit
from .jwks_cache import get_jwks, refresh_jwks, metrics as jwks_metrics, start_refresh_loop

app = FastAPI(title="Hindi Poem Writer", version="2.0.0")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Return structured JSON for HTTP errors
    content = {"error": exc.detail if isinstance(exc.detail, str) else str(exc.detail), "code": exc.status_code}
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Return validation errors in structured form
    return JSONResponse(status_code=422, content={"error": "Validation error", "details": exc.errors(), "code": 422})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Fallback generic handler that returns structured JSON
    return JSONResponse(status_code=500, content={"error": str(exc), "code": 500})

app.add_middleware(
    CORSMiddleware,
    # Normalize CORS config: if cors_origins is '*', allow explicit localhost origins only
    allow_origins=(settings.cors_list if settings.cors_list != ["*"] else ["http://localhost:5173","http://localhost:5174","http://localhost:5175"]),
    allow_origin_regex=(None if settings.cors_list != ["*"] else r"^http://localhost(:\d+)?$"),
    allow_credentials=True,
    allow_methods=["GET","POST","PUT","DELETE","OPTIONS"],
    allow_headers=["*"],
)

# Prometheus metrics endpoint (optional)
try:
    from prometheus_client import make_asgi_app
    app.mount('/metrics', make_asgi_app())
except Exception:
    pass

# NOOP: output directory creation moved elsewhere; retained here only for backwards compatibility.
# Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
limiter = SimpleRateLimiter(limit=60, window_seconds=60)


@app.get("/api/health")
def health():
    return {"status": "ok", "agent": "Hindi Poem Writer", "version": "2.0.0"}


# Simple catch-all preflight handler to ensure OPTIONS requests return a clean response
@app.options("/{full_path:path}")
def preflight(full_path: str):
    return Response(status_code=200)


@app.post("/api/poems/generate", response_model=PoemResponse)
def generate_poem(req: PoemRequest, user=Depends(require_auth)):
    if not limiter.allow(user["sub"]):
        raise HTTPException(429, "Rate limit exceeded. Please retry later.")
    try:
        result = PoemService().generate(req)
        audit("poem_generate", user["sub"], style=req.style)
        return result
    except Exception as exc:
        raise HTTPException(502, str(exc))


@app.post("/api/speech/transcribe")
async def transcribe(file: UploadFile = File(...), user=Depends(require_auth)):
    if not limiter.allow(user["sub"]):
        raise HTTPException(429, "Rate limit exceeded. Please retry later.")
    content = await file.read()
    try:
        validate_upload(file.filename or "voice.webm", content, "audio", settings.max_audio_bytes)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    try:
        text = ElevenLabsService().transcribe(file.filename or "voice.webm", content)
        audit("speech_transcribe", user["sub"])
        return {"text": text}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@app.post("/api/voice/clone")
async def clone_voice(
    consent: bool = Form(...),
    name: str = Form("My Hindi Poem Voice"),
    files: list[UploadFile] = File(...),
    user=Depends(require_auth),
):
    if not consent:
        raise HTTPException(400, "Explicit voice ownership/authorization consent is required.")
    if not limiter.allow(user["sub"]):
        raise HTTPException(429, "Rate limit exceeded. Please retry later.")
    if not files:
        raise HTTPException(400, "At least one voice sample is required.")

    payload = []
    for f in files:
        data = await f.read()
        try:
            validate_upload(f.filename or "voice.wav", data, "audio", settings.max_audio_bytes)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        payload.append((f.filename or "voice.wav", data, f.content_type or "audio/wav"))

    try:
        voice_id = ElevenLabsService().clone_voice(name, payload)
        audit("voice_clone_created", user["sub"], voice_id=voice_id)
        return {"voice_id": voice_id}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@app.post("/api/speech/synthesize")
def synthesize(req: TTSRequest, user=Depends(require_auth)):
    if not limiter.allow(user["sub"]):
        raise HTTPException(429, "Rate limit exceeded. Please retry later.")
    try:
        url = ElevenLabsService().synthesize(req.text, req.voice_id)
        audit("speech_synthesize", user["sub"])
        return {"audio_url": url}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@app.post("/api/video/create", response_model=VideoResponse)
async def create_video(
    photo: UploadFile = File(...),
    audio: UploadFile = File(...),
    user=Depends(require_auth),
):
    if not limiter.allow(user["sub"]):
        raise HTTPException(429, "Rate limit exceeded. Please retry later.")

    photo_bytes = await photo.read()
    audio_bytes = await audio.read()

    try:
        validate_upload(photo.filename or "photo.png", photo_bytes, "image", settings.max_image_bytes)
        validate_upload(audio.filename or "voice.mp3", audio_bytes, "audio", settings.max_audio_bytes)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    try:
        cartoon_url = CartoonService().create(photo.filename or "photo.png", photo_bytes)
        cartoon_name = cartoon_url.rsplit("/", 1)[-1]

        audio_name = f"uploaded_{photo_name_safe(audio.filename or 'voice.mp3')}"
        audio_path = Path(settings.output_dir) / audio_name
        audio_path.write_bytes(audio_bytes)

        cartoon_path = Path(settings.output_dir) / cartoon_name
        video_url = VideoService().create(str(cartoon_path), str(audio_path))

        audit("video_created", user["sub"])
        return VideoResponse(
            video_url=video_url,
            cartoon_url=cartoon_url,
            audio_url=f"/api/artifacts/{audio_name}",
        )
    except Exception as exc:
        raise HTTPException(502, str(exc))


def photo_name_safe(name):
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)[:80]


@app.get("/api/artifacts/{filename}")
def artifact(filename: str, user=Depends(require_auth)):
    base = Path(settings.output_dir).resolve()
    path = (base / filename).resolve()
    if base not in path.parents:
        raise HTTPException(400, "Invalid artifact path.")
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "Artifact not found.")
    return FileResponse(path)


@app.get("/api/auth/google/url")
def google_auth_url():
    # Build Google OAuth2 authorization URL with state for CSRF protection
    client_id = settings.google_client_id
    redirect_uri = f"{settings.frontend_origin}{settings.google_redirect_path}" if settings.frontend_origin else settings.google_redirect_path
    scope = "openid email profile"
    state = uuid.uuid4().hex
    # Save state for verification
    save_state(state)
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        f"&scope={scope}"
        f"&state={state}"
        "&access_type=offline&prompt=consent"
    )
    # Return only the redirect URL to the client; state is persisted server-side for CSRF protection
    return {"url": url}


@app.get('/.well-known/jwks')
def proxy_jwks():
    """Expose a proxied JWKS endpoint to avoid cross-origin issues for clients that may want to fetch it.
    This also allows caching on the server side.
    """
    try:
        r = requests.get('https://www.googleapis.com/oauth2/v3/certs', timeout=5)
        if r.status_code != 200:
            return JSONResponse(status_code=502, content={"error":"Failed to fetch JWKS", "code":502})
        return JSONResponse(status_code=200, content=r.json())
    except Exception:
        return JSONResponse(status_code=502, content={"error":"Failed to fetch JWKS", "code":502})


@app.get('/admin/jwks/metrics')
def get_jwks_metrics():
    try:
        return JSONResponse(status_code=200, content=jwks_metrics())
    except Exception:
        return JSONResponse(status_code=500, content={"error":"Failed to read metrics","code":500})


@app.api_route("/api/auth/google/callback", methods=["GET", "POST"])
def google_callback(code: str | None = None, state: str | None = None):
    if not code:
        raise HTTPException(400, "Missing code")
    # validate state
    if not state or not pop_state(state):
        raise HTTPException(400, "Invalid or missing state parameter")
    token_url = "https://oauth2.googleapis.com/token"
    client_id = settings.google_client_id
    client_secret = settings.google_client_secret
    # Use backend origin as redirect target for Google (Google must call our backend callback)
    redirect_uri = f"{settings.backend_origin}{settings.google_redirect_path}"
    # NOOP: touch file to ensure it is updated after settings changes
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    r = requests.post(token_url, data=data)
    if r.status_code != 200:
        raise HTTPException(502, "Failed to fetch token from Google")
    token_data = r.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(502, "No access token from Google")

    # Validate OIDC id_token if present for stronger verification, else fall back to userinfo
    user = None
    id_token = token_data.get("id_token")
    if id_token:
        # Perform full OIDC id_token verification using Google's JWKS
        try:
            header = jose_jwt.get_unverified_header(id_token)
            kid = header.get("kid")
            # Fetch JWKS via cached helper
            jwks = get_jwks()
            key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
            if not key:
                raise HTTPException(502, "Unable to find JWK for token")
            public_key = jwk.construct(key)
            # verify signature
            message, encoded_sig = id_token.rsplit('.', 1)
            decoded_sig = base64url_decode(encoded_sig.encode('utf-8'))
            if not public_key.verify(message.encode('utf-8'), decoded_sig):
                raise HTTPException(502, "Invalid id_token signature")
            # parse payload
            parts = id_token.split('.')
            payload_json = base64url_decode(parts[1].encode('utf-8')).decode('utf-8')
            claims = json.loads(payload_json)
            # validate standard claims
            aud = claims.get('aud')
            iss = claims.get('iss')
            exp = claims.get('exp')
            if aud != settings.google_client_id:
                raise HTTPException(400, "Invalid id_token audience")
            if iss not in ("https://accounts.google.com", "accounts.google.com"):
                raise HTTPException(400, "Invalid id_token issuer")
            if not exp or datetime.utcfromtimestamp(exp) < datetime.utcnow():
                raise HTTPException(400, "id_token expired")
            user = {"email": claims.get("email"), "name": claims.get("name"), "sub": claims.get("sub")}
        except HTTPException:
            raise
        except Exception as exc:
            # return structured json error
            return JSONResponse(status_code=502, content={"error": f"Failed to verify id_token: {str(exc)}", "code": 502})
    if not user:
        userinfo = requests.get("https://openidconnect.googleapis.com/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"})
        if userinfo.status_code != 200:
            return JSONResponse(status_code=502, content={"error":"Failed to fetch user info from Google","code":502})
        user = userinfo.json()

    # Create our own JWT session token and redirect to frontend with it
    # Find or create user record by email
    try:
        existing = get_user_by_email(user.get("email"))
        if existing:
            jwt = create_jwt(user, user_id=existing.get("id"))
        else:
            # Create lightweight user record
            names = (user.get("name") or "").split(" ", 1)
            first = names[0] if names else ""
            last = names[1] if len(names) > 1 else ""
            created = create_user(first, last, None, None, user.get("email"), password=None)
            jwt = create_jwt(user, user_id=created.get("id"))
    except Exception as exc:
        return JSONResponse(status_code=400, content={"error": str(exc), "code": 400})

    # Redirect back to frontend and include token in fragment (frontend will clear fragment)
    redirect_to = f"{settings.frontend_origin}/#signin?token={jwt}"
    return RedirectResponse(redirect_to)


@app.on_event("startup")
def cleanup_expired_oauth_states():
    """Remove oauth_states older than 1 day on startup to avoid table growth."""
    try:
        conn = sqlite3.connect(str(Path(__file__).resolve().parents[1] / "data" / "app.db"))
        cur = conn.cursor()
        cutoff = (datetime.utcnow() - timedelta(days=1)).isoformat()
        cur.execute("DELETE FROM oauth_states WHERE created_at < ?", (cutoff,))
        conn.commit()
        conn.close()
    except Exception:
        pass


@app.on_event("startup")
def preload_jwks():
    try:
        # load JWKS into cache at startup
        refresh_jwks()
        # start background refresher
        start_refresh_loop(settings.jwks_refresh_seconds)
    except Exception:
        pass


@app.post("/api/auth/signup")
def signup(payload: dict):
    # expected keys: first_name,last_name,mobile,dob,email,password
    first = payload.get("first_name")
    last = payload.get("last_name")
    mobile = payload.get("mobile")
    dob = payload.get("dob")
    email = payload.get("email")
    password = payload.get("password")
    if not mobile or not password:
        return JSONResponse(status_code=400, content={"error":"Mobile and password are required","code":400})
    if get_user_by_mobile(mobile):
        return JSONResponse(status_code=400, content={"error":"Mobile already registered","code":400})
    try:
        created = create_user(first or "", last or "", mobile, dob or "", email or None, password=password)
    except Exception as exc:
        return JSONResponse(status_code=400, content={"error": str(exc), "code":400})
    token = create_jwt(None, user_id=created.get("id"))
    return JSONResponse(status_code=200, content={"token": token})


@app.post("/api/auth/login")
def login(payload: dict):
    mobile = payload.get("mobile")
    password = payload.get("password")
    if not mobile or not password:
        return JSONResponse(status_code=400, content={"error":"Mobile and password are required","code":400})
    user = get_user_by_mobile(mobile)
    if not user:
        return JSONResponse(status_code=401, content={"error":"Invalid credentials","code":401})
    if not verify_password(user.get("password_hash"), user.get("salt") or "", password):
        return JSONResponse(status_code=401, content={"error":"Invalid credentials","code":401})
    token = create_jwt(None, user_id=user.get("id"))
    return JSONResponse(status_code=200, content={"token": token})


@app.delete("/api/artifacts/{filename}")
def delete_artifact(filename: str, user=Depends(require_auth)):
    base = Path(settings.output_dir).resolve()
    path = (base / filename).resolve()
    if base not in path.parents:
        raise HTTPException(400, "Invalid artifact path.")
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "Artifact not found.")
    path.unlink()
    audit("artifact_deleted", user["sub"], artifact=filename)
    return {"deleted": True}
