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
    openrouter_api_key: str | None = Field(default=None, validation_alias="OPENROUTER_API_KEY")
    groq_api_key: str | None = Field(default=None, validation_alias="GROQ_API_KEY")
    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    vision_provider_order: str = Field(default="gemini,openrouter,groq,anthropic", validation_alias="VISION_PROVIDER_ORDER")
    openrouter_vision_model: str = Field(default="inclusionai/ling-3.2-flash:free", validation_alias="OPENROUTER_VISION_MODEL")
    groq_vision_model: str = Field(default="qwen/qwen3.8-27b", validation_alias="GROQ_VISION_MODEL")
    anthropic_vision_model: str = Field(default="claude-haiku-5-5", validation_alias="ANTHROPIC_VISION_MODEL")
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
