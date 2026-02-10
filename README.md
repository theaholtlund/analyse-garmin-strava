# Data Analysis for Strava and Garmin Connect

Work in progress. Project working with Strava and Garmin Connect data in various ways, aiming to analyse, process and transform activities.

## Ideas for Later, Components to Implement

- Allow user to send some report regarding total distance ran this year so far at given time intervals, for example every morning? Include average per day that year so far, as well as total (helpful in terms of personal goal)?
- Implement functionality for dashboard on total distance ran this year, including from multisport activities?
- Include total distance for other activity types in dashboard too?
- Add to task in Todoist if one already exists, instead of creating new one?
- Implement working functionality in GitHub workflow to upload cycling activities to Garmin Connect?
- Remove default gear when uploading virtual ride activities to Garmin Connect?
- Implement functionality to update calendar notes using AppleScript?
- Implement functionality to create Todoist task suggesting updating gear in Garmin Connect if calendar description contains certain words, such as for a speed run?

## Requirements

- Python ≥ 3.10, as this is required by GarminConnect
- ChromeDriver, which can be installed for example via Homebrew
- Create a Google Account app password for sending e-mails via Google Account → Security → App passwords
- Strava developer app, created at <https://www.strava.com/settings/api>

## Create a Virtual Environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

## Install the Requirements

```bash
pip install -r requirements.txt
```

## Configure Environment Variables

Copy the environment template to an environment file, and fill in the variables needed to run the project scripts:

```bash
cp .env.template .env
```

## Run the Project Files

Garmin Connect:
The file holds functions related to Garmin Connect operations, and running the script will create follow-up tasks in Todoist for today's activities that have not yet been processed.

```bash
python garmin_connect.py
```

Strava:
The file holds functions related to Strava operations, and running the script will output details on the activities completed on the days specified in the ACTIVITY_DAYS_RANGE variable from Strava.

```bash
python strava.py
```

MOWL Cycling:
The file holds functions related to MOWL Cycling operations. No main script logic.

```bash
python mowl_cycling.py
```

Comparison between Strava and Garmin:
The file holds functions related to comparing activities from Garmin Connect to Strava, and running the script will output any activities from Garmin Connect that are not in Strava for the days specified in the ACTIVITY_DAYS_RANGE variable.

```bash
python compare_strava_garmin.py
```

Sync between Strava and Garmin:
The file holds functions related to keeping track of activities synchronised from Strava to Garmin Connect, and running the script will synchronise activities of the type virtual ride from Strava to Garmin Connect.

```bash
python strava_garmin_sync.py
```

Running metrics from Garmin Connect:
Running this script will display a dashboard with various metrics related to running activities, distances and statistics for the current year so far.

```bash
python dashboard.py
```

Testing:
The project has a tests directory. It uses pytest with mocked APIs, so no there are no real API calls.

```bash
pytest -v tests/test_garmin_connect.py
pytest -v tests/test_task_tracker.py
pytest -v tests/test_todoist_integration.py
```

## Useful External Resources

- [Garmin API Integration for Developers](https://help.validic.com/space/VCS/1681490020/Garmin+API+Integration+for+Developers): Contains list with the names of all Garmon Connect activities
