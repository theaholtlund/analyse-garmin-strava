# Import required libraries
from todoist_api_python.api import TodoistAPI
from config import TODOIST_API_TOKEN, logger

def create_todoist_task(content, due_string=None):
    if not TODOIST_API_TOKEN:
        logger.warning("No Todoist API token found in environment variables")
        return

    api = TodoistAPI(TODOIST_API_TOKEN)

    try:
        task = api.add_task(content=content, due_string=due_string)
        logger.info(f"Created Todoist task: {task.content}")
        return task
    except Exception as error:
        logger.error(f"Error creating Todoist task: {error}")
