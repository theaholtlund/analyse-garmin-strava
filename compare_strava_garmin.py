# Import required libraries
import datetime
import pandas as pd

# Import shared config and functions from other scripts
from config import logger
from garmin_connect import fetch_data
from strava import get_latest_activities
from intelligent_cycling import intelligent_cycling_login

def normalise_garmin(df):
    df = df[['activityName', 'startTimeLocal']].copy()
    df['startTimeLocal'] = pd.to_datetime(df['startTimeLocal']).dt.tz_localize(None).dt.floor('min')
    return df

def normalise_strava(df):
    df = df[['name', 'start_date_local']].copy()
    df['start_date_local'] = pd.to_datetime(df['start_date_local']).dt.tz_localize(None).dt.floor('min')
    return df

def main():
    # Fetch the activities from Garmin
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=14)
    _, garmin_df = fetch_data(start_date, end_date)
    garmin_df = normalise_garmin(garmin_df)

    # Fetch the activities from Strava
    strava_df = get_latest_activities(days=14)
    strava_df = normalise_strava(strava_df)

    # Compare by start time only
    garmin_times = set(garmin_df['startTimeLocal'])
    strava_times = set(strava_df['start_date_local'])

    missing_times = garmin_times - strava_times
    logger.info(f"Garmin activity times not found on Strava: {missing_times}")

    if missing_times:
        print("Simulating upload of these Garmin activities to Strava, not yet implemented:")
        for ts in sorted(missing_times):
            row = garmin_df[garmin_df['startTimeLocal'] == ts].iloc[0]
            print(f" - {row['activityName']} at {ts.strftime('%d-%m-%Y %H:%M')}")
    else:
        print("All Garmin activities are present on Strava")

    # Login to Intelligent Cycling profile
    try:
        intelligent_cycling_login()
        logger.info("The login for Intelligent Cycling was successful")
    except Exception as e:
        logger.error(f"The login for Intelligent Cycling failed: {e}")

if __name__ == "__main__":
    main()
