# Import required libraries
import pandas as pd

# Import shared configuration and functions from other scripts
from config import logger
from garmin_connect import prepare_dataframe

def filter_running_activities(df):
    if df.empty:
        logger.info("Received empty dataframe in filter_running_activities")
        return pd.DataFrame()

    df = prepare_dataframe(df)

    running_keys = [
        "running", "indoor_running", "treadmill_running", "track_running",
        "street_running", "obstacle_run", "ultra_run", "trail_running",
        "virtual_run", "multisport"
    ]

    df_running = df[df['activityTypeKey'].isin(running_keys)].copy()
    df_running['distance_km'] = df_running['distance'] / 1000 

    df_running['pace_min_per_km'] = df_running.apply(
        lambda r: (r['duration'] / 60 / r['distance_km']) if r['distance_km'] > 0 else None, axis=1
    )
