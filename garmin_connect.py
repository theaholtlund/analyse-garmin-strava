# Import required libraries
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from garminconnect import Garmin, GarminConnectAuthenticationError, GarminConnectConnectionError, GarminConnectTooManyRequestsError

# Import shared config and functions from other scripts
from config import logger, GARMIN_USER, GARMIN_PASS, ACTIVITY_DAYS_RANGE, ACTIVITY_TYPE_TRANSLATIONS
from todoist_integration import create_todoist_task
from task_tracker import init_db, task_exists, mark_task_created

# Validate credentials from shared configuration
if not GARMIN_USER or not GARMIN_PASS:
    raise RuntimeError("Garmin user and password must be set as environment variables")

def translate_activity_type(type_key):
    return ACTIVITY_TYPE_TRANSLATIONS.get(type_key.lower())

def extract_activity_type(row):
    return row.get('activityType', {}).get('typeKey', 'unknown')

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

def insert_logo(ax, fig):
    try:
        logo_img = mpimg.imread('graphics/app-logo-1.png')
        logo_ax = fig.add_axes([0.80, 0.80, 0.18, 0.18], anchor='NE', zorder=1)
        logo_ax.imshow(logo_img)
        logo_ax.axis('off')
    except FileNotFoundError:
        logger.warning("Logo not found at graphics folder")

def process_and_plot(df):
    if df.empty:
        print("No activities found in date range")
        return

    df = df[['activityId', 'activityType', 'startTimeLocal', 'duration', 'averageHR']].copy()
    df['activityTypeKey'] = df['activityType'].apply(lambda x: x.get('typeKey', 'unknown'))
    df['activityTypeNameNo'] = df['activityTypeKey'].apply(translate_activity_type)
    df['startTimeLocal'] = pd.to_datetime(df['startTimeLocal'])
    df['duration_hr'] = df['duration'] / 3600

    counts = df['activityTypeNameNo'].value_counts()
    # counts_filtered = counts[counts >= 5]
    # counts_filtered['Annet'] = counts[counts < 5].sum()

    print("Aktiviteter i perioden:")
    print(counts.to_string())

    # Create the graphics pie chart
    figure_1 = plt.figure(figsize=(6,6))
    plt.pie(counts.values, labels=counts.index.str.capitalize(), autopct='%1.1f%%')
    plt.title("Aktivitetsfordeling")
    insert_logo(plt.gca(), figure_1)
    plt.tight_layout()
    plt.show()

    # Create the graphics line plot
    figure_2 = plt.figure(figsize=(10,5))
    plt.plot(df['startTimeLocal'], df['duration_hr'], marker='o')
    plt.xlabel("Dato")
    plt.ylabel("Varighet i timer")
    plt.title("Varighet for aktivitet over tid")
    plt.xticks(rotation=45)
    insert_logo(plt.gca(), figure_2)
    plt.tight_layout()
    plt.show()

    print("\nGjennomsnittspuls per aktivitet:")
    print(df[['activityId', 'activityTypeNameNo', 'averageHR']].dropna()
          .assign(activityTypeNameNo=lambda x: x['activityTypeNameNo'].str.capitalize())
          .rename(columns={
            'activityId': 'Activity ID',
            'activityTypeNameNo': 'Activity Type',
            'averageHR': 'Average HR'
        }).to_string(index=False))

def main():
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

    df['activityTypeKey'] = df['activityType'].apply(lambda x: x.get('typeKey', 'unknown'))
    df['activityTypeNameNo'] = df['activityTypeKey'].apply(translate_activity_type)

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
