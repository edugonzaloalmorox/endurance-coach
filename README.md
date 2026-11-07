# Endurance Coach

Endurance Coach is a Python AI cycling coach for long-distance training, developed through a Dark
Software Factory in which PM, Engineer, and QA agents turn approved GitHub issues into reproducible,
independently verified changes. The current product includes validated data contracts,
deterministic cycling metrics, synthetic training data, one runtime coaching skill, and the public
seams for a local Ollama runtime.

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
uv run endurance-coach metrics --ftp 250
```

The default local model configuration is `qwen3:8b` at `http://localhost:11434`. Pull or select a
model only when working on an issue that exercises the Ollama agent loop.

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

## Scope and safety

The MVP excludes nutrition, Google Sheets, web frontends, multiple product/runtime coaching agents,
and autonomous workout-plan changes. Those product exclusions do not exclude the PM, Engineer, and
QA development agents used by the factory. Synthetic JSON is the current data source; external
training providers and persistence are introduced only by their approved backlog issues.

The coach may propose a workout-plan modification, but it must never apply one without the athlete's
explicit approval. See [`docs/architecture.md`](docs/architecture.md) for component boundaries and
data flow.

