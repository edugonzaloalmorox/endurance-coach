# Deferred executable specifications

Five tests marked `exercise` specify behavior assigned to open implementation issues. They remain
collected with their assertions and inputs unchanged, but are temporarily marked
`xfail(strict=True)` under the exceptional policy in
[`testing-guidelines.md`](testing-guidelines.md). Strict mode makes an unexpected pass fail the suite
until the owning issue deliberately removes its marker.

Do not skip these tests, make their xfail markers non-strict, or weaken their assertions. The owning
implementation issue must remove its marker when it implements the behavior.

## Skill discovery — issue #15

[`SkillLoader.discover()` implementation](https://github.com/edugonzaloalmorox/endurance-coach/issues/15)
must return an empty list when the root does not exist, inspect sorted immediate child directories
containing `SKILL.md`, parse YAML frontmatter, verify that the frontmatter `name` matches the
directory name, and return `SkillMetadata` objects. Discovery must not expose the Markdown body.

Owning test: `test_skill_discovery_returns_metadata_only`.

## Explicit skill loading — issue #16

[`SkillLoader.load_skill()` implementation](https://github.com/edugonzaloalmorox/endurance-coach/issues/16)
must reject unsafe names before constructing a path, raise a clear `FileNotFoundError` for an unknown
skill, parse the same frontmatter, and return `LoadedSkill` with the Markdown body in `instructions`.

Owning tests: `test_skill_is_loaded_progressively_only_when_requested` and
`test_missing_skill_has_a_clear_error`.

## Missing activity data — issue #18

[`AgentRuntime` context and missing-data behavior](https://github.com/edugonzaloalmorox/endurance-coach/issues/18)
must raise `MissingTrainingDataError` for an empty activity list before asking a model to plan from
fabricated history.

Owning test: `test_runtime_refuses_to_plan_without_activity_data`.

## Local skill tool loop — issue #19

[`AgentRuntime` skill tool loop](https://github.com/edugonzaloalmorox/endurance-coach/issues/19)
must use the configured model, validated activity and metric context, and a `load_skill` tool schema.
It must append assistant tool requests and tool results to bounded message history, then decode final
JSON and validate it as a current `WorkoutRecommendation`.

Owning test: `test_runtime_executes_skill_tool_call_and_validates_final_output`. Issue #19 also owns
updating that test's scripted final response to the current recommendation contract before removing
the strict xfail. Malformed-output repair and bounded retries remain assigned to
[#23](https://github.com/edugonzaloalmorox/endurance-coach/issues/23).

## Verification

Run `uv run pytest` and report all five expected failures with their owning issues. Also run
`uv run pytest -m "not exercise"` and `uv run ruff check .`. Completion of an owning issue means its
strict xfail marker is removed and its unchanged executable specification passes.

