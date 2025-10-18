# Import required libraries
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from garminconnect import Garmin, GarminConnectAuthenticationError, GarminConnectConnectionError, GarminConnectTooManyRequestsError
from pathlib import Path

# Import shared configuration and functions from other scripts
from config import logger, check_garmin_credentials, ACTIVITY_DAYS_RANGE, ACTIVITY_TYPE_TRANSLATIONS, RUNNING_THROUGH_GITHUB, LOGO_PATH
from todoist_integration import create_todoist_task
from task_tracker import init_db, task_exists, mark_task_created
from utils import ensure_dir

# Ensure project graphics directory exist
PLOTS_DIR = "graphics"
ensure_dir(PLOTS_DIR)


def translate_activity_type(type_key):
    """Return the Norwegian activity name for a given Garmin Connect type key."""
    return ACTIVITY_TYPE_TRANSLATIONS.get(type_key.lower(), "annet")


def fetch_data(start_date, end_date, creds=None):
    """Fetch activities from Garmin Connect for a given date range."""
    try:
        if creds is None:
            creds = check_garmin_credentials()
        api = Garmin(creds["GARMIN_USER"], creds["GARMIN_PASS"])
        api.login()
        logger.info("Authenticated as %s", creds["GARMIN_USER"])

        activities = api.get_activities_by_date(start_date.isoformat(), end_date.isoformat())
        df = pd.DataFrame(activities)
        return api, df

    except (GarminConnectAuthenticationError, GarminConnectConnectionError, GarminConnectTooManyRequestsError) as e:
        logger.error("API error: %s", e, exc_info=True)
    except AssertionError:
        logger.error("Token or cache error for Garmin", exc_info=True)
    except Exception as e:
        logger.error("Unexpected error fetching Garmin data: %s", e, exc_info=True)
    return None, pd.DataFrame()


def insert_logo(fig):
    """Insert application logo into the given figure if available."""
    try:
        logo_img = mpimg.imread(LOGO_PATH)
        logo_ax = fig.add_axes([0.80, 0.80, 0.18, 0.18], anchor='NE', zorder=1)
        logo_ax.imshow(logo_img)
        logo_ax.axis('off')
    except FileNotFoundError:
        logger.warning("Logo not found at path: %s", LOGO_PATH)
    except Exception as e:
        logger.warning("Failed to insert logo: %s", e)


def prepare_dataframe(df):
    """Normalise dataframe columns and add derived fields used for plotting and tasks."""
    if df.empty:
        return df

    # Ensure that the required columns exist
    required_columns = ['activityId', 'activityType', 'startTimeLocal', 'duration', 'averageHR']
    for column in required_columns:
        if column not in df.columns:
            df[column] = None

    df = df[required_columns].copy()
    df['activityTypeKey'] = df['activityType'].apply(lambda x: (x or {}).get('typeKey', 'unknown'))
    df['activityTypeNameNo'] = df['activityTypeKey'].apply(translate_activity_type)
    df['startTimeLocal'] = pd.to_datetime(df['startTimeLocal'], errors="coerce", utc=True).dt.tz_convert(None)
    df['duration_hr'] = df['duration'].fillna(0) / 3600
    return df


def plot_pie(counts):
    """Create pie chart for activity distribution."""
    figure_1 = plt.figure(figsize=(6, 6), constrained_layout=True)
    plt.pie(counts.values, labels=counts.index.str.capitalize(), autopct='%1.1f%%')
    plt.title("Aktivitetsfordeling")
    insert_logo(figure_1)
    plt.show()


def plot_line(df):
    """Create line plot for activity duration over time."""
    figure_2 = plt.figure(figsize=(10, 5), constrained_layout=True)
    plt.plot(df['startTimeLocal'], df['duration_hr'], marker='o')
    plt.xlabel("Dato")
    plt.ylabel("Varighet i timer")
    plt.title("Varighet for aktivitet over tid")
    plt.xticks(rotation=45)
    insert_logo(figure_2)
    plt.show()


def process_and_plot(df):
    """Process activities dataframe and produce plots and optional sensitive output."""
    if df.empty:
        print("No activities found in date range")
        return

    df = prepare_dataframe(df)

    counts = df['activityTypeNameNo'].value_counts()

    # Print the personal training summaries
    print("Aktiviteter i perioden:")
    counts_case = counts.rename(index=lambda x: x.capitalize())
    counts_case.index.name = "Activity Type"
    print(counts_case.to_string())

    # Create the graphics pie chart
    plot_pie(counts)

    # Create the graphics line plot
    plot_line(df)

    # Print the heart rate table
    print("\nGjennomsnittspuls per aktivitet:")
    print(df[['activityId', 'activityTypeNameNo', 'averageHR']].dropna()
          .assign(activityTypeNameNo=lambda x: x['activityTypeNameNo'].str.capitalize())
          .rename(columns={
              'activityId': 'Activity ID',
              'activityTypeNameNo': 'Activity Type',
              'averageHR': 'Average HR'
          }).to_string(index=False))


def upload_activity_file_to_garmin(file_path, creds=None):
    """Upload an activity FIT file to Garmin Connect."""
    if creds is None:
        creds = check_garmin_credentials()
    try:
        api = Garmin(creds["GARMIN_USER"], creds["GARMIN_PASS"])
        api.login()
        logger.info("Authenticated for Garmin Connect API")
        success = api.upload_activity(file_path)
        if success:
            logger.info("Successfully uploaded activity file: %s", file_path)
        else:
            logger.error("Failed to upload activity file: %s", file_path)
        return success
    except (GarminConnectAuthenticationError, GarminConnectConnectionError, GarminConnectTooManyRequestsError) as e:
        logger.error("Failed to upload activity to Garmin Connect: %s", e, exc_info=True)
        return False
    except AssertionError:
        logger.error("Token or cache error for Garmin", exc_info=True)
        return False


def main():
    """Main entry point for fetching, processing and creating tasks."""
    # Get credentials and run credentials check
    garmin_creds = check_garmin_credentials()

    today = datetime.date.today()
    start_time = today - datetime.timedelta(days=ACTIVITY_DAYS_RANGE)
    end_time = today

    # Fetch and process all activities for plotting, skip if running through GitHub
    if not RUNNING_THROUGH_GITHUB:
        _, df_all = fetch_data(start_time, end_time, garmin_creds)
        process_and_plot(df_all)

    # Initialise tracking database
    init_db()

    # Fetch today's activities for task creation
    _, df_today = fetch_data(today, today, garmin_creds)
    if df_today.empty:
        logger.info("No activities from Garmin found for today")
        return

    df_today = prepare_dataframe(df_today)

    for _, row in df_today.iterrows():
        activity_id = str(row['activityId'])
        activity_type_key = row['activityTypeKey']
        activity_type_no = row['activityTypeNameNo']

        if task_exists(activity_id):
            logger.info("Task already created for activity %s (%s), skipping.", activity_type_key, activity_id)
            continue

        task_content = f"Oppdatere notater i kalenderhendelse for {activity_type_no}"
        create_todoist_task(content=task_content, due_string="today")
        logger.info("Created task for Garmin activity %s (%s)", activity_type_key, activity_id)
        mark_task_created(activity_id)


if __name__ == "__main__":
    main()
