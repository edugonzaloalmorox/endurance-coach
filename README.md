# Endurance Coach

Endurance Coach is a Python AI cycling coach for long-distance training, developed through a Dark
Software Factory in which PM, Engineer, Documentation Impact Gate, and QA stages turn approved
GitHub issues into reproducible, independently verified changes. The current product includes
validated data contracts, deterministic cycling metrics, synthetic training data, one runtime
coaching skill, a versioned local SQLite schema, and the public seams for a local Ollama runtime.

Development-agent instructions and Codex skills guide repository work. They are separate from the
application's runtime coaching skills in `coach_skills/`, which guide the local coach while it is
running. See [`AGENTS.md`](AGENTS.md) and [`docs/process.md`](docs/process.md) for the factory roles,
gates, and evidence requirements.

## Setup

Requirements: Python 3.12+ and [uv](https://docs.astral.sh/uv/). A local
[Ollama](https://ollama.com/) server is optional and is not contacted by the setup or test commands.

```bash
git clone https://github.com/edugonzaloalmorox/endurance-coach.git
cd endurance-coach
uv sync
cp .env.example .env  # optional; alternatively export the values in your shell
uv run endurance-coach config
uv run endurance-coach db init
uv run endurance-coach db status
uv run endurance-coach metrics --ftp 250
```

The default local model configuration is `qwen3:8b` at `http://localhost:11434`. Pull or select a
model only when working on an issue that exercises the Ollama agent loop.

The database defaults to `data/endurance_coach.sqlite3`. Override it with
`ENDURANCE_COACH_DB_PATH`. `ENDURANCE_COACH_ARCHIVE_PATH` reserves a configurable location for the
historical importer; the current database commands do not read that archive. Their JSON output
contains only the schema version and per-table row counts, never configured paths or measurements.

Regenerate the committed deterministic fixture with:

```bash
uv run endurance-coach generate-data
```

## Verification

Run the full suite and lint checks:

```bash
uv run pytest
uv run pytest -m "not exercise"
uv run ruff check .
```

The full suite collects five deferred executable specifications as strict expected failures. Each is
linked to its owning implementation issue in the test marker and in
[`docs/exercises.md`](docs/exercises.md). Strict mode keeps the assertions visible and makes an
unexpected pass fail the suite until the owning issue removes its marker. Verification evidence must
report all expected failures explicitly; see
[`docs/testing-guidelines.md`](docs/testing-guidelines.md).

Before independent QA, every factory change also needs a Documentation Impact Report for its exact
candidate commit. The tracked [`docs-sync` skill](.agents/skills/docs-sync/SKILL.md) updates only
materially affected documentation or records a justified `NO_DOC_CHANGE`; the deterministic
validator blocks missing, stale, malformed, or `BLOCKED` evidence. This development gate does not
replace independent QA or hosted CI.

## Scope and safety

The MVP excludes nutrition, Google Sheets, web frontends, multiple product/runtime coaching agents,
and autonomous workout-plan changes. Those product exclusions do not exclude the PM, Engineer, and
QA development agents used by the factory. Synthetic JSON remains the only implemented activity
source. The SQLite foundation is implemented, while historical FIT/CSV ingestion and external
provider synchronization remain planned backlog work.

Real training archives, generated databases, FIT/GPX files, and Parquet files are excluded from
version control. Only explicitly approved synthetic fixtures under `tests/fixtures/` may opt back in
to the file-format ignore rules.

The coach may propose a workout-plan modification, but it must never apply one without the athlete's
explicit approval. See [`docs/architecture.md`](docs/architecture.md) for component boundaries and
data flow.

