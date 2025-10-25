# Import required libraries
import os
import sys
import pytest

# Ensure parent directory is on sys path so it can import script functionality
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import modules after patching
import task_tracker

@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    """Monkeypatch the DB_PATH to use a temporary file for testing."""
    db_file = tmp_path / "test_sync_tracker.db"
    monkeypatch.setattr(task_tracker, "DB_PATH", str(db_file))
    return db_file

def test_task_creation_and_upload_tracking(temp_db):
    # Initialise a clean temporary database
    task_tracker.init_db()

    # Create tasks for Garmin Connect activities
    assert not task_tracker.task_exists("123")
    task_tracker.mark_task_created("123")
    assert task_tracker.task_exists("123")

    # Strava to Garmin Connect upload tracking
    assert not task_tracker.is_uploaded_to_garmin("abc")
    task_tracker.mark_uploaded_to_garmin("abc")
    assert task_tracker.is_uploaded_to_garmin("abc")
