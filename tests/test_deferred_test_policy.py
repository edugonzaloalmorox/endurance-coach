"""Verify the repository's exceptional deferred-test policy."""

import ast
import re
from pathlib import Path

import pytest

EXPECTED_DEFERRED_TESTS = {
    "tests/test_skills_exercise.py::test_skill_discovery_returns_metadata_only": "#15",
    "tests/test_skills_exercise.py::test_skill_is_loaded_progressively_only_when_requested": "#16",
    "tests/test_skills_exercise.py::test_missing_skill_has_a_clear_error": "#16",
    (
        "tests/test_runtime_exercise.py::"
        "test_runtime_executes_skill_tool_call_and_validates_final_output"
    ): "#19",
    "tests/test_runtime_exercise.py::test_runtime_refuses_to_plan_without_activity_data": "#18",
}


def _qualified_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _qualified_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _marker_name(decorator: ast.expr) -> str | None:
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    return _qualified_name(target)


def _literal_keyword(call: ast.Call, name: str):
    for keyword in call.keywords:
        if keyword.arg == name:
            try:
                return ast.literal_eval(keyword.value)
            except (ValueError, TypeError):
                return None
    return None


def _policy_errors(
    sources: dict[str, str], expected_tests: dict[str, str]
) -> list[str]:
    errors: list[str] = []
    xfail_tests: dict[str, list[ast.expr]] = {}
    exercise_tests: set[str] = set()
    xfail_references = 0

    for path, source in sources.items():
        tree = ast.parse(source, filename=path)
        xfail_references += sum(
            _qualified_name(node) == "pytest.mark.xfail"
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
        )

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _qualified_name(node.func) == "pytest.skip":
                errors.append(f"{path} calls pytest.skip")
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue

            test_id = f"{path}::{node.name}"
            markers = [(_marker_name(item), item) for item in node.decorator_list]
            if any(name in {"pytest.mark.skip", "pytest.mark.skipif"} for name, _ in markers):
                errors.append(f"{test_id} uses a skip marker")
            if any(name == "pytest.mark.exercise" for name, _ in markers):
                exercise_tests.add(test_id)
            for name, decorator in markers:
                if name == "pytest.mark.xfail":
                    xfail_tests.setdefault(test_id, []).append(decorator)

    expected_ids = set(expected_tests)
    actual_ids = set(xfail_tests)
    for test_id in sorted(expected_ids - actual_ids):
        errors.append(f"{test_id} is missing its strict xfail")
    for test_id in sorted(actual_ids - expected_ids):
        errors.append(f"{test_id} has an unexpected xfail")
    for test_id in sorted(expected_ids - exercise_tests):
        errors.append(f"{test_id} is missing the exercise marker")
    for test_id in sorted(exercise_tests - expected_ids):
        errors.append(f"{test_id} has an unexpected exercise marker")

    decorator_count = sum(len(decorators) for decorators in xfail_tests.values())
    if xfail_references != decorator_count:
        errors.append("xfail references must appear only as test decorators")

    for test_id in sorted(expected_ids & actual_ids):
        decorators = xfail_tests[test_id]
        if len(decorators) != 1:
            errors.append(f"{test_id} must have exactly one xfail marker")
            continue
        decorator = decorators[0]
        if not isinstance(decorator, ast.Call):
            errors.append(f"{test_id} xfail marker must declare strict=True and a reason")
            continue

        strict = _literal_keyword(decorator, "strict")
        if strict is not True:
            errors.append(f"{test_id} xfail marker is not strict=True")

        reason = _literal_keyword(decorator, "reason")
        owner = expected_tests[test_id]
        if not isinstance(reason, str):
            errors.append(f"{test_id} xfail reason must be a literal string")
            continue
        issue_references = re.findall(r"#\d+", reason)
        if not issue_references or set(issue_references) != {owner}:
            errors.append(f"{test_id} xfail reason must identify only owner {owner}")
        removal_text = f"remove this marker when {owner} implements"
        if removal_text not in reason.lower():
            errors.append(f"{test_id} xfail reason must require removal by {owner}")

    return errors


def _valid_source(owner: str = "#15") -> str:
    return f'''import pytest

@pytest.mark.exercise
@pytest.mark.xfail(
    strict=True,
    reason="Deferred to {owner}; remove this marker when {owner} implements the behavior.",
)
def test_owned():
    assert True
'''


def test_repository_deferred_tests_follow_policy():
    sources = {
        path.as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(Path("tests").rglob("test_*.py"))
    }

    assert _policy_errors(sources, EXPECTED_DEFERRED_TESTS) == []


@pytest.mark.parametrize(
    ("source", "expected_error"),
    [
        (
            "import pytest\n@pytest.mark.exercise\ndef test_owned(): assert True\n",
            "missing its strict xfail",
        ),
        (_valid_source().replace("strict=True", "strict=False"), "not strict=True"),
        (
            _valid_source().replace("Deferred to #15", "Deferred to #16"),
            "identify only owner #15",
        ),
        (
            _valid_source().replace(
                "Deferred to #15; remove this marker when #15 implements the behavior.",
                "Deferred behavior; remove this marker when its owner implements.",
            ),
            "identify only owner #15",
        ),
        (
            _valid_source().replace("remove this marker when #15 implements", "finish"),
            "require removal by #15",
        ),
        (
            _valid_source().replace(
                "@pytest.mark.exercise", "@pytest.mark.skip\n@pytest.mark.exercise"
            ),
            "uses a skip marker",
        ),
    ],
)
def test_policy_rejects_invalid_owned_test(source, expected_error):
    errors = _policy_errors(
        {"tests/example.py": source},
        {"tests/example.py::test_owned": "#15"},
    )

    assert any(expected_error in error for error in errors)


def test_policy_rejects_an_extra_xfail():
    source = _valid_source() + '''
@pytest.mark.xfail(strict=True, reason="Deferred to #99; remove this marker when #99 implements.")
def test_extra():
    assert True
'''

    errors = _policy_errors(
        {"tests/example.py": source},
        {"tests/example.py::test_owned": "#15"},
    )

    assert "tests/example.py::test_extra has an unexpected xfail" in errors


def test_policy_rejects_pytest_skip_calls():
    source = _valid_source().replace("assert True", 'pytest.skip("not today")')

    errors = _policy_errors(
        {"tests/example.py": source},
        {"tests/example.py::test_owned": "#15"},
    )

    assert "tests/example.py calls pytest.skip" in errors
