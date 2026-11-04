"""Public local-agent interface; the execution loop is intentionally absent."""

from collections.abc import Sequence
from typing import Any

from endurance_coach.config import OllamaSettings
from endurance_coach.models import TrainingActivity, WorkoutRecommendation
from endurance_coach.skills import SkillLoader


class AgentRuntime:
    """Coordinate Ollama, tools, skills, and validated recommendations.

    The constructor and output-validation boundary are ready to use. ``run`` is
    the central learning exercise and deliberately has no agent loop.
    """

    def __init__(
        self,
        settings: OllamaSettings,
        skill_loader: SkillLoader,
        client: Any | None = None,
    ) -> None:
        self.settings = settings
        self.skill_loader = skill_loader
        self.client = client

    @staticmethod
    def validate_output(payload: dict[str, Any]) -> WorkoutRecommendation:
        """Validate untrusted model output at the application boundary."""
        return WorkoutRecommendation.model_validate(payload)

    def run(self, request: str, activities: Sequence[TrainingActivity]) -> WorkoutRecommendation:
        """Run the future Ollama tool loop and return validated structured output."""
        raise NotImplementedError("Learning exercise: implement the Ollama agent loop")
