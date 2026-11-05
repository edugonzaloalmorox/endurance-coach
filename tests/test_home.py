"""Smoke tests for the installable project scaffold."""

import endurance_coach


def test_package_is_importable() -> None:
    """The installed package exposes its initial version."""
    assert endurance_coach.__version__ == "0.1.0"
