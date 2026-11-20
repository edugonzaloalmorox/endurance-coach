# Deferred executable specifications

Two tests marked `exercise` preserve unfinished product specifications. They remain collected with
their assertions and inputs unchanged and are temporarily marked `xfail(strict=True)`. Strict mode
makes an unexpected pass fail the suite until the behavior is implemented and the marker is removed.

Do not skip these tests, make their xfail markers non-strict, or weaken their assertions merely to
obtain a pass.

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

Run `uv run pytest` and `uv run ruff check .`. When a deferred behavior is implemented, remove its
strict xfail marker and make the executable specification pass.

