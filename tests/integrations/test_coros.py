"""Tests for bounded, read-only COROS MCP access."""

import asyncio
import json
import stat
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool

from endurance_coach.config import CorosSettings
from endurance_coach.integrations.coros import (
    CorosClient,
    CorosError,
    FileTokenStorage,
)


def tool(name: str) -> Tool:
    """Return one minimal synthetic MCP tool definition."""
    return Tool(name=name, description="synthetic", inputSchema={"type": "object"})


class FakeCorosSession:
    """Return synthetic discovery pages and record tool calls."""

    def __init__(self, tool_names: list[str]) -> None:
        self.tool_names = tool_names
        self.calls: list[tuple[str, dict]] = []

    async def list_tools(self, *, cursor=None):
        if cursor is None:
            return ListToolsResult(
                tools=[tool(name) for name in self.tool_names[:2]],
                nextCursor="page-2" if len(self.tool_names) > 2 else None,
            )
        assert cursor == "page-2"
        return ListToolsResult(tools=[tool(name) for name in self.tool_names[2:]])

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return CallToolResult(
            content=[TextContent(type="text", text=f"synthetic result for {name}")]
        )


def client_with_session(session: FakeCorosSession, **settings) -> CorosClient:
    """Create a client connected to one in-memory synthetic session."""

    @asynccontextmanager
    async def connection():
        yield session

    return CorosClient(CorosSettings(**settings), session_factory=connection)


def test_discovery_paginates_and_blocks_every_unapproved_tool() -> None:
    session = FakeCorosSession(
        ["queryRecoveryStatus", "createTrainingPlan", "querySleepOverview"]
    )

    discovery = client_with_session(session).discover_tools()

    assert discovery.available_read_tools == (
        "queryRecoveryStatus",
        "querySleepOverview",
    )
    assert discovery.blocked_tools == ("createTrainingPlan",)
    assert "queryTrainingLoadAssessment" in discovery.unavailable_read_tools
    assert session.calls == []


def test_recovery_snapshot_calls_only_fixed_read_queries_with_bounded_arguments() -> None:
    session = FakeCorosSession(
        [
            "queryRecoveryStatus",
            "querySleepOverview",
            "querySleepHrv",
            "queryRestingHeartRate",
            "queryStressLevel",
            "queryTrainingLoadAssessment",
            "updateTrainingPlan",
        ]
    )

    snapshot = client_with_session(session).recovery_snapshot(30)

    assert snapshot.source == "coros_mcp"
    assert snapshot.days == 30
    assert snapshot.unavailable_tools == ()
    assert set(snapshot.observations) == {
        "queryRecoveryStatus",
        "querySleepOverview",
        "querySleepHrv",
        "queryRestingHeartRate",
        "queryStressLevel",
        "queryTrainingLoadAssessment",
    }
    assert session.calls == [
        ("queryRecoveryStatus", {}),
        ("querySleepOverview", {"days": 30}),
        ("querySleepHrv", {"days": 7}),
        ("queryRestingHeartRate", {"days": 30}),
        ("queryStressLevel", {"days": 30}),
        ("queryTrainingLoadAssessment", {"days": 30}),
    ]


@pytest.mark.parametrize("days", [0, 31, True, "7"])
def test_recovery_snapshot_rejects_invalid_bounds_without_connecting(days) -> None:
    session = FakeCorosSession(["queryRecoveryStatus"])

    with pytest.raises(CorosError, match="between 1 and 30"):
        client_with_session(session).recovery_snapshot(days)

    assert session.calls == []


def test_recovery_snapshot_rejects_non_text_and_oversized_results() -> None:
    class InvalidSession(FakeCorosSession):
        async def call_tool(self, name, arguments):
            return CallToolResult(
                content=[TextContent(type="text", text="x" * 1025)]
            )

    session = InvalidSession(["queryRecoveryStatus"])

    with pytest.raises(CorosError, match="response limit exceeded"):
        client_with_session(session, max_response_bytes=1024).recovery_snapshot()


def test_file_token_storage_round_trips_private_oauth_state(tmp_path: Path) -> None:
    state_path = tmp_path / "private" / "coros.json"
    storage = FileTokenStorage(state_path)
    tokens = OAuthToken(
        access_token="synthetic-access-token",
        refresh_token="synthetic-refresh-token",
        expires_in=3600,
    )
    client_info = OAuthClientInformationFull(
        client_id="synthetic-client",
        redirect_uris=["http://127.0.0.1:8765/callback"],
    )

    asyncio.run(storage.set_tokens(tokens))
    asyncio.run(storage.set_client_info(client_info))

    assert asyncio.run(storage.get_tokens()) == tokens
    assert asyncio.run(storage.get_client_info()) == client_info
    assert stat.S_IMODE(state_path.stat().st_mode) == 0o600
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert payload["tokens"]["access_token"] == "synthetic-access-token"
    assert payload["client_info"]["client_id"] == "synthetic-client"


def test_file_token_storage_rejects_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    link = tmp_path / "coros.json"
    link.symlink_to(target)

    with pytest.raises(CorosError, match="unsafe"):
        asyncio.run(FileTokenStorage(link).get_tokens())
