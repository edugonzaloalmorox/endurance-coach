import pytest

from endurance_coach.analysis import (
    LoadCompleteness,
    MissingTrainingDataError,
    calculate_training_load,
    intensity_factor,
    session_rpe_load,
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


def test_session_rpe_load_is_deterministic_and_preserves_missing_data(activities):
    assert session_rpe_load(activities[0]) == 300
    assert session_rpe_load(activities[0].model_copy(update={"perceived_exertion": None})) is None


def test_training_load_reports_coverage_units_and_provenance(activities):
    report = calculate_training_load(activities, ftp_watts=250)

    assert report.start_date.isoformat() == "2026-10-21"
    assert report.end_date.isoformat() == "2026-11-03"
    assert report.power_tss.value == 735.5
    assert report.power_tss.unit == "TSS"
    assert report.power_tss.sample_size == 8
    assert report.power_tss.missing_activity_count == 2
    assert report.power_tss.completeness is LoadCompleteness.PARTIAL
    assert report.power_tss.sources[0].model_dump(mode="json") == {
        "source": "synthetic",
        "activity_count": 8,
    }
    assert report.session_rpe_load.value == 5160
    assert report.session_rpe_load.sample_size == 10
    assert report.session_rpe_load.completeness is LoadCompleteness.COMPLETE


def test_training_load_keeps_unsupported_measures_unavailable(activities):
    without_load_inputs = [
        activity.model_copy(
            update={"normalized_power_w": None, "perceived_exertion": None}
        )
        for activity in activities[:2]
    ]

    report = calculate_training_load(without_load_inputs, ftp_watts=250)

    assert report.power_tss.value is None
    assert report.power_tss.sample_size == 0
    assert report.power_tss.missing_activity_count == 2
    assert report.power_tss.completeness is LoadCompleteness.UNAVAILABLE
    assert report.power_tss.sources == []
    assert report.power_tss.limitations == [
        "All 2 activities lack normalized power; this load is unavailable."
    ]
    assert report.session_rpe_load.value is None
    assert report.session_rpe_load.completeness is LoadCompleteness.UNAVAILABLE


def test_training_summary_covers_fourteen_days(activities):
    summary = summarize_training(activities, ftp_watts=250)
    assert (summary.end_date - summary.start_date).days == 13
    assert summary.activity_count == 10
    assert summary.activities_missing_power == 2
    assert summary.total_distance_km == 423.1
    assert summary.training_load.power_tss.value == summary.total_tss


def test_summary_requires_training_data():
    with pytest.raises(MissingTrainingDataError, match="at least one"):
        summarize_training([], ftp_watts=250)


def test_ftp_must_be_positive(activities):
    with pytest.raises(ValueError, match="positive"):
        training_stress_score(activities[0], ftp_watts=0)
