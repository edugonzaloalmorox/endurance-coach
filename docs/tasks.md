## 1. Create an empty project with a passing test
Goal: Establish the smallest runnable Python project and prove its test command works.
Description: Create the `uv` project metadata, `src/endurance_coach/` package, and `tests/` directory without implementing coaching behavior. Add one smoke test so `uv sync` and `uv run pytest` complete successfully.

## 2. Add linting and test configuration
Goal: Make the repository's automated quality checks reproducible.
Description: Configure Ruff and pytest in `pyproject.toml`, using settings appropriate for the `src/` layout. Verify that `uv run ruff check .` and `uv run pytest` both pass on the empty scaffold.

## 3. Add local configuration templates and ignore rules
Goal: Define safe conventions for local settings and generated files.
Description: Add `.env.example` entries for anticipated Ollama and integration settings without real credentials. Update `.gitignore` for virtual environments, caches, local databases, secrets, and generated artifacts while retaining useful fixtures.

## 4. Define the training activity contract
Goal: Create a strict typed boundary for cycling activity data.
Description: Add a Pydantic model for activity identity, dates, duration, distance, power, heart rate, intensity, and provenance, with units and optional fields documented. Include tests for valid records, rejected invalid values, missing optional measurements, and unexpected fields.

## 5. Define skill and tool contracts
Goal: Represent progressive skill loading and agent tool calls with explicit types.
Description: Add models for skill metadata, loaded skill instructions, tool definitions, tool requests, and tool results. Ensure discovery metadata cannot accidentally contain full instructions, and test validation of malformed names and payloads.

## 6. Define workout recommendation contracts
Goal: Specify the structured output expected from the coaching agent.
Description: Add Pydantic models for workout type, duration, intensity, objective, rationale, evidence, uncertainty, and warnings. Document constraints and test valid recommendations, boundary values, missing data disclosures, and invalid output.

## 7. Document repository setup and skill boundaries
Goal: Give a new contributor enough context to work safely in the repository.
Description: Write setup and verification instructions in the README and contribution guidance in `AGENTS.md`. Clearly distinguish Codex development skills from the application's runtime coaching skills, and state that nutrition, Google Sheets, frontends, multiple agents, and autonomous plan changes are outside the MVP.

## 8. Create the synthetic activity fixture
Goal: Provide a stable 14-day training history for local development and tests.
Description: Create clearly labeled synthetic activities using fixed dates, including rides with power, heart rate, varied intensities, rest days, and deliberately missing fields. Validate the fixture through the training activity contract and document that it contains no real athlete data.

## 9. Implement rolling volume and active-day metrics
Goal: Compute deterministic 7-day and 14-day training volume summaries.
Description: Add pure functions for duration, distance, and active-day counts over explicit date windows. Test window boundaries, rest days, empty input, and activities that cross calendar or week boundaries, with every returned unit documented.

## 10. Implement intensity and hard-session metrics
Goal: Summarize workout intensity without asking the language model to perform arithmetic.
Description: Add pure functions for supported intensity measures and hard-session counts, using only available validated fields. Test normal inputs, threshold boundaries, missing power, and cases where a metric must remain unknown rather than be guessed.

## 11. Implement weekly trend metrics
Goal: Compare recent training with the preceding period using deterministic calculations.
Description: Add pure functions that report changes in volume, active days, and supported intensity measures between defined weekly windows. Include period dates, units, and sample sizes in results, and test insufficient-history and missing-data behavior.

## 12. Create the plan-workout skill
Goal: Define the runtime procedure for proposing a workout from computed evidence.
Description: Add `coach_skills/plan-workout/SKILL.md` with valid frontmatter, a stepwise procedure, tool-use guidance, and rules for safety and uncertainty. Keep calculations out of the skill and instruct it to expose missing evidence instead of inventing data.

## 13. Specify skill discovery behavior with tests
Goal: Make progressive skill discovery executable as a clear contract.
Description: Add tests and an implementation skeleton for listing immediate skill directories and returning only validated name and description metadata. Cover a missing root, malformed frontmatter, name-directory mismatches, nested directories, stable ordering, and exclusion of instruction bodies.

## 14. Specify explicit skill loading and path safety with tests
Goal: Define how one selected skill is loaded without exposing unsafe filesystem access.
Description: Add tests and a skeleton for loading a named skill's metadata and Markdown instructions only when requested. Cover unknown skills, absolute paths, traversal attempts, unsafe names, symlinks that escape the skill root, and malformed documents.

