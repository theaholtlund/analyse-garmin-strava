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


def filter_running_activities(df):
    if df.empty:
        logger.info("Received empty dataframe in filter_running_activities")
        return pd.DataFrame()

    df = prepare_dataframe(df)

    running_keys = [
        "running", "indoor_running", "treadmill_running", "track_running",
        "street_running", "obstacle_run", "ultra_run", "trail_running", "virtual_run"
    ]

    df_running = df[df['activityTypeKey'].isin(running_keys)].copy()
    df_running['distance_km'] = df_running['distance'] / 1000
    df_running['month'] = df_running['startTimeLocal'].dt.to_period('M')

    logger.info("Filtered %d running activities (including multisport legs) out of %d total", len(df_running), len(df))
    return df_running


def generate_dashboard():
    """Fetch activities from Garmin Connect and generate running dashboard."""
    garmin_creds = check_garmin_credentials()

    today = datetime.date.today()
    start_of_year = datetime.date(today.year, 1, 1)
    logger.info("Fetching activities from %s to %s", start_of_year, today)

    _, df_all = fetch_data(start_of_year, today, garmin_creds)
    if df_all.empty:
        return

    df_running = filter_running_activities(df_all)
    if df_running.empty:
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
