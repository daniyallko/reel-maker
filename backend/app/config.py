from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", ".env"),
        extra="ignore",
        populate_by_name=True,
    )

    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    mock_mode: bool = Field(default=False, validation_alias="CUTLINE_MOCK_MODE")
    data_dir: Path = Field(
        default=BACKEND_DIR / "data", validation_alias="CUTLINE_DATA_DIR"
    )
    frontend_origin: str = "http://localhost:3000"

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key) and not self.mock_mode


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir = settings.data_dir.resolve()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