## 15. Implement skill discovery
Goal: Return safe skill metadata without loading full instructions.
Description: Implement the discovery method against the tests from task 13, reading only immediate `SKILL.md` files under the configured root. Validate frontmatter and preserve progressive disclosure by keeping instruction bodies out of discovery results.

## 16. Implement explicit skill loading
Goal: Load one validated coaching skill on demand.
Description: Implement the loading method against the tests from task 14, returning typed metadata and instructions for an exact safe name. Resolve and verify paths within the configured skill root before reading, and provide clear errors for unknown or invalid skills.

## 17. Build a scripted Ollama client for tests
Goal: Test model interactions without requiring a live local model.
Description: Create a deterministic fake client that can emit tool calls, final responses, malformed payloads, and transport errors in a prescribed sequence. Add reusable fixtures that record requests so tests can assert model, messages, tools, and iteration behavior.

## 18. Assemble validated agent context
Goal: Give the model only the training evidence and instructions required for a request.
Description: Build the agent runtime entry point that rejects empty activity history, validates inputs, computes metrics in Python, and assembles concise dated context. Test that raw missing values remain visible and that the runtime never asks the model to fabricate training history.

## 19. Implement the skill tool loop
Goal: Allow the model to discover and activate a coaching skill through bounded tool calls.
Description: Implement message handling for assistant tool requests, execute only the supported skill loader tool, append typed tool results, and continue until a final response arrives. Use the scripted client to verify message ordering, progressive loading, and that computed metrics—not model arithmetic—drive the recommendation.

## 20. Handle agent-loop errors and iteration limits
Goal: Ensure malformed model behavior terminates predictably and visibly.
Description: Add explicit handling for unknown tools, invalid arguments, tool failures, empty responses, client errors, and repeated calls beyond a configured step limit. Test each failure path and preserve useful error context without exposing hidden reasoning or secrets.

## 21. Add skill inspection CLI commands
Goal: Let users inspect available runtime skills from the command line.
Description: Add `skills list` to show metadata and `skills show <name>` to explicitly load one skill. Test empty roots, successful output, unknown names, and safe error messages while keeping discovery output free of full instructions.

## 22. Add the ask command and debug trace
Goal: Expose the synthetic-data coaching workflow through a local CLI.
Description: Add `ask <question>` to invoke the runtime and `--debug` to show an observable decision trace such as selected skills, tools, and validation attempts. Keep hidden model reasoning out of the trace, and test command success and agent failures with the scripted client.

## 23. Validate final model output with bounded retries
Goal: Return only recommendations that satisfy the workout contract.
Description: Parse final model content as JSON, validate it with Pydantic, and retry correction a small configured number of times when parsing or validation fails. Test immediate success, repair success, exhausted retries, invalid duration or intensity, and preservation of missing-data warnings.

## 24. Verify and document the M1 local workflow
Goal: Demonstrate the complete no-external-services milestone and explain its architecture.
Description: Add an end-to-end test proving that a synthetic-data request discovers a skill, loads it on demand, calls deterministic metrics, and returns validated JSON without a real Ollama server. Update the README to explain the distinct responsibilities of a skill, a Python tool, and the agent loop, and record whether a live Ollama run was actually verified.

## 25. Research Intervals.icu and COROS read interfaces
Goal: Establish verified integration contracts before writing connectors.
Description: Inspect current official documentation and representative real responses for Intervals.icu and the available COROS MCP server, covering authentication, pagination, schemas, rate limits, and tool availability. Record redacted examples, data gaps, and source limitations without inventing endpoints or COROS tools.

## 26. Implement Intervals.icu request authentication and configuration
Goal: Configure read-only Intervals.icu access without embedding credentials.
Description: Add environment-based connector settings and authenticated request construction for the verified endpoints documented in task 25. Use mocked HTTP responses to test missing credentials, correct request parameters, redacted errors, and the absence of write operations.

## 27. Implement paginated Intervals.icu activity retrieval
Goal: Retrieve all relevant activity and training metadata for a requested date range.
Description: Build the read-only pagination loop with explicit timeouts and a stable raw response boundary. Test one page, multiple pages, empty results, duplicate page items, malformed responses, rate limiting, and transient server failures using mocks.

