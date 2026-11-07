#!/usr/bin/env python3
"""Validate a Documentation Impact Report for an exact candidate commit."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

ALLOWED_RESULTS = frozenset({"UPDATED", "NO_DOC_CHANGE", "BLOCKED"})
REQUIRED_FIELDS = frozenset(
    {
        "result",
        "base_sha",
        "candidate_sha",
        "material_change_assessment",
        "files_updated",
        "validation_performed",
        "verified_behavior_basis",
        "escalations_or_blockers",
    }
)
SHA_PATTERN = re.compile(r"[0-9a-fA-F]{40}")
ASSESSMENT_FIELDS = frozenset(
    {
        "user_or_contributor_behavior",
        "interfaces_or_configuration",
        "safety_or_privacy",
        "ci_or_release_policy",
        "development_agent_responsibilities",
    }
)


class ReportValidationError(ValueError):
    """Indicate that a Documentation Impact Report cannot pass the gate."""


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReportValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _require_string_list(value: Any, field: str, *, nonempty: bool) -> list[str]:
    if not isinstance(value, list):
        raise ReportValidationError(f"{field} must be a list of strings")
    if nonempty and not value:
        raise ReportValidationError(f"{field} must contain at least one item")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ReportValidationError(f"{field} must contain only non-empty strings")
    return [item.strip() for item in value]


def _validate_sha(value: Any, field: str) -> str:
    sha = _require_nonempty_string(value, field)
    if SHA_PATTERN.fullmatch(sha) is None:
        raise ReportValidationError(f"{field} must be a full 40-character commit SHA")
    return sha.lower()


def _validate_material_assessment(value: Any) -> None:
    if not isinstance(value, dict):
        raise ReportValidationError("material_change_assessment must be an object")
    fields = set(value)
    if fields != ASSESSMENT_FIELDS:
        raise ReportValidationError(
            "material_change_assessment must cover every required impact category"
        )
    for field in sorted(ASSESSMENT_FIELDS):
        _require_nonempty_string(value[field], f"material_change_assessment.{field}")


def _validate_doc_path(value: str) -> None:
    path = PurePosixPath(value)
    if path.is_absolute() or "." in path.parts or ".." in path.parts:
        raise ReportValidationError("files_updated contains an unsafe path")
    if value != "README.md" and not value.startswith("docs/"):
        raise ReportValidationError(
            "files_updated paths must be README.md or under docs/"
        )


def validate_report(report: Any, expected_candidate_sha: str) -> str:
    """Validate a parsed report against the expected candidate commit.

    Args:
        report: Parsed JSON value for the external Documentation Impact Report.
        expected_candidate_sha: Full commit SHA that QA would receive.

    Returns:
        The valid non-blocking report result, either ``UPDATED`` or
        ``NO_DOC_CHANGE``.

    Raises:
        ReportValidationError: If the report is malformed, stale, blocked, or
            inconsistent with its declared outcome.
    """
    expected_sha = _validate_sha(expected_candidate_sha, "expected candidate SHA")
    if not isinstance(report, dict):
        raise ReportValidationError("report must be a JSON object")

    fields = set(report)
    missing = sorted(REQUIRED_FIELDS - fields)
    unknown = sorted(fields - REQUIRED_FIELDS)
    if missing:
        raise ReportValidationError(f"report is missing required fields: {', '.join(missing)}")
    if unknown:
        raise ReportValidationError("report contains unknown fields")

    result = _require_nonempty_string(report["result"], "result")
    if result not in ALLOWED_RESULTS:
        raise ReportValidationError(
            f"result must be one of: {', '.join(sorted(ALLOWED_RESULTS))}"
        )

    _validate_sha(report["base_sha"], "base_sha")
    candidate_sha = _validate_sha(report["candidate_sha"], "candidate_sha")
    if candidate_sha != expected_sha:
        raise ReportValidationError("candidate_sha does not match the expected candidate commit")

    _validate_material_assessment(report["material_change_assessment"])
    files_updated = _require_string_list(
        report["files_updated"], "files_updated", nonempty=False
    )
    validation = _require_string_list(
        report["validation_performed"], "validation_performed", nonempty=True
    )
    behavior_basis = _require_string_list(
        report["verified_behavior_basis"], "verified_behavior_basis", nonempty=True
    )
    blockers = _require_string_list(
        report["escalations_or_blockers"], "escalations_or_blockers", nonempty=False
    )
    del validation, behavior_basis

    if result == "BLOCKED":
        if not blockers:
            raise ReportValidationError(
                "BLOCKED report must identify at least one escalation or blocker"
            )
        raise ReportValidationError("documentation review result is BLOCKED")

    if blockers:
        raise ReportValidationError(
            f"{result} report cannot contain unresolved escalations or blockers"
        )

    if result == "UPDATED":
        if not files_updated:
            raise ReportValidationError("UPDATED report must name documentation files")
        for value in files_updated:
            _validate_doc_path(value)
    elif files_updated:
        raise ReportValidationError("NO_DOC_CHANGE report must not name updated files")

    return result


def load_report(path: Path) -> Any:
    """Load a JSON report without exposing its contents.

    Args:
        path: External report artifact to read.

    Returns:
        The parsed JSON value.

    Raises:
        ReportValidationError: If the artifact cannot be read or parsed as JSON.
    """
    try:
        contents = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ReportValidationError("report is missing or unreadable") from exc
    try:
        return json.loads(contents)
    except json.JSONDecodeError as exc:
        raise ReportValidationError("report is not valid JSON") from exc


def main(argv: list[str] | None = None) -> int:
    """Run the Documentation Impact Gate command.

    Args:
        argv: Optional command-line arguments, excluding the program name.

    Returns:
        Zero for a current valid ``UPDATED`` or ``NO_DOC_CHANGE`` report;
        otherwise one.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--candidate-sha", required=True)
    args = parser.parse_args(argv)

    try:
        report = load_report(args.report)
        result = validate_report(report, args.candidate_sha)
    except ReportValidationError as exc:
        print(f"Documentation Impact Gate: FAIL - {exc}", file=sys.stderr)
        return 1

    print(f"Documentation Impact Gate: PASS ({result}) for {args.candidate_sha.lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
