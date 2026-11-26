"""Read-only external provider integrations."""

from endurance_coach.integrations.coros import (
    CorosClient,
    CorosDiscovery,
    CorosError,
    CorosRecoverySnapshot,
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
    "IntervalsActivity",
    "IntervalsClient",
    "IntervalsError",
    "NormalizedIntervalsActivity",
    "normalize_intervals_activity",
]
