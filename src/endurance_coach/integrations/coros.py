"""OAuth-aware, read-only client for the official COROS MCP service."""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import sys
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qs, urlparse

import httpx2
from mcp import Client
from mcp.client.auth import AuthorizationCodeResult, OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken
from pydantic import AnyUrl, BaseModel, ConfigDict, Field, ValidationError

from endurance_coach.config import CorosSettings

# Verified against the official COROS MCP tool guide. Write and file-download operations are
# deliberately absent. Additions require an explicit product and privacy review.
READ_ONLY_COROS_TOOLS = frozenset(
    {
        "getActivityDetail",
        "queryActivityLapData",
        "queryAvgHeartRate",
        "queryCustomActivityLapData",
        "queryDailyHealthData",
        "queryFitnessAssessmentOverview",
        "queryHealthCheckTimeSeries",
        "queryRecoveryStatus",
        "queryRestingHeartRate",
        "querySleepHrv",
        "querySleepOverview",
        "querySportRecords",
        "queryStressLevel",
        "queryStressTimeSeries",
        "queryTrainingLoadAssessment",
        "queryTrainingPlanDetails",
        "queryTrainingPlanLibrary",
        "queryTrainingSchedule",
        "queryWorkoutDetails",
        "queryWorkoutLibrary",
    }
)

_RECOVERY_QUERIES: tuple[tuple[str, Callable[[int], dict[str, int]]], ...] = (
    ("queryRecoveryStatus", lambda _days: {}),
    ("querySleepOverview", lambda days: {"days": days}),
    ("querySleepHrv", lambda days: {"days": min(days, 7)}),
    ("queryRestingHeartRate", lambda days: {"days": days}),
    ("queryStressLevel", lambda days: {"days": days}),
    ("queryTrainingLoadAssessment", lambda days: {"days": days}),
)
_MAX_TOOL_PAGES = 10
_MAX_TOOLS = 200


class CorosError(RuntimeError):
    """Report a COROS connection failure without exposing tokens or health data."""


class CorosDiscovery(BaseModel):
    """Privacy-safe summary of COROS tool discovery."""

    model_config = ConfigDict(extra="forbid")

    available_read_tools: tuple[str, ...]
    unavailable_read_tools: tuple[str, ...]
    blocked_tools: tuple[str, ...]


class CorosRecoverySnapshot(BaseModel):
    """Bounded raw recovery observations with explicit missing-tool disclosure."""

    model_config = ConfigDict(extra="forbid")

    days: int = Field(ge=1, le=30)
    observations: dict[str, str]
    unavailable_tools: tuple[str, ...]
    source: str = "coros_mcp"


class _McpSession(Protocol):
    """Narrow async MCP surface consumed by the COROS integration."""

    async def list_tools(self, *, cursor: str | None = None) -> Any: ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


_SessionFactory = Callable[[], AsyncIterator[_McpSession]]
_RedirectHandler = Callable[[str], Awaitable[None]]
_CallbackHandler = Callable[[], Awaitable[AuthorizationCodeResult]]


