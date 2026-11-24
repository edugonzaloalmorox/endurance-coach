"""End-to-end tests for incremental Intervals.icu synchronization."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pytest

from endurance_coach.integrations import IntervalsActivity, IntervalsError
from endurance_coach.services import IntervalsSyncError, sync_intervals_activities


def _activity(name: str = "Synthetic Ride") -> IntervalsActivity:
    return IntervalsActivity(
        external_id="i-synthetic-1",
        raw={
            "id": "i-synthetic-1",
            "name": name,
            "type": "Ride",
            "start_date": "2026-11-01T08:00:00Z",
            "moving_time": 3600,
            "distance": 30_000,
        },
    )


class _Client:
    def __init__(
        self,
        activities: tuple[IntervalsActivity, ...] = (),
        error: IntervalsError | None = None,
    ) -> None:
        self.activities = activities
        self.error = error
        self.calls: list[tuple[date, date]] = []

    def list_activities(
        self, oldest: date, newest: date
    ) -> tuple[IntervalsActivity, ...]:
        self.calls.append((oldest, newest))
        if self.error is not None:
            raise self.error
        return self.activities


def test_sync_is_idempotent_and_retries_with_overlap(tmp_path: Path) -> None:
    database = tmp_path / "coach.sqlite3"
    first_client = _Client((_activity(),))
    first = sync_intervals_activities(
        database,
        first_client,
        oldest=date(2026, 11, 1),
        newest=date(2026, 11, 2),
    )
    second_client = _Client((_activity("Updated Synthetic Ride"),))
    second = sync_intervals_activities(
        database,
        second_client,
        newest=date(2026, 11, 3),
    )

    assert first.as_dict() == {
        "oldest": "2026-11-01",
        "newest": "2026-11-02",
        "fetched": 1,
        "inserted": 1,
        "updated": 0,
        "reconciled": 0,
    }
    assert second.inserted == 0
    assert second.updated == 1
    assert second_client.calls == [(date(2026, 10, 26), date(2026, 11, 3))]
    with sqlite3.connect(database) as connection:
        activity = connection.execute(
            "SELECT name, moving_seconds, distance_m FROM activities"
        ).fetchone()
        source_count = connection.execute(
            "SELECT COUNT(*) FROM activity_sources WHERE source_type = 'intervals'"
        ).fetchone()[0]
        state = connection.execute(
            "SELECT last_activity_date, status FROM sync_state WHERE source = 'intervals'"
        ).fetchone()
    assert activity == ("Updated Synthetic Ride", 3600.0, 30_000.0)
    assert source_count == 1
    assert state == ("2026-11-03", "succeeded")


def test_failed_retry_preserves_successful_cursor(tmp_path: Path) -> None:
    database = tmp_path / "coach.sqlite3"
    sync_intervals_activities(
        database,
        _Client((_activity(),)),
        oldest=date(2026, 11, 1),
        newest=date(2026, 11, 2),
    )

    with pytest.raises(IntervalsError, match="provider unavailable"):
        sync_intervals_activities(
            database,
            _Client(error=IntervalsError("provider unavailable")),
            newest=date(2026, 11, 3),
        )

    with sqlite3.connect(database) as connection:
        state = connection.execute(
            """SELECT last_activity_date, status, last_error_code
               FROM sync_state WHERE source = 'intervals'"""
        ).fetchone()
    assert state == ("2026-11-02", "failed", "sync_failed")


def test_initial_sync_requires_explicit_oldest(tmp_path: Path) -> None:
    with pytest.raises(IntervalsSyncError, match="requires --oldest"):
        sync_intervals_activities(
            tmp_path / "coach.sqlite3",
            _Client(),
            newest=date(2026, 11, 3),
        )
