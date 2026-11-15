"""Coordinate safe historical FIT ingestion and SQLite persistence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from endurance_coach.ingestion import (
    FitIngestionError,
    discover_fit_files,
    parse_fit_artifact,
)
from endurance_coach.storage import (
    initialize_database,
    record_fit_failure,
    store_fit_artifact,
)


@dataclass(frozen=True)
class ImportSummary:
    """Privacy-safe aggregate result for one archive import."""

    discovered: int
    validated: int
    imported: int
    duplicates: int
    failed: int
    activities_written: int
    records_written: int
    dry_run: bool

    def as_dict(self) -> dict[str, int | bool]:
        """Return JSON-safe aggregate counts without paths or measurements."""
        return asdict(self)


def import_fit_archive(
    archive_root: Path,
    database_path: Path,
    *,
    dry_run: bool = False,
    max_raw_bytes: int = 128 * 1024 * 1024,
    max_content_bytes: int = 1024 * 1024 * 1024,
) -> ImportSummary:
    """Import every FIT and FIT.GZ artifact found under an archive root.

    Each source file is parsed independently and committed in its own transaction. Parse failures
    do not stop later files. Dry-run mode performs discovery and parsing without opening or changing
    the application database.

    Args:
        archive_root: Root directory containing historical activity files.
        database_path: Local SQLite database populated when `dry_run` is false.
        dry_run: Validate inputs without changing the database.
        max_raw_bytes: Per-artifact compressed or plain size limit.
        max_content_bytes: Per-artifact decompressed payload limit.

    Returns:
        Aggregate counts safe for CLI output.
    """
    files = discover_fit_files(archive_root)
    if not dry_run:
        initialize_database(database_path)

    validated = imported = duplicates = failed = activities = records = 0
    resolved_root = archive_root.resolve(strict=True)
    for path in files:
        relative_path = path.relative_to(resolved_root).as_posix()
        source_type = "fit_gz" if path.name.lower().endswith(".fit.gz") else "fit"
        try:
            artifact = parse_fit_artifact(
                path,
                resolved_root,
                max_raw_bytes=max_raw_bytes,
                max_content_bytes=max_content_bytes,
            )
            validated += 1
        except FitIngestionError as exc:
            failed += 1
            if not dry_run:
                result = record_fit_failure(
                    database_path,
                    source_type=exc.source_type or source_type,
                    relative_path=relative_path,
                    error_code=exc.code,
                    raw_sha256=exc.raw_sha256,
                    content_sha256=exc.content_sha256,
                )
                if result.outcome == "duplicate":
                    failed -= 1
                    duplicates += 1
            continue

        if dry_run:
            continue
        result = store_fit_artifact(database_path, artifact)
        if result.outcome == "duplicate":
            duplicates += 1
        else:
            imported += 1
            activities += result.activities_written
            records += result.records_written

    return ImportSummary(
        discovered=len(files),
        validated=validated,
        imported=imported,
        duplicates=duplicates,
        failed=failed,
        activities_written=activities,
        records_written=records,
        dry_run=dry_run,
    )
