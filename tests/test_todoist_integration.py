# Import required libraries
import os
import sys
import types
import pytest

# Ensure parent directory is on sys path so it can import script functionality
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import modules after patching
from todoist_integration import create_todoist_task

class MockTodoistAPI:
    def __init__(self, token):
        self.token = token

    def add_task(self, **kwargs):
        task = types.SimpleNamespace(content=kwargs.get("content"))
        return task

@pytest.fixture
def mock_todoist(monkeypatch):
    monkeypatch.setattr("todoist_integration.TodoistAPI", MockTodoistAPI)

def test_create_task(mock_todoist):
    task = create_todoist_task("Test task for Garmin Connect")
    assert task is not None
    assert task.content == "Test task for Garmin Connect"
