import pytest

from endurance_coach.sample_data import synthetic_activities


@pytest.fixture
def activities():
    return synthetic_activities()
