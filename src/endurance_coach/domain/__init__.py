"""Domain contracts shared by ingestion and persistence."""

from endurance_coach.domain.imports import ImportedActivity, ImportedRecord
from endurance_coach.domain.reconciliation import (
    ActivityMatchCandidate,
    select_activity_match,
)
from endurance_coach.domain.wellness import WellnessObservation

__all__ = [
    "ActivityMatchCandidate",
    "ImportedActivity",
    "ImportedRecord",
    "WellnessObservation",
    "select_activity_match",
]
