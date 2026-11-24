"""Domain contracts shared by ingestion and persistence."""

from endurance_coach.domain.imports import ImportedActivity, ImportedRecord
from endurance_coach.domain.reconciliation import (
    ActivityMatchCandidate,
    select_activity_match,
)

__all__ = [
    "ActivityMatchCandidate",
    "ImportedActivity",
    "ImportedRecord",
    "select_activity_match",
]
