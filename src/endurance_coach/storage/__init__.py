"""SQLite persistence for local Endurance Coach data."""

from endurance_coach.storage.sqlite import (
    CURRENT_SCHEMA_VERSION,
    DatabaseStatus,
    FitWriteResult,
    IntervalsWriteResult,
    StorageError,
    SyncState,
    database_status,
    get_intervals_sync_state,
    initialize_database,
    mark_intervals_sync_failed,
    mark_intervals_sync_running,
    record_fit_failure,
    store_fit_artifact,
    store_intervals_activities,
)

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "DatabaseStatus",
    "FitWriteResult",
    "IntervalsWriteResult",
    "StorageError",
    "SyncState",
    "database_status",
    "get_intervals_sync_state",
    "initialize_database",
    "mark_intervals_sync_failed",
    "mark_intervals_sync_running",
    "record_fit_failure",
    "store_intervals_activities",
    "store_fit_artifact",
]
