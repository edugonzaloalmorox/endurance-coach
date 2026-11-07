"""Deferred executable specifications for Ollama runtime implementation issues."""

from pathlib import Path

import pytest

from endurance_coach.config import OllamaSettings
from endurance_coach.metrics import MissingTrainingDataError
from endurance_coach.runtime import AgentRuntime
from endurance_coach.skills import SkillLoader


class ScriptedOllamaClient:
    """Small fake showing the two-turn tool-call protocol expected from run()."""

    def __init__(self) -> None:
        self.calls = 0

    def chat(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return {
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {"function": {"name": "load_skill", "arguments": {"name": "plan-workout"}}}
                    ],
                }
            }
        return {
            "message": {
                "role": "assistant",
                "content": (
                    '{"workout_date":"2026-11-04","title":"Easy spin",'
                    '"ride_kind":"recovery","duration_minutes":30,'
                    '"rationale":"Absorb the recent load.","steps":['
                    '{"name":"Easy spin","duration_minutes":30,"intensity":"RPE 2"}],'
                    '"warnings":[],"source_skill":"plan-workout"}'
                ),
            }
        }


def make_runtime(client=None) -> AgentRuntime:
    return AgentRuntime(
        settings=OllamaSettings(),
        skill_loader=SkillLoader(Path("coach_skills")),
        client=client,
    )


@pytest.mark.exercise
@pytest.mark.xfail(
    strict=True,
    reason="Deferred to #19; remove this marker when #19 implements the skill tool loop.",
)
def test_runtime_executes_skill_tool_call_and_validates_final_output(activities):
    client = ScriptedOllamaClient()

    result = make_runtime(client).run("What should I ride tomorrow?", activities)

    assert client.calls == 2
    assert result.source_skill == "plan-workout"
    assert result.duration_minutes == 30


@pytest.mark.exercise
@pytest.mark.xfail(
    strict=True,
    reason="Deferred to #18; remove this marker when #18 implements missing-data handling.",
)
def test_runtime_refuses_to_plan_without_activity_data():
    with pytest.raises(MissingTrainingDataError, match="activity"):
        make_runtime().run("What should I ride tomorrow?", [])
