"""Read FIT and FIT.GZ artifacts into provider-neutral activity contracts."""

from __future__ import annotations

import gzip
import hashlib
import io
import os
import warnings
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import fitdecode

from endurance_coach.domain import ImportedActivity, ImportedRecord

_READ_CHUNK_SIZE = 1024 * 1024
_FIT_SUFFIXES = (".fit", ".fit.gz")


class FitIngestionError(ValueError):
    """Describe one artifact failure using a privacy-safe error code."""

    def __init__(
        self,
        code: str,
        *,
        source_type: str | None = None,
        raw_sha256: str | None = None,
        content_sha256: str | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.source_type = source_type
        self.raw_sha256 = raw_sha256
        self.content_sha256 = content_sha256


@dataclass(frozen=True)
class FitArtifact:
    """A decoded source artifact and the normalized activity it contains."""

    source_type: str
    relative_path: str
    raw_sha256: str
    content_sha256: str
    activity: ImportedActivity


@dataclass(frozen=True)
class _Session:
    """Decoded FIT session summary used to normalize a multi-session file."""

    start: datetime | None
    end: datetime | None
    sport: str | None
    elapsed_seconds: float | None
    timer_seconds: float | None
    distance_m: float | None
    elevation_gain_m: float | None
    average_power_w: float | None
    normalized_power_w: float | None
    average_heart_rate_bpm: float | None


def discover_fit_files(root: Path) -> list[Path]:
    """Recursively discover FIT inputs without escaping through symlinks.

    Args:
        root: Configured archive directory.

    Returns:
        Sorted resolved paths for `.fit` and `.fit.gz` files inside the root.

    Raises:
        FitIngestionError: If the archive root is missing or not a directory.
    """
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as exc:
        raise FitIngestionError("archive_unavailable") from exc
    if not resolved_root.is_dir():
        raise FitIngestionError("archive_unavailable")

    discovered: list[Path] = []
    for directory, directory_names, file_names in os.walk(
        resolved_root, followlinks=False
    ):
        directory_names[:] = sorted(directory_names)
        for file_name in sorted(file_names):
            if not file_name.lower().endswith(_FIT_SUFFIXES):
                continue
            candidate = Path(directory, file_name)
            try:
                resolved = candidate.resolve(strict=True)
                resolved.relative_to(resolved_root)
            except (OSError, ValueError):
                continue
            if resolved.is_file():
                discovered.append(resolved)
    return sorted(set(discovered), key=lambda path: path.relative_to(resolved_root).as_posix())


def parse_fit_artifact(
    path: Path,
    root: Path,
    *,
    max_raw_bytes: int,
    max_content_bytes: int,
) -> FitArtifact:
    """Decode one FIT or FIT.GZ artifact without modifying its source.

    Args:
        path: Discovered file inside `root`.
        root: Configured archive directory used to derive a relative path.
        max_raw_bytes: Maximum compressed or plain artifact size.
        max_content_bytes: Maximum decompressed FIT payload size.

    Returns:
        Source hashes and a normalized activity.

    Raises:
        FitIngestionError: If the artifact is unsafe, oversized, corrupt, or lacks a start time.
    """
    resolved_root = root.resolve(strict=True)
    try:
        resolved_path = path.resolve(strict=True)
        relative_path = resolved_path.relative_to(resolved_root).as_posix()
    except (OSError, ValueError) as exc:
        raise FitIngestionError("unsafe_path") from exc

    raw = _read_limited(resolved_path, max_raw_bytes)
    source_type = "fit_gz" if resolved_path.name.lower().endswith(".fit.gz") else "fit"
    raw_sha256 = hashlib.sha256(raw).hexdigest()
    try:
        content = (
            _decompress_limited(raw, max_content_bytes) if source_type == "fit_gz" else raw
        )
    except FitIngestionError as exc:
        raise FitIngestionError(
            exc.code, source_type=source_type, raw_sha256=raw_sha256
        ) from exc
    if len(content) > max_content_bytes:
        raise FitIngestionError(
            "content_too_large",
            source_type=source_type,
            raw_sha256=raw_sha256,
            content_sha256=raw_sha256,
        )

    content_sha256 = hashlib.sha256(content).hexdigest()
    try:
        activity = _parse_fit_content(content, content_sha256)
    except FitIngestionError as exc:
        raise FitIngestionError(
            exc.code,
            source_type=source_type,
            raw_sha256=raw_sha256,
            content_sha256=content_sha256,
        ) from exc
    return FitArtifact(
        source_type=source_type,
        relative_path=relative_path,
        raw_sha256=raw_sha256,
        content_sha256=content_sha256,
        activity=activity,
    )


def _read_limited(path: Path, limit: int) -> bytes:
    if limit <= 0:
        raise FitIngestionError("invalid_size_limit")
    try:
        if path.stat().st_size > limit:
            raise FitIngestionError("artifact_too_large")
        with path.open("rb") as source:
            data = source.read(limit + 1)
    except FitIngestionError:
        raise
    except OSError as exc:
        raise FitIngestionError("artifact_unreadable") from exc
    if len(data) > limit:
        raise FitIngestionError("artifact_too_large")
    return data


def _decompress_limited(raw: bytes, limit: int) -> bytes:
    if limit <= 0:
        raise FitIngestionError("invalid_size_limit")
    result = bytearray()
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as source:
            while chunk := source.read(min(_READ_CHUNK_SIZE, limit + 1 - len(result))):
                result.extend(chunk)
                if len(result) > limit:
                    raise FitIngestionError("content_too_large")
    except FitIngestionError:
        raise
    except (EOFError, OSError) as exc:
        raise FitIngestionError("invalid_gzip") from exc
    return bytes(result)


def _parse_fit_content(content: bytes, content_sha256: str) -> ImportedActivity:
    sessions: list[_Session] = []
    raw_records: list[dict[str, Any]] = []
    file_created_at: datetime | None = None
    activity_sport: str | None = None
    activity_name: str | None = None

    try:
        with warnings.catch_warnings(record=True) as parse_warnings:
            warnings.simplefilter("always", UserWarning)
            with fitdecode.FitReader(
                io.BytesIO(content),
                check_crc=fitdecode.CrcCheck.RAISE,
                error_handling=fitdecode.ErrorHandling.WARN,
            ) as reader:
                for frame in reader:
                    if frame.frame_type != fitdecode.FIT_FRAME_DATA:
                        continue
                    if frame.name == "file_id":
                        file_created_at = _utc(_value(frame, "time_created"))
                    elif frame.name == "activity":
                        activity_sport = _text(_value(frame, "sport")) or activity_sport
                        activity_name = _text(_value(frame, "name")) or activity_name
                    elif frame.name == "session":
                        sessions.append(_decode_session(frame))
                    elif frame.name == "record":
                        raw_records.append(_decode_record(frame))
                    elif frame.name in {"lap", "event", "device_info"}:
                        # FitReader validates these supported messages. Their fields are not
                        # persisted until the schema has a product use for them.
                        continue
    except FitIngestionError:
        raise
    except Exception as exc:
        raise FitIngestionError("invalid_fit") from exc

    sessions.sort(key=lambda item: item.start or datetime.max.replace(tzinfo=UTC))
    records = _assign_records(raw_records, sessions)
    record_times = [record.timestamp_utc for record in records if record.timestamp_utc]
    started_at = next(
        (session.start for session in sessions if session.start is not None),
        min(record_times) if record_times else file_created_at,
    )
    if started_at is None:
        raise FitIngestionError("missing_start_time")

    session_sport = next((session.sport for session in sessions if session.sport), None)
    activity_type = activity_sport or session_sport or "unknown"
    average_power = _weighted_session_average(sessions, "average_power_w")
    normalized_power = _weighted_session_average(sessions, "normalized_power_w")
    average_heart_rate = _weighted_session_average(
        sessions, "average_heart_rate_bpm"
    )
    if average_power is None:
        average_power = _record_average(records, "power_w")
    if average_heart_rate is None:
        average_heart_rate = _record_average(records, "heart_rate_bpm")
    has_power = any(record.power_w is not None for record in records)
    power_origin = "measured" if has_power or average_power is not None else "unavailable"

    return ImportedActivity(
        activity_id=f"fit:{content_sha256}",
        activity_type=activity_type,
        started_at_utc=started_at,
        records=records,
        name=activity_name,
        elapsed_seconds=_sum_present(sessions, "elapsed_seconds"),
        moving_seconds=_sum_present(sessions, "timer_seconds"),
        distance_m=_sum_present(sessions, "distance_m"),
        elevation_gain_m=_sum_present(sessions, "elevation_gain_m"),
        average_power_w=average_power,
        normalized_power_w=normalized_power,
        average_heart_rate_bpm=average_heart_rate,
        power_origin=power_origin,
        quality_status=(
            "complete" if sessions and records and not parse_warnings else "partial"
        ),
    )


def _decode_session(message: Any) -> _Session:
    start = _utc(_value(message, "start_time"))
    end = _utc(_value(message, "timestamp"))
    return _Session(
        start=start,
        end=end,
        sport=_text(_value(message, "sport")),
        elapsed_seconds=_number(_value(message, "total_elapsed_time")),
        timer_seconds=_number(_value(message, "total_timer_time")),
        distance_m=_number(_value(message, "total_distance")),
        elevation_gain_m=_number(_value(message, "total_ascent")),
        average_power_w=_number(_value(message, "avg_power")),
        normalized_power_w=_number(_value(message, "normalized_power")),
        average_heart_rate_bpm=_number(_value(message, "avg_heart_rate")),
    )


def _decode_record(message: Any) -> dict[str, Any]:
    latitude = _coordinate(_value(message, "position_lat"), 90)
    longitude = _coordinate(_value(message, "position_long"), 180)
    power = _nonnegative(_value(message, "power"))
    return {
        "timestamp_utc": _utc(_value(message, "timestamp")),
        "power_w": power,
        "power_origin": "measured" if power is not None else None,
        "heart_rate_bpm": _positive(_value(message, "heart_rate")),
        "cadence_rpm": _nonnegative(_value(message, "cadence")),
        "speed_mps": _nonnegative(
            _value(message, "enhanced_speed", _value(message, "speed"))
        ),
        "distance_m": _nonnegative(_value(message, "distance")),
        "altitude_m": _number(
            _value(message, "enhanced_altitude", _value(message, "altitude"))
        ),
        "temperature_c": _number(_value(message, "temperature")),
        "latitude": latitude,
        "longitude": longitude,
        "left_right_balance_pct": _percentage(_value(message, "left_right_balance")),
    }


def _assign_records(
    raw_records: list[dict[str, Any]], sessions: list[_Session]
) -> tuple[ImportedRecord, ...]:
    grouped_counts: dict[int, int] = {}
    result: list[ImportedRecord] = []
    activity_start = next((session.start for session in sessions if session.start), None)
    for raw in raw_records:
        timestamp = raw["timestamp_utc"]
        session_index = _session_for_timestamp(timestamp, sessions)
        record_index = grouped_counts.get(session_index, 0)
        grouped_counts[session_index] = record_index + 1
        session_start = sessions[session_index].start if sessions else activity_start
        elapsed = None
        if timestamp is not None and session_start is not None:
            elapsed = max(0.0, (timestamp - session_start).total_seconds())
        result.append(
            ImportedRecord(
                session_index=session_index,
                record_index=record_index,
                elapsed_seconds=elapsed,
                **raw,
            )
        )
    return tuple(result)


def _session_for_timestamp(timestamp: datetime | None, sessions: list[_Session]) -> int:
    if not sessions or timestamp is None:
        return 0
    for index, session in enumerate(sessions):
        if session.start is None:
            continue
        if session.end is None and timestamp >= session.start:
            return index
        if session.end is not None and session.start <= timestamp <= session.end:
            return index
    starts = [
        (index, session.start) for index, session in enumerate(sessions) if session.start
    ]
    if not starts:
        return 0
    return min(starts, key=lambda item: abs((timestamp - item[1]).total_seconds()))[0]


def _value(message: Any, name: str, fallback: Any = None) -> Any:
    return message.get_value(name, fallback=fallback)


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if number == number else None


def _nonnegative(value: Any) -> float | None:
    number = _number(value)
    return number if number is not None and number >= 0 else None


def _positive(value: Any) -> float | None:
    number = _number(value)
    return number if number is not None and number > 0 else None


def _percentage(value: Any) -> float | None:
    number = _number(value)
    return number if number is not None and 0 <= number <= 100 else None


def _coordinate(value: Any, bound: float) -> float | None:
    number = _number(value)
    if number is None:
        return None
    if abs(number) > bound:
        number *= 180.0 / (2**31)
    return number if -bound <= number <= bound else None


def _sum_present(sessions: list[_Session], field: str) -> float | None:
    values = [getattr(session, field) for session in sessions]
    present = [value for value in values if value is not None]
    return sum(present) if present else None


def _weighted_session_average(sessions: list[_Session], field: str) -> float | None:
    weighted: list[tuple[float, float]] = []
    for session in sessions:
        value = getattr(session, field)
        weight = session.timer_seconds or session.elapsed_seconds
        if value is not None and weight is not None and weight > 0:
            weighted.append((value, weight))
    if weighted:
        return sum(value * weight for value, weight in weighted) / sum(
            weight for _, weight in weighted
        )
    values = [getattr(session, field) for session in sessions]
    present = [value for value in values if value is not None]
    return sum(present) / len(present) if present else None


def _record_average(records: tuple[ImportedRecord, ...], field: str) -> float | None:
    values = [getattr(record, field) for record in records]
    present = [value for value in values if value is not None]
    return sum(present) / len(present) if present else None
