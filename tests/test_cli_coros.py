"""CLI coverage for read-only COROS MCP operations."""

import json

import endurance_coach.cli as cli
from endurance_coach.integrations.coros import CorosDiscovery, CorosRecoverySnapshot


def test_coros_discover_prints_only_safe_tool_metadata(monkeypatch, capsys) -> None:
    class FakeClient:
        def __init__(self, _settings) -> None:
            pass

        def discover_tools(self):
            return CorosDiscovery(
                available_read_tools=("queryRecoveryStatus",),
                unavailable_read_tools=("querySleepOverview",),
                blocked_tools=("createTrainingPlan",),
            )

    monkeypatch.setattr(cli, "CorosClient", FakeClient)

    assert cli.main(["coros", "discover"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "available_read_tools": ["queryRecoveryStatus"],
        "blocked_tools": ["createTrainingPlan"],
        "unavailable_read_tools": ["querySleepOverview"],
    }


def test_coros_recovery_passes_bounded_days_and_prints_snapshot(monkeypatch, capsys) -> None:
    observed = {}
    monkeypatch.setenv("COROS_MCP_URL", "https://mcp.coros.com/mcp")

    class FakeClient:
        def __init__(self, settings) -> None:
            observed["endpoint"] = settings.endpoint

        def recovery_snapshot(self, days):
            observed["days"] = days
            return CorosRecoverySnapshot(
                days=days,
                observations={"queryRecoveryStatus": "synthetic ready"},
                unavailable_tools=(),
            )

    monkeypatch.setattr(cli, "CorosClient", FakeClient)

    assert cli.main(["coros", "recovery", "--days", "5"]) == 0
    assert json.loads(capsys.readouterr().out)["source"] == "coros_mcp"
    assert observed == {"days": 5, "endpoint": "https://mcp.coros.com/mcp"}
