# Endurance Coach

Endurance Coach is a local Python AI cycling coach for long-distance training. Development follows
an implementation-first workflow: build the requested behavior, demonstrate it, add essential
tests, and run the final test and lint checks. The current product includes
validated data contracts, deterministic cycling metrics, synthetic training data, runtime skills
for workout planning and training analysis, a versioned local SQLite schema, and the public seams
for a local Ollama runtime.

Development-agent instructions and Codex skills guide repository work. They are separate from the
application's runtime coaching skills in `coach_skills/`, which guide the local coach while it is
running. See [`AGENTS.md`](AGENTS.md) and [`docs/process.md`](docs/process.md) for development and
safety guidance.

## Setup

Requirements: Python 3.12+ and [uv](https://docs.astral.sh/uv/). A running local
[Ollama](https://ollama.com/) server is required only for `ask`; setup and automated tests do not
contact it.

```bash
git clone https://github.com/edugonzaloalmorox/endurance-coach.git
cd endurance-coach
uv sync
cp .env.example .env  # optional; alternatively export the values in your shell
uv run endurance-coach config
uv run endurance-coach db init
uv run endurance-coach db status
uv run endurance-coach db inspect --limit 20
uv run endurance-coach db import-fit /path/to/archive --dry-run
uv run endurance-coach db import-fit /path/to/archive
uv run endurance-coach db sync-intervals --oldest 2026-01-01
make update-db
uv run endurance-coach coros discover
uv run endurance-coach coros recovery --days 7
uv run endurance-coach ask "Based on my last workouts, what should I focus next"
uv run endurance-coach metrics --ftp 250
```

The default local model configuration is `qwen3:8b` at `http://localhost:11434`. Pull or select a
model only when working on functionality that exercises the Ollama agent loop. The coach requests a
16,384-token context window so recent activity evidence, skill instructions, and the structured
recommendation contract are not truncated; override it with `OLLAMA_NUM_CTX` when the selected
model or available memory requires a different bounded value. Each model response is capped at
1,200 tokens; override the bound with `OLLAMA_NUM_PREDICT`.

`ask` reads up to 50 recent cycling summaries from the local database, computes metrics in Python,
loads the relevant planning or analysis skill on demand, and returns a validated workout
recommendation as JSON. Use
`--limit` to request a smaller history. Missing power, distance, elevation, intensity category, and
perceived exertion remain unavailable rather than being inferred. The command sends data only to
the configured local Ollama endpoint and never changes the database or a workout plan.

The database defaults to `data/endurance_coach.sqlite3`. Override it with
`ENDURANCE_COACH_DB_PATH`. Set `ENDURANCE_COACH_ARCHIVE_PATH` or pass an archive path to
`db import-fit`. The importer recursively reads FIT and FIT.GZ files without modifying them,
deduplicates raw and decompressed content, records per-file failures, and writes each valid file in
one SQLite transaction. When an archive-root `activities.csv` is present (or `--metadata-csv` names
one inside the archive), English or Spanish Strava export rows are matched by their filename column
and add descriptive name, description, and activity type without replacing FIT measurements. Manual
activities and unsupported file formats in the CSV are ignored rather than reported as malformed
FIT metadata. `--dry-run` parses inputs without changing the database. Import and status output
contains only aggregate counts or safe schema metadata, never configured paths or measurements.

`db inspect` returns schema counts and recent normalized activity summaries, newest first. The
optional `--limit` accepts 1 through 100 (default 20). Inspection is read-only and omits
descriptions, source paths, raw records, and GPS coordinates.

Set `INTERVALS_ICU_API_KEY` and optionally `INTERVALS_ICU_ATHLETE_ID` before the first read-only
sync. They may be exported or stored in the repository-local ignored `.env`; process variables take
precedence. `INTERVALS_API_KEY` is also accepted as a compatibility alias. The initial
`db sync-intervals` requires `--oldest`; later runs resume with a seven-day overlap and atomically
upsert summaries, reconcile unambiguous FIT/Strava duplicates, and advance the successful cursor.
Intervals.icu supplies the canonical activity identity and non-null summary fields; original FIT
sensor records and all source provenance remain attached. Matching uses exact source identities or
a unique start-time and duration match. Ambiguous or materially different activities remain
separate. Sync output includes the privacy-safe number of reconciled activities. No provider data
is written back.

The optional COROS integration uses the official single-user MCP service for supplementary health
and recovery observations. Run `uv run endurance-coach coros discover` for the initial OAuth flow:
the command opens COROS in your browser and receives the authorization response on a temporary
loopback listener. OAuth state is stored locally in the ignored
`data/coros_oauth.json` file with owner-only permissions; override its location with
`COROS_OAUTH_STATE_PATH`. European, US, and mainland-China accounts can set `COROS_MCP_URL` to the
corresponding official regional endpoint.

`coros discover` reports which verified read tools are available and which advertised tools are
blocked. `coros recovery --days 7` retrieves bounded sleep, HRV, resting-heart-rate, stress,
recovery-status, and training-load observations when those tools are available. The client never
calls COROS workout or training-plan creation/update tools, never downloads GPS-bearing FIT files,
and does not yet feed the recovery snapshot into `ask` automatically.

Run `make update-db` at the start of each fresh local session to update the database through today.
For a brand-new database, bootstrap it once with
`./scripts/update_database.sh --oldest YYYY-MM-DD`; subsequent runs need no arguments. A failed
provider request exits nonzero and does not advance the last successful sync cursor.

Regenerate the committed deterministic fixture with:

```bash
uv run endurance-coach generate-data
```

## Verification

Run the full suite and lint checks:

```bash
uv run pytest
uv run ruff check .
```

The scripted runtime tests exercise the local-model protocol without contacting an Ollama server.
They verify dated deterministic context, progressive skill loading, final recommendation validation,
and bounded safe failures. See [`docs/exercises.md`](docs/exercises.md) and
[`docs/testing-guidelines.md`](docs/testing-guidelines.md).

## Scope and safety

The MVP excludes nutrition, Google Sheets, web frontends, multiple product/runtime coaching agents,
automatic COROS-to-coaching supplementation, and autonomous workout-plan changes. Historical
FIT/FIT.GZ and read-only
Intervals.icu summaries in SQLite are the coaching workflow's activity source; deterministic
synthetic JSON remains available for tests and examples.

Real training archives, generated databases, FIT/GPX files, and Parquet files are excluded from
version control. Only explicitly approved synthetic fixtures under `tests/fixtures/` may opt back in
to the file-format ignore rules.

The coach may propose a workout-plan modification, but it must never apply one without the athlete's
explicit approval. See [`docs/architecture.md`](docs/architecture.md) for component boundaries and
data flow.

