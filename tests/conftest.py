import pytest

from endurance_coach.fixtures import synthetic_activities


@pytest.fixture
def activities():
    return synthetic_activities()
