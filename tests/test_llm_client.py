import json
import os
import pytest
from unittest.mock import patch
from llm_client import LlmClient

ACTIVITY_WITH_HR = {
    'name': 'Tempo Run',
    'type': 'Run',
    'start_date_local': '2026-04-13T07:00:00Z',
    'distance': 8000,
    'moving_time': 2400,           # 8 km in 40 min → 5:00 min/km
    'average_speed': 8000 / 2400,
    'elapsed_time': 2450,
    'total_elevation_gain': 30.0,
    'average_heartrate': 161.0,
    'max_heartrate': 178.0,
    'average_cadence': 88.0,
    'splits_metric': [{'distance': 1000, 'moving_time': 300}],
    'perceived_exertion': 7,
    'irrelevant_field': 'should be dropped',
    'another_extra': 123,
}

ACTIVITY_NO_HR = {k: v for k, v in ACTIVITY_WITH_HR.items() if 'heartrate' not in k}


@pytest.fixture(scope='module')
def client():
    with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
        return LlmClient()


# --- _filter_activity_data ---

def test_filter_drops_extra_keys(client):
    data_string = client._filter_activity_data(ACTIVITY_WITH_HR)
    data = json.loads(data_string)
    assert 'irrelevant_field' not in data
    assert 'another_extra' not in data


def test_filter_keeps_useful_keys(client):
    data_string = client._filter_activity_data(ACTIVITY_WITH_HR)
    data = json.loads(data_string)
    assert 'name' in data
    assert 'splits_metric' in data
    assert 'average_heartrate' in data


def test_filter_returns_valid_json(client):
    data_string = client._filter_activity_data(ACTIVITY_WITH_HR)
    parsed = json.loads(data_string)
    assert isinstance(parsed, dict)


def test_filter_ignores_missing_useful_keys(client):
    # Activity missing some useful keys — should not raise
    minimal = {'name': 'Easy Run', 'distance': 3000}
    data_string = client._filter_activity_data(minimal)
    data = json.loads(data_string)
    assert data == {'name': 'Easy Run', 'distance': 3000}


# --- _build_summary ---

def test_summary_contains_header(client):
    summary = client._build_summary(ACTIVITY_WITH_HR)
    assert 'Pre-calculated session summary' in summary


def test_summary_contains_distance(client):
    summary = client._build_summary(ACTIVITY_WITH_HR)
    assert '8.0 km' in summary


def test_summary_contains_pace(client):
    summary = client._build_summary(ACTIVITY_WITH_HR)
    assert '5:00 min/km' in summary


def test_summary_contains_elevation(client):
    summary = client._build_summary(ACTIVITY_WITH_HR)
    assert '30.0 m' in summary


def test_summary_contains_date(client):
    summary = client._build_summary(ACTIVITY_WITH_HR)
    assert '2026-04-13' in summary


def test_summary_includes_hr_lines_when_present(client):
    summary = client._build_summary(ACTIVITY_WITH_HR)
    assert 'Avg HR' in summary
    assert 'Max HR' in summary


def test_summary_omits_hr_lines_when_absent(client):
    summary = client._build_summary(ACTIVITY_NO_HR)
    assert 'Avg HR' not in summary
    assert 'Max HR' not in summary
