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
