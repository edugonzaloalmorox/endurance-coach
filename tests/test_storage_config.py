"""Tests for local storage configuration."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from endurance_coach.config import CorosSettings, StorageSettings


def test_storage_settings_have_safe_local_defaults(monkeypatch) -> None:
    monkeypatch.delenv("ENDURANCE_COACH_DB_PATH", raising=False)
    monkeypatch.delenv("ENDURANCE_COACH_ARCHIVE_PATH", raising=False)

    settings = StorageSettings.from_env()

    assert settings.database_path == Path("data/endurance_coach.sqlite3")
    assert settings.archive_path is None


def test_storage_settings_load_paths_without_accessing_them(monkeypatch, tmp_path: Path) -> None:
    database = tmp_path / "missing" / "coach.sqlite3"
    archive = tmp_path / "missing-archive"
    monkeypatch.setenv("ENDURANCE_COACH_DB_PATH", str(database))
    monkeypatch.setenv("ENDURANCE_COACH_ARCHIVE_PATH", str(archive))

    settings = StorageSettings.from_env()

    assert settings.database_path == database
    assert settings.archive_path == archive
    assert not database.exists()
    assert not archive.exists()


def test_coros_settings_use_official_endpoint_and_ignored_local_state(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("COROS_MCP_URL", raising=False)
    monkeypatch.delenv("COROS_OAUTH_STATE_PATH", raising=False)

    settings = CorosSettings.from_env()

    assert settings.endpoint == "https://mcp.coros.com/mcp"
    assert settings.oauth_state_path == Path("data/coros_oauth.json")


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://mcp.coros.com/mcp",
        "https://example.com/mcp",
        "https://mcp.coros.com/other",
        "https://mcp.coros.com/mcp?token=secret",
    ],
)
def test_coros_settings_reject_unofficial_endpoints(endpoint) -> None:
    with pytest.raises(ValidationError, match="official COROS"):
        CorosSettings(endpoint=endpoint)
