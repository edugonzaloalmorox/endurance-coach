"""Bounded, read-only access to Intervals.icu activity summaries."""

from __future__ import annotations

import base64
import json
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from types import TracebackType
from typing import Any, Protocol, Self
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from endurance_coach.config import IntervalsSettings
from endurance_coach.domain import ImportedActivity


class IntervalsError(RuntimeError):
    """Report an Intervals.icu failure without leaking credentials or response bodies."""


@dataclass(frozen=True)
class IntervalsActivity:
    """One provider activity summary with its raw, unmodified response fields."""

    external_id: str
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class NormalizedIntervalsActivity:
    """Provider identity paired with a normalized summary for persistence."""

    external_id: str
    activity: ImportedActivity


class _Response(Protocol):
    """Minimal HTTP response boundary used by the connector."""

    def read(self, size: int = -1) -> bytes: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...


_OpenRequest = Callable[[Request, float], _Response]


def _open(request: Request, timeout: float) -> _Response:
    return urlopen(request, timeout=timeout)  # noqa: S310 - fixed HTTPS origin from settings


class IntervalsClient:
    """Retrieve activity summaries using only the provider's GET endpoint."""

    def __init__(
        self,
        settings: IntervalsSettings,
        *,
        open_request: _OpenRequest = _open,
    ) -> None:
        self._settings = settings
        self._open_request = open_request

    def list_activities(self, oldest: date, newest: date) -> tuple[IntervalsActivity, ...]:
        """Return deduplicated activity summaries for an inclusive local-date range.

        Large ranges are split into bounded windows because the provider returns one JSON array
        rather than a cursor. Activity IDs make repeated provider results deterministic.

        Args:
            oldest: First athlete-local calendar date to request.
            newest: Last athlete-local calendar date to request.

        Returns:
            Activities in provider order, with duplicate IDs removed.

        Raises:
            IntervalsError: If dates, transport, status, size, or JSON shape are invalid.
        """
        if oldest > newest:
            raise IntervalsError("invalid date range")

        activities: dict[str, IntervalsActivity] = {}
        window_start = oldest
        while window_start <= newest:
            window_end = min(
                newest,
                window_start + timedelta(days=self._settings.request_window_days - 1),
            )
            for activity in self._fetch_window(window_start, window_end):
                activities.setdefault(activity.external_id, activity)
                if len(activities) > self._settings.max_activities:
                    raise IntervalsError("activity result limit exceeded")
            window_start = window_end + timedelta(days=1)
        return tuple(activities.values())

    def _fetch_window(self, oldest: date, newest: date) -> tuple[IntervalsActivity, ...]:
        query = urlencode({"oldest": oldest.isoformat(), "newest": newest.isoformat()})
        base_url = self._settings.base_url.rstrip("/")
        athlete_id = self._settings.athlete_id
        request = Request(
            f"{base_url}/api/v1/athlete/{athlete_id}/activities?{query}",
            headers={
                "Accept": "application/json",
                "Authorization": self._authorization_header(),
                "User-Agent": "endurance-coach/0.1",
            },
            method="GET",
        )
        try:
            with self._open_request(request, self._settings.timeout_seconds) as response:
                body = response.read(self._settings.max_response_bytes + 1)
        except HTTPError as exc:
            raise IntervalsError(f"Intervals.icu request failed with HTTP {exc.code}") from exc
        except (OSError, URLError, TimeoutError) as exc:
            raise IntervalsError("Intervals.icu request failed") from exc
        if len(body) > self._settings.max_response_bytes:
            raise IntervalsError("Intervals.icu response limit exceeded")

        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IntervalsError("Intervals.icu returned invalid JSON") from exc
        if not isinstance(payload, list):
            raise IntervalsError("Intervals.icu returned an invalid activity list")

        result: list[IntervalsActivity] = []
        for item in payload:
            if not isinstance(item, dict):
                raise IntervalsError("Intervals.icu returned an invalid activity")
            external_id = item.get("id")
            if not isinstance(external_id, str) or not external_id.strip():
                raise IntervalsError("Intervals.icu activity is missing an ID")
            result.append(IntervalsActivity(external_id=external_id, raw=item))
        return tuple(result)

    def _authorization_header(self) -> str:
        credentials = f"API_KEY:{self._settings.api_key.get_secret_value()}".encode()
        return "Basic " + base64.b64encode(credentials).decode("ascii")


def normalize_intervals_activity(
    source: IntervalsActivity,
) -> NormalizedIntervalsActivity:
    """Map one Intervals.icu summary to the provider-neutral activity contract.

    Summary power is derived by Intervals.icu, so it is never labelled as a directly measured
    value. Missing optional fields remain null.

    Args:
        source: Valid provider record and external identity.

    Returns:
        Provider identity and normalized summary.

    Raises:
        IntervalsError: If required fields or numeric measurements are invalid.
    """
    raw = source.raw
    started_at = _utc_datetime(raw.get("start_date"))
    activity_type = _text(raw.get("type")) or "unknown"
    average_power = _number(raw, "average_watts", "icu_average_watts")
    normalized_power = _number(
        raw, "icu_weighted_avg_watts", "weighted_average_watts"
    )
    return NormalizedIntervalsActivity(
        external_id=source.external_id,
        activity=ImportedActivity(
            activity_id=f"intervals:{source.external_id}",
            activity_type=activity_type.lower().replace(" ", "_"),
            started_at_utc=started_at,
            records=(),
            name=_text(raw.get("name")),
            description=_text(raw.get("description")),
            timezone_offset_minutes=_timezone_offset_minutes(raw, started_at),
            elapsed_seconds=_number(raw, "elapsed_time"),
            moving_seconds=_number(raw, "moving_time"),
            distance_m=_number(raw, "distance"),
            elevation_gain_m=_number(raw, "total_elevation_gain"),
            average_power_w=average_power,
            normalized_power_w=normalized_power,
            average_heart_rate_bpm=_number(
                raw, "average_heartrate", strictly_positive=True
            ),
            power_origin=(
                "derived"
                if average_power is not None or normalized_power is not None
                else "unavailable"
            ),
            quality_status="partial",
        ),
    )


def _utc_datetime(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise IntervalsError("Intervals.icu activity is missing a UTC start time")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise IntervalsError("Intervals.icu activity has an invalid UTC start time") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _timezone_offset_minutes(
    raw: Mapping[str, Any], started_at: datetime
) -> int | None:
    timezone_name = _text(raw.get("timezone"))
    if timezone_name is None:
        return None
    try:
        offset = started_at.astimezone(ZoneInfo(timezone_name)).utcoffset()
    except ZoneInfoNotFoundError as exc:
        raise IntervalsError("Intervals.icu activity has an invalid timezone") from exc
    if offset is None:
        raise IntervalsError("Intervals.icu activity has an invalid timezone")
    return int(offset.total_seconds() // 60)


def _number(
    raw: Mapping[str, Any],
    *names: str,
    strictly_positive: bool = False,
) -> float | None:
    value = next((raw[name] for name in names if raw.get(name) is not None), None)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise IntervalsError(f"Intervals.icu activity has invalid {names[0]}")
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0 or (strictly_positive and parsed <= 0):
        raise IntervalsError(f"Intervals.icu activity has invalid {names[0]}")
    return parsed


def _text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise IntervalsError("Intervals.icu activity has invalid text")
    return value.strip() or None
