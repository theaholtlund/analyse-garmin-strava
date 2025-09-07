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