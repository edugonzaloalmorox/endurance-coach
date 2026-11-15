"""End-to-end tests for historical FIT archive imports."""

from __future__ import annotations

import csv
import hashlib
import sqlite3
from pathlib import Path

from endurance_coach.services import import_fit_archive
from endurance_coach.storage import database_status
from tests.fit_fixture import write_fit_fixture


def _write_metadata(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(
            destination,
            fieldnames=[
                "Activity ID",
                "Activity Name",
                "Activity Description",
                "Activity Type",
                "Filename",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def test_import_populates_sqlite_and_is_idempotent_across_fit_and_gzip(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "archive"
    plain = archive / "ride.fit"
    compressed = archive / "copy.fit.gz"
    database = tmp_path / "coach.sqlite3"
    write_fit_fixture(plain)
    write_fit_fixture(compressed, compressed=True)
    original_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (plain, compressed)
    }

    first = import_fit_archive(archive, database)
    second = import_fit_archive(archive, database)

    assert first.imported == 1
    assert first.duplicates == 1
    assert first.activities_written == 1
    assert first.records_written == 2
    assert second.imported == 0
    assert second.duplicates == 2
    status = database_status(database)
    assert status.table_counts["activities"] == 1
    assert status.table_counts["activity_sources"] == 1
    assert status.table_counts["activity_records"] == 2
    assert {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (plain, compressed)
    } == original_hashes


def test_corrupt_file_is_recorded_without_stopping_valid_files(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    database = tmp_path / "coach.sqlite3"
    write_fit_fixture(archive / "valid.fit")
    (archive / "corrupt.fit").write_bytes(b"broken")

    result = import_fit_archive(archive, database)

    assert result.imported == 1
    assert result.failed == 1
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT parse_status, error_code FROM activity_sources ORDER BY parse_status"
        ).fetchall()
    assert rows == [("failed", "invalid_fit"), ("imported", None)]


def test_dry_run_validates_without_creating_database(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    database = tmp_path / "missing.sqlite3"
    write_fit_fixture(archive / "ride.fit.gz", compressed=True)

    result = import_fit_archive(archive, database, dry_run=True)

    assert result.discovered == 1
    assert result.validated == 1
    assert result.imported == 0
    assert result.failed == 0
    assert not database.exists()


def test_csv_metadata_enriches_fit_atomically_and_remains_idempotent(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "archive"
    database = tmp_path / "coach.sqlite3"
    write_fit_fixture(archive / "activities" / "ride.fit.gz", compressed=True)
    _write_metadata(
        archive / "activities.csv",
        [
            {
                "Activity ID": "synthetic-101",
                "Activity Name": "Synthetic Long Ride",
                "Activity Description": "No athlete data",
                "Activity Type": "Virtual Ride",
                "Filename": "activities/ride.fit.gz",
            }
        ],
    )

    first = import_fit_archive(archive, database)
    second = import_fit_archive(archive, database)

    assert first.metadata_associated == 1
    assert first.metadata_unmatched == 0
    assert first.metadata_failed == 0
    assert second.duplicates == 1
    assert second.metadata_associated == 1
    with sqlite3.connect(database) as connection:
        activity = connection.execute(
            """SELECT name, description, activity_type, average_power_w
               FROM activities"""
        ).fetchone()
        sources = connection.execute(
            "SELECT source_type, external_id FROM activity_sources ORDER BY source_type"
        ).fetchall()
    assert activity == (
        "Synthetic Long Ride",
        "No athlete data",
        "virtual_ride",
        200.0,
    )
    assert sources == [
        (
            "fit_gz",
            "2160e2ab02e0b2f45e33cb33755a3123ff9ceba7f9c2030eeeeca37d624fbca8",
        ),
        ("strava_csv", "synthetic-101"),
    ]


def test_csv_reports_unmatched_and_invalid_rows_without_blocking_fit(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "archive"
    database = tmp_path / "coach.sqlite3"
    write_fit_fixture(archive / "ride.fit")
    _write_metadata(
        archive / "activities.csv",
        [
            {"Activity ID": "unmatched", "Filename": "missing.fit"},
            {"Activity ID": "unsafe", "Filename": "../private.fit"},
        ],
    )

    result = import_fit_archive(archive, database)

    assert result.imported == 1
    assert result.metadata_rows == 1
    assert result.metadata_associated == 0
    assert result.metadata_unmatched == 1
    assert result.metadata_failed == 1
