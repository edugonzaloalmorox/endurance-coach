# Architecture

The design is intentionally small. Pydantic models form the boundaries, pure metric functions do the
cycling arithmetic, and two learner-owned classes will eventually connect an Agent Skill to Ollama.

```text
synthetic JSON -> TrainingActivity -> deterministic metrics
                                      |
user request -> AgentRuntime ---------+-> WorkoutRecommendation
                    |
                    +-> SkillLoader -> coach_skills/*/SKILL.md
                    +-> local Ollama model
```

## Components

- `models.py` defines strict contracts for activities, progressive skill representations, workout
  steps, and recommendations. Unexpected keys are rejected at boundaries.
- `metrics.py` contains deterministic, side-effect-free intensity factor, TSS, and summary functions.
  Missing power stays visible rather than being guessed.
- `sample_data.py` creates ten rides spanning 14 calendar days. The same records are committed in
  `data/synthetic_activities.json` for inspection and repeatable tests.
- `skills.py` defines `SkillLoader`. Both methods are intentionally unimplemented.
- `runtime.py` defines `AgentRuntime`. Output validation is implemented; the Ollama tool loop is not.
- `coach_skills/plan-workout/SKILL.md` follows the Agent Skills directory and frontmatter rules. At
  discovery time only `name` and `description` should be loaded; instructions are loaded on demand.
- `cli.py` exposes safe scaffold operations. It deliberately has no `coach` command yet.

## Boundaries

`SkillLoader.discover()` must inspect only immediate skill directories, validate frontmatter, and
return metadata. `load_skill()` is the only operation that should expose Markdown instructions.

`AgentRuntime.run()` owns conversation messages and tool-call iteration. It should expose one narrow
`load_skill` tool, place returned instructions into the conversation, stop on a final answer, parse
JSON, and validate it with `WorkoutRecommendation`. It must not silently invent activities or power.

No networking occurs in metrics, model validation, skill loading, or sample-data generation. Ollama
is the sole future network boundary and is expected to run locally.

