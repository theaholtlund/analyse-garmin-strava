# Import required libraries
import os
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from garminconnect import Garmin, GarminConnectAuthenticationError, GarminConnectConnectionError, GarminConnectTooManyRequestsError

# Import shared config and functions from other scripts
from config import (logger, GARMIN_USER, GARMIN_PASS, ACTIVITY_DAYS_RANGE, ACTIVITY_TYPE_TRANSLATIONS, RUNNING_THROUGH_GITHUB, LOGO_PATH, PLOT_ENABLED)
from todoist_integration import create_todoist_task
from task_tracker import init_db, task_exists, mark_task_created

# Validate credentials from shared configuration
if not GARMIN_USER or not GARMIN_PASS:
    raise RuntimeError("Garmin user and password must be set as environment variables")

def translate_activity_type(type_key):
    """Return the Norwegian activity name for a given Garmin Connect type key."""
    return ACTIVITY_TYPE_TRANSLATIONS.get(type_key.lower())

def extract_activity_type(row):
    """Extract the typeKey from activity row."""
    return row.get('activityType', {}).get('typeKey', 'unknown')

def fetch_data(start_date, end_date):
    """Fetch activities from Garmin Connect for a given date range."""
    try:
        api = Garmin(GARMIN_USER, GARMIN_PASS)
        api.login()
        logger.info("Authenticated as %s", GARMIN_USER)

        acts = api.get_activities_by_date(start_date.isoformat(), end_date.isoformat())
        df = pd.DataFrame(acts)
        return api, df

    except (GarminConnectAuthenticationError, GarminConnectConnectionError, GarminConnectTooManyRequestsError) as e:
        logger.error("API error: %s", e, exc_info=True)
    except AssertionError:
        logger.error("Token or cache error for Garmin", exc_info=True)
    return None, pd.DataFrame()

def insert_logo(ax, fig):
    """Insert application logo into the given figure if available."""
    try:
        logo_img = mpimg.imread(LOGO_PATH)
        logo_ax = fig.add_axes([0.80, 0.80, 0.18, 0.18], anchor='NE', zorder=1)
        logo_ax.imshow(logo_img)
        logo_ax.axis('off')
    except FileNotFoundError:
        logger.warning("Logo not found at graphics folder")
    except Exception as e:
        logger.warning("Failed to insert logo: %s", e)

def prepare_dataframe(df):
    """Normalise dataframe columns and add derived fields used for plotting and tasks."""
    if df.empty:
        return df
    # Keep only expected columns if present, handle missing keys safely
    cols = ['activityId', 'activityType', 'startTimeLocal', 'duration', 'averageHR']
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df = df[cols].copy()
    df['activityTypeKey'] = df['activityType'].apply(lambda x: (x or {}).get('typeKey', 'unknown'))
    df['activityTypeNameNo'] = df['activityTypeKey'].apply(lambda k: translate_activity_type(k) or 'annet')
    df['startTimeLocal'] = pd.to_datetime(df['startTimeLocal'])
    df['duration_hr'] = df['duration'].fillna(0) / 3600
    return df

def plot_pie(counts):
    """Create pie chart for activity distribution."""
    figure_1 = plt.figure(figsize=(6, 6), constrained_layout=True)
    plt.pie(counts.values, labels=counts.index.str.capitalize(), autopct='%1.1f%%')
    plt.title("Aktivitetsfordeling")
    insert_logo(plt.gca(), figure_1)
    if PLOT_ENABLED:
        plt.show()
    else:
        plt.close(figure_1)

def plot_line(df):
    """Create line plot for activity duration over time."""
    figure_2 = plt.figure(figsize=(10, 5), constrained_layout=True)
    plt.plot(df['startTimeLocal'], df['duration_hr'], marker='o')
    plt.xlabel("Dato")
    plt.ylabel("Varighet i timer")
    plt.title("Varighet for aktivitet over tid")
    plt.xticks(rotation=45)
    insert_logo(plt.gca(), figure_2)
    if PLOT_ENABLED:
        plt.show()
    else:
        plt.close(figure_2)

def process_and_plot(df):
    """Process activities dataframe and produce plots and optional sensitive output."""
    if df.empty:
        if not RUNNING_THROUGH_GITHUB:
            print("No activities found in date range")
        return

    df = prepare_dataframe(df)

    counts = df['activityTypeNameNo'].value_counts()
    # counts_filtered = counts[counts >= 5]
    # counts_filtered['Annet'] = counts[counts < 5].sum()

    # Only print personal training summaries when running locally
    if not RUNNING_THROUGH_GITHUB:
        print("Aktiviteter i perioden:")
        counts_case = counts.rename(index=lambda x: x.capitalize())
        counts_case.index.name = "Activity Type"
        print(counts_case.to_string())

    # Create the graphics pie chart
    plot_pie(counts)

    # Create the graphics line plot
    plot_line(df)

    # Only print sensitive HR table when running locally
    if not RUNNING_THROUGH_GITHUB:
        print("\nGjennomsnittspuls per aktivitet:")
        print(df[['activityId', 'activityTypeNameNo', 'averageHR']].dropna()
              .assign(activityTypeNameNo=lambda x: x['activityTypeNameNo'].str.capitalize())
              .rename(columns={
                'activityId': 'Activity ID',
                'activityTypeNameNo': 'Activity Type',
                'averageHR': 'Average HR'
            }).to_string(index=False))

def upload_activity_file_to_garmin(file_path): # FOR WIP FUNCTIONALITY
    """Upload activity FIT file to Garmin Connect using garminconnect library."""
    api = Garmin(GARMIN_USER, GARMIN_PASS)
    api.login()
    api.upload_activity(file_path)

def main():
    """Main entry point for fetching, processing and creating tasks."""
    end_time = datetime.date.today()
    start_time = end_time - datetime.timedelta(days=ACTIVITY_DAYS_RANGE)

    api, df = fetch_data(start_time, end_time)
    process_and_plot(df)

    """
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

    # Use today only for task creation
    today = datetime.date.today()
    _, df = fetch_data(today, today)

    if df.empty:
        logger.info("No activities from Garmin found for today")
        return

    df = prepare_dataframe(df)

    for _, row in df.iterrows():
        activity_id = str(row['activityId'])
        activity_type_key = row['activityTypeKey']
        activity_type_no = row['activityTypeNameNo']

        if task_exists(activity_id):
            logger.info(f"Task already created for activity {activity_type_key} ({activity_id}), skipping.")
            continue

        task_content = f"Oppdatere notater i kalenderhendelse for {activity_type_no}"
        create_todoist_task(content=task_content, due_string="today")
        logger.info(f"Created task for Garmin activity {activity_type_key} ({activity_id})")
        mark_task_created(activity_id)

if __name__ == "__main__":
    main()
