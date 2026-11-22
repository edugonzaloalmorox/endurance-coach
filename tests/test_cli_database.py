"""CLI tests for privacy-safe database initialization and status."""

import json
import sqlite3
from pathlib import Path

import endurance_coach.cli as cli
from endurance_coach.cli import main
from endurance_coach.integrations import IntervalsActivity
from tests.fit_fixture import write_fit_fixture


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


def test_db_inspect_reports_bounded_recent_summaries_without_private_details(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    database = tmp_path / "private-athlete-name" / "coach.sqlite3"
    monkeypatch.setenv("ENDURANCE_COACH_DB_PATH", str(database))
    assert main(["db", "init"]) == 0
    capsys.readouterr()
    with sqlite3.connect(database) as connection:
        for activity_id, started_at in (
            ("synthetic-old", "2026-01-01T08:00:00+00:00"),
            ("synthetic-new", "2026-01-02T08:00:00+00:00"),
        ):
            connection.execute(
                """INSERT INTO activities (
                       id, activity_type, name, description, started_at_utc,
                       distance_m, power_origin, quality_status, created_at, updated_at
                   ) VALUES (?, 'cycling', 'Synthetic ride', 'private route notes', ?,
                             NULL, 'unavailable', 'partial', 'now', 'now')""",
                (activity_id, started_at),
            )
        connection.execute(
            """INSERT INTO activity_sources (
                   id, activity_id, source_type, relative_path, completeness,
                   parse_status, imported_at
               ) VALUES ('source-new', 'synthetic-new', 'fit',
                         'private/archive/ride.fit', 'complete', 'imported', 'now')"""
        )
        connection.execute(
            """INSERT INTO activity_records (
                   activity_id, session_index, record_index, latitude, longitude
               ) VALUES ('synthetic-new', 0, 0, 40.4168, -3.7038)"""
        )

    assert main(["db", "inspect", "--limit", "1"]) == 0

    output = capsys.readouterr().out
    inspection = json.loads(output)
    assert inspection["initialized"] is True
    assert inspection["table_counts"]["activities"] == 2
    assert inspection["activities"] == [
        {
            "activity_id": "synthetic-new",
            "activity_type": "cycling",
            "average_heart_rate_bpm": None,
            "average_power_w": None,
            "distance_m": None,
            "elapsed_seconds": None,
            "elevation_gain_m": None,
            "moving_seconds": None,
            "name": "Synthetic ride",
            "normalized_power_w": None,
            "power_origin": "unavailable",
            "quality_status": "partial",
            "record_count": 1,
            "source_types": ["fit"],
            "started_at_utc": "2026-01-02T08:00:00+00:00",
        }
    ]
    assert "private route notes" not in output
    assert "private/archive" not in output
    assert "40.4168" not in output
    assert "-3.7038" not in output
    assert str(database) not in output


def test_db_inspect_missing_database_is_read_only(tmp_path: Path, monkeypatch, capsys) -> None:
    database = tmp_path / "missing.sqlite3"
    monkeypatch.setenv("ENDURANCE_COACH_DB_PATH", str(database))

    assert main(["db", "inspect"]) == 0

    assert json.loads(capsys.readouterr().out) == {
        "activities": [],
        "initialized": False,
        "schema_version": 0,
        "table_counts": {},
    }
    assert not database.exists()


def test_db_inspect_rejects_unbounded_limit(tmp_path: Path, monkeypatch, capsys) -> None:
    database = tmp_path / "coach.sqlite3"
    monkeypatch.setenv("ENDURANCE_COACH_DB_PATH", str(database))

    assert main(["db", "inspect", "--limit", "101"]) == 2

    assert json.loads(capsys.readouterr().out) == {
        "error": "inspection limit must be between 1 and 100"
    }
    assert not database.exists()


def test_db_init_returns_safe_error_for_invalid_path(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("ENDURANCE_COACH_DB_PATH", str(tmp_path))

    assert main(["db", "init"]) == 2

    output = capsys.readouterr().out
    assert json.loads(output) == {"error": "database initialization failed"}
    assert str(tmp_path) not in output


def test_db_import_fit_reports_only_aggregate_counts(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    archive = tmp_path / "private-athlete-archive"
    database = tmp_path / "private-athlete-database.sqlite3"
    write_fit_fixture(archive / "identifying-file-name.fit.gz", compressed=True)
    monkeypatch.setenv("ENDURANCE_COACH_DB_PATH", str(database))

    assert main(["db", "import-fit", str(archive)]) == 0

    output = capsys.readouterr().out
    assert json.loads(output) == {
        "activities_written": 1,
        "discovered": 1,
        "dry_run": False,
        "duplicates": 0,
        "failed": 0,
        "imported": 1,
        "metadata_associated": 0,
        "metadata_failed": 0,
        "metadata_rows": 0,
        "metadata_unmatched": 0,
        "records_written": 2,
        "validated": 1,
    }
    assert "private-athlete" not in output
    assert "identifying-file-name" not in output


def test_db_import_fit_requires_configured_archive(monkeypatch, capsys) -> None:
    monkeypatch.delenv("ENDURANCE_COACH_ARCHIVE_PATH", raising=False)

    assert main(["db", "import-fit"]) == 2

    assert json.loads(capsys.readouterr().out) == {"error": "archive_not_configured"}


def test_db_sync_intervals_reports_aggregate_counts(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    database = tmp_path / "private-athlete-database.sqlite3"
    monkeypatch.setenv("ENDURANCE_COACH_DB_PATH", str(database))
    monkeypatch.setenv("INTERVALS_ICU_API_KEY", "synthetic-secret")

    class FakeClient:
        def __init__(self, _settings) -> None:
            pass

        def list_activities(self, _oldest, _newest):
            return (
                IntervalsActivity(
                    external_id="i-synthetic-1",
                    raw={
                        "id": "i-synthetic-1",
                        "type": "Ride",
                        "start_date": "2026-11-01T08:00:00Z",
                    },
                ),
            )

    monkeypatch.setattr(cli, "IntervalsClient", FakeClient)

    assert main(
        [
            "db",
            "sync-intervals",
            "--oldest",
            "2026-11-01",
            "--newest",
            "2026-11-02",
        ]
    ) == 0

    output = capsys.readouterr().out
    assert json.loads(output) == {
        "fetched": 1,
        "inserted": 1,
        "newest": "2026-11-02",
        "oldest": "2026-11-01",
        "updated": 0,
    }
    assert "synthetic-secret" not in output
    assert "private-athlete" not in output
