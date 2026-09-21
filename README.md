# Hindi Poem Writer

Production-oriented starter repository for an AI agent named **Hindi Poem Writer**.

## What it does

- Accepts typed Hindi/English input or an uploaded voice recording.
- Accepts a few user poem lines as inspiration.
- Generates an original Hindi poem with:
  - Chhand-aware generation (Doha / Chaupai / Muktak)
  - Maatraa guidance and validation
  - Yati / Gati guidance
  - Tukbandi
  - Bhaav and natural Hindi word choice
- Does not reproduce the supplied input as a copy; the prompt explicitly requires transformation into a new work.
- Produces TXT and CSV downloads.
- Can transcribe voice input.
- Can create an instant clone of the end user's voice with ElevenLabs after explicit consent.
- Can synthesize the new poem in that user's cloned voice.
- Can transform an uploaded user photo into a cartoon-style image and make a poem video using FFmpeg.
- Keeps provider-specific integrations behind service classes so they can be replaced.

## Architecture

```text
React UI
   |
   v
FastAPI
   |
   +--> PoemService --------> OpenAI Responses API
   |
   +--> SpeechService -------> ElevenLabs STT
   |
   +--> VoiceCloneService ---> ElevenLabs IVC
   |
   +--> TTSService ----------> ElevenLabs TTS
   |
   +--> CartoonService ------> OpenAI Images API
   |
   +--> VideoService --------> FFmpeg
   |
   +--> Local artifact store
```

## Important production note

No software project can honestly be called "bug free" before it is deployed and tested against the exact production provider accounts, limits, browser matrix, audio devices, and infrastructure. This repository includes automated unit/API tests and validation, but provider integration tests require real API credentials.

Voice cloning must only be enabled for the user's own voice or a voice for which the user has the necessary rights/authorization. The UI therefore contains an explicit consent checkbox.

## Requirements

- Python 3.11+
- Node.js 20+
- FFmpeg installed and available on PATH
- OpenAI API key
- ElevenLabs API key for voice/STT/voice-clone features

## Run backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env  # macOS/Linux

uvicorn app.main:app --reload --port 8000
```

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal.

## Test

Backend:

```bash
cd backend
pytest -q
```

Frontend:

```bash
cd frontend
npm install
npm run build
```

## Environment

See `backend/.env.example`.

## API

- `GET /api/health`
- `POST /api/poems/generate`
- `POST /api/speech/transcribe`
- `POST /api/voice/clone`
- `POST /api/speech/synthesize`
- `POST /api/video/create`
- `GET /api/artifacts/{filename}`

## Output

Artifacts are stored in `backend/data/outputs/`:

- `.txt` Hindi poem
- `.csv` Hindi UTF-8 BOM CSV
- `.mp3` voice poem
- `.png` cartoon portrait
- `.mp4` poem video

The frontend provides download buttons for each available artifact.


## Provider implementation notes

The poem generation uses the OpenAI Responses API. OpenAI currently documents GPT-5.6 model
family support for multilingual text generation. citeturn0search0turn3search2

Voice transcription, instant voice cloning and Hindi multilingual TTS are implemented against
ElevenLabs APIs. Their current documentation describes Instant Voice Cloning from audio samples,
Hindi support in multilingual speech models, and the text-to-speech endpoint. citeturn1search0turn1search1turn1search8turn1search11

The cartoon portrait uses an image-edit request. The video renderer in this starter uses
FFmpeg to combine the portrait and the generated audio. If you later want a fully animated
talking avatar, replace `VideoService` with an avatar/video provider.

## Production hardening checklist

Before public launch:

- Put API keys in a cloud secret manager, never in Git.
- Add authentication and per-user authorization.
- Replace local artifact storage with S3/Azure Blob/GCS.
- Add signed, expiring download URLs.
- Add rate limiting and request quotas.
- Add virus/content scanning for uploaded media.
- Add image/audio size and duration limits.
- Add background job processing (Celery/RQ/Temporal) for voice/video generation.
- Add database records for jobs, artifact ownership and deletion.
- Add observability: structured logs, tracing, metrics and provider request IDs.
- Add data-retention/deletion controls for uploaded voice/photo media.
- Require explicit user consent before voice cloning.
- Run real provider integration tests in staging before production.


## Production facilities added

- **Authentication:** protected API endpoints with a bearer-token integration point. Connect
  this to Cognito/Auth0/Azure OIDC and validate JWT signature, issuer, audience and expiry.
- **Cloud storage:** S3 adapter with private objects, encryption and presigned GET URLs.
- **Background jobs:** Celery + Redis worker entry point for TTS/video jobs.
- **Rate limiting:** per-user limiter; replace with Redis/API Gateway/WAF for horizontally scaled deployments.
- **Media scanning:** extension/size validation and a ClamAV/managed scanner integration hook.
- **Observability:** JSON audit events for poem generation, transcription, voice cloning,
  synthesis, video creation and deletion.
- **Retention/deletion:** configurable retention helper plus artifact deletion endpoint;
  use S3 lifecycle policies for cloud storage.
- **Production deployment:** Docker production compose stack and AWS architecture blueprint.

### Security requirement

The development bearer-token verifier intentionally accepts any non-empty bearer token so the
UI can be tested without a particular identity provider. **It is not a production identity
system.** Before public launch, connect `require_auth()` to a real OIDC/JWT verifier and add
database-backed user/object ownership so one user can never access another user's artifacts.
