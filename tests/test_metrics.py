import pytest

from endurance_coach.metrics import (
    MissingTrainingDataError,
    intensity_factor,
    summarize_training,
    training_stress_score,
)


def test_power_metrics_are_deterministic(activities):
    ride = activities[0]
    assert intensity_factor(ride, ftp_watts=250) == 0.696
    assert training_stress_score(ride, ftp_watts=250) == 60.6


def test_power_metrics_preserve_missing_data(activities):
    ride_without_power = activities[1]
    assert intensity_factor(ride_without_power, ftp_watts=250) is None
    assert training_stress_score(ride_without_power, ftp_watts=250) is None


def test_training_summary_covers_fourteen_days(activities):
    summary = summarize_training(activities, ftp_watts=250)
    assert (summary.end_date - summary.start_date).days == 13
    assert summary.activity_count == 10
    assert summary.activities_missing_power == 2
    assert summary.total_distance_km == 423.1


def test_summary_requires_training_data():
    with pytest.raises(MissingTrainingDataError, match="at least one"):
        summarize_training([], ftp_watts=250)


def test_ftp_must_be_positive(activities):
    with pytest.raises(ValueError, match="positive"):
        training_stress_score(activities[0], ftp_watts=0)
