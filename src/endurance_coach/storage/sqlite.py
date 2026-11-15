"""Versioned SQLite schema and safe database inspection."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

CURRENT_SCHEMA_VERSION = 1

INITIAL_TABLES = (
    "activities",
    "activity_sources",
    "activity_records",
    "activity_metrics",
    "athlete_profiles",
    "wellness",
    "sync_state",
)

_ORIGINS = "'measured', 'estimated', 'derived', 'unavailable'"

_MIGRATION_1 = f"""
CREATE TABLE activities (
    id TEXT PRIMARY KEY,
    activity_type TEXT NOT NULL,
    name TEXT,
    description TEXT,
    started_at_utc TEXT NOT NULL,
    timezone_offset_minutes INTEGER,
    elapsed_seconds REAL CHECK (elapsed_seconds IS NULL OR elapsed_seconds >= 0),
    moving_seconds REAL CHECK (moving_seconds IS NULL OR moving_seconds >= 0),
    distance_m REAL CHECK (distance_m IS NULL OR distance_m >= 0),
    elevation_gain_m REAL CHECK (elevation_gain_m IS NULL OR elevation_gain_m >= 0),
    average_power_w REAL CHECK (average_power_w IS NULL OR average_power_w >= 0),
    normalized_power_w REAL CHECK (normalized_power_w IS NULL OR normalized_power_w >= 0),
    average_heart_rate_bpm REAL CHECK (
        average_heart_rate_bpm IS NULL OR average_heart_rate_bpm > 0
    ),
    power_origin TEXT NOT NULL DEFAULT 'unavailable'
        CHECK (power_origin IN ({_ORIGINS})),
    quality_status TEXT NOT NULL DEFAULT 'partial'
        CHECK (quality_status IN ('complete', 'partial', 'restricted', 'invalid')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE activity_sources (
    id TEXT PRIMARY KEY,
    activity_id TEXT REFERENCES activities(id) ON DELETE SET NULL,
    source_type TEXT NOT NULL
        CHECK (source_type IN ('fit', 'fit_gz', 'strava_csv', 'intervals')),
    external_id TEXT,
    relative_path TEXT,
    raw_sha256 TEXT CHECK (raw_sha256 IS NULL OR length(raw_sha256) = 64),
    content_sha256 TEXT CHECK (content_sha256 IS NULL OR length(content_sha256) = 64),
    completeness TEXT NOT NULL
        CHECK (completeness IN ('complete', 'summary_only', 'restricted', 'failed')),
    parse_status TEXT NOT NULL
        CHECK (parse_status IN ('pending', 'imported', 'duplicate', 'failed')),
    error_code TEXT,
    imported_at TEXT NOT NULL,
    UNIQUE (source_type, external_id)
);

CREATE UNIQUE INDEX activity_sources_raw_hash
    ON activity_sources(raw_sha256) WHERE raw_sha256 IS NOT NULL;
CREATE UNIQUE INDEX activity_sources_content_hash
    ON activity_sources(content_sha256) WHERE content_sha256 IS NOT NULL;

CREATE TABLE athlete_profiles (
    id TEXT PRIMARY KEY,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    ftp_w REAL CHECK (ftp_w IS NULL OR ftp_w > 0),
    weight_kg REAL CHECK (weight_kg IS NULL OR weight_kg > 0),
    power_zones_json TEXT,
    heart_rate_zones_json TEXT,
    timezone TEXT,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL,
    CHECK (valid_to IS NULL OR valid_to > valid_from)
);

CREATE TABLE activity_records (
    activity_id TEXT NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    session_index INTEGER NOT NULL CHECK (session_index >= 0),
    record_index INTEGER NOT NULL CHECK (record_index >= 0),
    timestamp_utc TEXT,
    elapsed_seconds REAL CHECK (elapsed_seconds IS NULL OR elapsed_seconds >= 0),
    timer_seconds REAL CHECK (timer_seconds IS NULL OR timer_seconds >= 0),
    power_w REAL CHECK (power_w IS NULL OR power_w >= 0),
    power_origin TEXT CHECK (power_origin IS NULL OR power_origin IN ({_ORIGINS})),
    heart_rate_bpm REAL CHECK (heart_rate_bpm IS NULL OR heart_rate_bpm > 0),
    cadence_rpm REAL CHECK (cadence_rpm IS NULL OR cadence_rpm >= 0),
    speed_mps REAL CHECK (speed_mps IS NULL OR speed_mps >= 0),
    distance_m REAL CHECK (distance_m IS NULL OR distance_m >= 0),
    altitude_m REAL,
    temperature_c REAL,
    latitude REAL CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
    longitude REAL CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180),
    left_right_balance_pct REAL CHECK (
        left_right_balance_pct IS NULL OR left_right_balance_pct BETWEEN 0 AND 100
    ),
    PRIMARY KEY (activity_id, session_index, record_index)
);

CREATE TABLE activity_metrics (
    id TEXT PRIMARY KEY,
    activity_id TEXT NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL,
    value REAL,
    unit TEXT NOT NULL,
    origin TEXT NOT NULL CHECK (origin IN ({_ORIGINS})),
    calculation_version TEXT,
    profile_id TEXT REFERENCES athlete_profiles(id) ON DELETE SET NULL,
    coverage REAL CHECK (coverage IS NULL OR coverage BETWEEN 0 AND 1),
    calculated_at TEXT NOT NULL,
    UNIQUE (activity_id, metric_name, calculation_version)
);

CREATE TABLE wellness (
    date TEXT NOT NULL,
    source TEXT NOT NULL,
    weight_kg REAL CHECK (weight_kg IS NULL OR weight_kg > 0),
    resting_heart_rate_bpm REAL CHECK (
        resting_heart_rate_bpm IS NULL OR resting_heart_rate_bpm > 0
    ),
    hrv_ms REAL CHECK (hrv_ms IS NULL OR hrv_ms >= 0),
    sleep_seconds REAL CHECK (sleep_seconds IS NULL OR sleep_seconds >= 0),
    quality_status TEXT NOT NULL DEFAULT 'partial'
        CHECK (quality_status IN ('complete', 'partial', 'restricted', 'invalid')),
    updated_at TEXT NOT NULL,
    PRIMARY KEY (date, source)
);

CREATE TABLE sync_state (
    source TEXT PRIMARY KEY,
    last_successful_at TEXT,
    last_activity_date TEXT,
    overlap_days INTEGER NOT NULL DEFAULT 7 CHECK (overlap_days >= 0),
    status TEXT NOT NULL DEFAULT 'never_run'
        CHECK (status IN ('never_run', 'running', 'succeeded', 'failed')),
    last_error_code TEXT,
    updated_at TEXT NOT NULL
);
"""


class StorageError(RuntimeError):
    """Report a database failure without exposing a private filesystem path."""


class UnsupportedSchemaVersion(StorageError):
    """Indicate that the database was created by a newer application version."""


@dataclass(frozen=True)
class DatabaseStatus:
    """Safe database metadata suitable for CLI output."""

    initialized: bool
    schema_version: int
    table_counts: dict[str, int]

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serializable status without paths or measurements."""
        return {
            "initialized": self.initialized,
            "schema_version": self.schema_version,
            "table_counts": self.table_counts,
        }


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _schema_version(connection: sqlite3.Connection) -> int:
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def _status(connection: sqlite3.Connection) -> DatabaseStatus:
    version = _schema_version(connection)
    if version > CURRENT_SCHEMA_VERSION:
        raise UnsupportedSchemaVersion("database schema is newer than this application")
    if version == 0:
        return DatabaseStatus(initialized=False, schema_version=0, table_counts={})
    counts = {
        table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in INITIAL_TABLES
    }
    return DatabaseStatus(initialized=True, schema_version=version, table_counts=counts)


def initialize_database(path: Path) -> DatabaseStatus:
    """Create or validate the versioned SQLite database.

    Args:
        path: Local SQLite file path. Parent directories are created when needed.

    Returns:
        Safe schema status and row counts.

    Raises:
        StorageError: If the path or migration cannot be initialized safely.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _connect(path) as connection:
            version = _schema_version(connection)
            if version > CURRENT_SCHEMA_VERSION:
                raise UnsupportedSchemaVersion(
                    "database schema is newer than this application"
                )
            if version == 0:
                try:
                    connection.executescript(
                        "BEGIN IMMEDIATE;\n"
                        + _MIGRATION_1
                        + f"\nPRAGMA user_version = {CURRENT_SCHEMA_VERSION};\nCOMMIT;"
                    )
                except Exception:
                    connection.rollback()
                    raise
            return _status(connection)
    except UnsupportedSchemaVersion:
        raise
    except (OSError, sqlite3.Error) as exc:
        raise StorageError("database initialization failed") from exc


def database_status(path: Path) -> DatabaseStatus:
    """Inspect schema version and row counts without creating a database.

    Args:
        path: Local SQLite file path.

    Returns:
        Safe database status. A missing path is reported as uninitialized.

    Raises:
        StorageError: If an existing database cannot be inspected safely.
    """
    if not path.exists():
        return DatabaseStatus(initialized=False, schema_version=0, table_counts={})
    try:
        with _connect(path) as connection:
            return _status(connection)
    except UnsupportedSchemaVersion:
        raise
    except (OSError, sqlite3.Error) as exc:
        raise StorageError("database inspection failed") from exc
