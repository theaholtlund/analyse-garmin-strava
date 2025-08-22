# Import required libraries
import requests
import sqlite3
from pathlib import Path
from garminconnect import GarminConnectAuthenticationError, GarminConnectConnectionError, GarminConnectTooManyRequestsError

# Import shared configuration and functions from other scripts
from config import logger, ACTIVITY_DAYS_RANGE
from strava import get_virtual_ride_activities, download_activity_fit
from garmin_connect import upload_activity_file_to_garmin

# Define the path to the local SQLite database file for sync tracking
DB_PATH = Path("strava_garmin_sync.db")


def init_db():
    """Initialise the database and create tracking table if it does not exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS strava_garmin_sync (
            strava_activity_id TEXT PRIMARY KEY,
            garmin_upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def is_synced(strava_activity_id):
    """Check if a Strava activity has already been synced."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM strava_garmin_sync WHERE strava_activity_id = ?", (strava_activity_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def mark_synced(strava_activity_id):
    """Record that a Strava activity has been synced."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO strava_garmin_sync (strava_activity_id) VALUES (?)", (strava_activity_id,))
    conn.commit()
    conn.close()


def sync_virtual_rides(): # FOR WIP FUNCTIONALITY
    """Synchronise activities of the type virtual ride from Strava to Garmin Connect."""
    init_db()

    # Get virtual ride activities from Strava within the defined date range
    logger.info(f"Fetching Virtual Ride activities from Strava for the last {ACTIVITY_DAYS_RANGE} days")
    df = get_virtual_ride_activities(days=ACTIVITY_DAYS_RANGE)

    if df.empty:
        logger.info("No new Virtual Ride activities found on Strava.")
        return

    # Bulk download the virtual ride activities
    logger.info(f"Starting bulk download of {len(df)} Virtual Ride activities")
    downloaded_files = download_multiple_activities(df)

    downloaded_count = sum(1 for f in downloaded_files if f is not None)
    failed_count = len(downloaded_files) - downloaded_count
    logger.info(f"Download complete, successfully downloaded: {downloaded_count}, failed: {failed_count}")


if __name__ == "__main__":
    sync_virtual_rides()
