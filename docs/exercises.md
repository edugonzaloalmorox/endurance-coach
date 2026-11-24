# Runtime executable specifications

The formerly deferred runtime specifications for issues 18 and 19 are now implemented as ordinary
passing tests in `tests/test_runtime_exercise.py`. They cover missing activity data, dated context,
visible missing measurements, deterministic metrics, progressive skill loading, typed tool results,
message ordering, safe failures, and the configured step limit from issues 18–20.

Malformed-output repair and bounded retries remain assigned to
[#23](https://github.com/edugonzaloalmorox/endurance-coach/issues/23); the current runtime rejects an
invalid final recommendation immediately and visibly.

## Verification

Run `uv run pytest` and `uv run ruff check .`.

