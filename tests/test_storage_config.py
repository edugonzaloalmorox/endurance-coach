"""Tests for local storage configuration."""

from pathlib import Path

from endurance_coach.config import StorageSettings


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
