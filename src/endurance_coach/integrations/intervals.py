"""Bounded, read-only access to Intervals.icu activity summaries."""

from __future__ import annotations

import base64
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from types import TracebackType
from typing import Any, Protocol, Self
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from endurance_coach.config import IntervalsSettings


class IntervalsError(RuntimeError):
    """Report an Intervals.icu failure without leaking credentials or response bodies."""


@dataclass(frozen=True)
class IntervalsActivity:
    """One provider activity summary with its raw, unmodified response fields."""

    external_id: str
    raw: Mapping[str, Any]


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
