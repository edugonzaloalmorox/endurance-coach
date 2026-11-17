"""Coordinate incremental Intervals.icu retrieval and atomic persistence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

from endurance_coach.integrations import (
    IntervalsActivity,
    IntervalsError,
    normalize_intervals_activity,
)
from endurance_coach.storage import (
    StorageError,
    get_intervals_sync_state,
    initialize_database,
    mark_intervals_sync_failed,
    mark_intervals_sync_running,
    store_intervals_activities,
)


class IntervalsSyncError(RuntimeError):
    """Report a safe incremental-sync configuration or workflow failure."""


class IntervalsActivitySource(Protocol):
    """Read-only activity retrieval boundary used by the sync workflow."""

    def list_activities(
        self, oldest: date, newest: date
    ) -> tuple[IntervalsActivity, ...]: ...


@dataclass(frozen=True)
class IntervalsSyncSummary:
    """Privacy-safe aggregate result for one Intervals.icu sync."""

    oldest: date
    newest: date
    fetched: int
    inserted: int
    updated: int

    def as_dict(self) -> dict[str, str | int]:
        """Return JSON-safe dates and aggregate counts."""
        values = asdict(self)
        values["oldest"] = self.oldest.isoformat()
        values["newest"] = self.newest.isoformat()
        return values


def sync_intervals_activities(
    database_path: Path,
    client: IntervalsActivitySource,
    *,
    oldest: date | None = None,
    newest: date | None = None,
) -> IntervalsSyncSummary:
    """Fetch and persist one retry-safe incremental activity window.

    An initial sync requires an explicit oldest date. Later runs resume from the stored successful
    date with the configured overlap. The cursor advances only in the same transaction as all
    activity upserts.

    Args:
        database_path: Local SQLite database.
        client: Configured read-only provider client.
        oldest: Optional explicit first date, required for the first sync.
        newest: Inclusive final date, defaulting to the local current date.

    Returns:
        Aggregate fetch and persistence counts.

    Raises:
        IntervalsSyncError: If an initial start date is missing or the range is invalid.
        IntervalsError: If provider retrieval or normalization fails.
        StorageError: If local state cannot be safely persisted.
    """
    initialize_database(database_path)
    state = get_intervals_sync_state(database_path)
    if oldest is None:
        if state.last_activity_date is None:
            raise IntervalsSyncError("initial Intervals.icu sync requires --oldest")
        oldest = state.last_activity_date - timedelta(days=state.overlap_days)
    newest = newest or date.today()
    if oldest > newest:
        raise IntervalsSyncError("invalid Intervals.icu sync date range")

    mark_intervals_sync_running(database_path)
    try:
        fetched = client.list_activities(oldest, newest)
        normalized = tuple(normalize_intervals_activity(item) for item in fetched)
        result = store_intervals_activities(
            database_path, normalized, synced_through=newest
        )
    except (IntervalsError, StorageError):
        mark_intervals_sync_failed(database_path, "sync_failed")
        raise
    return IntervalsSyncSummary(
        oldest=oldest,
        newest=newest,
        fetched=len(fetched),
        inserted=result.inserted,
        updated=result.updated,
    )
