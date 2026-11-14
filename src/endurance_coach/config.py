"""Typed runtime configuration loaded from environment variables."""

import os
from pathlib import Path

from pydantic import BaseModel, Field


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
