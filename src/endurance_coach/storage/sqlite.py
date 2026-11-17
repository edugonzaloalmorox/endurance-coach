"""Versioned SQLite schema and safe database inspection."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from endurance_coach.ingestion.csv_metadata import HistoricalMetadata
from endurance_coach.ingestion.fit import FitArtifact
from endurance_coach.integrations import NormalizedIntervalsActivity

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


@dataclass(frozen=True)
class FitWriteResult:
    """Outcome of one transactional FIT persistence attempt."""

    outcome: str
    activities_written: int = 0
    records_written: int = 0
    metadata_associated: bool = False


@dataclass(frozen=True)
class SyncState:
    """Incremental cursor and retry overlap for one external source."""

    last_activity_date: date | None
    overlap_days: int = 7


@dataclass(frozen=True)
class IntervalsWriteResult:
    """Aggregate outcome of one atomic Intervals.icu persistence batch."""

    inserted: int
    updated: int


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


def store_fit_artifact(
    path: Path,
    artifact: FitArtifact,
    metadata: HistoricalMetadata | None = None,
) -> FitWriteResult:
    """Persist one parsed FIT artifact atomically and idempotently.

    Args:
        path: Initialized SQLite database path.
        artifact: Parsed source hashes and normalized activity.
        metadata: Optional descriptive CSV row matched to this artifact.

    Returns:
        Whether the artifact was imported or was already present.

    Raises:
        StorageError: If persistence fails. No partial activity remains committed.
    """
    now = datetime.now(UTC).isoformat()
    activity = artifact.activity
    try:
        with _connect(path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """SELECT id, parse_status FROM activity_sources
                   WHERE raw_sha256 = ? OR content_sha256 = ?
                   ORDER BY parse_status = 'imported' DESC
                   LIMIT 1""",
                (artifact.raw_sha256, artifact.content_sha256),
            ).fetchone()
            if existing and existing[1] != "failed":
                associated = _associate_metadata(connection, activity.activity_id, metadata, now)
                connection.commit()
                return FitWriteResult(
                    outcome="duplicate", metadata_associated=associated
                )
            if existing:
                connection.execute("DELETE FROM activity_sources WHERE id = ?", (existing[0],))

            connection.execute(
                """INSERT INTO activities (
                       id, activity_type, name, description, started_at_utc,
                       timezone_offset_minutes, elapsed_seconds, moving_seconds,
                       distance_m, elevation_gain_m, average_power_w,
                       normalized_power_w, average_heart_rate_bpm, power_origin,
                       quality_status, created_at, updated_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO NOTHING""",
                (
                    activity.activity_id,
                    activity.activity_type,
                    activity.name,
                    activity.description,
                    activity.started_at_utc.isoformat(),
                    activity.timezone_offset_minutes,
                    activity.elapsed_seconds,
                    activity.moving_seconds,
                    activity.distance_m,
                    activity.elevation_gain_m,
                    activity.average_power_w,
                    activity.normalized_power_w,
                    activity.average_heart_rate_bpm,
                    activity.power_origin,
                    activity.quality_status,
                    now,
                    now,
                ),
            )
            activity_exists = connection.execute(
                "SELECT 1 FROM activities WHERE id = ?", (activity.activity_id,)
            ).fetchone()
            if not activity_exists:
                raise sqlite3.IntegrityError("activity insert failed")

            connection.execute(
                """INSERT INTO activity_sources (
                       id, activity_id, source_type, external_id, relative_path,
                       raw_sha256, content_sha256, completeness, parse_status,
                       error_code, imported_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'imported', NULL, ?)""",
                (
                    f"fit-source:{artifact.raw_sha256}",
                    activity.activity_id,
                    artifact.source_type,
                    artifact.content_sha256,
                    artifact.relative_path,
                    artifact.raw_sha256,
                    artifact.content_sha256,
                    "complete" if activity.quality_status == "complete" else "summary_only",
                    now,
                ),
            )
            connection.executemany(
                """INSERT INTO activity_records (
                       activity_id, session_index, record_index, timestamp_utc,
                       elapsed_seconds, timer_seconds, power_w, power_origin,
                       heart_rate_bpm, cadence_rpm, speed_mps, distance_m,
                       altitude_m, temperature_c, latitude, longitude,
                       left_right_balance_pct
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        activity.activity_id,
                        record.session_index,
                        record.record_index,
                        record.timestamp_utc.isoformat() if record.timestamp_utc else None,
                        record.elapsed_seconds,
                        record.timer_seconds,
                        record.power_w,
                        record.power_origin,
                        record.heart_rate_bpm,
                        record.cadence_rpm,
                        record.speed_mps,
                        record.distance_m,
                        record.altitude_m,
                        record.temperature_c,
                        record.latitude,
                        record.longitude,
                        record.left_right_balance_pct,
                    )
                    for record in activity.records
                ],
            )
            associated = _associate_metadata(connection, activity.activity_id, metadata, now)
            connection.commit()
            return FitWriteResult(
                outcome="imported",
                activities_written=1,
                records_written=len(activity.records),
                metadata_associated=associated,
            )
    except (OSError, sqlite3.Error) as exc:
        raise StorageError("FIT artifact persistence failed") from exc


