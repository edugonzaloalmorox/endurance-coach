## Commands

- `uv sync` - install dependencies
- `uv run pytest` - the whole suite
- `uv run pytest tests/test_home.py` - one test file

## Rules

- Dependencies are added in `pyproject.toml`. Do not add one without
  asking

## Documents

- `_docs/process.md` - how work is organized
- Before writing tests, read `_docs/testing-guidelines.md`
- For anything touching the UI, read `_docs/design-system.md`

## Roles

- PM - grooms a task before anyone implements it, follows `docs/agents/pm.md`
- Engineer - implements one groomed task, follows `docs/agents/software-engineer.md`
- QA Engineer - checks the result against the acceptance criteria, follows `docs/agents/qa-engineer.md`


## Python Documentation Standards

When writing or modifying Python code:

- Write complete Google-style docstrings for all public
  modules, classes, methods, and functions.
- Explain the purpose and behavior, not merely restate
  the function name.
- Document Args, Returns, Raises, and Yields where applicable.
- Include types and relevant constraints.
- Document important side effects and assumptions.
- Keep docstrings synchronized with code changes.
- Do not invent behavior that the implementation
  does not support.
- Avoid redundant docstrings for trivial private helpers.