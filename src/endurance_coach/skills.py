"""Public skill-loader interface for the learner to implement."""

from pathlib import Path

from endurance_coach.models import LoadedSkill, SkillMetadata


class SkillLoader:
    """Discover skill metadata, then load full instructions on demand.

    Milestone 1 exercise: implement both methods without changing their public
    contracts. Discovery must not read skill bodies into the returned models.
    """

    def __init__(self, skills_directory: Path | str) -> None:
        self.skills_directory = Path(skills_directory)

    def discover(self) -> list[SkillMetadata]:
        """Return validated metadata for each valid immediate child skill."""
        raise NotImplementedError("Learning exercise: implement skill discovery")

    def load_skill(self, name: str) -> LoadedSkill:
        """Load and validate one named skill's complete SKILL.md instructions."""
        raise NotImplementedError("Learning exercise: implement progressive skill loading")
