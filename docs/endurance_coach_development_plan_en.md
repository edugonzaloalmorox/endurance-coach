# Endurance Coach — Guided Development Plan

**Technical goal:** learn to build an agent with Agent Skills, progressive loading, tool calling, MCP, structured data, evaluation, and human approval workflows.

**Sports goal:** recommend weekly long-distance cycling workouts, adjust them daily based on training load and recovery, and improve the ability to sustain performance under fatigue.

**Working approach:** Codex prepares scaffolding, contracts, fixtures, and tests; you implement the key mechanisms; the assistant reviews architecture, decisions, and code. Use one agent with a local Ollama model and deterministic Python metrics and validation. Do not introduce agent orchestration frameworks in M1.

## Cross-cutting requirements

- COROS activities are already synced to Intervals.icu: Intervals.icu will be the primary source for activities and power; COROS MCP will provide supplementary data after verifying which tools are actually available.
- Power data is available for nearly all rides; do not assume that complete time-series data is available for every activity.
- Default availability: **9 hours/week**, Mon 1 h, Tue 1 h, Wed 1 h, Thu 1 h, Fri 1 h, Sat 3 h, Sun 1 h. Allow weekly overrides. This includes strength training.
- Strength-training frequency varies by training phase; sessions are entered manually through the CLI.
- The main goal is continuous improvement in endurance and *durability*, with optional event-specific periodization.
- Weekly planning with daily adjustments. Combine a short subjective recovery check-in with COROS data.
- No plan changes without explicit approval; store plans and audit history in SQLite.
- Nutrition and Google Sheets are out of scope for this MVP.

## Target end-to-end workflow

1. Sync activities from Intervals.icu; retrieve supplementary COROS data without double-counting workouts.
2. Compute training load, volume, power, trends, and data limitations using deterministic functions.
3. Record availability and strength sessions manually; complete the daily recovery check-in.
4. The agent discovers skills and loads their instructions on demand.
5. Skills guide Python tool calls to analyze performance, assess recovery, and propose a plan.
6. Validators check the plan and constraints; the system presents evidence, uncertainty, and rationale.
7. Initial plans and proposed changes are saved or applied only after explicit approval, with a revision history.

## M0 — Repository setup

| ID | Task | Owner | Acceptance criteria |
|---|---|---|---|
| M0-01 | Inspect the repository and agree on a minimal structure with `uv`, `src/`, `tests/`, `coach_skills/`, and `data/` | Codex + you | Structure agreed; no unnecessary empty modules |
| M0-02 | Define Pydantic contracts for activities, skills, tools, and recommendations | You (design), Codex (scaffolding) | Types and units documented; optional fields explicit |
| M0-03 | Configure Ruff, pytest, `.env.example`, `.gitignore`, README, and a basic CLI | Codex | Reproducible local setup; lint and tests runnable |
| M0-04 | Define contribution instructions (`AGENTS.md`) and distinguish Codex skills from application skills | You + Codex | Documentation clearly separates the two skill layers |

**M0 completion gate:** `uv sync`, `uv run pytest`, and `uv run ruff check .` work with the scaffold, or intentionally pending tests are identified precisely.

## M1 — Skills Foundation (no external services)