def _associate_metadata(
    connection: sqlite3.Connection,
    activity_id: str,
    metadata: HistoricalMetadata | None,
    now: str,
) -> bool:
    if metadata is None:
        return False
    identity = metadata.external_id or metadata.fit_relative_path
    source_id = "strava-csv:" + hashlib.sha256(identity.encode()).hexdigest()
    connection.execute(
        """INSERT INTO activity_sources (
               id, activity_id, source_type, external_id, relative_path,
               raw_sha256, content_sha256, completeness, parse_status,
               error_code, imported_at
           ) VALUES (?, ?, 'strava_csv', ?, ?, NULL, NULL, 'summary_only',
                     'imported', NULL, ?)
           ON CONFLICT(source_type, external_id) DO UPDATE SET
               activity_id = excluded.activity_id,
               relative_path = excluded.relative_path,
               imported_at = excluded.imported_at""",
        (source_id, activity_id, identity, metadata.fit_relative_path, now),
    )
    connection.execute(
        """UPDATE activities
           SET name = COALESCE(?, name),
               description = COALESCE(?, description),
               activity_type = COALESCE(?, activity_type),
               updated_at = ?
           WHERE id = ?""",
        (metadata.name, metadata.description, metadata.activity_type, now, activity_id),
    )
    return True


def record_fit_failure(
    path: Path,
    *,
    source_type: str,
    relative_path: str,
    error_code: str,
    raw_sha256: str | None = None,
    content_sha256: str | None = None,
) -> FitWriteResult:
    """Record one failed source artifact without exposing a partial activity.

    Args:
        path: Initialized SQLite database path.
        source_type: `fit` or `fit_gz`.
        relative_path: Archive-relative source path.
        error_code: Privacy-safe failure classification.
        raw_sha256: Raw artifact digest when reading succeeded.
        content_sha256: Decompressed FIT digest when decompression succeeded.

    Returns:
        A failed or duplicate outcome.

    Raises:
        StorageError: If the failure record cannot be stored atomically.
    """
    now = datetime.now(UTC).isoformat()
    identity = raw_sha256 or hashlib.sha256(relative_path.encode()).hexdigest()
    try:
        with _connect(path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """SELECT id, parse_status FROM activity_sources
                   WHERE (? IS NOT NULL AND raw_sha256 = ?)
                      OR (? IS NOT NULL AND content_sha256 = ?)
                   LIMIT 1""",
                (raw_sha256, raw_sha256, content_sha256, content_sha256),
            ).fetchone()
            if existing and existing[1] != "failed":
                connection.rollback()
                return FitWriteResult(outcome="duplicate")
            if existing:
                connection.execute(
                    """UPDATE activity_sources
                       SET error_code = ?, imported_at = ?, relative_path = ?
                       WHERE id = ?""",
                    (error_code, now, relative_path, existing[0]),
                )
            else:
                connection.execute(
                    """INSERT INTO activity_sources (
                           id, activity_id, source_type, external_id, relative_path,
                           raw_sha256, content_sha256, completeness, parse_status,
                           error_code, imported_at
                       ) VALUES (?, NULL, ?, ?, ?, ?, ?, 'failed', 'failed', ?, ?)""",
                    (
                        f"fit-failure:{identity}",
                        source_type,
                        identity,
                        relative_path,
                        raw_sha256,
                        content_sha256,
                        error_code,
                        now,
                    ),
                )
            connection.commit()
            return FitWriteResult(outcome="failed")
    except (OSError, sqlite3.Error) as exc:
        raise StorageError("FIT failure persistence failed") from exc


def get_intervals_sync_state(path: Path) -> SyncState:
    """Read the Intervals.icu cursor without changing database state."""
    try:
        with _connect(path) as connection:
            row = connection.execute(
                "SELECT last_activity_date, overlap_days FROM sync_state WHERE source = 'intervals'"
            ).fetchone()
        if row is None:
            return SyncState(last_activity_date=None)
        return SyncState(
            last_activity_date=date.fromisoformat(row[0]) if row[0] else None,
            overlap_days=int(row[1]),
        )
    except (OSError, sqlite3.Error, ValueError, TypeError) as exc:
        raise StorageError("sync state inspection failed") from exc


def mark_intervals_sync_running(path: Path) -> None:
    """Record the start of an Intervals.icu attempt without advancing its cursor."""
    _set_intervals_sync_status(path, "running", None)


def mark_intervals_sync_failed(path: Path, error_code: str) -> None:
    """Record a safe failure classification without advancing the cursor."""
    _set_intervals_sync_status(path, "failed", error_code)


