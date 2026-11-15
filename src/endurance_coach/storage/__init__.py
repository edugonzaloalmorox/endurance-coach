"""SQLite persistence for local Endurance Coach data."""

from endurance_coach.storage.sqlite import (
    CURRENT_SCHEMA_VERSION,
    DatabaseStatus,
    FitWriteResult,
    StorageError,
    database_status,
    initialize_database,
    record_fit_failure,
    store_fit_artifact,
)

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "DatabaseStatus",
    "FitWriteResult",
    "StorageError",
    "database_status",
    "initialize_database",
    "record_fit_failure",
    "store_fit_artifact",
]
