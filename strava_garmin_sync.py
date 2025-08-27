# Import required libraries
import sqlite3
from pathlib import Path

# Import shared configuration and functions from other scripts
from config import logger, ACTIVITY_DAYS_RANGE
from task_tracker import init_db, is_uploaded_to_garmin, mark_uploaded_to_garmin
from strava import get_virtual_ride_activities, download_multiple_activities
from garmin_connect import upload_activity_file_to_garmin


def sync_virtual_rides():
    """Synchronise activities of the type virtual ride from Strava to Garmin Connect."""
    init_db()

    # Get virtual ride activities from Strava within the defined date range
    logger.info(f"Fetching virtual ride activities from Strava for the last {ACTIVITY_DAYS_RANGE} days")
    df = get_virtual_ride_activities(days=ACTIVITY_DAYS_RANGE)

    if df.empty:
        logger.info("No new virtual ride activities found on Strava.")
        return

    # Filter out already synced activities
    df_to_download = df[~df['id'].astype(str).apply(is_uploaded_to_garmin)]
    if df_to_download.empty:
        logger.info("All virtual ride activities have already been synced.")
        return

    logger.info(f"Starting bulk download of {len(df_to_download)} virtual ride activities")
    downloaded_files = download_multiple_activities(df_to_download)

    # Record successful downloads in the database
    for activity_id, file_path in zip(df_to_download['id'], downloaded_files):
        if file_path is not None:
            mark_uploaded_to_garmin(str(activity_id))

    downloaded_count = sum(1 for f in downloaded_files if f is not None)
    failed_count = len(downloaded_files) - downloaded_count
    logger.info(f"Download complete, successfully downloaded: {downloaded_count}, failed: {failed_count}")

    # Placeholder for Garmin Connect upload functionality
    logger.info("Starting Garmin Connect upload for downloaded activities")
    for file_path in downloaded_files:
        if file_path is not None:
            try:
                upload_activity_file_to_garmin(file_path)
                logger.info(f"Uploaded to Garmin: {file_path}")
            except Exception as e:
                logger.error(f"Failed to upload {file_path} to Garmin: {e}")


if __name__ == "__main__":
    sync_virtual_rides()
