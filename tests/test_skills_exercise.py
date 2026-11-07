"""Deferred executable specifications for SkillLoader implementation issues."""

import pytest

from endurance_coach.models import LoadedSkill, SkillMetadata
from endurance_coach.skills import SkillLoader


@pytest.mark.exercise
@pytest.mark.xfail(
    strict=True,
    reason="Deferred to #15; remove this marker when #15 implements skill discovery.",
)
def test_skill_discovery_returns_metadata_only():
    loader = SkillLoader(skills_directory="coach_skills")

    skills = loader.discover()

    assert skills == [
        SkillMetadata(
            name="plan-workout",
            description=(
                "Plans one safe cycling workout from recent training activities and current "
                "fatigue. Use when a cyclist asks what ride to do next or requests a workout "
                "recommendation."
            ),
        )
    ]
    assert not hasattr(skills[0], "instructions")


@pytest.mark.exercise
@pytest.mark.xfail(
    strict=True,
    reason="Deferred to #16; remove this marker when #16 implements explicit skill loading.",
)
def test_skill_is_loaded_progressively_only_when_requested():
    loader = SkillLoader(skills_directory="coach_skills")

    skill = loader.load_skill("plan-workout")

    assert isinstance(skill, LoadedSkill)
    assert skill.name == "plan-workout"
    assert "## Process" in skill.instructions


@pytest.mark.exercise
@pytest.mark.xfail(
    strict=True,
    reason="Deferred to #16; remove this marker when #16 implements explicit skill loading.",
)
def test_missing_skill_has_a_clear_error():
    loader = SkillLoader(skills_directory="coach_skills")

    with pytest.raises(FileNotFoundError, match="does-not-exist"):
        loader.load_skill("does-not-exist")
