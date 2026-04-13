import pytest
from data_processing import StravaDataProcessor

# Base activity with all fields present. average_speed chosen so pace math
# stays clean with integer arithmetic (5000m / 1500s = 5:00 min/km).
BASE_ACTIVITY = {
    'name': 'Morning Run',
    'type': 'Run',
    'start_date_local': '2026-04-13T07:30:00Z',
    'distance': 5000,        # 5 km
    'moving_time': 1500,     # 25 min → 5:00 min/km
    'average_speed': 5000 / 1500,  # 3.333... m/s → 5:00 min/km
    'total_elevation_gain': 42.0,
    'average_heartrate': 152.0,
    'max_heartrate': 168.0,
}


# --- distance ---

def test_distance_converted_to_km():
    result = StravaDataProcessor.process_activity(BASE_ACTIVITY)
    assert result['distance_km'] == 5.0


# --- pace from average_speed ---

def test_pace_from_average_speed():
    result = StravaDataProcessor.process_activity(BASE_ACTIVITY)
    assert result['pace'] == '5:00 min/km'


def test_pace_includes_unit():
    result = StravaDataProcessor.process_activity(BASE_ACTIVITY)
    assert 'min/km' in result['pace']


# --- pace fallback when average_speed is 0 ---

def test_pace_fallback_uses_time_and_distance():
    activity = {**BASE_ACTIVITY, 'average_speed': 0}
    result = StravaDataProcessor.process_activity(activity)
    assert result['pace'] == '5:00 min/km'


def test_pace_when_no_speed_and_no_distance():
    activity = {**BASE_ACTIVITY, 'average_speed': 0, 'distance': 0}
    result = StravaDataProcessor.process_activity(activity)
    assert result['pace'] == '--:-- min/km'


# --- duration format ---

def test_duration_under_one_hour():
    # 45 min 30 s → "45:30"
    activity = {**BASE_ACTIVITY, 'moving_time': 45 * 60 + 30}
    result = StravaDataProcessor.process_activity(activity)
    assert result['duration'] == '45:30'


def test_duration_exactly_one_hour():
    activity = {**BASE_ACTIVITY, 'moving_time': 3600}
    result = StravaDataProcessor.process_activity(activity)
    assert result['duration'] == '1:00:00'


def test_duration_over_one_hour():
    # 1h 23min 45s → "1:23:45"
    activity = {**BASE_ACTIVITY, 'moving_time': 3600 + 23 * 60 + 45}
    result = StravaDataProcessor.process_activity(activity)
    assert result['duration'] == '1:23:45'


# --- heart rate ---

def test_hr_fields_present_when_available():
    result = StravaDataProcessor.process_activity(BASE_ACTIVITY)
    assert result['avg_heartrate'] == 152.0
    assert result['max_heartrate'] == 168.0


def test_hr_fields_absent_when_missing():
    activity = {k: v for k, v in BASE_ACTIVITY.items() if 'heartrate' not in k}
    result = StravaDataProcessor.process_activity(activity)
    assert 'avg_heartrate' not in result
    assert 'max_heartrate' not in result


def test_only_avg_hr_missing():
    activity = {k: v for k, v in BASE_ACTIVITY.items() if k != 'average_heartrate'}
    result = StravaDataProcessor.process_activity(activity)
    assert 'avg_heartrate' not in result
    assert result['max_heartrate'] == 168.0


# --- other fields ---

def test_date_extracted_from_iso_string():
    result = StravaDataProcessor.process_activity(BASE_ACTIVITY)
    assert result['date'] == '2026-04-13'


def test_elevation_present():
    result = StravaDataProcessor.process_activity(BASE_ACTIVITY)
    assert result['elevation_m'] == 42.0


def test_name_and_type_passed_through():
    result = StravaDataProcessor.process_activity(BASE_ACTIVITY)
    assert result['name'] == 'Morning Run'
    assert result['type'] == 'Run'


# --- edge cases ---

def test_empty_activity_returns_empty():
    result = StravaDataProcessor.process_activity({})
    assert result == {}