class FileTokenStorage:
    """Persist OAuth state in one ignored, owner-readable JSON file."""

    def __init__(self, path: Path) -> None:
        self._path = path

    async def get_tokens(self) -> OAuthToken | None:
        """Return stored OAuth tokens, or null before authorization."""
        payload = self._read()
        if payload is None or payload.get("tokens") is None:
            return None
        try:
            return OAuthToken.model_validate(payload["tokens"])
        except ValidationError as exc:
            raise CorosError("stored COROS authorization is invalid") from exc

    async def set_tokens(self, tokens: OAuthToken) -> None:
        """Atomically replace the stored OAuth tokens."""
        payload = self._read() or {}
        payload["tokens"] = tokens.model_dump(mode="json")
        self._write(payload)

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        """Return dynamic client registration data when available."""
        payload = self._read()
        if payload is None or payload.get("client_info") is None:
            return None
        try:
            return OAuthClientInformationFull.model_validate(payload["client_info"])
        except ValidationError as exc:
            raise CorosError("stored COROS client registration is invalid") from exc

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        """Atomically replace dynamic client registration data."""
        payload = self._read() or {}
        payload["client_info"] = client_info.model_dump(mode="json")
        self._write(payload)

    def _read(self) -> dict[str, Any] | None:
        if not self._path.exists():
            return None
        if self._path.is_symlink() or not self._path.is_file():
            raise CorosError("COROS authorization state path is unsafe")
        try:
            if self._path.stat().st_size > 64 * 1024:
                raise CorosError("COROS authorization state is too large")
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except CorosError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CorosError("could not read COROS authorization state") from exc
        if not isinstance(payload, dict):
            raise CorosError("stored COROS authorization is invalid")
        return payload

    def _write(self, payload: Mapping[str, Any]) -> None:
        parent = self._path.parent
        temporary = parent / f".{self._path.name}.{secrets.token_hex(8)}.tmp"
        try:
            parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if self._path.exists() and self._path.is_symlink():
                raise CorosError("COROS authorization state path is unsafe")
            data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                with os.fdopen(descriptor, "wb") as target:
                    target.write(data)
                    target.flush()
                    os.fsync(target.fileno())
            except Exception:
                with suppress(OSError):
                    os.close(descriptor)
                raise
            os.replace(temporary, self._path)
            os.chmod(self._path, 0o600)
        except CorosError:
            raise
        except OSError as exc:
            raise CorosError("could not store COROS authorization state") from exc
        finally:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)


async def _show_authorization_url(url: str) -> None:
    """Display an OAuth URL without attempting to launch a GUI."""
    print("Open this COROS authorization URL in a browser:", file=sys.stderr)
    print(url, file=sys.stderr)


async def _read_callback_url() -> AuthorizationCodeResult:
    """Read and validate the browser's local redirect URL."""
    redirected = input("Paste the final browser redirect URL: ").strip()
    query = parse_qs(urlparse(redirected).query)
    code = query.get("code", [])
    state = query.get("state", [])
    if len(code) != 1 or len(state) != 1:
        raise CorosError("COROS authorization callback is missing required values")
    issuer = query.get("iss", [])
    return AuthorizationCodeResult(
        code=code[0],
        state=state[0],
        iss=issuer[0] if len(issuer) == 1 else None,
    )


