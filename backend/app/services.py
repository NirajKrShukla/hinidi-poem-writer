import csv
import io
import os
import subprocess
import uuid
from pathlib import Path

import requests
from openai import OpenAI

from .config import settings
from .poem_rules import validate_poem


SYSTEM_PROMPT = """You are Hindi Poem Writer, a specialist Hindi poet and prosody-aware editor.

Write an ORIGINAL Hindi poem. User input is inspiration only. Do not reproduce distinctive
phrasing from the input. Transform the idea, imagery and emotion into newly written text.

Quality requirements:
1. Bhaav: emotionally genuine and coherent.
2. Chhand: if Doha, target the traditional 13/11 matra structure; if Chaupai, target the
   traditional approximately 16-matra line structure. If Muktak/free verse, prioritize
   musical rhythm rather than forcing a meter.
3. Maatraa: count and revise lines before final output. Avoid claiming exact scansion if
   uncertain.
4. Yati: use natural pause points and punctuation.
5. Gati: lines should read smoothly aloud.
6. Tukbandi: follow requested AABB/ABAB where practical; do not force awkward words.
7. Shabd Chayan: use natural, evocative Hindi, not unnecessarily Sanskritized vocabulary.
8. Return ONLY the poem, no analysis, no numbering, no markdown fences.
"""


class PoemService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    def generate(self, req):
        if not self.client:
            # Deterministic local fallback for development/testing.
            poem = (
                "मन की धरती पर आशा का दीप जलाएँ,\n"
                "सूनी राहों में फिर सपनों के फूल खिलाएँ,\n"
                "दुख की धूप ढले तो छाँव स्वयं आ जाएगी,\n"
                "हम अपने भीतर से नई सुबह ले आएँ।"
            )
            validation = validate_poem(poem, req.style)
            return self._save(poem, req.style, validation)

        style_desc = {
            "doha": "Doha; make paired lines with disciplined 13/11 matra rhythm.",
            "chaupai": "Chaupai; aim for the traditional approximately 16-matra cadence per line.",
            "muktak": "Muktak; compact self-contained modern Hindi poem with musical flow.",
            "free": "Free verse; no forced meter, but preserve strong cadence and imagery.",
        }[req.style]

        user_prompt = f"""Theme/inspiration:
{req.prompt or "आशा, जीवन और मनुष्य की संवेदना"}

Requested form: {style_desc}
Emotion: {req.emotion}
Number of lines: {req.lines}
Rhyme: {req.rhyme}

Create a completely new Hindi poem. If the inspiration contains poem lines, do not copy them.
Revise internally for rhythm, natural pauses and rhyme before returning the final poem."""

        response = self.client.responses.create(
            model=settings.openai_text_model,
            instructions=SYSTEM_PROMPT,
            input=user_prompt,
        )
        poem = response.output_text.strip()
        if not poem:
            raise RuntimeError("Poem model returned empty output.")

        validation = validate_poem(poem, req.style)
        return self._save(poem, req.style, validation)

    def _save(self, poem, style, validation):
        out = Path(settings.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        token = uuid.uuid4().hex
        txt = out / f"poem_{token}.txt"
        csv_path = out / f"poem_{token}.csv"

        txt.write_text(poem + "\n", encoding="utf-8")
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["पंक्ति", "मात्रा_अनुमान"])
            for line, count in zip(
                [x for x in poem.splitlines() if x.strip()],
                validation["matra_counts"],
            ):
                writer.writerow([line, count])

        return {
            "poem": poem,
            "meter": style,
            "validation": validation,
            "txt_url": f"/api/artifacts/{txt.name}",
            "csv_url": f"/api/artifacts/{csv_path.name}",
        }


class ElevenLabsService:
    base = "https://api.elevenlabs.io/v1"

    def __init__(self):
        if not settings.elevenlabs_api_key:
            raise RuntimeError("ELEVENLABS_API_KEY is not configured.")

    @property
    def headers(self):
        return {"xi-api-key": settings.elevenlabs_api_key}

    def transcribe(self, filename, content):
        r = requests.post(
            f"{self.base}/speech-to-text",
            headers=self.headers,
            files={"file": (filename, content)},
            data={"model_id": settings.elevenlabs_stt_model, "language_code": "hin"},
            timeout=120,
        )
        r.raise_for_status()
        return r.json().get("text", "")

    def clone_voice(self, name, files):
        multipart = [
            ("files", (filename, content, mime))
            for filename, content, mime in files
        ]
        data = {"name": name, "description": "User-authorized Hindi Poem Writer voice clone"}
        r = requests.post(
            f"{self.base}/voices/add",
            headers=self.headers,
            files=multipart,
            data=data,
            timeout=180,
        )
        r.raise_for_status()
        return r.json()["voice_id"]

    def synthesize(self, text, voice_id):
        r = requests.post(
            f"{self.base}/text-to-speech/{voice_id}",
            headers={**self.headers, "Content-Type": "application/json"},
            params={"output_format": "mp3_44100_128"},
            json={"text": text, "model_id": settings.elevenlabs_tts_model},
            timeout=180,
        )
        r.raise_for_status()
        out = Path(settings.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        name = f"voice_{uuid.uuid4().hex}.mp3"
        (out / name).write_bytes(r.content)
        return f"/api/artifacts/{name}"


class CartoonService:
    def create(self, image_filename, image_bytes):
        if not settings.openai_api_key:
            # Development fallback: preserve the uploaded image.
            out = Path(settings.output_dir)
            out.mkdir(parents=True, exist_ok=True)
            name = f"cartoon_{uuid.uuid4().hex}.png"
            (out / name).write_bytes(image_bytes)
            return f"/api/artifacts/{name}"

        # OpenAI image edit endpoint. The image is transformed rather than copied.
        r = requests.post(
            "https://api.openai.com/v1/images/edits",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            files={"image": (image_filename, image_bytes, "image/png")},
            data={
                "model": "gpt-image-1",
                "prompt": (
                    "Turn this person's photo into a tasteful warm Indian editorial "
                    "cartoon portrait. Preserve the person's recognizable facial "
                    "identity and pose. No text, no watermark."
                ),
                "size": "1024x1024",
            },
            timeout=180,
        )
        r.raise_for_status()
        data = r.json()
        import base64
        image = base64.b64decode(data["data"][0]["b64_json"])
        out = Path(settings.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        name = f"cartoon_{uuid.uuid4().hex}.png"
        (out / name).write_bytes(image)
        return f"/api/artifacts/{name}"


class VideoService:
    def create(self, cartoon_path: str, audio_path: str):
        # cartoon_path/audio_path are local paths in this service.
        if shutil_which("ffmpeg") is None:
            raise RuntimeError("FFmpeg is required for video generation.")

        out = Path(settings.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        name = f"poem_video_{uuid.uuid4().hex}.mp4"
        target = out / name

        # Still portrait + poem audio, with a gentle zoom/pan effect.
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", cartoon_path,
            "-i", audio_path,
            "-vf", "scale=1280:1280:force_original_aspect_ratio=decrease,"
                   "pad=1280:1280:(ow-iw)/2:(oh-ih)/2,"
                   "zoompan=z='min(zoom+0.0008,1.08)':d=1:s=1280x1280:fps=25",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            str(target),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return f"/api/artifacts/{name}"


def shutil_which(name):
    import shutil
    return shutil.which(name)