## 28. Implement COROS MCP discovery and allowlisting
Goal: Use only verified read-only COROS tools that are actually available.
Description: Add OAuth-aware MCP setup, tool discovery, and a strict allowlist derived from task 25 for supplementary recovery or activity data. Test missing authorization, unavailable tools, unexpected tools, malformed responses, and rejection of any write-capable operation with recorded fixtures.

## 29. Normalize external activity fields
Goal: Convert Intervals.icu and COROS records into the shared training activity contract.
Description: Map verified dates, time zones, identifiers, units, zones, duration, power, and heart-rate fields while preserving raw source identifiers and field-level provenance. Test unit conversion, daylight-saving boundaries, absent measurements, unknown activity types, and invalid records.

## 30. Reconcile duplicate activities across sources
Goal: Prevent one workout from being counted more than once.
Description: Implement deterministic matching rules that treat Intervals.icu as the primary activity source and COROS as supplementary, with ambiguity left unresolved rather than silently merged. Test exact IDs, close timestamps, differing durations, conflicting measurements, unmatched sessions, and preserved provenance.

## 31. Create the activity and sync-state database schema
Goal: Store normalized activities and incremental synchronization state in SQLite.
Description: Add migrations for source records, normalized activities, provenance, and per-source sync cursors or windows. Define uniqueness and foreign-key constraints that support idempotency and failure recovery, and test migration on a fresh and already-initialized database.

## 32. Implement idempotent activity persistence
Goal: Save normalized activities without creating duplicates on repeated imports.
Description: Add repository methods for transactional upsert, lookup by source identity, and provenance-preserving updates. Test repeated writes, changed supplementary fields, conflicting identities, transaction rollback, and database constraint errors.

## 33. Orchestrate incremental activity synchronization
Goal: Run repeatable real-data syncs that resume safely after failures.
Description: Coordinate Intervals.icu retrieval, optional COROS supplementation, normalization, reconciliation, persistence, and sync-state advancement. Advance state only after a successful transaction, and test first sync, no-op repeat sync, partial failure, retry, and overlapping date windows with mocked connectors.

## 34. Create the analyze-training skill
Goal: Guide the agent in turning deterministic metrics into an evidence-based training analysis.
Description: Add `coach_skills/analyze-training/SKILL.md` with valid frontmatter, a procedure for selecting metric tools, provenance requirements, and uncertainty rules. Keep calculations in Python and require analysis to separate observed facts from interpretations and unavailable evidence.

## 35. Test multi-skill selection and integration CLI behavior
Goal: Prove the agent can select and combine analysis and planning skills appropriately.
Description: Add deterministic scenarios where the correct behavior is to load `analyze-training`, `plan-workout`, or both, plus a CLI command for triggering and inspecting a sync. Assert no duplicate activity counts, safe errors, provenance in results, and no real network dependency in automated tests.

## 36. Implement deterministic training-load metrics
Goal: Calculate supported load measures with transparent inputs and limitations.
Description: Add pure functions for load derived from the available activity fields, returning units, period, sample size, and provenance. Test known examples, boundary values, missing power or duration, mixed-source data, and cases where load cannot be calculated.

## 37. Implement power-duration summaries
Goal: Summarize best sustained power only when suitable time-series data exists.
Description: Add deterministic power-duration calculations for documented durations using validated time-series samples, without inferring absent traces from activity summaries. Test regular and irregular samples, gaps, short activities, missing series, invalid power, and provenance of each result.

## 38. Compare performance under accumulated fatigue
Goal: Quantify comparable performance before and after documented prior workload.
Description: Define and implement deterministic comparisons using explicit fatigue windows, comparable efforts, dates, units, and minimum sample rules. Test valid comparisons, non-comparable sessions, insufficient samples, missing power, and uncertainty caused by changed conditions.

## 39. Implement durability analysis
Goal: Measure the ability to sustain power late in long rides when adequate data is available.
Description: Add calculations based on elapsed time, power, and accumulated kilojoules from time-series data, with configurable comparison segments and data-quality checks. Test complete rides, gaps, short rides, missing series, implausible samples, and output that clearly states why analysis is unavailable.

## 40. Implement individual recovery trends
Goal: Summarize sleep, HRV, and resting-heart-rate changes without clinical interpretation.
Description: Add deterministic baselines and recent-trend calculations only for recovery signals actually exposed by verified COROS tools, retaining date, unit, sample count, and provenance. Test missing metrics, sparse history, outliers, stale observations, and the rule that unknown data stays unknown.

