from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from endurance_coach.models import (
    LoadedSkill,
    RecommendationEvidence,
    RecommendationUncertainty,
    SkillMetadata,
    ToolDefinition,
    ToolRequest,
    ToolResult,
    TrainingActivity,
    WorkoutRecommendation,
    WorkoutStep,
)
from endurance_coach.runtime import AgentRuntime


def valid_recommendation() -> dict:
    return {
        "workout_date": date(2026, 11, 4),
        "title": "Easy aerobic spin",
        "ride_kind": "recovery",
        "duration_minutes": 45,
        "objective": "Promote recovery while maintaining easy aerobic movement.",
        "rationale": "Recover from Sunday's long ride before adding intensity.",
        "evidence": [
            {
                "observation": "The most recent long ride lasted 210 minutes.",
                "source": "14-day training summary",
            }
        ],
        "uncertainty": {"level": "low", "reasons": []},
        "steps": [
            {"name": "Warm up", "duration_minutes": 10, "intensity": "RPE 1-2"},
            {"name": "Easy spin", "duration_minutes": 30, "intensity": "RPE 2"},
            {"name": "Cool down", "duration_minutes": 5, "intensity": "Very easy"},
        ],
        "warnings": [],
        "source_skill": "plan-workout",
    }


def valid_activity() -> dict:
    return {
        "activity_id": "local-ride-1",
        "source": "intervals_icu",
        "source_activity_id": "i-123",
        "started_at": datetime(2026, 11, 4, 7, 0, tzinfo=UTC),
        "title": "Morning endurance",
        "ride_kind": "endurance",
        "duration_minutes": 60,
        "distance_km": 28.5,
        "elevation_gain_m": 320,
        "average_power_w": 170,
        "normalized_power_w": 181,
        "average_heart_rate_bpm": 138,
        "perceived_exertion": 4,
    }


def test_runtime_validates_structured_output():
    result = AgentRuntime.validate_output(valid_recommendation())
    assert isinstance(result, WorkoutRecommendation)
    assert result.duration_minutes == 45
    assert result.ride_kind == "recovery"
    assert result.objective == "Promote recovery while maintaining easy aerobic movement."
    assert result.evidence[0].source == "14-day training summary"
    assert result.uncertainty.level == "low"
    assert '"ride_kind":"recovery"' in result.model_dump_json()


@pytest.mark.parametrize(
    "model",
    [WorkoutRecommendation, WorkoutStep, RecommendationEvidence, RecommendationUncertainty],
)
def test_recommendation_contract_fields_are_documented(model):
    properties = model.model_json_schema()["properties"]

    assert properties
    assert all(field.get("description") for field in properties.values())


def test_recommendation_duration_schema_documents_units_and_bounds():
    duration = WorkoutRecommendation.model_json_schema()["properties"]["duration_minutes"]

    assert duration["exclusiveMinimum"] == 0
    assert duration["maximum"] == 360
    assert "minutes" in duration["description"]


@pytest.mark.parametrize("duration_minutes", [1, 360])
def test_recommendation_accepts_duration_boundaries(duration_minutes):
    payload = valid_recommendation()
    payload["duration_minutes"] = duration_minutes
    payload["steps"] = [
        {
            "name": "Complete workout",
            "duration_minutes": duration_minutes,
            "intensity": "RPE 2",
        }
    ]

    result = WorkoutRecommendation.model_validate(payload)

    assert result.duration_minutes == duration_minutes


def test_recommendation_preserves_missing_power_disclosure():
    payload = valid_recommendation()
    payload["evidence"] = [
        {
            "observation": "Two recent activities have no power measurement.",
            "source": "14-day training summary",
        }
    ]
    payload["uncertainty"] = {
        "level": "high",
        "reasons": ["Recent power data is incomplete."],
    }
    payload["warnings"] = ["Use RPE because recent power data is incomplete."]

    result = WorkoutRecommendation.model_validate(payload)

    assert result.uncertainty.level == "high"
    assert result.uncertainty.reasons == ["Recent power data is incomplete."]
    assert result.warnings == ["Use RPE because recent power data is incomplete."]


def test_output_validation_rejects_step_duration_mismatch():
    payload = valid_recommendation()
    payload["duration_minutes"] = 60

    with pytest.raises(ValidationError, match="step durations"):
        AgentRuntime.validate_output(payload)


@pytest.mark.parametrize("field", ["title", "objective", "rationale"])
@pytest.mark.parametrize("value", ["", "   "])
def test_recommendation_rejects_empty_required_text(field, value):
    payload = valid_recommendation()
    payload[field] = value

    with pytest.raises(ValidationError):
        WorkoutRecommendation.model_validate(payload)


@pytest.mark.parametrize("field", ["name", "intensity"])
def test_recommendation_rejects_empty_step_text(field):
    payload = valid_recommendation()
    payload["steps"][0][field] = " "

    with pytest.raises(ValidationError):
        WorkoutRecommendation.model_validate(payload)


@pytest.mark.parametrize("duration_minutes", [0, -1])
def test_recommendation_rejects_non_positive_step_duration(duration_minutes):
    payload = valid_recommendation()
    payload["steps"][0]["duration_minutes"] = duration_minutes

    with pytest.raises(ValidationError):
        WorkoutRecommendation.model_validate(payload)


def test_recommendation_rejects_unknown_workout_type():
    payload = valid_recommendation()
    payload["ride_kind"] = "sprint"

    with pytest.raises(ValidationError):
        WorkoutRecommendation.model_validate(payload)


