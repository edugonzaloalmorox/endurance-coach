"""Tests for defensive FIT/FIT.GZ discovery and normalization."""

from __future__ import annotations

import gzip
import hashlib
from pathlib import Path

import pytest

from endurance_coach.ingestion import (
    FitIngestionError,
    discover_fit_files,
    parse_fit_artifact,
)
from tests.fit_fixture import build_fit_bytes, write_fit_fixture


def _parse(path: Path, root: Path):
    return parse_fit_artifact(
        path,
        root,
        max_raw_bytes=1024 * 1024,
        max_content_bytes=1024 * 1024,
    )


def test_discovery_is_recursive_and_does_not_escape_archive_symlinks(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "archive"
    inside = archive / "nested" / "ride.fit"
    outside = tmp_path / "private.fit"
    write_fit_fixture(inside)
    write_fit_fixture(outside)
    (archive / "outside.fit").symlink_to(outside)
    (archive / "outside-directory").symlink_to(tmp_path, target_is_directory=True)

    assert discover_fit_files(archive) == [inside.resolve()]


def test_fit_and_fit_gz_normalize_to_the_same_content_and_records(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "archive"
    plain = archive / "ride.fit"
    compressed = archive / "ride.fit.gz"
    write_fit_fixture(plain)
    write_fit_fixture(compressed, compressed=True)

    fit = _parse(plain, archive)
    fit_gz = _parse(compressed, archive)

    assert fit.raw_sha256 != fit_gz.raw_sha256
    assert fit.content_sha256 == fit_gz.content_sha256
    assert fit.activity.activity_id == fit_gz.activity.activity_id
    assert fit.activity.activity_type == "cycling"
    assert fit.activity.elapsed_seconds == 75
    assert fit.activity.distance_m == 250
    assert fit.activity.average_power_w == 200
    assert fit.activity.normalized_power_w == 210
    assert [record.elapsed_seconds for record in fit.activity.records] == [0, 75]
    assert [record.power_w for record in fit.activity.records] == [180, 220]


def test_missing_power_stays_missing(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    path = archive / "no-power.fit"
    path.parent.mkdir(parents=True)
    path.write_bytes(build_fit_bytes(include_power=False))

    artifact = _parse(path, archive)

    assert artifact.activity.average_power_w is None
    assert artifact.activity.normalized_power_w is None
    assert artifact.activity.power_origin == "unavailable"
    assert all(record.power_w is None for record in artifact.activity.records)
    assert all(record.power_origin is None for record in artifact.activity.records)


def test_multiple_sessions_preserve_session_indices_and_sampling(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    path = archive / "multisport.fit"
    path.parent.mkdir(parents=True)
    path.write_bytes(build_fit_bytes(multiple_sessions=True))

    artifact = _parse(path, archive)

    assert [record.session_index for record in artifact.activity.records] == [0, 0, 1, 1]
    assert [record.record_index for record in artifact.activity.records] == [0, 1, 0, 1]
    assert [record.elapsed_seconds for record in artifact.activity.records] == [0, 75, 0, 75]
    assert artifact.activity.elapsed_seconds == 150
    assert artifact.activity.distance_m == 550


def test_corrupt_fit_has_safe_error_and_content_hash(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    path = archive / "corrupt.fit"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"not a FIT file")

    with pytest.raises(FitIngestionError) as raised:
        _parse(path, archive)

    assert raised.value.code == "invalid_fit"
    assert raised.value.raw_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert raised.value.content_sha256 == raised.value.raw_sha256


def test_compressed_content_limit_stops_expansion(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    path = archive / "large.fit.gz"
    path.parent.mkdir(parents=True)
    path.write_bytes(gzip.compress(b"x" * 4096, mtime=0))

    with pytest.raises(FitIngestionError, match="content_too_large"):
        parse_fit_artifact(
            path,
            archive,
            max_raw_bytes=1024,
            max_content_bytes=128,
        )
