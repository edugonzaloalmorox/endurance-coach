"""Tests for the initial SQLite schema and migration behavior."""

import sqlite3
from pathlib import Path

import pytest

import endurance_coach.storage.sqlite as sqlite_storage
from endurance_coach.storage.sqlite import (
    CURRENT_SCHEMA_VERSION,
    INITIAL_TABLES,
    StorageError,
    UnsupportedSchemaVersion,
    database_status,
    initialize_database,
)


def test_initialize_creates_exact_initial_tables(tmp_path: Path) -> None:
    database = tmp_path / "nested" / "coach.sqlite3"

    status = initialize_database(database)

    assert status.initialized is True
    assert status.schema_version == CURRENT_SCHEMA_VERSION
    assert status.table_counts == dict.fromkeys(INITIAL_TABLES, 0)
    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
            if not row[0].startswith("sqlite_")
        }
        assert tables == set(INITIAL_TABLES)
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1


def test_initialize_is_idempotent_and_preserves_rows(tmp_path: Path) -> None:
    database = tmp_path / "coach.sqlite3"
    initialize_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            """INSERT INTO activities (
                id, activity_type, started_at_utc, power_origin,
                quality_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                "activity-1",
                "cycling",
                "2026-01-01T10:00:00+00:00",
                "unavailable",
                "partial",
                "2026-01-01T12:00:00+00:00",
                "2026-01-01T12:00:00+00:00",
            ),
        )

    status = initialize_database(database)

    assert status.table_counts["activities"] == 1


def test_foreign_keys_and_measurement_constraints_are_enforced(tmp_path: Path) -> None:
    database = tmp_path / "coach.sqlite3"
    initialize_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """INSERT INTO activity_records (
                    activity_id, session_index, record_index, power_w
                ) VALUES ('missing', 0, 0, 200)"""
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """INSERT INTO wellness (
                    date, source, weight_kg, quality_status, updated_at
                ) VALUES ('2026-01-01', 'synthetic', -1, 'partial', 'now')"""
            )


def test_sources_can_record_an_unmatched_failed_artifact(tmp_path: Path) -> None:
    database = tmp_path / "coach.sqlite3"
    initialize_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """INSERT INTO activity_sources (
                id, activity_id, source_type, completeness,
                parse_status, error_code, imported_at
            ) VALUES (?, NULL, ?, ?, ?, ?, ?)""",
            (
                "source-1",
                "fit_gz",
                "failed",
                "failed",
                "corrupt_file",
                "2026-01-01T12:00:00+00:00",
            ),
        )
        row = connection.execute(
            "SELECT activity_id, error_code FROM activity_sources"
        ).fetchone()
    assert row == (None, "corrupt_file")


def test_record_measurements_may_remain_null(tmp_path: Path) -> None:
    database = tmp_path / "coach.sqlite3"
    initialize_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """INSERT INTO activities (
                id, activity_type, started_at_utc, power_origin,
                quality_status, created_at, updated_at
            ) VALUES ('activity-1', 'cycling', '2026-01-01T10:00:00+00:00',
                      'unavailable', 'partial', 'now', 'now')"""
        )
        connection.execute(
            """INSERT INTO activity_records (
                activity_id, session_index, record_index, timestamp_utc
            ) VALUES ('activity-1', 0, 0, '2026-01-01T10:00:00+00:00')"""
        )
        row = connection.execute(
            """SELECT power_w, heart_rate_bpm, cadence_rpm, speed_mps,
                      distance_m, altitude_m, temperature_c, latitude,
                      longitude, left_right_balance_pct
               FROM activity_records"""
        ).fetchone()
    assert row == (None,) * 10


def test_missing_database_status_does_not_create_a_file(tmp_path: Path) -> None:
    database = tmp_path / "missing.sqlite3"

    status = database_status(database)

    assert status.initialized is False
    assert status.schema_version == 0
    assert not database.exists()


def test_future_schema_is_rejected(tmp_path: Path) -> None:
    database = tmp_path / "future.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA user_version = 99")

    with pytest.raises(UnsupportedSchemaVersion, match="newer"):
        initialize_database(database)
    with pytest.raises(UnsupportedSchemaVersion, match="newer"):
        database_status(database)


def test_directory_cannot_be_used_as_database_file(tmp_path: Path) -> None:
    with pytest.raises(StorageError, match="initialization failed"):
        initialize_database(tmp_path)


def test_failed_migration_rolls_back_all_schema_changes(
    tmp_path: Path, monkeypatch
) -> None:
    database = tmp_path / "broken.sqlite3"
    monkeypatch.setattr(
        sqlite_storage,
        "_MIGRATION_1",
        "CREATE TABLE partial_table (id TEXT); INVALID SQL;",
    )

    with pytest.raises(StorageError, match="initialization failed"):
        initialize_database(database)

    with sqlite3.connect(database) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        assert tables == []
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
