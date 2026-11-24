"""CLI coverage for database-backed local coaching responses."""

import json
from datetime import date

import endurance_coach.cli as cli
from endurance_coach.domain.models import WorkoutRecommendation
from endurance_coach.fixtures import synthetic_activities


def test_ask_uses_recent_database_activities_and_prints_validated_json(
    monkeypatch, capsys
) -> None:
    question = "Based on my last workouts, what should I focus next"
    activities = tuple(synthetic_activities()[-3:])
    observed = {}

    def fake_load(_path, *, limit):
        observed["limit"] = limit
        return activities

    class FakeRuntime:
        def __init__(self, settings, skill_loader):
            observed["model"] = settings.model
            observed["skills"] = [skill.name for skill in skill_loader.discover()]

        def run(self, request, supplied_activities, *, current_date):
            observed["request"] = request
            observed["activity_ids"] = [item.activity_id for item in supplied_activities]
            observed["current_date"] = current_date.isoformat()
            return WorkoutRecommendation.model_validate(
                {
                    "workout_date": "2026-11-04",
                    "title": "Easy aerobic reset",
                    "ride_kind": "recovery",
                    "duration_minutes": 30,
                    "objective": "Maintain aerobic consistency.",
                    "rationale": "Recent load supports a conservative next session.",
                    "evidence": [
                        {
                            "observation": "Three recent rides were supplied.",
                            "source": "deterministic_training_summary",
                        }
                    ],
                    "uncertainty": {"level": "low", "reasons": []},
                    "warnings": [],
                    "steps": [
                        {
                            "name": "Easy spin",
                            "duration_minutes": 30,
                            "intensity": "Conversational, RPE 1-2",
                        }
                    ],
                    "source_skill": "plan-workout",
                }
            )

    monkeypatch.setattr(cli, "load_recent_training_activities", fake_load)
    monkeypatch.setattr(cli, "AgentRuntime", FakeRuntime)

    assert cli.main(["ask", question]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["title"] == "Easy aerobic reset"
    assert observed == {
        "activity_ids": ["ride-008", "ride-009", "ride-010"],
        "current_date": date.today().isoformat(),
        "limit": 50,
        "model": "qwen3:8b",
        "request": question,
        "skills": ["plan-workout"],
    }
