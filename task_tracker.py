# Import required libraries
import os
import sqlite3
from contextlib import contextmanager

# Define the path to the local SQLite database file
DB_PATH = os.path.join(os.path.dirname(__file__), "sync_tracker.db")


@contextmanager
def get_connection():
    """Provide a transactional scope around SQLite DB operations."""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialise local SQLite database and create tracking tables if they do not exist."""
    with get_connection() as conn:
        cursor = conn.cursor()

    # Track tasks in Garmin Connect, used for Todoist task creation
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS garmin_tasks (
            activity_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Track activity uploads to Garmin Connect from Strava
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS strava_garmin_sync (
            strava_activity_id TEXT PRIMARY KEY,
            garmin_upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def task_exists(activity_id):
    """Check if a Garmin Connect task already exists for the given activity ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM garmin_tasks WHERE activity_id = ?", (activity_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def mark_task_created(activity_id):
    """Mark a Garmin Connect task as created for the specified activity ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO garmin_tasks (activity_id) VALUES (?)", (activity_id,))
    conn.commit()
    conn.close()


def is_uploaded_to_garmin(activity_id):
    """Check if a Strava activity has already been uploaded to Garmin Connect."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM strava_garmin_sync WHERE strava_activity_id = ?", (activity_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def mark_uploaded_to_garmin(activity_id):
    """Mark a Strava activity as uploaded to Garmin Connect."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO strava_garmin_sync (strava_activity_id) VALUES (?)", (activity_id,))
    conn.commit()
    conn.close()
