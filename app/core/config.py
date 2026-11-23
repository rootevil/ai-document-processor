
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    app_name: str = "Document AI"
    app_version: str = "0.1.0"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    max_upload_size: int = 10 * 1024 * 1024
    upload_dir: Path = Path("data/uploads")
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
