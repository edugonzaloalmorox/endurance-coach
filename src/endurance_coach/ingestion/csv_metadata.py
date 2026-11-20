"""Read bounded Strava-style CSV metadata for historical FIT activities."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from endurance_coach.ingestion.fit import FitIngestionError

_MAX_CSV_BYTES = 32 * 1024 * 1024
_MAX_ROWS = 250_000
_HEADERS = {
    "external_id": ("Activity ID", "ID de actividad"),
    "name": ("Activity Name", "Nombre de la actividad"),
    "description": ("Activity Description", "Descripción de la actividad"),
    "activity_type": ("Activity Type", "Tipo de actividad"),
    "filename": ("Filename", "Nombre del archivo"),
}


@dataclass(frozen=True)
class HistoricalMetadata:
    """Complementary descriptive fields associated with one archive artifact."""

    fit_relative_path: str
    external_id: str | None = None
    name: str | None = None
    description: str | None = None
    activity_type: str | None = None


@dataclass(frozen=True)
class MetadataCatalog:
    """Valid metadata rows plus a count of independently rejected rows."""

    rows: dict[str, HistoricalMetadata]
    invalid_rows: int = 0


def read_metadata_csv(path: Path, archive_root: Path) -> MetadataCatalog:
    """Read a CSV contained in the archive and index valid rows by FIT path.

    Args:
        path: CSV file to read.
        archive_root: Archive boundary that the CSV may not escape.

    Returns:
        Valid unique metadata rows and an aggregate invalid-row count.

    Raises:
        FitIngestionError: If the CSV itself is missing, unsafe, oversized, or malformed.
    """
    try:
        root = archive_root.resolve(strict=True)
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
        if not resolved.is_file() or resolved.stat().st_size > _MAX_CSV_BYTES:
            raise FitIngestionError("metadata_unavailable")
        with resolved.open("rb") as source:
            payload = source.read(_MAX_CSV_BYTES + 1)
        if len(payload) > _MAX_CSV_BYTES:
            raise FitIngestionError("metadata_unavailable")
        text = payload.decode("utf-8-sig")
    except (OSError, UnicodeError, ValueError) as exc:
        raise FitIngestionError("metadata_unavailable") from exc

    try:
        reader = csv.DictReader(text.splitlines(), strict=True)
        fieldnames = set(reader.fieldnames or ())
        if not fieldnames.intersection(_HEADERS["filename"]):
            raise FitIngestionError("metadata_missing_filename_column")
        rows: dict[str, HistoricalMetadata] = {}
        external_ids: set[str] = set()
        invalid = 0
        for index, row in enumerate(reader, start=1):
            if index > _MAX_ROWS:
                raise FitIngestionError("metadata_too_many_rows")
            filename = (_first(row, "filename") or "").strip()
            if not filename or not filename.lower().endswith((".fit", ".fit.gz")):
                # A complete activity export can include manual activities and
                # unsupported source formats. They are not malformed FIT metadata.
                continue
            relative_path = _safe_relative_path(filename)
            external_id = _optional(_first(row, "external_id"))
            if (
                relative_path is None
                or relative_path in rows
                or (external_id is not None and external_id in external_ids)
            ):
                invalid += 1
                continue
            if external_id is not None:
                external_ids.add(external_id)
            rows[relative_path] = HistoricalMetadata(
                fit_relative_path=relative_path,
                external_id=external_id,
                name=_optional(_first(row, "name")),
                description=_optional(_first(row, "description")),
                activity_type=_normalize_activity_type(_first(row, "activity_type")),
            )
    except (csv.Error, TypeError) as exc:
        raise FitIngestionError("invalid_metadata_csv") from exc
    return MetadataCatalog(rows=rows, invalid_rows=invalid)


def _first(row: dict[str, str | None], field: str) -> str | None:
    return next((row.get(header) for header in _HEADERS[field] if row.get(header)), None)


def _safe_relative_path(value: str | None) -> str | None:
    candidate = (value or "").strip().replace("\\", "/")
    if not candidate:
        return None
    path = PurePosixPath(candidate)
    if path.is_absolute() or ".." in path.parts:
        return None
    normalized = path.as_posix().removeprefix("./")
    if not normalized.lower().endswith((".fit", ".fit.gz")):
        return None
    return normalized


def _optional(value: str | None) -> str | None:
    stripped = (value or "").strip()
    return stripped or None


def _normalize_activity_type(value: str | None) -> str | None:
    stripped = _optional(value)
    return stripped.lower().replace(" ", "_") if stripped else None
