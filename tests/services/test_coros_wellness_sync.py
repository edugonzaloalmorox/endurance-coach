"""End-to-end tests for incremental COROS wellness synchronization."""

import json
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from endurance_coach.integrations import CorosError, CorosRecoverySnapshot
from endurance_coach.services import sync_coros_wellness


def _snapshot(*, include_sleep_and_hrv: bool = True) -> CorosRecoverySnapshot:
    observations = {
        "queryRestingHeartRate": json.dumps(
            "Resting Heart Rate\n2026-11-26: 48 bpm"
        )
    }
    if include_sleep_and_hrv:
        observations |= {
            "querySleepOverview": json.dumps(
                "Sleep Overview\n2026-11-26\nDaily Sleep: 7h 30min (incl. naps)"
            ),
            "querySleepHrv": json.dumps(
                "Sleep HRV\n2026-11-26:\n  HRV Avg: 42 ms — Normal"
            ),
        }
    return CorosRecoverySnapshot(
        days=7,
        observations=observations,
        unavailable_tools=(),
    )


class _Client:
    def __init__(
        self,
        snapshot: CorosRecoverySnapshot | None = None,
        error: CorosError | None = None,
    ) -> None:
        self.snapshot = snapshot or _snapshot()
        self.error = error
        self.calls: list[int] = []

    def recovery_snapshot(self, days: int = 7) -> CorosRecoverySnapshot:
        self.calls.append(days)
        if self.error is not None:
            raise self.error
        return self.snapshot


def test_sync_is_incremental_idempotent_and_preserves_missing_retry_values(
    tmp_path: Path,
) -> None:
    database = tmp_path / "coach.sqlite3"
    first_client = _Client()
    first = sync_coros_wellness(
        database,
        first_client,
        days=7,
        current_date=date(2026, 11, 27),
    )
    retry_client = _Client(_snapshot(include_sleep_and_hrv=False))
    retry = sync_coros_wellness(
        database,
        retry_client,
        current_date=date(2026, 11, 27),
    )

    assert first.as_dict() == {
        "lookback_days": 7,
        "normalized_days": 1,
        "inserted": 1,
        "updated": 0,
        "with_sleep": 1,
        "with_hrv": 1,
        "with_resting_heart_rate": 1,
        "partial_days": 0,
    }
    assert retry.inserted == 0
    assert retry.updated == 1
    assert retry.partial_days == 1
    assert first_client.calls == [7]
    assert retry_client.calls == [3]
    with sqlite3.connect(database) as connection:
        wellness = connection.execute(
            """SELECT resting_heart_rate_bpm, hrv_ms, sleep_seconds, quality_status
               FROM wellness"""
        ).fetchone()
        state = connection.execute(
            """SELECT last_activity_date, status
               FROM sync_state WHERE source = 'coros_wellness'"""
        ).fetchone()
    assert wellness == (48.0, 42.0, 27_000.0, "complete")
    assert state == ("2026-11-27", "succeeded")


def test_failed_retry_preserves_successful_cursor(tmp_path: Path) -> None:
    database = tmp_path / "coach.sqlite3"
    sync_coros_wellness(
        database,
        _Client(),
        days=7,
        current_date=date(2026, 11, 27),
    )

    with pytest.raises(CorosError, match="provider unavailable"):
        sync_coros_wellness(
            database,
            _Client(error=CorosError("provider unavailable")),
            current_date=date(2026, 11, 28),
        )

    with sqlite3.connect(database) as connection:
        state = connection.execute(
            """SELECT last_activity_date, status, last_error_code
               FROM sync_state WHERE source = 'coros_wellness'"""
        ).fetchone()
    assert state == ("2026-11-27", "failed", "sync_failed")
