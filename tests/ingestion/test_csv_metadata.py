"""Tests for bounded, path-safe historical CSV metadata ingestion."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from endurance_coach.ingestion import FitIngestionError, read_metadata_csv


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def test_reads_metadata_and_rejects_unsafe_or_duplicate_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "activities.csv"
    _write_csv(
        csv_path,
        [
            {
                "Activity ID": "101",
                "Activity Name": "Long Ride",
                "Activity Description": "Synthetic description",
                "Activity Type": "Virtual Ride",
                "Filename": "activities/ride.fit.gz",
            },
            {"Activity ID": "101", "Filename": "activities/other.fit"},
            {"Activity ID": "102", "Filename": "../private.fit"},
        ],
    )

    catalog = read_metadata_csv(csv_path, tmp_path)

    assert catalog.invalid_rows == 2
    assert list(catalog.rows) == ["activities/ride.fit.gz"]
    metadata = catalog.rows["activities/ride.fit.gz"]
    assert metadata.external_id == "101"
    assert metadata.name == "Long Ride"
    assert metadata.description == "Synthetic description"
    assert metadata.activity_type == "virtual_ride"


def test_rejects_csv_outside_archive_and_missing_filename_column(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    outside = tmp_path / "activities.csv"
    outside.write_text("Filename\nride.fit\n", encoding="utf-8")

    with pytest.raises(FitIngestionError, match="metadata_unavailable"):
        read_metadata_csv(outside, archive)

    inside = archive / "activities.csv"
    inside.write_text("Activity ID,Activity Name\n1,Ride\n", encoding="utf-8")
    with pytest.raises(FitIngestionError, match="metadata_missing_filename_column"):
        read_metadata_csv(inside, archive)


def test_reads_spanish_strava_headers(tmp_path: Path) -> None:
    csv_path = tmp_path / "activities.csv"
    csv_path.write_text(
        "ID de actividad,Nombre de la actividad,Tipo de actividad,"
        "Descripción de la actividad,Nombre del archivo\n"
        "101,Vuelta sintética,Ciclismo virtual,Sin datos personales,"
        "activities/ride.fit.gz\n"
        "102,Actividad manual,Ciclismo virtual,Sin archivo,\n"
        "103,Otro formato,Ciclismo virtual,No es FIT,activities/ride.gpx\n",
        encoding="utf-8",
    )

    catalog = read_metadata_csv(csv_path, tmp_path)

    metadata = catalog.rows["activities/ride.fit.gz"]
    assert catalog.invalid_rows == 0
    assert len(catalog.rows) == 1
    assert metadata.external_id == "101"
    assert metadata.name == "Vuelta sintética"
    assert metadata.activity_type == "ciclismo_virtual"
    assert metadata.description == "Sin datos personales"
