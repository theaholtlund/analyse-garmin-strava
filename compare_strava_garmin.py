# Import required libraries
import datetime
import logging
from garmin_connect import fetch_data
from strava import get_latest_activities
from intelligent_cycling import intelligent_cycling_login

# Set up logging for information
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_garmin_activity_ids(df):
    if df.empty:
        return set()
    return set(df['activityId'].astype(str))

def get_strava_activity_ids(df):
    if df.empty:
        return set()
    return set(df['id'].astype(str))

def main():
    # Fetch the Garmin activities for last 14 days
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=14)
    _, garmin_df = fetch_data(start_date, end_date)
    garmin_ids = get_garmin_activity_ids(garmin_df)

    # Fetch the latest 30 Strava activities
    strava_df = get_latest_activities(limit=30)
    strava_ids = get_strava_activity_ids(strava_df)

    # Find the Garmin activities missing on Strava
    missing_on_strava = garmin_ids - strava_ids
    logger.info(f"Garmin activities not on Strava: {missing_on_strava}")

    if missing_on_strava:
        print("Simulating upload of these Garmin activities to Strava, not yet implemented:")
        for act_id in missing_on_strava:
            print(f" - Activity ID {act_id}")

    # Login to Intelligent Cycling, simulate integration
    try:
        intelligent_cycling_login()
        logger.info("Intelligent Cycling login successful.")
    except Exception as e:
        logger.error(f"Intelligent Cycling login failed: {e}")

if __name__ == "__main__":
    main()
