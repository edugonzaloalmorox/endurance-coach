"""Tests for transactional Intervals/FIT activity reconciliation."""

import sqlite3
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from endurance_coach.domain import ImportedActivity
from endurance_coach.integrations import NormalizedIntervalsActivity
from endurance_coach.storage import initialize_database, store_intervals_activities

_START = datetime(2026, 11, 12, 8, 0, tzinfo=UTC)


def _insert_fit_activity(
    database: Path,
    activity_id: str,
    *,
    start: datetime,
    elapsed_seconds: float = 3600,
) -> None:
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """INSERT INTO activities (
                   id, activity_type, name, started_at_utc, elapsed_seconds,
                   moving_seconds, distance_m, average_power_w, power_origin,
                   quality_status, created_at, updated_at
               ) VALUES (?, 'cycling', 'FIT Ride', ?, ?, 3500, 30000, 200,
                         'measured', 'complete', 'now', 'now')""",
            (activity_id, start.isoformat(), elapsed_seconds),
        )
        connection.execute(
            """INSERT INTO activity_sources (
                   id, activity_id, source_type, external_id, completeness,
                   parse_status, imported_at
               ) VALUES (?, ?, 'fit', ?, 'complete', 'imported', 'now')""",
            (f"source:{activity_id}", activity_id, f"external:{activity_id}"),
        )
        connection.execute(
            """INSERT INTO activity_records (
                   activity_id, session_index, record_index, power_w, power_origin
               ) VALUES (?, 0, 0, 250, 'measured')""",
            (activity_id,),
        )


def _intervals_activity() -> NormalizedIntervalsActivity:
    return NormalizedIntervalsActivity(
        external_id="i1",
        activity=ImportedActivity(
            activity_id="intervals:i1",
            activity_type="ride",
            name="Intervals Ride",
            started_at_utc=_START + timedelta(seconds=60),
            elapsed_seconds=3650,
            moving_seconds=3600,
            distance_m=31000,
            average_power_w=210,
            normalized_power_w=220,
            average_heart_rate_bpm=145,
            power_origin="derived",
            quality_status="partial",
            records=(),
        ),
    )


def test_reconciliation_uses_intervals_summary_and_preserves_fit_provenance(
    tmp_path: Path,
) -> None:
    database = tmp_path / "coach.sqlite3"
    initialize_database(database)
    _insert_fit_activity(database, "fit:one", start=_START)

    result = store_intervals_activities(
        database, (_intervals_activity(),), synced_through=date(2026, 11, 12)
    )

    assert (result.inserted, result.updated, result.reconciled) == (0, 1, 1)
    with sqlite3.connect(database) as connection:
        activity = connection.execute(
            """SELECT id, activity_type, name, distance_m, average_power_w,
                      normalized_power_w, power_origin, quality_status
               FROM activities"""
        ).fetchone()
        sources = connection.execute(
            """SELECT source_type, activity_id FROM activity_sources
               ORDER BY source_type"""
        ).fetchall()
        record = connection.execute(
            "SELECT activity_id, power_w, power_origin FROM activity_records"
        ).fetchone()
    assert activity == (
        "intervals:i1",
        "ride",
        "Intervals Ride",
        31000.0,
        210.0,
        220.0,
        "derived",
        "complete",
    )
    assert sources == [("fit", "intervals:i1"), ("intervals", "intervals:i1")]
    assert record == ("intervals:i1", 250.0, "measured")


def test_ambiguous_candidates_remain_separate(tmp_path: Path) -> None:
    database = tmp_path / "coach.sqlite3"
    initialize_database(database)
    _insert_fit_activity(
        database, "fit:before", start=_START - timedelta(seconds=60)
    )
    _insert_fit_activity(database, "fit:after", start=_START + timedelta(seconds=60))

    result = store_intervals_activities(
        database, (_intervals_activity(),), synced_through=date(2026, 11, 12)
    )

    assert (result.inserted, result.updated, result.reconciled) == (1, 0, 0)
    with sqlite3.connect(database) as connection:
        activity_ids = {
            row[0] for row in connection.execute("SELECT id FROM activities")
        }
    assert activity_ids == {"fit:before", "fit:after", "intervals:i1"}
