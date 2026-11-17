"""Read-only external provider integrations."""

from endurance_coach.integrations.intervals import (
    IntervalsActivity,
    IntervalsClient,
    IntervalsError,
    NormalizedIntervalsActivity,
    normalize_intervals_activity,
)

__all__ = [
    "IntervalsActivity",
    "IntervalsClient",
    "IntervalsError",
    "NormalizedIntervalsActivity",
    "normalize_intervals_activity",
]