## 41. Persist subjective recovery check-ins
Goal: Store one validated daily athlete check-in for fatigue, soreness, and readiness.
Description: Add a dated Pydantic contract and SQLite migration/repository for 1–10 ratings plus an optional note, with an explicit policy for replacing or revising a same-day entry. Test valid boundaries, invalid ratings, time-zone date handling, duplicates, retrieval, and revision history.

## 42. Add the recovery check-in CLI
Goal: Let the athlete enter and review subjective recovery data manually.
Description: Add a `check-in` command that validates fatigue, soreness, readiness, and date before persistence, plus a way to view recent entries. Test interactive or flag-based input, cancellation, invalid values, same-day updates, and database failures without losing the previous entry.

## 43. Create the assess-recovery skill
Goal: Guide cautious recovery assessment from objective trends and subjective input.
Description: Add `coach_skills/assess-recovery/SKILL.md` with rules for combining the check-in with available sleep, HRV, and resting-heart-rate trends. Require multiple-signal reasoning, explicit uncertainty, no diagnosis, and no decision based on a single signal.

## 44. Produce an explainable training and recovery report
Goal: Present observations, hypotheses, and insufficient evidence as separate categories.
Description: Add a structured report contract and runtime path that combines training, durability, and recovery tools without fabricating scores. Test fatigue, missing power, missing HRV, contradictory signals, sparse history, and appropriately cautious recommendations with fixed scenarios.

## 45. Define and persist the athlete profile
Goal: Store validated athlete settings used by weekly planning.
Description: Add contracts and SQLite persistence for goals, FTP, power or heart-rate zones, time zone, and the default 9-hour availability of Mon–Fri 1 hour, Sat 3 hours, and Sun 1 hour. Support dated weekly availability overrides and test invalid zones, overlapping settings, missing optional FTP, and override retrieval.

## 46. Add athlete profile and availability CLI commands
Goal: Let users inspect and edit planning settings without changing code.
Description: Add commands to show and update profile fields and to create, view, or remove a weekly availability override. Validate input before writing, show effective daily and weekly limits, and test partial edits, invalid durations, cancellation, and fallback to defaults.

## 47. Define optional event goals and planning modes
Goal: Support continuous improvement by default and event preparation when requested.
Description: Add an optional event contract with date, distance, elevation, and athlete goal, plus an explicit planning mode. Persist and validate events, test past or incomplete events, and ensure a recommendation can be generated when no event exists.

## 48. Persist strength-training sessions
Goal: Record manually entered strength work as part of total training context.
Description: Add contracts and SQLite persistence for session date, exercises, sets, repetitions, kilograms, and optional RPE, preserving edit history. Test multi-exercise sessions, bodyweight or missing-load cases, invalid values, deletion policy, and retrieval by date range.

## 49. Add strength-training CLI commands
Goal: Let users add, view, and edit strength sessions from the command line.
Description: Implement validated commands for creating a session, listing history, viewing details, and editing an existing record. Test cancellation, malformed exercises, optional RPE, same-day sessions, not-found IDs, and preservation of the prior version after an unsuccessful edit.

## 50. Enforce weekly and daily availability constraints
Goal: Reject plans that exceed effective time availability.
Description: Implement a deterministic constraint engine that applies the default schedule or a dated weekly override, counting cycling and strength duration toward the same total. Return checkable violations by day and week, and test exact limits, overages, missing days, cross-midnight sessions, and invalid negative duration.

## 51. Enforce rest, intensity, and strength-load constraints
Goal: Flag unsafe or impossible weekly training arrangements using explicit rules.
Description: Add deterministic checks for required recovery, spacing of hard sessions, strength load, and other documented hard or warning-level constraints. Test consecutive hard days, strength combined with cycling, insufficient recovery data, impossible schedules, and the distinction between rejection, risk warning, and uncertainty.

## 52. Define and validate a seven-day plan
Goal: Represent a complete weekly proposal with evidence for every session.
Description: Add structured contracts for seven dated days containing rest or sessions with duration, intensity, objective, evidence, and uncertainty. Validate week boundaries, total time, daily limits, flexible strength frequency, duplicate days, and incomplete plans through the constraint engine.

## 53. Extend plan-workout for weekly and event-aware planning
Goal: Make the planning skill produce constrained seven-day proposals for either planning mode.
Description: Update the skill procedure to use athlete settings, availability, recent training, recovery, strength history, and optional event context through Python tools. Require continuous-improvement plans when no event is set and event-specific rationale when one is active, while keeping all proposals inactive until approval.

