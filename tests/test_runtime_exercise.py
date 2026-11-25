"""Agent runtime context, skill-loop, and bounded-failure behavior."""

import copy
import json
from pathlib import Path

import pytest

from endurance_coach.analysis import MissingTrainingDataError
from endurance_coach.config import OllamaSettings
from endurance_coach.llm import (
    AgentClientError,
    AgentIterationLimitError,
    AgentProtocolError,
    AgentRuntime,
    AgentToolError,
)
from endurance_coach.skills import SkillLoader


class ScriptedOllamaClient:
    """Emit prescribed responses while recording immutable request snapshots."""

    def __init__(self, *responses) -> None:
        self.responses = list(responses)
        self.requests = []

    def chat(self, **kwargs):
        self.requests.append(copy.deepcopy(kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def tool_call(name="load_skill", arguments=None, *, thinking=None):
    message = {
        "role": "assistant",
        "tool_calls": [
            {
                "function": {
                    "name": name,
                    "arguments": {"name": "plan-workout"} if arguments is None else arguments,
                }
            }
        ],
    }
    if thinking is not None:
        message["thinking"] = thinking
    return {"message": message}


def final_response():
    payload = {
        "workout_date": "2026-11-04",
        "title": "Easy spin",
        "ride_kind": "recovery",
        "duration_minutes": 30,
        "objective": "Support recovery while maintaining easy aerobic movement.",
        "rationale": "Recent volume was high and the latest session was a recovery ride.",
        "evidence": [
            {
                "observation": "Ten rides totalled 423.1 km in the training window.",
                "source": "deterministic_training_summary",
            }
        ],
        "uncertainty": {
            "level": "medium",
            "reasons": ["Two activities have no power measurement."],
        },
        "steps": [
            {"name": "Easy spin", "duration_minutes": 30, "intensity": "RPE 2"}
        ],
        "warnings": ["Use RPE because some recent power data is unavailable."],
        "source_skill": "plan-workout",
    }
    return {"message": {"role": "assistant", "content": json.dumps(payload)}}


def make_runtime(client=None, **settings) -> AgentRuntime:
    return AgentRuntime(
        settings=OllamaSettings(**settings),
        skill_loader=SkillLoader(Path("coach_skills")),
        client=client,
    )


def test_runtime_executes_skill_tool_call_and_validates_final_output(activities):
    client = ScriptedOllamaClient(
        tool_call(thinking="private chain of thought"),
        final_response(),
    )

    result = make_runtime(client).run("What should I ride tomorrow?", activities)

    assert len(client.requests) == 2
    assert result.source_skill == "plan-workout"
    assert result.duration_minutes == 30
    assert client.requests[0]["model"] == "qwen3:8b"
    assert client.requests[0]["think"] is False
    assert "format" not in client.requests[0]
    assert "tools" in client.requests[0]
    assert "tools" not in client.requests[1]
    recommendation_schema = client.requests[1]["format"]
    assert recommendation_schema["type"] == "object"
    assert set(recommendation_schema["required"]) == {
        "workout_date",
        "title",
        "ride_kind",
        "duration_minutes",
        "objective",
        "rationale",
        "evidence",
        "uncertainty",
        "steps",
        "source_skill",
    }
    assert "$defs" not in recommendation_schema

    first_messages = client.requests[0]["messages"]
    assert [message["role"] for message in first_messages] == ["system", "user"]
    assert "# Plan a cycling workout" not in json.dumps(first_messages)
    assert "Never fabricate missing history" in first_messages[0]["content"]

    context = json.loads(first_messages[1]["content"])
    assert all("instructions" not in skill for skill in context["available_skills"])
    assert context["context_as_of"] == "2026-11-03"
    assert context["training_data_through"] == "2026-11-03"
    assert context["days_since_last_activity"] == 0
    assert context["available_skills"] == [
        {
            "name": "plan-workout",
            "description": (
                "Plans one safe cycling workout from recent training activities and current "
                "fatigue. Use when a cyclist asks what ride to do next or requests a workout "
                "recommendation."
            ),
        }
    ]
    assert context["metric_inputs"] == {"ftp_watts": 250}
    assert context["deterministic_training_summary"]["total_tss"] == 735.5
    assert context["deterministic_training_summary"]["activities_missing_power"] == 2
    missing_power = context["recent_activities"][1]
    assert missing_power["average_power_w"] is None
    assert missing_power["normalized_power_w"] is None

    second_messages = client.requests[1]["messages"]
    assert [message["role"] for message in second_messages] == [
        "system",
        "user",
        "assistant",
        "tool",
    ]
    assert "private chain of thought" not in json.dumps(second_messages)
    tool_result = json.loads(second_messages[-1]["content"])
    assert tool_result["tool_call_id"] == "step-1-call-1"
    assert tool_result["name"] == "load_skill"
    assert tool_result["is_error"] is False
    assert tool_result["content"]["name"] == "plan-workout"
    assert "# Plan a cycling workout" in tool_result["content"]["instructions"]

    tool = client.requests[0]["tools"][0]["function"]
    assert tool["name"] == "load_skill"
    assert tool["parameters"]["required"] == ["name"]
    assert tool["parameters"]["additionalProperties"] is False


def test_runtime_refuses_to_plan_without_activity_data():
    client = ScriptedOllamaClient(final_response())

    with pytest.raises(MissingTrainingDataError, match="activity"):
        make_runtime(client).run("What should I ride tomorrow?", [])

    assert client.requests == []


@pytest.mark.parametrize("request_value", ["", "   ", 123])
def test_runtime_rejects_invalid_request_before_calling_model(activities, request_value):
    client = ScriptedOllamaClient(final_response())

    with pytest.raises(ValueError, match="request"):
        make_runtime(client).run(request_value, activities)

    assert client.requests == []


def test_runtime_revalidates_activity_inputs_before_calling_model(activities):
    invalid = activities[0].model_dump()
    invalid["duration_minutes"] = 0
    client = ScriptedOllamaClient(final_response())

    with pytest.raises(ValueError, match="invalid activity"):
        make_runtime(client).run("Plan tomorrow", [invalid])

    assert client.requests == []


def test_runtime_bounds_activity_context(activities):
    client = ScriptedOllamaClient(final_response())

    with pytest.raises(ValueError, match="context limit of 2"):
        make_runtime(client, max_context_activities=2).run("Plan tomorrow", activities)

    assert client.requests == []


@pytest.mark.parametrize(
    ("response", "error", "match"),
    [
        (tool_call("delete_history"), AgentToolError, "unsupported tool 'delete_history'"),
        (tool_call(arguments={}), AgentToolError, "invalid arguments"),
        (
            tool_call(arguments={"name": "unknown-skill"}),
            AgentToolError,
            "load_skill failed for 'unknown-skill'",
        ),
        ({"message": {"role": "assistant", "content": ""}}, AgentProtocolError, "empty"),
        ({"message": {"role": "user", "content": "no"}}, AgentProtocolError, "assistant"),
        (
            {"message": {"role": "assistant", "tool_calls": {}}},
            AgentProtocolError,
            "invalid tool calls",
        ),
        (
            {"message": {"role": "assistant", "tool_calls": [{"function": {}}]}},
            AgentProtocolError,
            "malformed tool call",
        ),
    ],
)
def test_runtime_terminates_on_malformed_model_behavior(activities, response, error, match):
    with pytest.raises(error, match=match):
        make_runtime(ScriptedOllamaClient(response)).run("Plan tomorrow", activities)


def test_runtime_rejects_recommendation_without_loaded_skill_at_limit(activities):
    with pytest.raises(AgentProtocolError, match="before loading a skill"):
        make_runtime(ScriptedOllamaClient(final_response()), max_steps=1).run(
            "Plan tomorrow", activities
        )


def test_runtime_reports_client_error_without_exposing_client_message(activities):
    client = ScriptedOllamaClient(ConnectionError("secret-token=do-not-expose"))

    with pytest.raises(AgentClientError) as error:
        make_runtime(client).run("Plan tomorrow", activities)

    assert "step 1" in str(error.value)
    assert "ConnectionError" in str(error.value)
    assert "secret-token" not in str(error.value)
    assert error.value.__cause__ is None


def test_runtime_retries_invalid_recommendation_with_bounded_feedback(activities):
    client = ScriptedOllamaClient(
        tool_call(),
        {"message": {"role": "assistant", "content": "not-json"}},
        final_response(),
    )

    result = make_runtime(client, max_steps=3).run(
        "Based on my last workouts, what should I focus next", activities
    )

    assert result.source_skill == "plan-workout"
    assert len(client.requests) == 3
    feedback = client.requests[2]["messages"][-1]
    assert feedback["role"] == "user"
    assert "did not match" in feedback["content"]
    assert "not-json" not in feedback["content"]


def test_runtime_redirects_premature_wrapped_recommendation_to_skill_tool(activities):
    client = ScriptedOllamaClient(
        {
            "message": {
                "role": "assistant",
                "content": json.dumps({"workout_recommendation": {}}),
            }
        },
        tool_call(),
        final_response(),
    )

    result = make_runtime(client, max_steps=3).run(
        "Based on my last workouts, what should I focus next", activities
    )

    assert result.source_skill == "plan-workout"
    correction = client.requests[1]["messages"][-1]
    assert correction["role"] == "user"
    assert "Call load_skill" in correction["content"]
    assert "format" not in client.requests[1]
    assert "format" in client.requests[2]


def test_runtime_rejects_invalid_recommendation_at_step_limit(activities):
    client = ScriptedOllamaClient(
        tool_call(),
        {"message": {"role": "assistant", "content": json.dumps({})}},
    )

    with pytest.raises(AgentProtocolError, match="invalid workout recommendation"):
        make_runtime(client, max_steps=2).run("Plan tomorrow", activities)


def test_runtime_stops_at_configured_step_limit(activities):
    client = ScriptedOllamaClient(tool_call(), tool_call(), final_response())

    with pytest.raises(AgentIterationLimitError, match="within 2 steps"):
        make_runtime(client, max_steps=2).run("Plan tomorrow", activities)

    assert len(client.requests) == 2
