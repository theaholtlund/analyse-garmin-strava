# Import required libraries
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Import shared configuration and functions from other scripts
from config import logger, check_garmin_credentials, RUNNING_THROUGH_GITHUB
from garmin_connect import fetch_data, prepare_dataframe
from utils import ensure_dir

# Ensure outputs directory exists
PLOTS_DIR = "outputs"
ensure_dir(PLOTS_DIR)

# Orange colour palette
ORANGE_PALETTE = ["#FF8C42", "#FF6700", "#FF9505", "#FFA347", "#FFB366", "#FFC680", "#FFD699"]

sns.set_style("whitegrid")
plt.rcParams.update({'figure.facecolor': 'white'})


def extract_multisport_running(df):
    """Extract running distances from multisport activities and assign to correct month."""
    if df.empty:
        return pd.DataFrame()

    df = prepare_dataframe(df)
    df_multisport = df[df['activityTypeKey'] == 'multisport'].copy()
    running_records = []

    for _, row in df_multisport.iterrows():
        running_distance = 0
        laps = row.get('laps', [])

        for lap in laps:
            lap_type = lap.get('activityTypeKey') or lap.get('activityType', '').lower()
            if lap_type == 'running':
                running_distance += lap.get('distance', 0)

    df_running_multisport = pd.DataFrame(running_records)
    df_running_multisport['distance_km'] = df_running_multisport['distance'] / 1000
    df_running_multisport['month'] = df_running_multisport['startTimeLocal'].dt.to_period('M')
    return df_running_multisport


def filter_running_activities(df):
    if df.empty:
        logger.info("Received empty dataframe in filter_running_activities")
        return pd.DataFrame()

    df = prepare_dataframe(df)

    running_keys = [
        "running", "indoor_running", "treadmill_running", "track_running",
        "street_running", "obstacle_run", "ultra_run", "trail_running", "virtual_run"
    ]

    # Standard running activities
    df_running = df[df['activityTypeKey'].isin(running_keys)].copy()
    df_running['distance_km'] = df_running['distance'] / 1000
    df_running['month'] = df_running['startTimeLocal'].dt.to_period('M')

    df_multisport_running = extract_multisport_running(df)
    if not df_multisport_running.empty:
        df_running = pd.concat([df_running, df_multisport_running], ignore_index=True)

    logger.info("Filtered %d running activities (including multisport legs) out of %d total", len(df_running), len(df))
    return df_running


def generate_dashboard():
    """Fetch activities from Garmin Connect and generate running dashboard."""
    logger.info("Starting dashboard generation")
    garmin_creds = check_garmin_credentials()

    today = datetime.date.today()
    start_of_year = datetime.date(today.year, 1, 1)
    logger.info("Fetching activities from %s to %s", start_of_year, today)

    _, df_all = fetch_data(start_of_year, today, garmin_creds)
    if df_all.empty:
        logger.warning("No activities fetched from Garmin Connect")
        return
    logger.info("Fetched %d total activities", len(df_all))

    df_running = filter_running_activities(df_all)
    if df_running.empty:
        logger.warning("No running activities found for this year")
        return

    fig = plt.figure(constrained_layout=True, figsize=(14, 10))

    dashboard_path = PLOTS_DIR + "/run_distance.png"
    fig.savefig(dashboard_path, dpi=150)
    plt.show()


if __name__ == "__main__":
    if RUNNING_THROUGH_GITHUB:
        logger.warning("Dashboard not generated when running in GitHub Actions")
    else:
        generate_dashboard()
