# Import required libraries
import tempfile
import argparse

# Import shared configuration and functions from other scripts
from config import logger, ACTIVITY_DAYS_RANGE
from task_tracker import init_db, is_uploaded_to_garmin, mark_uploaded_to_garmin
from strava_playwright import get_virtual_ride_activities, download_multiple_activities
from garmin_connect import upload_activity_file_to_garmin, check_garmin_credentials

def sync_virtual_rides(dry_run=False, limit=None, headless=True):
    """Synchronise activities of the type virtual ride from Strava to Garmin Connect."""
    init_db()

    # Get virtual ride activities from Strava within the defined date range
    logger.info("Fetching virtual ride activities from Strava for the last %s days", ACTIVITY_DAYS_RANGE)
    df = get_virtual_ride_activities(days=ACTIVITY_DAYS_RANGE)

    if df.empty:
        logger.info("No new virtual ride activities found on Strava.")
        return 0, 0

    # Filter out already synced activities
    df_to_download = df[~df['id'].astype(str).apply(is_uploaded_to_garmin)]
    if df_to_download.empty:
        logger.info("All virtual ride activities have already been synced.")
        return 0, 0

    if limit:
        df_to_download = df_to_download.head(limit)

    logger.info("Starting bulk download of %d virtual ride activities", len(df_to_download))

    uploaded_count = 0
    failed_count = 0

    # Use a temporary directory for downloads
    with tempfile.TemporaryDirectory() as tmp_download_dir:
        logger.info("Using temporary download directory: %s", tmp_download_dir)
        downloaded_files = download_multiple_activities(df_to_download, download_dir=tmp_download_dir, headless=headless)

        # Upload the activity to Garmin Connect
        logger.info("Starting Garmin Connect upload for downloaded activities")
        garmin_creds = check_garmin_credentials()
        for activity_id, file_path in zip(df_to_download['id'], downloaded_files):
            if file_path is None:
                failed_count += 1
                continue

            if dry_run:
                logger.info("Dry run enabled: Would upload %s (activity %s)", file_path, activity_id)
                uploaded_count += 1
                continue

            try:
                if upload_activity_file_to_garmin(file_path, creds=garmin_creds):
                    mark_uploaded_to_garmin(str(activity_id))
                    uploaded_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error("Failed to upload %s to Garmin Connect: %s", file_path, e)
                failed_count += 1

    logger.info("Sync complete, uploaded %d, failed %d", uploaded_count, failed_count)
    return uploaded_count, failed_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync virtual rides from Strava to Garmin Connect using Playwright")
    parser.add_argument("--dry-run", action="store_true", help="Do not perform uploads, just simulate")
    parser.add_argument("--limit", type=int, help="Limit number of activities to sync")
    parser.add_argument("--no-headless", action="store_true", help="Show browser window (default is headless mode)")
    args = parser.parse_args()

    sync_virtual_rides(dry_run=args.dry_run, limit=args.limit, headless=not args.no_headless)