@pytest.mark.parametrize("duration_minutes", [0, 361])
def test_recommendation_rejects_duration_outside_supported_range(duration_minutes):
    payload = valid_recommendation()
    payload["duration_minutes"] = duration_minutes
    payload["steps"] = [
        {
            "name": "Complete workout",
            "duration_minutes": max(duration_minutes, 1),
            "intensity": "RPE 2",
        }
    ]

    with pytest.raises(ValidationError):
        WorkoutRecommendation.model_validate(payload)


def test_recommendation_requires_structured_evidence():
    payload = valid_recommendation()
    payload["evidence"] = []

    with pytest.raises(ValidationError):
        WorkoutRecommendation.model_validate(payload)

    for field in ("observation", "source"):
        payload = valid_recommendation()
        payload["evidence"][0][field] = " "

        with pytest.raises(ValidationError):
            WorkoutRecommendation.model_validate(payload)


def test_evidence_rejects_embedded_raw_activity_records():
    payload = valid_recommendation()
    payload["evidence"][0]["raw_activity"] = {"activity_id": "ride-001"}

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        WorkoutRecommendation.model_validate(payload)


@pytest.mark.parametrize("level", ["medium", "high"])
def test_non_low_uncertainty_requires_a_reason(level):
    payload = valid_recommendation()
    payload["uncertainty"] = {"level": level, "reasons": []}

    with pytest.raises(ValidationError, match="requires at least one reason"):
        WorkoutRecommendation.model_validate(payload)


def test_recommendation_rejects_malformed_uncertainty():
    payload = valid_recommendation()
    payload["uncertainty"] = {"level": "unknown", "reasons": []}

    with pytest.raises(ValidationError):
        WorkoutRecommendation.model_validate(payload)

    payload = valid_recommendation()
    payload["uncertainty"] = {"level": "medium", "reasons": [" "]}

    with pytest.raises(ValidationError):
        WorkoutRecommendation.model_validate(payload)


def test_recommendation_rejects_empty_warning():
    payload = valid_recommendation()
    payload["warnings"] = [""]

    with pytest.raises(ValidationError):
        WorkoutRecommendation.model_validate(payload)


def test_recommendation_rejects_unexpected_fields():
    payload = valid_recommendation()
    payload["raw_model_response"] = "hidden"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        WorkoutRecommendation.model_validate(payload)


def test_training_activity_accepts_valid_data_with_provenance():
    activity = TrainingActivity.model_validate(valid_activity())

    assert activity.source == "intervals_icu"
    assert activity.source_activity_id == "i-123"
    assert activity.duration_minutes == 60


def test_training_activity_preserves_missing_optional_measurements():
    payload = valid_activity()
    payload["average_power_w"] = None
    payload["normalized_power_w"] = None
    payload["average_heart_rate_bpm"] = None

    activity = TrainingActivity.model_validate(payload)

    assert activity.average_power_w is None
    assert activity.normalized_power_w is None
    assert activity.average_heart_rate_bpm is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("duration_minutes", 0),
        ("distance_km", -1),
        ("average_power_w", 0),
        ("average_heart_rate_bpm", 231),
        ("perceived_exertion", 11),
        ("source", "unknown"),
    ],
)
def test_training_activity_rejects_invalid_values(field, value):
    payload = valid_activity()
    payload[field] = value

    with pytest.raises(ValidationError):
        TrainingActivity.model_validate(payload)


def test_training_activity_rejects_unexpected_fields():
    payload = valid_activity()
    payload["power_guess_w"] = 200

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        TrainingActivity.model_validate(payload)


def test_training_activity_rejects_a_naive_start_datetime():
    payload = valid_activity()
    payload["started_at"] = datetime(2026, 11, 4, 7, 0)

    with pytest.raises(ValidationError, match="timezone offset"):
        TrainingActivity.model_validate(payload)


def test_skill_metadata_cannot_contain_loaded_instructions():
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        SkillMetadata(
            name="plan-workout",
            description="Plan one workout.",
            instructions="These must only appear after activation.",
        )

    loaded = LoadedSkill(
        name="plan-workout",
        description="Plan one workout.",
        instructions="Use deterministic metrics.",
    )
    assert loaded.instructions == "Use deterministic metrics."


def test_tool_contracts_accept_valid_definition_request_and_result():
    definition = ToolDefinition(
        name="load_skill",
        description="Load one skill by name.",
        input_schema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    )
    request = ToolRequest(
        tool_call_id="call-1",
        name=definition.name,
        arguments={"name": "plan-workout"},
    )
    result = ToolResult(
        tool_call_id=request.tool_call_id,
        name=request.name,
        content={"name": "plan-workout", "loaded": True},
    )

    assert definition.input_schema["type"] == "object"
    assert request.arguments == {"name": "plan-workout"}
    assert result.is_error is False


@pytest.mark.parametrize(
    "payload",
    [
        {"tool_call_id": "call-1", "name": "Load Skill", "arguments": {}},
        {"tool_call_id": "call-1", "name": "load_skill", "arguments": []},
        {
            "tool_call_id": "call-1",
            "name": "load_skill",
            "arguments": {},
            "unexpected": True,
        },
    ],
)
def test_tool_request_rejects_malformed_payloads(payload):
    with pytest.raises(ValidationError):
        ToolRequest.model_validate(payload)


def test_tool_definition_requires_an_object_input_schema():
    with pytest.raises(ValidationError, match="type must be object"):
        ToolDefinition(
            name="load_skill",
            description="Load one skill by name.",
            input_schema={"type": "array"},
        )
