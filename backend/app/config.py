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
    db_path: str = "./data/app.db"
    # Optional environment flags for easy deployment
    env: str = "development"  # development | production
    host: str = "0.0.0.0"
    port: int = 8000
    # For local development allow all origins by default. In production set specific origins.
    cors_origins: str = "*"
    # Google OAuth settings for sign-in (set via .env in production)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_path: str = "/api/auth/google/callback"
    frontend_origin: str = "http://localhost:5173"
    backend_origin: str = "http://localhost:8000"
    jwks_refresh_seconds: int = 3600

    # JWT for session tokens
    # In production set a strong secret via the environment variable JWT_SECRET or in the .env file
    # Default is empty to avoid accidentally using a weak hard-coded secret in production.
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
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

# Safety check: require a non-empty JWT secret when running in production.
if settings.env == "production" and not settings.jwt_secret:
    raise RuntimeError(
        "JWT secret is required in production. Set JWT_SECRET in the environment or .env to a strong secret."
    )
