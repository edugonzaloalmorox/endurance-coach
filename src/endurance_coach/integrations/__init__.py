"""Read-only external provider integrations."""

from endurance_coach.integrations.coros import (
    CorosClient,
    CorosDiscovery,
    CorosError,
    CorosRecoverySnapshot,
    normalize_coros_wellness,
)
from endurance_coach.integrations.intervals import (
    IntervalsActivity,
    IntervalsClient,
    IntervalsError,
    NormalizedIntervalsActivity,
    normalize_intervals_activity,
)

__all__ = [
    "CorosClient",
    "CorosDiscovery",
    "CorosError",
    "CorosRecoverySnapshot",
    "normalize_coros_wellness",
    "IntervalsActivity",
    "IntervalsClient",
    "IntervalsError",
    "NormalizedIntervalsActivity",
    "normalize_intervals_activity",
]
