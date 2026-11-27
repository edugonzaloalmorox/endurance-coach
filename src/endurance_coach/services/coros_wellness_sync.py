"""Coordinate incremental COROS wellness retrieval and atomic persistence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

from endurance_coach.integrations import (
    CorosError,
    CorosRecoverySnapshot,
    normalize_coros_wellness,
)
from endurance_coach.storage import (
    StorageError,
    get_coros_wellness_sync_state,
    initialize_database,
    mark_coros_wellness_sync_failed,
    mark_coros_wellness_sync_running,
    store_coros_wellness,
)


class CorosWellnessSyncError(RuntimeError):
    """Report a safe COROS wellness workflow failure."""


class CorosWellnessSource(Protocol):
    """Read-only recovery retrieval boundary used by the sync workflow."""

    def recovery_snapshot(self, days: int = 7) -> CorosRecoverySnapshot: ...


@dataclass(frozen=True)
class CorosWellnessSyncSummary:
    """Privacy-safe aggregate result for one COROS wellness sync."""

    lookback_days: int
    normalized_days: int
    inserted: int
    updated: int
    with_sleep: int
    with_hrv: int
    with_resting_heart_rate: int
    partial_days: int

    def as_dict(self) -> dict[str, int]:
        """Return only aggregate counts, never health measurements."""
        return asdict(self)


def sync_coros_wellness(
    database_path: Path,
    client: CorosWellnessSource,
    *,
    days: int | None = None,
    current_date: date | None = None,
) -> CorosWellnessSyncSummary:
    """Fetch and persist a retry-safe incremental wellness window.

    An explicit ``days`` value forces a bounded 1-to-30-day lookback. Without one,
    the first sync uses 30 days and later runs resume from the successful cursor
    with a two-day overlap. The cursor advances in the same transaction as every
    wellness upsert.
    """
    if days is not None and (isinstance(days, bool) or not 1 <= days <= 30):
        raise CorosWellnessSyncError("COROS wellness days must be between 1 and 30")

    initialize_database(database_path)
    today = current_date or date.today()
    state = get_coros_wellness_sync_state(database_path)
    if days is not None:
        lookback_days = days
    elif state.last_activity_date is None:
        lookback_days = 30
    else:
        if state.last_activity_date > today:
            raise CorosWellnessSyncError("COROS wellness cursor is in the future")
        oldest = state.last_activity_date - timedelta(days=state.overlap_days)
        lookback_days = min(30, max(1, (today - oldest).days + 1))

    mark_coros_wellness_sync_running(database_path)
    try:
        snapshot = client.recovery_snapshot(lookback_days)
        observations = normalize_coros_wellness(snapshot)
        if not observations:
            raise CorosWellnessSyncError(
                "COROS returned no supported sleep, HRV, or resting-heart-rate data"
            )
        result = store_coros_wellness(
            database_path, observations, synced_through=today
        )
    except (CorosError, CorosWellnessSyncError, StorageError):
        mark_coros_wellness_sync_failed(database_path, "sync_failed")
        raise

    with_sleep = sum(item.sleep_seconds is not None for item in observations)
    with_hrv = sum(item.hrv_ms is not None for item in observations)
    with_resting_heart_rate = sum(
        item.resting_heart_rate_bpm is not None for item in observations
    )
    return CorosWellnessSyncSummary(
        lookback_days=lookback_days,
        normalized_days=len(observations),
        inserted=result.inserted,
        updated=result.updated,
        with_sleep=with_sleep,
        with_hrv=with_hrv,
        with_resting_heart_rate=with_resting_heart_rate,
        partial_days=sum(
            any(
                value is None
                for value in (
                    item.sleep_seconds,
                    item.hrv_ms,
                    item.resting_heart_rate_bpm,
                )
            )
            for item in observations
        ),
    )
