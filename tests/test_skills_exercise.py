"""Behavior and security tests for runtime skill loading."""

from pathlib import Path

import pytest

from endurance_coach.models import LoadedSkill, SkillMetadata
from endurance_coach.skills import SkillFormatError, SkillLoader


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


def test_skill_is_loaded_progressively_only_when_requested():
    loader = SkillLoader(skills_directory="coach_skills")

    skill = loader.load_skill("plan-workout")

    assert isinstance(skill, LoadedSkill)
    assert skill.name == "plan-workout"
    assert "## Process" in skill.instructions


def test_missing_skill_has_a_clear_error():
    loader = SkillLoader(skills_directory="coach_skills")

    with pytest.raises(FileNotFoundError, match="does-not-exist"):
        loader.load_skill("does-not-exist")


def _write_skill(root: Path, name: str, frontmatter_name: str | None = None) -> Path:
    directory = root / name
    directory.mkdir(parents=True)
    skill_file = directory / "SKILL.md"
    skill_file.write_text(
        "---\n"
        f"name: {frontmatter_name or name}\n"
        f"description: Synthetic description for {name}.\n"
        "---\n\n"
        f"# {name}\n\nSynthetic instructions.\n",
        encoding="utf-8",
    )
    return skill_file


def test_discovery_is_sorted_immediate_and_tolerates_invalid_skills(tmp_path: Path) -> None:
    _write_skill(tmp_path, "zeta")
    _write_skill(tmp_path, "alpha")
    _write_skill(tmp_path, "mismatch", frontmatter_name="different")
    (tmp_path / "plain-file").write_text("not a skill", encoding="utf-8")
    nested = tmp_path / "container"
    nested.mkdir()
    _write_skill(nested, "nested")

    skills = SkillLoader(tmp_path).discover()

    assert [skill.name for skill in skills] == ["alpha", "zeta"]
    assert SkillLoader(tmp_path / "missing").discover() == []


@pytest.mark.parametrize("name", ["", "../outside", "/absolute", "name/child", "Uppercase"])
def test_loading_rejects_unsafe_names(tmp_path: Path, name: str) -> None:
    with pytest.raises(ValueError, match="unsafe skill name"):
        SkillLoader(tmp_path).load_skill(name)


def test_loading_rejects_malformed_document(tmp_path: Path) -> None:
    skill_file = _write_skill(tmp_path, "mismatch", frontmatter_name="different")

    with pytest.raises(SkillFormatError, match="does not match"):
        SkillLoader(tmp_path).load_skill("mismatch")

    skill_file.write_text("---\nname: mismatch\n---\n\n# Missing description\n", encoding="utf-8")
    with pytest.raises(SkillFormatError, match="invalid skill document"):
        SkillLoader(tmp_path).load_skill("mismatch")


def test_symlink_cannot_escape_skill_root(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    root.mkdir()
    outside = tmp_path / "outside"
    _write_skill(outside, "escaped")
    (root / "escaped").symlink_to(outside / "escaped", target_is_directory=True)
    loader = SkillLoader(root)

    assert loader.discover() == []
    with pytest.raises(FileNotFoundError, match="escaped"):
        loader.load_skill("escaped")
