from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    database_url: str = "postgresql://billvision@127.0.0.1:54329/billvision"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout: int = 600
    storage_dir: Path = ROOT / "storage"
    docling_artifacts_path: Path = ROOT / "models/docling"
    max_file_mb: int = 10
    max_pages: int = 5
    max_image_pixels: int = 25_000_000


settings = Settings()
