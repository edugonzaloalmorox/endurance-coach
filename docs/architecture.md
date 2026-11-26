# Architecture

The design is intentionally small. Pydantic models form the boundaries, pure metric functions do the
cycling arithmetic, SQLite provides local persistence, and incremental product work connects
historical ingestion and Agent Skills to Ollama.

```text
FIT/FIT.GZ + Intervals.icu -> SQLite -> TrainingActivity -> deterministic metrics
                                                               |
user request -> AgentRuntime ----------------------------------+-> WorkoutRecommendation
                    |
                    +-> SkillLoader -> coach_skills/*/SKILL.md
                    +-> local Ollama model
```

Historical FIT/FIT.GZ ingestion populates the persistence foundation, with optional Strava-style
CSV rows adding descriptive metadata by archive-relative filename. Bounded Intervals.icu summary
retrieval, normalization, incremental persistence, and conservative reconciliation with historical
FIT/Strava activities are implemented. Recent persisted cycling summaries feed the local coaching
runtime. A read-only COROS MCP boundary now supports OAuth-aware tool discovery and bounded recovery
snapshot retrieval; deterministic normalization and automatic coaching-context supplementation
remain planned.

## Components

- `domain/models.py` defines strict contracts for activities, progressive skill representations,
  workout steps, and recommendations. Unexpected keys are rejected at boundaries.
- `analysis/metrics.py` contains deterministic, side-effect-free intensity factor, TSS, and summary
  functions. Missing power stays visible rather than being guessed.
- `fixtures/synthetic.py` creates ten rides spanning 14 calendar days. The same records are
  committed in `data/synthetic_activities.json` for inspection and repeatable tests.
- `storage/sqlite.py` owns the versioned schema, transactional initialization, foreign-key and data
  constraints, per-file import transactions, idempotent source hashes, bounded read-only
  inspection, and the privacy-limited recent-activity query used by coaching. It uses the Python
  standard library `sqlite3` module and `PRAGMA user_version`; no ORM or migration framework is
  present.
- `ingestion/fit.py` discovers archive-contained FIT/FIT.GZ inputs, bounds decompression, verifies
  FIT structure and CRCs with `fitdecode`, and normalizes summaries and original sensor samples into
  provider-neutral domain contracts.
- `ingestion/csv_metadata.py` safely reads bounded archive-contained CSV metadata and indexes valid
  rows by their FIT filename without treating CSV summaries as sensor measurements.
- `integrations/intervals.py` retrieves and normalizes read-only activity summaries in bounded date
  windows while preserving missing fields and source identity.
- `integrations/coros.py` uses the official MCP SDK for OAuth and Streamable HTTP, persists tokens
  in an ignored owner-only local file, discovers tools through a strict read allowlist, and retrieves
  bounded raw recovery observations without exposing COROS write or FIT-download operations.
- `services/historical_import.py` coordinates independent file imports, dry-run validation, safe
  failure recording, and aggregate reporting without exposing archive paths or measurements.
- `services/intervals_sync.py` applies overlap windows and advances sync state only in the same
  transaction as a successful idempotent activity batch.
- `domain/reconciliation.py` selects only unique exact-identity or compatible time-and-duration
  matches. Intervals.icu becomes the canonical summary while FIT measurements and source provenance
  remain attached; ambiguous candidates stay separate.
- `config.py` loads local database, archive, Intervals.icu, and Ollama settings. Intervals
  credentials may come from process variables or a small repository-local `.env` parsed as data,
  never executed; loading configuration performs no network I/O.
- `skills/loader.py` discovers validated metadata from immediate runtime-skill directories and
  explicitly loads one selected instruction body while rejecting unsafe names and escaping paths.
- `llm/context.py`, `llm/protocol.py`, and `llm/runtime.py` separately own evidence assembly,
  validated tool/message handling, and the bounded `AgentRuntime` loop. `llm/errors.py` defines the
  safely reportable failure boundary.
- `coach_skills/plan-workout/SKILL.md` and `coach_skills/analyze-training/SKILL.md` follow the Agent
  Skills directory and frontmatter rules. The first guides next-workout requests; the second keeps
  observed facts, interpretations, and unavailable training evidence distinct. At discovery time
  only `name` and `description` are loaded; instructions are loaded on demand.
- `cli.py` exposes the database operations and `ask`, which passes bounded recent local activity
  summaries to `AgentRuntime` and prints only a validated recommendation or safe error.

## Persistence boundary

Schema version 1 contains exactly seven product tables: `activities`, `activity_sources`,
`activity_records`, `activity_metrics`, `athlete_profiles`, `wellness`, and `sync_state`.
`activity_sources.activity_id` is nullable so a later importer can record a failed or unmatched
artifact without manufacturing an activity. Time-series measurements are nullable and retain a
session and record index; ingestion will preserve the source sampling frequency rather than
resampling at this boundary.

The schema distinguishes measured, estimated, derived, and unavailable metric origins. Effective
dates on athlete profiles support later selection of historically valid FTP and weight. Database
initialization is idempotent and rejects schema versions newer than the application supports.

The status CLI reports only schema version and row counts. The bounded inspection CLI adds recent
normalized summaries and source types but excludes descriptions, source paths, raw records, and GPS
coordinates. Configured paths and credentials are never included. Real archives and generated
analytical files are ignored by Git;
approved synthetic test fixtures are the only permitted format-specific exceptions.

## Boundaries

`SkillLoader.discover()` must inspect only immediate skill directories, validate frontmatter, and
return metadata. `load_skill()` is the only operation that should expose Markdown instructions.

`AgentRuntime.run()` owns conversation messages and bounded tool-call iteration. It exposes one
narrow `load_skill` tool, places returned instructions into the conversation only after activation,
stops on a final answer, parses JSON, and validates it with `WorkoutRecommendation`. One invalid
structured response receives bounded correction feedback before the remaining step limit. Raw missing
measurements remain `null`, deterministic summary metrics and their configured FTP input come from
Python, and model thinking is neither requested nor copied into message history. It never silently
invents activities or power.

No networking occurs in metrics, model validation, skill loading, or sample-data generation. Ollama
is the sole model network boundary and is expected to run locally.

## Development boundary

Development agents change and verify the repository using the optional guidance in
[`process.md`](process.md) and [`agents/`](agents/). They are separate from the product's runtime
coaching agent shown above. The runtime agent loads coaching skills and produces validated
recommendations without gaining authority to apply training-plan changes.