| ID | Task | Owner | Dependency / acceptance criteria |
|---|---|---|---|
| M1-01 | Create a synthetic 14-day dataset with power, heart rate, intensities, rest days, and missing fields | Codex | Fixed reference dates; clearly labeled synthetic data |
| M1-02 | Implement pure functions for 7-/14-day volume, active days, intensity, hard sessions, and weekly trends | Codex; reviewed by you | Reproducible tests and documented units |
| M1-03 | Create `coach_skills/plan-workout/SKILL.md` with frontmatter, a procedure, and safety/uncertainty guidance | **You** | Skill defines a procedure; does not perform calculations |
| M1-04 | Write tests and skeletons for `SkillLoader` (discovery, metadata, explicit loading, safe paths) | Codex | Pending tests identified and isolated |
| M1-05 | Implement `SkillLoader.list_skills()` and `load_skill()` with progressive loading | **You** | Full instructions stay out of context until activation; path traversal blocked |
| M1-06 | Write mocks/tests for the Ollama loop: tool calls, failures, and step limits | Codex | Tests do not require a live Ollama server |
| M1-07 | Implement the agent loop, including messages, tool selection, tool results, errors, and iteration limits | **You** | Activates a skill and uses computed metrics instead of calculating them in the LLM |
| M1-08 | Expose CLI commands: `skills list`, `skills show`, `ask "What should I train tomorrow?"`, `--debug` | You + Codex | Local end-to-end flow; observable decision trace without exposing hidden reasoning |
| M1-09 | Validate JSON output with Pydantic, including bounded retries and warnings | **You** | Valid duration/intensity/type/rationale; missing data handled |
| M1-10 | Review tests and README; explain skill vs. tool vs. agent loop in your own words | You + assistant | pytest and Ruff pass; live Ollama execution verified or limitation clearly stated |

**M1 completion gate:** `endurance-coach ask "What should I train tomorrow?"` produces a JSON recommendation using synthetic data and a skill loaded on demand; tests pass without a real model.

## M2 — Real data integrations and the `analyze-training` skill

| ID | Task | Owner | Acceptance criteria |
|---|---|---|---|
| M2-01 | Inspect current documentation and real responses from Intervals.icu and COROS; document limitations | You + Codex | Schemas, authentication, and endpoints verified; no invented tools |
| M2-02 | Build a read-only Intervals.icu connector with environment-based credentials, error handling, and pagination | **You**; Codex writes tests | Retrieves relevant activities and training metadata |
| M2-03 | Build a read-only COROS MCP connector (OAuth, tool discovery, allowlist) | **You**; Codex provides fixtures | Uses only tools actually available; no write operations |
| M2-04 | Normalize dates, units, IDs, zones, power, and heart rate; reconcile duplicates and preserve provenance | You + Codex | Same session is never counted twice; source traceability preserved |
| M2-05 | Add SQLite storage for normalized activities and incremental sync state | Codex scaffolding; you implement logic | Idempotent sync and failure recovery |
| M2-06 | Create `analyze-training/SKILL.md` and tests for choosing between two skills | **You** | Agent can select and combine `analyze-training` and `plan-workout` |

**M2 completion gate:** repeatable real-data sync without duplicates, with power and heart-rate fields attributed to their sources; integration tests use mocked responses.

## M3 — Performance, recovery, and the `assess-recovery` skill

| ID | Task | Owner | Acceptance criteria |
|---|---|---|---|
| M3-01 | Implement deterministic metrics: load, volume, power-duration curve when available, and performance comparisons under accumulated fatigue | You (design), Codex (tests), you (implementation) | Metrics include units, period, sample size, and provenance; no fabricated scores |
| M3-02 | Analyze *durability* using power, time, and kJ when time-series data is available | **You** | Valid comparisons and documented limitations |
| M3-03 | Assess recovery using individual sleep, HRV, and resting-heart-rate trends where data is accessible | You + Codex | Missing metrics remain unknown |
| M3-04 | Implement a CLI `check-in` for fatigue, soreness, and readiness (1–10), saved with a date | **You** | Validated and persisted input |
| M3-05 | Create the `assess-recovery` skill and uncertainty-handling rules | **You** | No diagnoses or decisions based on a single signal |
| M3-06 | Create test scenarios for fatigue, missing power, and insufficient data | Codex | Edge-case tests and appropriately cautious recommendations |

**M3 completion gate:** an explainable report distinguishes observations, hypotheses, and insufficient evidence; recovery informs recommendations without clinical conclusions.

## M4 — Weekly planning, strength, and events

