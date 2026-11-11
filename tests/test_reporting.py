import datetime
from unittest.mock import Mock

import pandas as pd

import dashboard
import weekly_report
from garmin_connect import prepare_dataframe
from utils import save_debug_screenshot


def test_repeated_normalization_preserves_activity_type():
    df = pd.DataFrame([{'activityTypeKey': 'running', 'distance': 1000}])
    assert dashboard.filter_running_activities(prepare_dataframe(df))['distance_km'].tolist() == [1.0]


def test_running_activity_without_distance():
    df = pd.DataFrame([{'activityType': {'typeKey': 'running'}}])
    assert dashboard.filter_running_activities(df)['distance_km'].tolist() == [0]


def test_year_end_progress_uses_calendar_year(monkeypatch):
    class YearEnd(datetime.date):
        @classmethod
        def today(cls):
            return cls(2024, 12, 31)

    monkeypatch.setattr(dashboard.datetime, 'date', YearEnd)
    monkeypatch.setattr(dashboard, 'check_garmin_credentials', lambda: {})
    monkeypatch.setattr(dashboard, 'fetch_data', lambda *args: (None, pd.DataFrame([
        {'activityType': {'typeKey': 'walking'}, 'distance': 1000}
    ])))
    status = dashboard.generate_weekly_running_status(3660)
    assert status['expected_km_by_now'] == 3660
    assert status['total_km'] == 0


def test_weekly_report_calls_generator(monkeypatch):
    generator = Mock(return_value=None)
    monkeypatch.setattr(weekly_report, 'generate_weekly_running_status', generator)
    weekly_report.main()
    generator.assert_called_once()


def test_screenshot_accepts_boolean_configuration(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    driver = Mock()
    assert save_debug_screenshot(driver, Mock(), True) is not None
    driver.save_screenshot.assert_called_once()
    assert save_debug_screenshot(driver, Mock(), False) is None
