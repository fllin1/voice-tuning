from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # VT_ prefix applies to internal knobs; HUME_API_KEY uses its canonical name
    # so users can paste the value straight from Hume's dashboard.
    model_config = SettingsConfigDict(env_file=".env", env_prefix="VT_", extra="ignore")

    db_path: Path = Path("voice-tuning.db")
    audio_cache_dir: Path = Path("audio_cache")
    hume_api_key: str | None = Field(default=None, validation_alias="HUME_API_KEY")
    kokoro_repo: str = "prince-canuma/Kokoro-82M"
    orpheus_repo: str = "mlx-community/orpheus-3b-0.1-ft-bf16"
    local_concurrency: int = 1
    cloud_concurrency: int = 4

    def model_post_init(self, _ctx) -> None:
        self.audio_cache_dir.mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
