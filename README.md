# Data Analysis for Strava and Garmin Connect

Work in progress. Project working with Strava and Garmin Connect data in various ways, aiming to analyse, process and transform activities.

## Ideas for Later, Components to Implement

- Allow user to send some report regarding total distance ran this year so far at given time intervals, for example every morning? Include average per day that year so far, as well as total (helpful in terms of personal goal)?
- Implement functionality for dashboard on total distance ran this year, including from multisport activities?
- Include total distance for other activity types in dashboard too?
- Add to task in Todoist if one already exists, instead of creating new one?
- Implement working functionality in GitHub workflow to upload cycling activities to Garmin Connect?
- Remove default gear when uploading virtual ride activities to Garmin Connect?
- Implement functionality to update calendar notes with calories using AppleScript?
- Implement functionality to create Todoist task suggesting updating gear in Garmin Connect if calendar description contains certain words, such as for a speed run?

## Requirements

- Python ≥ 3.12, as this is required by the pinned GarminConnect version
- ChromeDriver, which can be installed for example via Homebrew
- Create a Google Account app password for sending e-mails via Google Account → Security → App passwords
- Strava developer app, created at <https://www.strava.com/settings/api>

## Create a Virtual Environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

## Garmin MFA and GitHub Actions

Garmin MFA cannot be completed inside a scheduled GitHub Actions run. Log in once locally, save the Garmin token file, and let the workflow restore that token file from a GitHub secret.

1. Install the requirements locally:

```bash
pip install -r requirements.txt
```

2. Create the Garmin token file locally and enter the MFA code from your email when prompted:

```bash
python scripts/create_garmin_tokens.py
```

3. Add a GitHub Actions repository secret named `GARMIN_TOKENS_JSON` with the contents of:

```bash
~/.garminconnect/garmin_tokens.json
```

On macOS, this copies the token JSON to your clipboard:

```bash
pbcopy < ~/.garminconnect/garmin_tokens.json
```

4. Keep these existing GitHub secrets configured too: `GARMIN_USER`, `GARMIN_PASS`, `TODOIST_SECTION_ID`, `TODOIST_PROJECT_ID`, and `TODOIST_API_TOKEN`.

After that, the scheduled workflow writes the token JSON back to `~/.garminconnect/garmin_tokens.json`, sets `GARMINTOKENS=~/.garminconnect`, and the `garminconnect` library refreshes the session automatically. If Garmin later revokes or expires the refresh token, rerun `python scripts/create_garmin_tokens.py` and update `GARMIN_TOKENS_JSON`.

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
The project has a tests directory and uses pytest with mocked APIs.

```bash
pytest -v
```

## Useful External Resources

- [Garmin API Integration for Developers](https://help.validic.com/space/VCS/1681490020/Garmin+API+Integration+for+Developers): Contains list with the names of all Garmon Connect activities
- [Previous problem with Garmin Connect Authentication](https://github.com/cyberjunky/python-garminconnect/issues/332): Discussion related to problems authenticating with Garmi Connect

## Experimental MOWL and Garmin FIT merge

Create a local test file from a MOWL original FIT and a Garmin original FIT or
Garmin original ZIP:

```bash
python merge_cycling_fit.py path/to/mowl.fit path/to/garmin.zip outputs/merged.fit
```

The files must contain one session each and overlap by at least 80% of the
shorter record interval. The output has one record per timestamp; on overlapping
heart-rate readings MOWL is preferred, with Garmin as fallback when MOWL has no valid reading. Power, cadence,
speed and distance records come from MOWL. The larger session distance is used
as the total, without scaling the original MOWL distance series. Elapsed time
covers both recordings; timer time is the larger explicitly recorded timer value,
if present. These are different measures, especially when a device was paused.

This is an experimental local export, not an automated synchronization. The
summary distance may differ from the record series and Garmin may recalculate it.
The Garmin file supplies the base, including its device-specific messages, laps,
events, calories and training-effect fields. MOWL power and cadence summaries
are added; pause events remain Garmin’s. Some summaries may not describe the
added data exactly, and Garmin may ignore or recalculate fields on import. Import
behavior, including possible duplicates or rejection, has not been verified. Keep both originals and do not delete the watch
activity based on this file without checking the imported result.

## Automatic MOWL to Garmin sync

On the configured Mac, the user LaunchAgent `no.theaholtlund.mowl-garmin-sync`
runs hourly, only for sessions starting after installation. It waits two hours
after the MOWL activity ends to allow the watch to sync. macOS must be running
and the user must be logged in; an expired Strava browser session or Garmin
authentication will stop sync until reauthenticated. The launchd log and local
journal are in `outputs/mowl-sync`. Keep this ignored folder: the journal prevents
repeat uploads, and it also contains original and merged backups.

The sync uses the logged-in Strava website because the user's Strava API
application currently reports `Inactive`. It identifies MOWL rides using
`MOWL_STRAVA_MARKER` in the activity name. It matches at most one Garmin cycling
activity using timestamps and duration. If there is no match after the waiting
period, it uploads the original MOWL FIT; if a matching Garmin activity arrives
later, it cannot retroactively merge that activity automatically. Change the
waiting period in the LaunchAgent if Garmin regularly syncs late.

When there is a match, the Garmin original is downloaded and combined with MOWL.
MOWL heart rate is preferred, with Garmin as fallback. After uploading, key
metrics are compared with Garmin's imported activity. The program locates Strava
watch copies by comparing the Garmin FIT's device ID and session timestamps to
the Strava original FIT. Once a matching Strava copy is found and the checks
pass, it deletes that copy and the original Garmin activity. The MOWL activity
is protected. If verification fails, the original Garmin activity is kept. If
an upload or cleanup result is uncertain, the journal blocks automatic retries
until reviewed. A missing Strava watch copy leaves the original Garmin activity
in place and will be retried while the activity remains in the lookback window.
Web selectors, exports and Garmin's unofficial API can change or stop working.

Useful commands (run from the project directory):

```bash
# Check without uploading or deleting anything:
.venv/bin/python mowl_sync.py --source browser --days 2
# Check the scheduled run's logs:
tail -n 100 outputs/mowl-sync/launchd.log
# Stop the scheduled job:
launchctl bootout gui/$(id -u)/no.theaholtlund.mowl-garmin-sync
```

To re-enable after stopping, use `launchctl bootstrap gui/$(id -u)
~/Library/LaunchAgents/no.theaholtlund.mowl-garmin-sync.plist`. To install on
another Mac after setup, run `.venv/bin/python scripts/install_mowl_sync.py`.
To restore an expired Strava session, run
`.venv/bin/python scripts/strava_session_setup.py` and log in in the Chrome
window. The dedicated profile `outputs/strava-browser-profile` grants access to
the account and must remain private. Never commit credentials or token files.
