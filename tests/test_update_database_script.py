"""Tests for the fresh-run database update script."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _fake_uv(tmp_path: Path) -> tuple[Path, Path]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    capture = tmp_path / "uv-call.txt"
    executable = fake_bin / "uv"
    executable.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$PWD\" \"$@\" > \"$UV_CALL_CAPTURE\"\n"
        "exit \"${UV_EXIT_CODE:-0}\"\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return fake_bin, capture


def test_update_database_runs_from_repository_root_and_forwards_arguments(
    tmp_path: Path,
) -> None:
    repository = Path(__file__).resolve().parents[1]
    fake_bin, capture = _fake_uv(tmp_path)
    environment = os.environ | {
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "UV_CALL_CAPTURE": str(capture),
    }

    result = subprocess.run(
        [repository / "scripts/update_database.sh", "--oldest", "2026-01-01"],
        cwd=tmp_path,
        env=environment,
        check=False,
    )

    assert result.returncode == 0
    assert capture.read_text(encoding="utf-8").splitlines() == [
        str(repository),
        "run",
        "endurance-coach",
        "db",
        "sync-intervals",
        "--oldest",
        "2026-01-01",
    ]


def test_update_database_propagates_sync_failure(tmp_path: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    fake_bin, capture = _fake_uv(tmp_path)
    environment = os.environ | {
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "UV_CALL_CAPTURE": str(capture),
        "UV_EXIT_CODE": "7",
    }

    result = subprocess.run(
        [repository / "scripts/update_database.sh"],
        cwd=tmp_path,
        env=environment,
        check=False,
    )

    assert result.returncode == 7


def test_make_update_db_runs_incremental_sync(tmp_path: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    fake_bin, capture = _fake_uv(tmp_path)
    environment = os.environ | {
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "UV_CALL_CAPTURE": str(capture),
    }

    result = subprocess.run(
        ["make", "update-db"],
        cwd=repository,
        env=environment,
        check=False,
    )

    assert result.returncode == 0
    assert capture.read_text(encoding="utf-8").splitlines() == [
        str(repository),
        "run",
        "endurance-coach",
        "db",
        "sync-intervals",
    ]