class CorosClient:
    """Discover and call a fixed set of read-only COROS MCP tools."""

    def __init__(
        self,
        settings: CorosSettings,
        *,
        session_factory: _SessionFactory | None = None,
        redirect_handler: _RedirectHandler = _show_authorization_url,
        callback_handler: _CallbackHandler = _read_callback_url,
    ) -> None:
        self._settings = settings
        self._redirect_handler = redirect_handler
        self._callback_handler = callback_handler
        self._session_factory = session_factory or self._oauth_session

    def discover_tools(self) -> CorosDiscovery:
        """Authenticate if needed and return a safe allowlist comparison."""
        return self._run(self._discover_tools())

    def recovery_snapshot(self, days: int = 7) -> CorosRecoverySnapshot:
        """Return bounded supplementary recovery observations from available tools."""
        if not isinstance(days, int) or isinstance(days, bool) or not 1 <= days <= 30:
            raise CorosError("COROS recovery days must be between 1 and 30")
        return self._run(self._recovery_snapshot(days))

    @staticmethod
    def _run(awaitable: Awaitable[Any]) -> Any:
        try:
            return asyncio.run(awaitable)
        except CorosError:
            raise
        except (OSError, TimeoutError, httpx2.HTTPError) as exc:
            raise CorosError("COROS MCP request failed") from exc
        except Exception as exc:
            raise CorosError(f"COROS MCP request failed ({type(exc).__name__})") from None

    @asynccontextmanager
    async def _oauth_session(self) -> AsyncIterator[_McpSession]:
        storage = FileTokenStorage(self._settings.oauth_state_path)
        oauth = OAuthClientProvider(
            server_url=self._settings.endpoint,
            client_metadata=OAuthClientMetadata(
                client_name="Endurance Coach",
                software_id="endurance-coach",
                software_version="0.1.0",
                redirect_uris=[AnyUrl(self._settings.redirect_uri)],
                token_endpoint_auth_method="none",
            ),
            storage=storage,
            redirect_handler=self._redirect_handler,
            callback_handler=self._callback_handler,
        )
        timeout = httpx2.Timeout(
            self._settings.timeout_seconds,
            read=self._settings.timeout_seconds,
        )
        async with httpx2.AsyncClient(auth=oauth, timeout=timeout) as http_client:
            transport = streamable_http_client(
                self._settings.endpoint,
                http_client=http_client,
                max_sse_event_size=self._settings.max_response_bytes,
            )
            async with Client(
                transport,
                read_timeout_seconds=self._settings.timeout_seconds,
            ) as client:
                yield client

    async def _tool_names(self, session: _McpSession) -> set[str]:
        names: set[str] = set()
        cursor: str | None = None
        for _page in range(_MAX_TOOL_PAGES):
            result = await session.list_tools(cursor=cursor)
            tools = getattr(result, "tools", None)
            if not isinstance(tools, list):
                raise CorosError("COROS returned an invalid tool list")
            for tool in tools:
                name = getattr(tool, "name", None)
                if not isinstance(name, str) or not name:
                    raise CorosError("COROS returned an invalid tool definition")
                names.add(name)
                if len(names) > _MAX_TOOLS:
                    raise CorosError("COROS tool discovery limit exceeded")
            cursor = getattr(result, "next_cursor", None)
            if cursor is None:
                return names
            if not isinstance(cursor, str) or not cursor:
                raise CorosError("COROS returned an invalid tool cursor")
        raise CorosError("COROS tool discovery page limit exceeded")

    async def _discover_tools(self) -> CorosDiscovery:
        async with self._session_factory() as session:
            discovered = await self._tool_names(session)
        available = discovered & READ_ONLY_COROS_TOOLS
        return CorosDiscovery(
            available_read_tools=tuple(sorted(available)),
            unavailable_read_tools=tuple(sorted(READ_ONLY_COROS_TOOLS - available)),
            blocked_tools=tuple(sorted(discovered - READ_ONLY_COROS_TOOLS)),
        )

    async def _recovery_snapshot(self, days: int) -> CorosRecoverySnapshot:
        observations: dict[str, str] = {}
        unavailable: list[str] = []
        async with self._session_factory() as session:
            discovered = await self._tool_names(session)
            for name, arguments_for_days in _RECOVERY_QUERIES:
                if name not in discovered:
                    unavailable.append(name)
                    continue
                if name not in READ_ONLY_COROS_TOOLS:
                    raise CorosError("COROS tool is not approved for read-only use")
                result = await session.call_tool(name, arguments_for_days(days))
                observations[name] = self._text_result(name, result)
        return CorosRecoverySnapshot(
            days=days,
            observations=observations,
            unavailable_tools=tuple(unavailable),
        )

    def _text_result(self, name: str, result: Any) -> str:
        if getattr(result, "is_error", False):
            raise CorosError(f"COROS tool {name} reported an error")
        content = getattr(result, "content", None)
        if not isinstance(content, list):
            raise CorosError(f"COROS tool {name} returned invalid content")
        text_parts: list[str] = []
        for item in content:
            text = getattr(item, "text", None)
            if not isinstance(text, str):
                raise CorosError(f"COROS tool {name} returned unsupported content")
            text_parts.append(text)
        combined = "\n".join(text_parts).strip()
        if not combined:
            raise CorosError(f"COROS tool {name} returned empty content")
        if len(combined.encode("utf-8")) > self._settings.max_response_bytes:
            raise CorosError(f"COROS tool {name} response limit exceeded")
        return combined


__all__ = [
    "CorosClient",
    "CorosDiscovery",
    "CorosError",
    "CorosRecoverySnapshot",
    "FileTokenStorage",
    "READ_ONLY_COROS_TOOLS",
]
