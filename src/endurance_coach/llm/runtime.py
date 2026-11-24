"""Bounded local-model runtime for evidence-based workout recommendations."""

import json
from collections.abc import Mapping, Sequence
from typing import Any

import ollama
from pydantic import ValidationError

from endurance_coach.analysis.metrics import summarize_training
from endurance_coach.config import OllamaSettings
from endurance_coach.domain.models import TrainingActivity, WorkoutRecommendation
from endurance_coach.llm.context import (
    build_initial_messages,
    validate_activities,
    validate_request,
)
from endurance_coach.llm.errors import (
    AgentClientError,
    AgentIterationLimitError,
    AgentProtocolError,
    AgentRuntimeError,
    AgentToolError,
)
from endurance_coach.llm.protocol import (
    execute_tool,
    ollama_tool_definition,
    parse_assistant_message,
    parse_tool_request,
)
from endurance_coach.skills import SkillLoader


class AgentRuntime:
    """Coordinate local Ollama messages, skill loading, and output validation."""

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
        """Return one validated recommendation using bounded local-model tool calls.

        Activity validation and all training calculations happen before the model is
        called. Full skill instructions enter message history only after the model
        explicitly requests the supported ``load_skill`` tool.

        Args:
            request: Athlete's non-empty workout question.
            activities: Recent, validated activities used as training evidence.

        Returns:
            A recommendation validated against the public workout contract.

        Raises:
            ValueError: If request or activity inputs are invalid or out of bounds.
            MissingTrainingDataError: If no activity history is supplied.
            AgentRuntimeError: If the client, tool loop, or model response fails.
        """
        normalized_request = validate_request(request)
        validated_activities = validate_activities(
            activities, self.settings.max_context_activities
        )
        summary = summarize_training(validated_activities, self.settings.ftp_watts)
        messages = build_initial_messages(
            normalized_request,
            validated_activities,
            summary,
            self.settings,
            self.skill_loader,
        )
        tools = [ollama_tool_definition()]
        client = self.client or ollama.Client(host=self.settings.host)
        loaded_skills: set[str] = set()

        for step in range(1, self.settings.max_steps + 1):
            response_message = self._chat(client, messages, tools, step)
            assistant_message, tool_calls, content = parse_assistant_message(
                response_message, step
            )
            messages.append(assistant_message)

            if tool_calls:
                for call_number, raw_call in enumerate(tool_calls, start=1):
                    request_model = parse_tool_request(raw_call, step, call_number)
                    result = execute_tool(self.skill_loader, request_model, step)
                    if isinstance(result.content, dict):
                        loaded_skills.add(str(result.content["name"]))
                    messages.append(
                        {
                            "role": "tool",
                            "tool_name": result.name,
                            "content": result.model_dump_json(),
                        }
                    )
                continue

            if content is None or not content.strip():
                raise AgentProtocolError(f"model returned an empty response at step {step}")
            recommendation = self._parse_final_output(content, step)
            if recommendation.source_skill not in loaded_skills:
                raise AgentProtocolError(
                    f"model referenced an unloaded source skill at step {step}"
                )
            return recommendation

        raise AgentIterationLimitError(
            f"model did not return a final response within {self.settings.max_steps} steps"
        )

    def _chat(
        self,
        client: Any,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        step: int,
    ) -> Any:
        try:
            response = client.chat(
                model=self.settings.model,
                messages=messages,
                tools=tools,
                think=False,
                format=WorkoutRecommendation.model_json_schema(),
                options={"temperature": self.settings.temperature},
            )
        except Exception as exc:
            raise AgentClientError(
                f"local model request failed at step {step} ({type(exc).__name__})"
            ) from None
        if isinstance(response, Mapping):
            return response.get("message")
        return getattr(response, "message", None)

    def _parse_final_output(self, content: str, step: int) -> WorkoutRecommendation:
        try:
            payload = json.loads(content)
            if not isinstance(payload, dict):
                raise TypeError
            return self.validate_output(payload)
        except (json.JSONDecodeError, TypeError, ValidationError):
            raise AgentProtocolError(
                f"model returned an invalid workout recommendation at step {step}"
            ) from None


__all__ = [
    "AgentClientError",
    "AgentIterationLimitError",
    "AgentProtocolError",
    "AgentRuntime",
    "AgentRuntimeError",
    "AgentToolError",
]
