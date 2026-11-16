"""Read-only external provider integrations."""

from endurance_coach.integrations.intervals import (
    IntervalsActivity,
    IntervalsClient,
    IntervalsError,
)

__all__ = ["IntervalsActivity", "IntervalsClient", "IntervalsError"]
