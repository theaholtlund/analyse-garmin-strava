# Import required libraries
import os
import sys
import datetime

# Ensure parent directory is on sys path so it can import script functionality
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import modules after patching
import garmin_connect


# The actual unit tests start here
def test_fetch_data_returns_dataframe(tmp_path):
    """
    GIVEN valid Garmin credentials
    WHEN fetch_data() is called
    THEN it should return a non-empty DataFrame
         containing expected activity fields.
    """
    creds = {"GARMIN_USER": "u", "GARMIN_PASS": "p"}
    start = datetime.date(2024, 1, 1)
    end = datetime.date(2024, 1, 2)
    _, df = garmin_connect.fetch_data(start, end, creds)

    assert not df.empty, "Expected at least one activity in DataFrame"
    assert "activityId" in df.columns, "Missing expected column from activity data"


def test_upload_activity_success(tmp_path):
    """
    GIVEN valid Garmin credentials
    WHEN upload_activity_file_to_garmin() is called with a 'good' file
    THEN it should return True, meaning upload succeeded.
    """
    creds = {"GARMIN_USER": "u", "GARMIN_PASS": "p"}
    assert garmin_connect.upload_activity_file_to_garmin("good.fit", creds) is True


def test_upload_activity_failure(tmp_path):
    """
    GIVEN valid Garmin credentials
    WHEN upload_activity_file_to_garmin() is called with a 'bad' file
         (filename contains 'fail', which our mock simulates as error)
    THEN it should return False, meaning upload failed gracefully.
    """
    creds = {"GARMIN_USER": "u", "GARMIN_PASS": "p"}
    assert garmin_connect.upload_activity_file_to_garmin("fail.fit", creds) is False
