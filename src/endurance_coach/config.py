"""Typed runtime configuration loaded from environment variables."""

import os
from pathlib import Path

from pydantic import BaseModel, Field, SecretStr


class OllamaSettings(BaseModel):
    """Configuration for the local Ollama model."""

    host: str = Field(default="http://localhost:11434")
    model: str = Field(default="qwen3:8b", min_length=1)
    temperature: float = Field(default=0.2, ge=0, le=2)

    @classmethod
    def from_env(cls) -> "OllamaSettings":
        """Load Ollama configuration from environment variables."""
        return cls(
            host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
        )


class StorageSettings(BaseModel):
    """Local database and private archive locations.

    Paths are configuration values only. Loading settings does not create,
    inspect, or otherwise access either location.
    """

    database_path: Path = Field(default=Path("data/endurance_coach.sqlite3"))
    archive_path: Path | None = None

    @classmethod
    def from_env(cls) -> "StorageSettings":
        """Load storage paths without resolving or accessing them."""
        archive_value = os.getenv("ENDURANCE_COACH_ARCHIVE_PATH", "").strip()
        return cls(
            database_path=Path(
                os.getenv("ENDURANCE_COACH_DB_PATH", "data/endurance_coach.sqlite3")
            ),
            archive_path=Path(archive_value) if archive_value else None,
        )


class IntervalsSettings(BaseModel):
    """Read-only Intervals.icu API configuration."""

    athlete_id: str = Field(default="0", min_length=1, pattern=r"^(0|i[0-9]+)$")
    api_key: SecretStr = Field(min_length=1)
    base_url: str = Field(default="https://intervals.icu", pattern=r"^https://")
    timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    request_window_days: int = Field(default=90, ge=1, le=366)
    max_response_bytes: int = Field(default=16 * 1024 * 1024, ge=1024)
    max_activities: int = Field(default=10_000, ge=1)

    @classmethod
    def from_env(cls) -> "IntervalsSettings":
        """Load credentials without accessing the network or exposing the API key."""
        api_key = os.getenv("INTERVALS_ICU_API_KEY", "").strip()
        if not api_key:
            raise ValueError("INTERVALS_ICU_API_KEY is required")
        return cls(
            athlete_id=os.getenv("INTERVALS_ICU_ATHLETE_ID", "0").strip() or "0",
            api_key=api_key,
        )
