"""Verify private training artifacts are excluded without hiding synthetic fixtures."""

from pathlib import Path


def test_private_archive_formats_and_locations_are_ignored() -> None:
    ignore = Path(".gitignore").read_text(encoding="utf-8")

    for pattern in (
        "*.fit",
        "*.fit.gz",
        "*.gpx",
        "*.parquet",
        "/activities.csv",
        "/activities.json",
        "/local-data/",
        "/private-data/",
        "/data/archive/",
        "/data/private/",
    ):
        assert pattern in ignore
    for fixture_exception in (
        "!tests/fixtures/**/*.fit",
        "!tests/fixtures/**/*.fit.gz",
        "!tests/fixtures/**/*.gpx",
    ):
        assert fixture_exception in ignore
    assert "data/synthetic_activities.json" not in ignore
    assert Path("data/synthetic_activities.json").is_file()
