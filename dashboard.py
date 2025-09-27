# Import required libraries
import pandas as pd

# Import shared configuration and functions from other scripts
from config import logger
from garmin_connect import prepare_dataframe
from utils import ensure_dir

# Ensure outputs directory exists
PLOTS_DIR = "outputs"
ensure_dir(PLOTS_DIR)


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