def _set_intervals_sync_status(path: Path, status: str, error_code: str | None) -> None:
    now = datetime.now(UTC).isoformat()
    try:
        with _connect(path) as connection:
            connection.execute(
                """INSERT INTO sync_state (
                       source, status, last_error_code, updated_at
                   ) VALUES ('intervals', ?, ?, ?)
                   ON CONFLICT(source) DO UPDATE SET
                       status = excluded.status,
                       last_error_code = excluded.last_error_code,
                       updated_at = excluded.updated_at""",
                (status, error_code, now),
            )
    except (OSError, sqlite3.Error) as exc:
        raise StorageError("sync state update failed") from exc


def store_intervals_activities(
    path: Path,
    activities: tuple[NormalizedIntervalsActivity, ...],
    *,
    synced_through: date,
) -> IntervalsWriteResult:
    """Upsert one provider batch and advance its cursor in a single transaction.

    Args:
        path: Initialized SQLite database path.
        activities: Validated provider summaries with stable source identities.
        synced_through: Inclusive date through which retrieval succeeded.

    Returns:
        Inserted and updated activity counts.

    Raises:
        StorageError: If any write fails; the batch and cursor are rolled back together.
    """
    now = datetime.now(UTC).isoformat()
    inserted = updated = 0
    try:
        with _connect(path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            for normalized in activities:
                activity = normalized.activity
                existed = connection.execute(
                    "SELECT 1 FROM activities WHERE id = ?", (activity.activity_id,)
                ).fetchone()
                connection.execute(
                    """INSERT INTO activities (
                           id, activity_type, name, description, started_at_utc,
                           timezone_offset_minutes, elapsed_seconds, moving_seconds,
                           distance_m, elevation_gain_m, average_power_w,
                           normalized_power_w, average_heart_rate_bpm, power_origin,
                           quality_status, created_at, updated_at
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET
                           activity_type = excluded.activity_type,
                           name = excluded.name,
                           description = excluded.description,
                           started_at_utc = excluded.started_at_utc,
                           timezone_offset_minutes = excluded.timezone_offset_minutes,
                           elapsed_seconds = excluded.elapsed_seconds,
                           moving_seconds = excluded.moving_seconds,
                           distance_m = excluded.distance_m,
                           elevation_gain_m = excluded.elevation_gain_m,
                           average_power_w = excluded.average_power_w,
                           normalized_power_w = excluded.normalized_power_w,
                           average_heart_rate_bpm = excluded.average_heart_rate_bpm,
                           power_origin = excluded.power_origin,
                           quality_status = excluded.quality_status,
                           updated_at = excluded.updated_at""",
                    (
                        activity.activity_id,
                        activity.activity_type,
                        activity.name,
                        activity.description,
                        activity.started_at_utc.isoformat(),
                        activity.timezone_offset_minutes,
                        activity.elapsed_seconds,
                        activity.moving_seconds,
                        activity.distance_m,
                        activity.elevation_gain_m,
                        activity.average_power_w,
                        activity.normalized_power_w,
                        activity.average_heart_rate_bpm,
                        activity.power_origin,
                        activity.quality_status,
                        now,
                        now,
                    ),
                )
                source_id = "intervals:" + hashlib.sha256(
                    normalized.external_id.encode()
                ).hexdigest()
                connection.execute(
                    """INSERT INTO activity_sources (
                           id, activity_id, source_type, external_id, relative_path,
                           raw_sha256, content_sha256, completeness, parse_status,
                           error_code, imported_at
                       ) VALUES (?, ?, 'intervals', ?, NULL, NULL, NULL,
                                 'summary_only', 'imported', NULL, ?)
                       ON CONFLICT(source_type, external_id) DO UPDATE SET
                           activity_id = excluded.activity_id,
                           completeness = excluded.completeness,
                           parse_status = excluded.parse_status,
                           error_code = NULL,
                           imported_at = excluded.imported_at""",
                    (source_id, activity.activity_id, normalized.external_id, now),
                )
                if existed:
                    updated += 1
                else:
                    inserted += 1
            connection.execute(
                """INSERT INTO sync_state (
                       source, last_successful_at, last_activity_date, status,
                       last_error_code, updated_at
                   ) VALUES ('intervals', ?, ?, 'succeeded', NULL, ?)
                   ON CONFLICT(source) DO UPDATE SET
                       last_successful_at = excluded.last_successful_at,
                       last_activity_date = MAX(
                           COALESCE(
                               sync_state.last_activity_date, excluded.last_activity_date
                           ),
                           excluded.last_activity_date
                       ),
                       status = excluded.status,
                       last_error_code = NULL,
                       updated_at = excluded.updated_at""",
                (now, synced_through.isoformat(), now),
            )
            connection.commit()
        return IntervalsWriteResult(inserted=inserted, updated=updated)
    except (OSError, sqlite3.Error) as exc:
        raise StorageError("Intervals.icu persistence failed") from exc
