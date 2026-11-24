"""Tests for deterministic cross-source activity matching."""

from datetime import UTC, datetime, timedelta

from endurance_coach.domain import (
    ActivityMatchCandidate,
    ImportedActivity,
    select_activity_match,
)

_START = datetime(2026, 11, 12, 8, 0, tzinfo=UTC)


def _activity(*, elapsed_seconds: float | None = 3600) -> ImportedActivity:
    return ImportedActivity(
        activity_id="intervals:i1",
        activity_type="ride",
        started_at_utc=_START,
        elapsed_seconds=elapsed_seconds,
        records=(),
    )


def _candidate(
    activity_id: str,
    *,
    start_offset_seconds: int = 0,
    elapsed_seconds: float | None = 3600,
    external_ids: tuple[str, ...] = (),
) -> ActivityMatchCandidate:
    return ActivityMatchCandidate(
        activity_id=activity_id,
        started_at_utc=_START + timedelta(seconds=start_offset_seconds),
        elapsed_seconds=elapsed_seconds,
        moving_seconds=None,
        source_external_ids=external_ids,
    )


def test_shared_external_identity_is_an_exact_match() -> None:
    candidate = _candidate(
        "fit:exact",
        start_offset_seconds=3600,
        elapsed_seconds=7200,
        external_ids=("i1",),
    )

    assert select_activity_match(_activity(), "i1", (candidate,)) == "fit:exact"


def test_close_timestamp_and_compatible_duration_match() -> None:
    candidate = _candidate(
        "fit:close", start_offset_seconds=90, elapsed_seconds=3700
    )

    assert select_activity_match(_activity(), "i1", (candidate,)) == "fit:close"


def test_differing_duration_does_not_match() -> None:
    candidate = _candidate(
        "fit:different", start_offset_seconds=30, elapsed_seconds=5400
    )

    assert select_activity_match(_activity(), "i1", (candidate,)) is None


def test_multiple_plausible_candidates_are_left_ambiguous() -> None:
    candidates = (
        _candidate("fit:before", start_offset_seconds=-60),
        _candidate("fit:after", start_offset_seconds=60),
    )

    assert select_activity_match(_activity(), "i1", candidates) is None


def test_missing_duration_requires_an_effectively_exact_start() -> None:
    exact = _candidate("fit:exact-time", elapsed_seconds=None)
    close = _candidate(
        "fit:close-time", start_offset_seconds=30, elapsed_seconds=None
    )

    assert select_activity_match(_activity(elapsed_seconds=None), "i1", (exact,)) == (
        "fit:exact-time"
    )
    assert select_activity_match(_activity(elapsed_seconds=None), "i1", (close,)) is None
