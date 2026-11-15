"""Provider-neutral contracts for historical activity imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ImportedRecord:
    """One recorded sensor sample, preserving its original session and order."""

    session_index: int
    record_index: int
    timestamp_utc: datetime | None = None
    elapsed_seconds: float | None = None
    timer_seconds: float | None = None
    power_w: float | None = None
    power_origin: str | None = None
    heart_rate_bpm: float | None = None
    cadence_rpm: float | None = None
    speed_mps: float | None = None
    distance_m: float | None = None
    altitude_m: float | None = None
    temperature_c: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    left_right_balance_pct: float | None = None


@dataclass(frozen=True)
class ImportedActivity:
    """Normalized activity summary and sensor records ready for persistence."""

    activity_id: str
    activity_type: str
    started_at_utc: datetime
    records: tuple[ImportedRecord, ...]
    name: str | None = None
    description: str | None = None
    timezone_offset_minutes: int | None = None
    elapsed_seconds: float | None = None
    moving_seconds: float | None = None
    distance_m: float | None = None
    elevation_gain_m: float | None = None
    average_power_w: float | None = None
    normalized_power_w: float | None = None
    average_heart_rate_bpm: float | None = None
    power_origin: str = "unavailable"
    quality_status: str = "partial"
