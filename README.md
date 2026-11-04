# Endurance Coach

Endurance Coach is a guided Python project for learning how
[Agent Skills](https://agentskills.io/specification) can support a local AI cycling trainer. Milestone
1 provides validated data contracts, deterministic cycling metrics, synthetic training data, one
example skill, and the public seams for an Ollama runtime.

The important gaps are intentional: skill discovery/loading and the Ollama agent loop are exercises,
not hidden framework code.

## Setup

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/), and optionally a local
[Ollama](https://ollama.com/) server for the runtime exercise.

```bash
uv sync
cp .env.example .env  # optional; export these values in your shell
uv run endurance-coach config
uv run endurance-coach metrics --ftp 250
```

The default model configuration is `qwen3:8b` at `http://localhost:11434`. Pull or choose a model
only when you start the agent-loop exercise; the completed scaffold does not contact Ollama.

Regenerate the committed deterministic fixture with:

```bash
uv run endurance-coach generate-data
```

## Tests

Passing scaffold tests:

```bash
uv run pytest -m "not exercise"
uv run ruff check .
```

The learner-owned specifications are marked `exercise` and are expected to fail initially:

```bash
uv run pytest -m exercise
```

Do not treat those failures as scaffold defects. Implement them in the order described in
[`docs/exercises.md`](docs/exercises.md). Afterward, `uv run pytest` should pass without exclusions.

## Scope

Milestone 1 deliberately excludes external training providers, SQLite, a web frontend, and multiple
agents. Synthetic JSON is the only data source. See [`docs/architecture.md`](docs/architecture.md)
for component boundaries and data flow.

