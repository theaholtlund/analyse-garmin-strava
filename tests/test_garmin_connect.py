# Import required libraries
import sys
import types

# Define lightweight, fake Garmin class instead of calling real Garmin Connect API
# Simulate login, fetch activities and upload files in a predictable, testable way
class MockGarmin:
    def __init__(self, user, pw):
        self.user, self.pw = user, pw

    def login(self):
        # Simulate successful login without contacting Garmin
        return True

    def get_activities_by_date(self, start, end):
        # Return a single fake activity as a list of dicts, shaped like what the real API would return
        return [{
            "activityId": 1,
            "activityName": "Run",
            "activityType": {"typeKey": "running"},
            "startTimeLocal": "2024-01-01T10:00:00",
            "duration": 1800,  # 30 minutes
            "averageHR": 140   # Beats per minute
        }]

    def upload_activity(self, file_path):
        # Simulate upload success unless file name contains "fail"
        if "fail" in str(file_path):
            raise Exception("Upload failed")
        return True


# Define fake Garmin exceptions, needed because Garmin Connect script imports them
class DummyError(Exception):
    pass


# Garmin Connect script imports Garmin and related exceptions from the Garmin Connect package
# To avoid using real package, mock versions are injected so that test doubles are used instead on import
sys.modules['garminconnect'] = types.SimpleNamespace(
    Garmin=MockGarmin,
    GarminConnectAuthenticationError=DummyError,
    GarminConnectConnectionError=DummyError,
    GarminConnectTooManyRequestsError=DummyError,
)

# After patching, the module can safely be imported
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
    _, df = garmin_connect.fetch_data("2024-01-01", "2024-01-02", creds)

    assert not df.empty, "Expected at least one activity in DataFrame"
    assert "activityId" in df.columns, "Missing expected column from activity data"
