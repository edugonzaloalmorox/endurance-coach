"""Validate Ollama assistant messages and execute allowlisted runtime tools."""

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import ValidationError

from endurance_coach.domain.models import StrictModel, ToolDefinition, ToolRequest, ToolResult
from endurance_coach.llm.errors import AgentProtocolError, AgentToolError
from endurance_coach.skills import SkillLoader

_MAX_TOOL_CALLS_PER_STEP = 4


class _LoadSkillArguments(StrictModel):
    """Validated arguments accepted by the only runtime tool."""

    name: str


def ollama_tool_definition() -> dict[str, Any]:
    """Return the Ollama function definition for the skill loader."""
    definition = ToolDefinition(
        name="load_skill",
        description="Load the validated instructions for one discovered coaching skill.",
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Exact name of a discovered coaching skill.",
                }
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    )
    return {
        "type": "function",
        "function": {
            "name": definition.name,
            "description": definition.description,
            "parameters": definition.input_schema,
        },
    }


def as_mapping(value: Any) -> Mapping[str, Any] | None:
    """Convert an Ollama model object or mapping to a plain mapping."""
    if isinstance(value, Mapping):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(exclude_none=True)
        return dumped if isinstance(dumped, Mapping) else None
    return None


def parse_assistant_message(
    raw_message: Any, step: int
) -> tuple[dict[str, Any], list[Any], str | None]:
    """Validate one assistant response and strip hidden model thinking."""
    message = as_mapping(raw_message)
    if message is None or message.get("role") != "assistant":
        raise AgentProtocolError(f"model returned an invalid assistant message at step {step}")

    content = message.get("content")
    if content is not None and not isinstance(content, str):
        raise AgentProtocolError(f"model returned invalid content at step {step}")
    raw_tool_calls = message.get("tool_calls")
    tool_calls = [] if raw_tool_calls is None else raw_tool_calls
    if not isinstance(tool_calls, Sequence) or isinstance(tool_calls, (str, bytes)):
        raise AgentProtocolError(f"model returned invalid tool calls at step {step}")
    if len(tool_calls) > _MAX_TOOL_CALLS_PER_STEP:
        raise AgentProtocolError(f"model exceeded the tool-call limit at step {step}")

    assistant_message: dict[str, Any] = {"role": "assistant"}
    if content is not None:
        assistant_message["content"] = content
    if tool_calls:
        assistant_message["tool_calls"] = [
            safe_tool_call_message(call, step) for call in tool_calls
        ]
    return assistant_message, list(tool_calls), content


def safe_tool_call_message(raw_call: Any, step: int) -> dict[str, Any]:
    """Return a validated tool call without untrusted extra fields."""
    call = as_mapping(raw_call)
    function = as_mapping(call.get("function")) if call is not None else None
    if function is None:
        raise AgentProtocolError(f"model returned a malformed tool call at step {step}")
    name = function.get("name")
    arguments = function.get("arguments")
    if not isinstance(name, str) or not isinstance(arguments, Mapping):
        raise AgentProtocolError(f"model returned a malformed tool call at step {step}")
    return {"function": {"name": name, "arguments": dict(arguments)}}


def parse_tool_request(raw_call: Any, step: int, call_number: int) -> ToolRequest:
    """Convert one validated Ollama tool call to the domain request contract."""
    safe_call = safe_tool_call_message(raw_call, step)
    function = safe_call["function"]
    try:
        return ToolRequest(
            tool_call_id=f"step-{step}-call-{call_number}",
            name=function["name"],
            arguments=function["arguments"],
        )
    except ValidationError:
        raise AgentProtocolError(
            f"model returned invalid tool-call arguments at step {step}"
        ) from None


def execute_tool(skill_loader: SkillLoader, request: ToolRequest, step: int) -> ToolResult:
    """Execute the single allowlisted runtime tool and return a typed result."""
    if request.name != "load_skill":
        raise AgentToolError(f"model requested unsupported tool {request.name!r} at step {step}")
    try:
        arguments = _LoadSkillArguments.model_validate(request.arguments)
    except ValidationError:
        raise AgentToolError(f"load_skill received invalid arguments at step {step}") from None
    try:
        skill = skill_loader.load_skill(arguments.name)
    except Exception as exc:
        raise AgentToolError(
            f"load_skill failed for {arguments.name!r} at step {step} "
            f"({type(exc).__name__})"
        ) from None
    return ToolResult(
        tool_call_id=request.tool_call_id,
        name=request.name,
        content=skill.model_dump(mode="json"),
    )
