# Learning exercises

The five tests marked `exercise` are executable specifications. Keep them failing until you implement
the corresponding behavior; do not weaken or skip them.

## 1. Discover skill metadata

Start with `SkillLoader.discover()` in `src/endurance_coach/skills.py`.

It should return an empty list when the root does not exist, inspect sorted immediate child
directories containing `SKILL.md`, parse YAML frontmatter, verify that the frontmatter `name` matches
the directory name, and return `SkillMetadata` objects. Do not put the Markdown body in a discovery
result. Confirm with `test_skill_discovery_returns_metadata_only`.

## 2. Load one skill progressively

Implement `SkillLoader.load_skill(name)`. Reject unsafe names before constructing a path, raise a
clear `FileNotFoundError` for an unknown skill, parse the same frontmatter, and return `LoadedSkill`
with the Markdown body in `instructions`. Confirm with
`test_skill_is_loaded_progressively_only_when_requested` and `test_missing_skill_has_a_clear_error`.

## 3. Handle missing activity data

At the beginning of `AgentRuntime.run()`, raise `MissingTrainingDataError` for an empty activity list.
The runtime must not ask a model to fabricate training history. Confirm with
`test_runtime_refuses_to_plan_without_activity_data`.

## 4. Implement the local tool loop

Complete `AgentRuntime.run()` last. If no client was injected, create `ollama.Client` from the host
setting. Supply the configured model, a concise system prompt, validated activity/metric context, and
a `load_skill` tool schema. When the assistant requests that tool, call your loader, append both the
assistant tool request and tool result to the message history, then call the model again. Bound the
number of iterations so malformed model behavior cannot loop forever.

When Ollama returns final content, decode JSON and call `validate_output()` before returning. Do not
catch and hide JSON or Pydantic validation errors. Confirm the protocol first with the deterministic
`ScriptedOllamaClient` in `test_runtime_executes_skill_tool_call_and_validates_final_output`; a live
model is not required for that test.

## Completion check

Run `uv run pytest`. The implementation is complete only when the scaffold tests and all five
exercise tests pass together. Keep external services, persistence, frontends, and additional agents
out of this milestone.

