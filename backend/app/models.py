from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


class PoemRequest(BaseModel):
    prompt: str = Field(default="", max_length=5000)
    style: Literal["doha", "chaupai", "muktak", "free"] = "muktak"
    emotion: str = Field(default="गंभीर और आशावादी", max_length=200)
    lines: int = Field(default=8, ge=2, le=32)
    rhyme: Literal["auto", "AABB", "ABAB", "none"] = "auto"
    language: Literal["hi"] = "hi"

    @field_validator("prompt")
    @classmethod
    def strip_prompt(cls, v):
        return v.strip()


class PoemResponse(BaseModel):
    poem: str
    meter: str
    validation: dict
    txt_url: str
    csv_url: str


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    voice_id: str = Field(min_length=1, max_length=200)


class VoiceCloneResponse(BaseModel):
    voice_id: str


class VideoResponse(BaseModel):
    video_url: str
    cartoon_url: Optional[str] = None
    audio_url: Optional[str] = None
