"""Build deterministic miniature FIT files containing only synthetic measurements."""

from __future__ import annotations

import gzip
import struct
from datetime import UTC, datetime
from pathlib import Path

_CRC_TABLE = (
    0x0000,
    0xCC01,
    0xD801,
    0x1400,
    0xF001,
    0x3C00,
    0x2800,
    0xE401,
    0xA001,
    0x6C00,
    0x7800,
    0xB401,
    0x5000,
    0x9C01,
    0x8801,
    0x4400,
)
_FIT_EPOCH = datetime(1989, 12, 31, tzinfo=UTC)


def _crc(data: bytes, initial: int = 0) -> int:
    crc = initial
    for byte in data:
        low = _CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc ^= low ^ _CRC_TABLE[byte & 0xF]
        low = _CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc ^= low ^ _CRC_TABLE[(byte >> 4) & 0xF]
    return crc


def _definition(local: int, global_number: int, fields: list[tuple[int, int, int]]) -> bytes:
    return (
        bytes((0x40 | local, 0, 0))
        + struct.pack("<H", global_number)
        + bytes((len(fields),))
        + b"".join(bytes(field) for field in fields)
    )


def _timestamp(value: datetime) -> int:
    return int((value - _FIT_EPOCH).total_seconds())


def build_fit_bytes(
    *,
    include_power: bool = True,
    multiple_sessions: bool = False,
    malformed_optional_field: bool = False,
) -> bytes:
    """Return a valid synthetic cycling FIT payload with two irregular samples."""
    start = datetime(2026, 1, 2, 8, 0, tzinfo=UTC)
    start_value = _timestamp(start)
    end_value = start_value + (195 if multiple_sessions else 75)

    file_fields = [(0, 1, 0x00), (4, 4, 0x86)]
    record_fields = [
        (253, 4, 0x86),
        (3, 1, 0x02),
        (4, 1, 0x02),
        (5, 4, 0x86),
        (6, 2, 0x84),
    ]
    if include_power:
        record_fields.append((7, 2, 0x84))
    session_fields = [
        (253, 4, 0x86),
        (2, 4, 0x86),
        (7, 4, 0x86),
        (8, 4, 0x86),
        (9, 4, 0x86),
        (5, 1, 0x00),
        (16, 1, 0x02),
        (20, 2, 0x84),
        (22, 2, 0x84),
        (34, 2, 0x84),
    ]

    data = bytearray()
    data += _definition(0, 0, file_fields)
    data += bytes((0, 4)) + struct.pack("<I", start_value)
    if malformed_optional_field:
        # Synthetic device-info field with a nonstandard size. Real exporters sometimes include
        # optional definitions like this; core activity messages remain structurally valid.
        data += _definition(3, 23, [(0, 1, 0x86)])
        data += bytes((3, 0))
    data += _definition(1, 20, record_fields)
    samples = [
        (start_value, 120, 80, 0, 7000, 180),
        (start_value + 75, 140, 88, 25000, 8000, 220),
    ]
    if multiple_sessions:
        samples.extend(
            [
                (start_value + 120, 125, 82, 0, 7200, 190),
                (end_value, 145, 90, 30000, 8200, 230),
            ]
        )
    for timestamp, heart_rate, cadence, distance, speed, power in samples:
        data += bytes((1,))
        data += struct.pack("<IBBIH", timestamp, heart_rate, cadence, distance, speed)
        if include_power:
            data += struct.pack("<H", power)
    data += _definition(2, 18, session_fields)
    session_values = [(start_value, start_value + 75, 25000, 130, 200, 12, 210)]
    if multiple_sessions:
        session_values.append((start_value + 120, end_value, 30000, 135, 210, 15, 220))
    for (
        session_start,
        session_end,
        distance,
        heart_rate,
        power,
        ascent,
        normalized,
    ) in session_values:
        data += bytes((2,))
        data += struct.pack(
            "<IIIII BBHHH",
            session_end,
            session_start,
            75000,
            70000,
            distance,
            2,
            heart_rate,
            power if include_power else 0xFFFF,
            ascent,
            normalized if include_power else 0xFFFF,
        )

    header_without_crc = struct.pack("<BBHI4s", 14, 0x20, 2200, len(data), b".FIT")
    header = header_without_crc + struct.pack("<H", _crc(header_without_crc))
    body_crc = _crc(data, _crc(header))
    return header + bytes(data) + struct.pack("<H", body_crc)


def write_fit_fixture(path: Path, *, compressed: bool = False) -> None:
    """Write one deterministic FIT or FIT.GZ fixture."""
    payload = build_fit_bytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(payload, mtime=0) if compressed else payload)
