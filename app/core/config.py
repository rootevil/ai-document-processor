"""
Application configuration.

Environment variables can override the default settings.

AI extraction is disabled by default so that existing
document-processing tests and workflows remain independent
of whether Ollama is running.
"""

from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):

    app_name: str = "Document AI"

    app_version: str = "0.1.0"

    debug: bool = False

    api_v1_prefix: str = "/api/v1"

    max_upload_size: int = 10 * 1024 * 1024

    upload_dir: Path = Path("data/uploads")

    database_path: Path = Path("data/database/document_ai.db")

    # --------------------------------------------------
    # Ollama AI configuration
    # --------------------------------------------------

    # Local Ollama server address.
    ollama_base_url: str = "http://localhost:11434"

    # Initial language model for invoice extraction.
    ollama_model: str = "qwen3.5:9b"

    # Maximum time allowed for an AI request.
    ollama_timeout_seconds: float = 180.0

    # AI is opt-in to keep the existing pipeline reliable.
    ai_extraction_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()