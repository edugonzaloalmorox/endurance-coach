import json
from pathlib import Path

from endurance_coach.models import TrainingActivity


def test_committed_sample_data_is_valid_and_spans_fourteen_days():
    data_path = Path(__file__).parents[1] / "data" / "synthetic_activities.json"
    activities = [
        TrainingActivity.model_validate(row)
        for row in json.loads(data_path.read_text(encoding="utf-8"))
    ]

    assert len(activities) == 10
    assert (activities[-1].started_at.date() - activities[0].started_at.date()).days == 13