| ID | Task | Owner | Acceptance criteria |
|---|---|---|---|
| M4-01 | Define an athlete profile with goals, FTP, zones, optional events, and editable weekly availability | You + Codex | Persisted, validated settings |
| M4-02 | Build a CLI for logging strength training: exercise, sets, reps, kg, and optional RPE | **You** | Validated history can be viewed and edited |
| M4-03 | Implement a deterministic constraint engine for the default 9 h/week, daily limits, rest, and strength load | You + Codex | Rejects impossible plans; flags risk and uncertainty |
| M4-04 | Extend `plan-workout` to propose seven days with duration, intensity, objective, and evidence | **You** | Structured plan, valid total hours, flexible strength frequency |
| M4-05 | Support continuous improvement and event preparation modes (optional date/distance/elevation) | You | No event required to receive recommendations |
| M4-06 | Persist plans and versions in SQLite and display them through the CLI | Codex scaffolding; you implement logic | Plans can be retrieved by week and version |

**M4 completion gate:** the agent proposes a week that meets availability and training constraints; plans are reviewed before becoming active.

## M5 — Daily adjustments and human approval

| ID | Task | Owner | Acceptance criteria |
|---|---|---|---|
| M5-01 | Compare planned sessions with completed sessions and daily recovery | You | Differences explained with data and dates |
| M5-02 | Create the `adjust-plan` skill that produces proposals, never direct changes | **You** | Rationale includes impact on the rest of the week |
| M5-03 | Implement `proposed`, `approved`, `rejected`, and `applied` states with valid transitions | **You**; Codex writes tests | No write path without approval |
| M5-04 | Expose CLI commands: `plan proposals`, `approve <id>`, and `reject <id>` | You + Codex | Explicit interaction; rejection preserves the previous plan |
| M5-05 | Implement SQLite auditing: previous/new versions, rationale, timestamp, and approval | You | Reproducible history; idempotent operations |
| M5-06 | Add safety tests for unapproved writes, failures/rollback, and retries | Codex + you | Invalid flow and basic concurrency tests |

**M5 completion gate:** an agent-proposed adjustment is approved by the user and applied with full history; rejection leaves the plan unchanged.

## M6 — Evaluation and quality

| ID | Task | Owner | Acceptance criteria |
|---|---|---|---|
| M6-01 | Build a scenario suite: fatigue, excessive training load, missing HRV, events, and constrained schedules | You (criteria), Codex (fixtures) | Representative cases with expected outcomes |
| M6-02 | Evaluate skill selection, tool sequence, metric accuracy, and JSON validity | **You** | Repeatable success and regression metrics |
| M6-03 | Evaluate training safety and adherence to availability/approval constraints | You | 100% compliance with hard constraints in deterministic tests |
| M6-04 | Add local observability: errors, estimated local token costs, latency, and traces without sensitive data | Codex + you | Useful configurable logs without secrets |
| M6-05 | Update architecture, limitations, and decisions; create a nutrition/Google Sheets backlog | You + Codex | README and architecture decision records (ADRs) updated |

**M6 completion gate:** every agent version can be checked against fixed scenarios without regressing on critical rules.

## Implementation order and dependencies

`M0 → M1 → M2 → M3 → M4 → M5 → M6`

M4 may be prototyped using synthetic data before M3 is finished, but introduce new skills and services incrementally. Do not connect real data sources until M1 demonstrates skill discovery, activation, tool calling, and validation.

## Definition of Done for each task

- Code integrated with clear interfaces and typing.
- Relevant tests (normal behavior, errors, missing data) and Ruff executed.
- Contracts and README updated when behavior changes.
- Claims of successful live execution only when actually tested.
- Understanding demonstrated: you can explain the inputs, outputs, failures, and why each piece of logic belongs in a skill, tool, or Python service.

## First work block — next development session

1. Codex: complete M0-01 through M0-04 and M1-01/M1-02/M1-04/M1-06, without implementing the mechanisms reserved for you.
2. You: inspect the tests and create M1-03 (`SKILL.md`).
3. You: implement M1-05 (`SkillLoader`).
4. Review together: frontmatter, path security, progressive disclosure, and tests.
5. Proceed to M1-07 (agent loop) only after `SkillLoader` passes its tests.

## Out of scope for the MVP

Nutrition, Google Sheets food records, frontend, multiple agents, RAG/vector databases, write-back synchronization to COROS/Intervals.icu, and autonomous changes without approval.
