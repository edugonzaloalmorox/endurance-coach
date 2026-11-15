# Architecture

The design is intentionally small. Pydantic models form the boundaries, pure metric functions do the
cycling arithmetic, SQLite provides local persistence, and incremental product work connects
historical ingestion and Agent Skills to Ollama.

```text
synthetic JSON -> TrainingActivity -> deterministic metrics
                                      |
                                      +-> SQLite schema
                                      |
user request -> AgentRuntime ---------+-> WorkoutRecommendation
                    |
                    +-> SkillLoader -> coach_skills/*/SKILL.md
                    +-> local Ollama model
```

Historical FIT/FIT.GZ ingestion populates the persistence foundation. CSV metadata association,
Intervals.icu synchronization, retrieval tools, and database-backed coaching remain planned.

## Components

- `models.py` defines strict contracts for activities, progressive skill representations, workout
  steps, and recommendations. Unexpected keys are rejected at boundaries.
- `metrics.py` contains deterministic, side-effect-free intensity factor, TSS, and summary functions.
  Missing power stays visible rather than being guessed.
- `sample_data.py` creates ten rides spanning 14 calendar days. The same records are committed in
  `data/synthetic_activities.json` for inspection and repeatable tests.
- `storage/sqlite.py` owns the versioned schema, transactional initialization, foreign-key and data
  constraints, per-file import transactions, idempotent source hashes, and privacy-safe status
  inspection. It uses the Python standard library `sqlite3` module and `PRAGMA user_version`; no ORM
  or migration framework is present.
- `ingestion/fit.py` discovers archive-contained FIT/FIT.GZ inputs, bounds decompression, verifies
  FIT structure and CRCs with `fitdecode`, and normalizes summaries and original sensor samples into
  provider-neutral domain contracts.
- `services/historical_import.py` coordinates independent file imports, dry-run validation, safe
  failure recording, and aggregate reporting without exposing archive paths or measurements.
- `config.py` loads local database and optional archive paths independently from Ollama settings.
- `skills.py` defines `SkillLoader`. Both methods are intentionally unimplemented.
- `runtime.py` defines `AgentRuntime`. Output validation is implemented; the Ollama tool loop is not.
- `coach_skills/plan-workout/SKILL.md` follows the Agent Skills directory and frontmatter rules. At
  discovery time only `name` and `description` should be loaded; instructions are loaded on demand.
- `cli.py` exposes safe scaffold operations plus `db init`, `db status`, and `db import-fit`. It has
  no provider synchronization or coaching command yet.

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

The CLI reports only schema version and row counts. Configured paths, measurements, GPS coordinates,
and credentials are not included. Real archives and generated analytical files are ignored by Git;
approved synthetic test fixtures are the only permitted format-specific exceptions.

## Boundaries

`SkillLoader.discover()` must inspect only immediate skill directories, validate frontmatter, and
return metadata. `load_skill()` is the only operation that should expose Markdown instructions.

`AgentRuntime.run()` owns conversation messages and tool-call iteration. It should expose one narrow
`load_skill` tool, place returned instructions into the conversation, stop on a final answer, parse
JSON, and validate it with `WorkoutRecommendation`. It must not silently invent activities or power.

No networking occurs in metrics, model validation, skill loading, or sample-data generation. Ollama
is the sole future network boundary and is expected to run locally.

## Development boundary

Development agents change and verify the repository using the optional guidance in
[`process.md`](process.md) and [`agents/`](agents/). They are separate from the product's runtime
coaching agent shown above. The runtime agent loads coaching skills and produces validated
recommendations without gaining authority to apply training-plan changes.

