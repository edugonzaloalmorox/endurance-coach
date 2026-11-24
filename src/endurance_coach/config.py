"""Typed runtime configuration loaded from environment variables."""

import os
from pathlib import Path

from pydantic import BaseModel, Field, SecretStr

_MAX_DOTENV_BYTES = 64 * 1024


def _dotenv_value(name: str) -> str | None:
    """Read one exact key from a small local dotenv file without executing it."""
    path = Path(".env")
    try:
        if not path.is_file() or path.stat().st_size > _MAX_DOTENV_BYTES:
            return None
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line.removeprefix("export ").lstrip()
            key, separator, raw_value = line.partition("=")
            if separator and key.strip() == name:
                value = raw_value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                    value = value[1:-1]
                return value
    except (OSError, UnicodeError):
        return None
    return None


def _env_or_dotenv(name: str, *aliases: str) -> str:
    """Resolve a setting with process environment taking precedence over dotenv."""
    names = (name, *aliases)
    for candidate in names:
        value = os.getenv(candidate)
        if value is not None:
            return value.strip()
    for candidate in names:
        value = _dotenv_value(candidate)
        if value is not None:
            return value.strip()
    return ""


class OllamaSettings(BaseModel):
    """Configuration for the local Ollama model."""

    host: str = Field(default="http://localhost:11434")
    model: str = Field(default="qwen3:8b", min_length=1)
    temperature: float = Field(default=0.2, ge=0, le=2)
    ftp_watts: int = Field(default=250, gt=0, le=1_000)
    max_steps: int = Field(default=4, ge=1, le=20)
    max_context_activities: int = Field(default=50, ge=1, le=500)
    context_length: int = Field(default=16_384, ge=2_048, le=131_072)
    max_output_tokens: int = Field(default=1_200, ge=128, le=4_096)

    @classmethod
    def from_env(cls) -> "OllamaSettings":
        """Load Ollama configuration from environment variables."""
        return cls(
            host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
            context_length=int(os.getenv("OLLAMA_NUM_CTX", "16384")),
            max_output_tokens=int(os.getenv("OLLAMA_NUM_PREDICT", "1200")),
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
        """Load credentials from the process or local dotenv without exposing them."""
        api_key = _env_or_dotenv("INTERVALS_ICU_API_KEY", "INTERVALS_API_KEY")
        if not api_key:
            raise ValueError("INTERVALS_ICU_API_KEY is required")
        return cls(
            athlete_id=_env_or_dotenv("INTERVALS_ICU_ATHLETE_ID") or "0",
            api_key=api_key,
        )
