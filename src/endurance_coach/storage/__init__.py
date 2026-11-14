"""SQLite persistence for local Endurance Coach data."""

from endurance_coach.storage.sqlite import (
    CURRENT_SCHEMA_VERSION,
    DatabaseStatus,
    StorageError,
    database_status,
    initialize_database,
)

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "DatabaseStatus",
    "StorageError",
    "database_status",
    "initialize_database",
]
