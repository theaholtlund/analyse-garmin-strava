# Import required libraries
import sys
import types

# Define lightweight, fake Garmin class instead of calling real Garmin Connect API
# Simulate login, fetch activities and upload files in a predictable, testable way
class MockGarmin:
    def __init__(self, email=None, password=None, **kwargs):
        self.user, self.pw = email, password
        self.kwargs = kwargs

    def login(self, tokenstore=None):
        # Simulate successful login without contacting Garmin
        self.tokenstore = tokenstore
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
            return False
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
