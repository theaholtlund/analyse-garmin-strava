# Import required libraries
import tempfile

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

    uploaded_count = 0
    failed_count = 0

    # Use a temporary directory for downloads
    with tempfile.TemporaryDirectory() as tmp_download_dir:
        logger.info(f"Using temporary download directory: {tmp_download_dir}")
        downloaded_files = download_multiple_activities(df_to_download, download_dir=tmp_download_dir)

        # Upload the activity to Garmin Connect
        logger.info("Starting Garmin Connect upload for downloaded activities")
        for activity_id, file_path in zip(df_to_download['id'], downloaded_files):
            if file_path is None:
                failed_count += 1
                continue
            try:
                if upload_activity_file_to_garmin(file_path):
                    mark_uploaded_to_garmin(str(activity_id))
                    uploaded_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Failed to upload {file_path} to Garmin Connect: {e}")
                failed_count += 1

    logger.info(f"Sync complete, uploaded {uploaded_count}, failed {failed_count}")
    return uploaded_count, failed_count

if __name__ == "__main__":
    sync_virtual_rides()
