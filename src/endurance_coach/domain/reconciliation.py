"""Deterministic activity matching without provider or persistence dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from endurance_coach.domain.imports import ImportedActivity

_START_TOLERANCE_SECONDS = 5 * 60
_EXACT_START_TOLERANCE_SECONDS = 1
_DURATION_TOLERANCE_SECONDS = 2 * 60
_DURATION_TOLERANCE_RATIO = 0.05


@dataclass(frozen=True)
class ActivityMatchCandidate:
    """Existing logical activity considered for source reconciliation."""

    activity_id: str
    started_at_utc: datetime
    elapsed_seconds: float | None
    moving_seconds: float | None
    source_external_ids: tuple[str, ...] = ()


def select_activity_match(
    activity: ImportedActivity,
    source_external_id: str,
    candidates: tuple[ActivityMatchCandidate, ...],
) -> str | None:
    """Return one unambiguous matching activity ID, otherwise ``None``.

    A shared external source identity is definitive only when it resolves to one logical
    activity. Otherwise, start times must be close and available durations must agree within two
    minutes or five percent. When either duration is unavailable, timestamps must be effectively
    exact. Multiple plausible candidates are deliberately left unresolved.

    Args:
        activity: Incoming normalized activity.
        source_external_id: Stable identity supplied by its provider.
        candidates: Existing activities without the incoming primary source.

    Returns:
        The sole deterministic match, or ``None`` for no match or ambiguity.
    """
    exact_ids = {
        candidate.activity_id
        for candidate in candidates
        if source_external_id in candidate.source_external_ids
    }
    if exact_ids:
        return next(iter(exact_ids)) if len(exact_ids) == 1 else None

    matches = {
        candidate.activity_id
        for candidate in candidates
        if _timestamps_and_durations_match(activity, candidate)
    }
    return next(iter(matches)) if len(matches) == 1 else None


def _timestamps_and_durations_match(
    activity: ImportedActivity,
    candidate: ActivityMatchCandidate,
) -> bool:
    start_difference = abs(
        (activity.started_at_utc - candidate.started_at_utc).total_seconds()
    )
    if start_difference > _START_TOLERANCE_SECONDS:
        return False

    incoming_durations = _durations(activity.elapsed_seconds, activity.moving_seconds)
    candidate_durations = _durations(
        candidate.elapsed_seconds, candidate.moving_seconds
    )
    if not incoming_durations or not candidate_durations:
        return start_difference <= _EXACT_START_TOLERANCE_SECONDS

    return any(
        abs(incoming - existing)
        <= max(
            _DURATION_TOLERANCE_SECONDS,
            max(incoming, existing) * _DURATION_TOLERANCE_RATIO,
        )
        for incoming in incoming_durations
        for existing in candidate_durations
    )


def _durations(elapsed: float | None, moving: float | None) -> tuple[float, ...]:
    return tuple(value for value in (elapsed, moving) if value is not None)
