"""Runtime configuration for the local Ollama model."""

import os

from pydantic import BaseModel, Field


class OllamaSettings(BaseModel):
    host: str = Field(default="http://localhost:11434")
    model: str = Field(default="qwen3:8b", min_length=1)
    temperature: float = Field(default=0.2, ge=0, le=2)

    @classmethod
    def from_env(cls) -> "OllamaSettings":
        return cls(
            host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
        )
