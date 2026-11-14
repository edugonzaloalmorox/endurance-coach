"""CLI tests for privacy-safe database initialization and status."""

import json
from pathlib import Path

from endurance_coach.cli import main


def test_db_init_and_status_report_only_safe_metadata(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    database = tmp_path / "private-athlete-name" / "coach.sqlite3"
    monkeypatch.setenv("ENDURANCE_COACH_DB_PATH", str(database))

    assert main(["db", "init"]) == 0
    initialized = json.loads(capsys.readouterr().out)
    assert initialized["initialized"] is True
    assert initialized["schema_version"] == 1
    assert set(initialized["table_counts"]) == {
        "activities",
        "activity_sources",
        "activity_records",
        "activity_metrics",
        "athlete_profiles",
        "wellness",
        "sync_state",
    }

    assert main(["db", "status"]) == 0
    output = capsys.readouterr().out
    status = json.loads(output)
    assert status == initialized
    assert "private-athlete-name" not in output
    assert str(database) not in output


def test_db_status_reports_missing_database_without_creating_it(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    database = tmp_path / "missing.sqlite3"
    monkeypatch.setenv("ENDURANCE_COACH_DB_PATH", str(database))

    assert main(["db", "status"]) == 0

    assert json.loads(capsys.readouterr().out) == {
        "initialized": False,
        "schema_version": 0,
        "table_counts": {},
    }
    assert not database.exists()


def test_db_init_returns_safe_error_for_invalid_path(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("ENDURANCE_COACH_DB_PATH", str(tmp_path))

    assert main(["db", "init"]) == 2

    output = capsys.readouterr().out
    assert json.loads(output) == {"error": "database initialization failed"}
    assert str(tmp_path) not in output
