from datetime import date

import pytest
from pydantic import ValidationError

from endurance_coach.models import WorkoutRecommendation
from endurance_coach.runtime import AgentRuntime


def valid_recommendation() -> dict:
    return {
        "workout_date": date(2026, 11, 4),
        "title": "Easy aerobic spin",
        "ride_kind": "recovery",
        "duration_minutes": 45,
        "rationale": "Recover from Sunday's long ride before adding intensity.",
        "steps": [
            {"name": "Warm up", "duration_minutes": 10, "intensity": "RPE 1-2"},
            {"name": "Easy spin", "duration_minutes": 30, "intensity": "RPE 2"},
            {"name": "Cool down", "duration_minutes": 5, "intensity": "Very easy"},
        ],
        "warnings": [],
        "source_skill": "plan-workout",
    }


def test_runtime_validates_structured_output():
    result = AgentRuntime.validate_output(valid_recommendation())
    assert isinstance(result, WorkoutRecommendation)
    assert result.duration_minutes == 45


def test_output_validation_rejects_step_duration_mismatch():
    payload = valid_recommendation()
    payload["duration_minutes"] = 60

    with pytest.raises(ValidationError, match="step durations"):
        AgentRuntime.validate_output(payload)
