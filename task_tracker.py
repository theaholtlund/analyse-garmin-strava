# Import required libraries
import sqlite3
from pathlib import Path

# Define the path to the local SQLite database file
DB_PATH = Path("created_tasks.db")

# Initialise the database and create tracking table if it does not exist
def init_db():
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

# Check whether a task has already been created for a given activity ID
def task_exists(activity_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM garmin_tasks WHERE activity_id = ?", (activity_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

# Record that a task has been created for the specified activity ID
def mark_task_created(activity_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO garmin_tasks (activity_id) VALUES (?)", (activity_id,))
    conn.commit()
    conn.close()
