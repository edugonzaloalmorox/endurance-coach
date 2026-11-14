"""Tests for the deterministic pre-QA Documentation Impact Gate."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

VALIDATOR_PATH = Path(".agents/validate_docs_impact.py")
BASE_SHA = "1" * 40
CANDIDATE_SHA = "2" * 40


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_docs_impact", VALIDATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = _load_validator()


def _report(result: str = "NO_DOC_CHANGE") -> dict[str, object]:
    return {
        "result": result,
        "base_sha": BASE_SHA,
        "candidate_sha": CANDIDATE_SHA,
        "material_change_assessment": {
            "user_or_contributor_behavior": "No user or contributor behavior changed.",
            "interfaces_or_configuration": "No interface or configuration changed.",
            "safety_or_privacy": "No safety or privacy rule changed.",
            "ci_or_release_policy": "No CI or release policy changed.",
            "development_agent_responsibilities": (
                "No development-agent responsibility changed."
            ),
        },
        "files_updated": [],
        "validation_performed": ["Compared the exact base-to-candidate diff."],
        "verified_behavior_basis": ["Focused tests prove the same public behavior."],
        "escalations_or_blockers": [],
    }


def _run_cli(tmp_path: Path, report: object, candidate_sha: str = CANDIDATE_SHA):
    report_path = tmp_path / "documentation-impact.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR_PATH),
            "--report",
            str(report_path),
            "--candidate-sha",
            candidate_sha,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_cli_accepts_updated_report_for_exact_candidate(tmp_path):
    report = _report("UPDATED")
    report["material_change_assessment"]["user_or_contributor_behavior"] = (
        "The CLI changed and its verified usage is documented."
    )
    report["files_updated"] = ["README.md", "docs/process.md"]
    report["verified_behavior_basis"] = [
        "CLI tests and --help output verify the documented command."
    ]

    result = _run_cli(tmp_path, report)

    assert result.returncode == 0
    assert f"PASS (UPDATED) for {CANDIDATE_SHA}" in result.stdout
    assert result.stderr == ""


def test_cli_accepts_evidence_based_no_doc_change_report(tmp_path):
    result = _run_cli(tmp_path, _report())

    assert result.returncode == 0
    assert f"PASS (NO_DOC_CHANGE) for {CANDIDATE_SHA}" in result.stdout
    assert result.stderr == ""


def test_cli_rejects_missing_report(tmp_path):
    missing = tmp_path / "missing.json"

    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR_PATH),
            "--report",
            str(missing),
            "--candidate-sha",
            CANDIDATE_SHA,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "missing or unreadable" in result.stderr


def test_cli_rejects_unreadable_report_path(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR_PATH),
            "--report",
            str(tmp_path),
            "--candidate-sha",
            CANDIDATE_SHA,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "missing or unreadable" in result.stderr


@pytest.mark.parametrize("invalid_report", ["not JSON", [], None])
def test_cli_rejects_malformed_report(tmp_path, invalid_report):
    report_path = tmp_path / "documentation-impact.json"
    if invalid_report == "not JSON":
        report_path.write_text(invalid_report, encoding="utf-8")
    else:
        report_path.write_text(json.dumps(invalid_report), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR_PATH),
            "--report",
            str(report_path),
            "--candidate-sha",
            CANDIDATE_SHA,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Documentation Impact Gate: FAIL" in result.stderr


@pytest.mark.parametrize("field", sorted(VALIDATOR.REQUIRED_FIELDS))
def test_validator_rejects_each_missing_required_field(field):
    report = _report()
    del report[field]

    with pytest.raises(VALIDATOR.ReportValidationError, match="missing required fields"):
        VALIDATOR.validate_report(report, CANDIDATE_SHA)


def test_validator_rejects_unknown_field():
    report = _report()
    report["private_athlete_data"] = "must not be accepted"

    with pytest.raises(VALIDATOR.ReportValidationError, match="unknown fields"):
        VALIDATOR.validate_report(report, CANDIDATE_SHA)


def test_validator_rejects_unknown_result():
    report = _report("SKIPPED")

    with pytest.raises(VALIDATOR.ReportValidationError, match="result must be one of"):
        VALIDATOR.validate_report(report, CANDIDATE_SHA)


@pytest.mark.parametrize("field", ["base_sha", "candidate_sha"])
def test_validator_rejects_invalid_report_sha(field):
    report = _report()
    report[field] = "short"

    with pytest.raises(VALIDATOR.ReportValidationError, match="full 40-character"):
        VALIDATOR.validate_report(report, CANDIDATE_SHA)


def test_validator_rejects_invalid_expected_sha():
    with pytest.raises(VALIDATOR.ReportValidationError, match="full 40-character"):
        VALIDATOR.validate_report(_report(), "short")


def test_validator_rejects_stale_candidate_report():
    with pytest.raises(VALIDATOR.ReportValidationError, match="does not match"):
        VALIDATOR.validate_report(_report(), "3" * 40)


def test_cli_exits_nonzero_for_stale_candidate_report(tmp_path):
    result = _run_cli(tmp_path, _report(), candidate_sha="3" * 40)

    assert result.returncode == 1
    assert "does not match the expected candidate commit" in result.stderr


def test_cli_does_not_echo_blocker_contents(tmp_path):
    report = _report("BLOCKED")
    sensitive_text = "synthetic-secret-must-not-appear"
    report["escalations_or_blockers"] = [sensitive_text]

    result = _run_cli(tmp_path, report)

    assert result.returncode == 1
    assert sensitive_text not in result.stdout
    assert sensitive_text not in result.stderr


def test_validator_rejects_blocked_report():
    report = _report("BLOCKED")
    report["escalations_or_blockers"] = ["The comparison base is unknown."]

    with pytest.raises(VALIDATOR.ReportValidationError, match="result is BLOCKED"):
        VALIDATOR.validate_report(report, CANDIDATE_SHA)


def test_validator_requires_reason_for_blocked_report():
    with pytest.raises(VALIDATOR.ReportValidationError, match="at least one"):
        VALIDATOR.validate_report(_report("BLOCKED"), CANDIDATE_SHA)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("material_change_assessment", {}, "every required impact category"),
        ("validation_performed", [], "at least one"),
        ("verified_behavior_basis", [], "at least one"),
        ("files_updated", "README.md", "list of strings"),
        ("escalations_or_blockers", [""], "non-empty strings"),
    ],
)
def test_validator_rejects_invalid_required_field_values(field, value, message):
    report = _report()
    report[field] = value

    with pytest.raises(VALIDATOR.ReportValidationError, match=message):
        VALIDATOR.validate_report(report, CANDIDATE_SHA)


def test_validator_requires_nonempty_material_assessment_for_each_category():
    report = _report()
    report["material_change_assessment"]["safety_or_privacy"] = ""

    with pytest.raises(VALIDATOR.ReportValidationError, match="non-empty string"):
        VALIDATOR.validate_report(report, CANDIDATE_SHA)


def test_validator_rejects_updated_report_without_files():
    with pytest.raises(VALIDATOR.ReportValidationError, match="must name documentation files"):
        VALIDATOR.validate_report(_report("UPDATED"), CANDIDATE_SHA)


@pytest.mark.parametrize("path", ["AGENTS.md", "../README.md", "/docs/process.md"])
def test_validator_rejects_updated_report_with_out_of_scope_path(path):
    report = _report("UPDATED")
    report["files_updated"] = [path]

    with pytest.raises(VALIDATOR.ReportValidationError, match="path"):
        VALIDATOR.validate_report(report, CANDIDATE_SHA)


def test_validator_rejects_no_doc_change_report_with_files():
    report = _report()
    report["files_updated"] = ["README.md"]

    with pytest.raises(VALIDATOR.ReportValidationError, match="must not name updated files"):
        VALIDATOR.validate_report(report, CANDIDATE_SHA)


def test_validator_rejects_unresolved_blocker_on_nonblocked_result():
    report = _report()
    report["escalations_or_blockers"] = ["A policy decision remains unresolved."]

    with pytest.raises(VALIDATOR.ReportValidationError, match="cannot contain unresolved"):
        VALIDATOR.validate_report(report, CANDIDATE_SHA)


def test_repository_tracks_skill_and_pre_qa_gate_policy():
    agents = Path("AGENTS.md").read_text(encoding="utf-8")
    process = Path("docs/process.md").read_text(encoding="utf-8")
    qa_role = Path("docs/agents/qa-engineer.md").read_text(encoding="utf-8")

    assert Path(".agents/skills/docs-sync/SKILL.md").is_file()
    assert "Documentation Impact Gate" in agents
    assert "before QA starts" in agents
    assert "Engineer → Documentation Impact Gate" in process
    assert "Documentation Impact Gate → QA" in process
    assert "Any new commit invalidates prior documentation" in process
    assert "refuse a missing, stale, malformed, or `BLOCKED`" in qa_role


def test_gate_policy_preserves_qa_ci_and_human_merge_control():
    process = Path("docs/process.md").read_text(encoding="utf-8")

    assert "Independent QA evidence" in process
    assert "Automated CI evidence" in process
    assert "human has explicitly authorized the merge" in process
    assert "Required-check bypass is forbidden" in process


def test_issue_75_keeps_sequential_engineering_and_independent_qa():
    agents = Path("AGENTS.md").read_text(encoding="utf-8")
    process = Path("docs/process.md").read_text(encoding="utf-8")
    engineer = Path("docs/agents/software-engineer.md").read_text(encoding="utf-8")
    qa = Path("docs/agents/qa-engineer.md").read_text(encoding="utf-8")

    assert (
        "routine, short, or inherently sequential implementation in one Engineer context"
        in agents
    )
    assert "subagents only for genuinely independent work" in agents
    assert "Final QA remains a separate read-only context when supported" in agents
    assert "all issue-authorized implementation" in engineer
    assert "until the Engineering candidate is stable" in engineer
    assert "required final local verification once" in process
    assert "final full-suite release verification" in process
    assert "Remain in a separate read-only context when supported" in qa
    assert "rely on that evidence instead of redundantly repeating full-suite coverage" in qa


def test_issue_75_precheck_is_advisory_and_cannot_bypass_docs_sync():
    process = Path("docs/process.md").read_text(encoding="utf-8")
    testing = Path("docs/testing-guidelines.md").read_text(encoding="utf-8")

    assert "## Deterministic documentation-impact pre-check" in process
    assert "explicit base SHA" in process
    assert "stable candidate SHA" in process
    assert "MATERIAL_CANDIDATE" in process
    assert "NO_MATERIAL_INDICATOR" in process
    assert "Any other unrecognized path" in process
    assert "both results invoke `docs-sync`" in process
    assert "paths alone cannot prove documentation impact" in process
    assert "never produces `UPDATED`, `NO_DOC_CHANGE`, or `BLOCKED`" in testing
    assert "never permits QA to bypass `docs-sync`" in testing
    assert "evidence-based `NO_DOC_CHANGE` report" in testing


def test_issue_75_handoff_examples_are_machine_readable_and_invalidate_later_commits():
    process = Path("docs/process.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", process, re.DOTALL)
    records = [json.loads(block) for block in blocks]

    required = {
        "phase",
        "issue",
        "specification_version",
        "candidate_sha",
        "duration_seconds",
        "retry_count",
        "token_usage",
        "outcome",
        "evidence_links",
        "blockers",
    }
    assert len(records) >= 3
    assert all(required <= record.keys() for record in records)

    route_records = {record["routing"]: record for record in records if "routing" in record}
    assert set(route_records) == {"MATERIAL_CANDIDATE", "NO_MATERIAL_INDICATOR"}
    assert route_records["MATERIAL_CANDIDATE"]["report_result"] == "UPDATED"
    assert route_records["NO_MATERIAL_INDICATOR"]["report_result"] == "NO_DOC_CHANGE"
    for record in route_records.values():
        assert record["docs_sync_invoked"] is True
        assert record["validator_exit_code"] == 0
        assert record["validated_candidate_sha"] == record["candidate_sha"]
        assert record["after_later_commit"]["candidate_sha"] != record["candidate_sha"]
        assert record["after_later_commit"]["prior_report_status"] == "STALE"
        assert record["after_later_commit"]["qa_allowed"] is False


def test_issue_75_preserves_retry_privacy_and_human_control_contracts():
    agents = Path("AGENTS.md").read_text(encoding="utf-8")
    process = Path("docs/process.md").read_text(encoding="utf-8")
    testing = Path("docs/testing-guidelines.md").read_text(encoding="utf-8")

    assert "three total Engineering attempts" in agents
    assert "initial implementation plus at most two automated repair attempts" in agents
    assert "A further failure or an unreproducible result requires `NEEDS_HUMAN`" in agents
    assert "unsupported effort selection as `unavailable`" in process
    assert "Never estimate token usage" in process
    assert "Do not include prompts, hidden reasoning" in process
    assert (
        "Repository settings, branch protection, destructive changes, or merge authorization"
        in process
    )
    assert "third-party writes" in process
    assert "Training-safety, athlete approval, or personal-data protections" in process
    assert "No proposed workout-plan modification" in agents
    assert "Required-check bypass is forbidden" in process
    assert "human has explicitly authorized the merge" in process
    assert "uv run pytest tests/test_documentation_impact_gate.py" in testing
    assert "git diff --check" in testing
