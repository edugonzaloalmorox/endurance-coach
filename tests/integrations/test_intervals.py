"""Tests for bounded, read-only Intervals.icu retrieval."""

from __future__ import annotations

import base64
import io
import json
from collections.abc import Callable
from datetime import date
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from endurance_coach.config import IntervalsSettings
from endurance_coach.integrations import IntervalsClient, IntervalsError


def _opener(
    payloads: list[object], calls: list[tuple[Request, float]]
) -> Callable[[Request, float], io.BytesIO]:
    encoded = iter(json.dumps(payload).encode() for payload in payloads)

    def open_request(request: Request, timeout: float) -> io.BytesIO:
        calls.append((request, timeout))
        return io.BytesIO(next(encoded))

    return open_request


def test_list_activities_uses_read_only_auth_and_bounded_windows() -> None:
    calls: list[tuple[Request, float]] = []
    client = IntervalsClient(
        IntervalsSettings(
            api_key="synthetic-secret",
            athlete_id="i123",
            request_window_days=2,
        ),
        open_request=_opener(
            [
                [{"id": "i1", "type": "Ride"}, {"id": "i2", "type": "Ride"}],
                [{"id": "i2", "type": "Ride"}, {"id": "i3", "type": "Run"}],
            ],
            calls,
        ),
    )

    result = client.list_activities(date(2026, 1, 1), date(2026, 1, 3))

    assert [activity.external_id for activity in result] == ["i1", "i2", "i3"]
    assert [request.method for request, _ in calls] == ["GET", "GET"]
    assert calls[0][0].full_url.endswith(
        "/api/v1/athlete/i123/activities?oldest=2026-01-01&newest=2026-01-02"
    )
    assert calls[1][0].full_url.endswith(
        "/api/v1/athlete/i123/activities?oldest=2026-01-03&newest=2026-01-03"
    )
    authorization = calls[0][0].get_header("Authorization")
    assert authorization is not None
    assert base64.b64decode(authorization.removeprefix("Basic ")).decode() == (
        "API_KEY:synthetic-secret"
    )
    assert [timeout for _, timeout in calls] == [20.0, 20.0]


@pytest.mark.parametrize(
    "payload",
    [
        {"id": "not-a-list"},
        ["not-an-object"],
        [{"type": "Ride"}],
    ],
)
def test_list_activities_rejects_malformed_provider_data(payload: object) -> None:
    client = IntervalsClient(
        IntervalsSettings(api_key="synthetic-secret"),
        open_request=_opener([payload], []),
    )

    with pytest.raises(IntervalsError, match="invalid|missing"):
        client.list_activities(date(2026, 1, 1), date(2026, 1, 1))


def test_list_activities_reports_http_status_without_response_or_secret() -> None:
    def fail(_request: Request, _timeout: float) -> io.BytesIO:
        raise HTTPError(
            "https://intervals.icu/private",
            401,
            "body contains synthetic-secret",
            {},
            None,
        )

    client = IntervalsClient(
        IntervalsSettings(api_key="synthetic-secret"), open_request=fail
    )

    with pytest.raises(IntervalsError, match="HTTP 401") as error:
        client.list_activities(date(2026, 1, 1), date(2026, 1, 1))
    assert "synthetic-secret" not in str(error.value)


def test_list_activities_rejects_reversed_range_before_network_access() -> None:
    client = IntervalsClient(
        IntervalsSettings(api_key="synthetic-secret"),
        open_request=lambda _request, _timeout: pytest.fail("unexpected HTTP request"),
    )

    with pytest.raises(IntervalsError, match="invalid date range"):
        client.list_activities(date(2026, 1, 2), date(2026, 1, 1))


def test_settings_require_api_key_without_disclosing_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("INTERVALS_ICU_API_KEY", raising=False)

    with pytest.raises(ValueError, match="INTERVALS_ICU_API_KEY is required"):
        IntervalsSettings.from_env()
