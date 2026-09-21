from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_text_model: str = "gpt-5.6-luna"
    elevenlabs_api_key: str = ""
    elevenlabs_tts_model: str = "eleven_multilingual_v2"
    elevenlabs_stt_model: str = "scribe_v2"
    max_input_chars: int = 5000
    max_poem_lines: int = 32
    output_dir: str = "./data/outputs"
    cors_origins: str = "http://localhost:5173"
    artifact_retention_days: int = 7
    max_audio_bytes: int = 25 * 1024 * 1024
    max_image_bytes: int = 10 * 1024 * 1024
    storage_backend: str = "local"
    s3_bucket: str = ""
    s3_region: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_list(self):
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]


settings = Settings()
