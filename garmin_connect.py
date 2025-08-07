# Import required libraries
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from garminconnect import Garmin, GarminConnectAuthenticationError, GarminConnectConnectionError, GarminConnectTooManyRequestsError

# Import shared config and functions from other scripts
from config import logger, ACTIVITY_DAYS_RANGE, GARMIN_USER, GARMIN_PASS
from todoist_integration import create_todoist_task
from task_tracker import init_db, task_exists, mark_task_created

# Validate credentials from shared configuration
if not GARMIN_USER or not GARMIN_PASS:
    raise RuntimeError("Garmin user and password must be set as environment variables")

def fetch_data(start_date, end_date):
    try:
        api = Garmin(GARMIN_USER, GARMIN_PASS)
        api.login()
        logger.info("Authenticated as %s", GARMIN_USER)

        acts = api.get_activities_by_date(start_date.isoformat(), end_date.isoformat())
        df = pd.DataFrame(acts)
        return api, df

    except (GarminConnectAuthenticationError, GarminConnectConnectionError, GarminConnectTooManyRequestsError) as e:
        logger.error("API error: %s", e)
    except AssertionError:
        logger.error("Token/cache error — run example.py first")
    return None, pd.DataFrame()

def process_and_plot(df):
    if df.empty:
        print("No activities found in date range")
        return

    df = df[['activityId', 'activityType', 'startTimeLocal', 'duration', 'averageHR']].copy()
    df['activityType'] = df['activityType'].apply(lambda x: x.get('typeKey', 'unknown'))
    df['startTimeLocal'] = pd.to_datetime(df['startTimeLocal'])
    df['duration_hr'] = df['duration'] / 3600

    counts = df['activityType'].value_counts()
    counts_filtered = counts[counts >= 5]
    counts_filtered['Other'] = counts[counts < 5].sum()

    print("Activity counts in period:")
    print(counts_filtered.to_string())

    plt.figure(figsize=(6,6))
    plt.pie(counts_filtered.values, labels=counts_filtered.index, autopct='%1.1f%%')
    plt.title("Activity type distribution")
    plt.tight_layout()
    plt.show()

    plt.figure(figsize=(10,5))
    plt.plot(df['startTimeLocal'], df['duration_hr'], marker='o')
    plt.xlabel("Date")
    plt.ylabel("Duration (hr)")
    plt.title("Activity durations over time")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    print("\nAverage heart rate per activity:")
    print(df[['activityId','activityType','averageHR']].dropna().to_string(index=False))

def main():
    """
    end_time = datetime.date.today()
    start_time = end_time - datetime.timedelta(days=ACTIVITY_DAYS_RANGE)

    api, df = fetch_data(start_time, end_time)
    process_and_plot(df)

    today = end_time.isoformat()
    sleep = api.get_sleep_data(today)
    stats = api.get_stats(today)
    print("\nSleep summary for", today, ":", sleep.get("dailySleepDTO", {}))
    print("Stats for", today, ":", stats)

    # Create a task in Todoist
    create_todoist_task(content="Data has been analysed for Garmin Connect", due_string="today")
    """

    # Initialise tracking database
    init_db()

    # Use today only
    today = datetime.date.today()
    api, df = fetch_data(today, today)

    if df.empty:
        logger.info("No Garmin activities found for today")
        return

    for _, row in df.iterrows():
        activity_id = str(row['activityId'])

        if task_exists(activity_id):
            logger.info(f"Task already created for activity {activity_id}, skipping.")
            continue

        create_todoist_task(content="Oppdatere notater i kalenderhendelse for trening", due_string="today")
        logger.info(f"Created task for Garmin activity {activity_id}")
        mark_task_created(activity_id)

if __name__ == "__main__":
    main()
