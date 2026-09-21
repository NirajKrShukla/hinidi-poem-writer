from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import settings
from .models import PoemRequest, PoemResponse, TTSRequest, VideoResponse
from .services import PoemService, ElevenLabsService, CartoonService, VideoService
from .security import require_auth
from .rate_limit import SimpleRateLimiter
from .media_scan import validate_upload
from .audit import audit

app = FastAPI(title="Hindi Poem Writer", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
limiter = SimpleRateLimiter(limit=60, window_seconds=60)


@app.get("/api/health")
def health():
    return {"status": "ok", "agent": "Hindi Poem Writer", "version": "2.0.0"}


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
