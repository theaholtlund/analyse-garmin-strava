# Import required libraries
import sqlite3
from pathlib import Path

# Define the path to the local SQLite database file
DB_PATH = Path("created_tasks.db")


def init_db():
    """Initialise local SQLite database and create Garmin Connect tasks table if it does not exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS garmin_tasks (
            activity_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def task_exists(activity_id):
    """Check if a task already exists for the given activity ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM garmin_tasks WHERE activity_id = ?", (activity_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def mark_task_created(activity_id):
    """Mark a task as created for the specified activity ID in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO garmin_tasks (activity_id) VALUES (?)", (activity_id,))
    conn.commit()
    conn.close()