## 54. Persist versioned weekly plan proposals
Goal: Store immutable plan versions that can be retrieved without making them active automatically.
Description: Add SQLite migrations and repository methods for plan identity, week, version, structured content, creation metadata, and status. Test first and subsequent versions, retrieval by week and version, immutable content, transaction rollback, and the rule that saving a proposal does not activate it.

## 55. Display weekly plans and versions in the CLI
Goal: Let users inspect proposed and historical plans before approval.
Description: Add commands to list plan weeks and show a selected version with totals, sessions, evidence, warnings, and status. Test absent plans, multiple versions, date selection, readable constraint failures, and output that makes inactive versus active plans unmistakable.

## 56. Compare planned and completed training
Goal: Explain dated differences between the active plan and actual activity or recovery data.
Description: Implement deterministic matching and comparison for planned sessions, completed cycling or strength work, and the latest daily check-in. Report completed, missed, shortened, extended, or substituted work with evidence and ambiguity, and test rest days, duplicate candidates, late syncs, and missing data.

## 57. Create the adjust-plan skill
Goal: Guide the agent to propose daily changes without applying them.
Description: Add `coach_skills/adjust-plan/SKILL.md` with a procedure using plan-versus-actual differences, recovery, remaining availability, and constraint tools. Require each proposal to explain its evidence, uncertainty, and impact on the rest of the week, and forbid direct plan mutation.

## 58. Define proposal states and transitions
Goal: Model the lifecycle `proposed`, `approved`, `rejected`, and `applied` with valid transitions.
Description: Add typed states and a deterministic transition service that rejects skipping approval, changing terminal decisions, or applying stale proposals. Test every allowed and forbidden transition, repeated requests, version conflicts, and the guarantee that rejected proposals leave the prior plan unchanged.

## 59. Add proposal review CLI commands
Goal: Provide explicit human review through `plan proposals`, `approve <id>`, and `reject <id>`.
Description: Implement commands that show the exact proposed changes and downstream weekly impact before accepting a decision. Require clear confirmation where appropriate, and test not-found IDs, cancellation, repeated approval or rejection, invalid state, and preservation of the current active plan.

## 60. Apply approved proposals transactionally
Goal: Create a new active plan version only from an approved proposal.
Description: Implement one transaction that verifies the proposal and base version, writes the new immutable plan version, marks it active, and records the proposal as applied. Test success, unapproved access, stale versions, constraint failure, database failure, rollback, retry, and idempotent repeated application.

## 61. Record a complete plan audit history
Goal: Make every planning decision reproducible from SQLite records.
Description: Store previous and new version references, structured differences, rationale, evidence, timestamps, actor or approval metadata, and rejection details without secrets. Add retrieval tests that reconstruct proposal, decision, and application history in order, including failed attempts and concurrent proposals.

## 62. Build fixed end-to-end evaluation scenarios
Goal: Create representative, repeatable cases for agent quality and safety.
Description: Add fixtures for fatigue, excessive load, missing HRV, missing power, insufficient history, an upcoming event, and constrained weekly schedules, each with explicit expected outcomes. Keep dates and model responses fixed and document which assertions are hard constraints versus qualitative expectations.

## 63. Evaluate skill selection, tool sequence, and metric accuracy
Goal: Detect regressions in how the agent chooses skills and obtains evidence.
Description: Build a repeatable evaluation runner that scores expected skill activation, allowed tool ordering, deterministic metric values, and prohibited model-side calculations across the fixed scenarios. Produce machine-readable and human-readable results, and test the evaluator itself with known pass and fail cases.

## 64. Evaluate structured output and coaching constraints
Goal: Verify that recommendations remain valid and obey all non-negotiable rules.
Description: Measure JSON validity, availability compliance, safety constraints, uncertainty disclosure, and the requirement for approval before any plan mutation. Require 100% deterministic-test compliance for hard availability and approval rules, while reporting qualitative coaching expectations separately.

## 65. Add safe local observability and final documentation
Goal: Make runs diagnosable and leave the MVP architecture and limitations explicit.
Description: Add configurable local logs or traces for errors, latency, tool activity, validation retries, and estimated local token usage, with tests that redact credentials, health data, prompts, and hidden reasoning. Update the README, architecture documents, and ADRs with verified behavior and limitations, and create a clearly deferred backlog for nutrition and Google Sheets work without implementing either feature.
