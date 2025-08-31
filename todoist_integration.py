# Import required libraries
from todoist_api_python.api import TodoistAPI

# Import shared configuration and functions from other scripts
from config import logger, TODOIST_SECTION_ID, TODOIST_PROJECT_ID, TODOIST_API_TOKEN


def create_todoist_task(content, due_string="today"):
    """Create a Todoist task with a Garmin Connect label."""
    if not TODOIST_API_TOKEN:
        logger.warning("No Todoist API token found in environment variables")
        return None

    api = TodoistAPI(TODOIST_API_TOKEN)

    try:
        task = api.add_task(
            content=content,
            section_id=TODOIST_SECTION_ID,
            project_id=TODOIST_PROJECT_ID,
            due_string=due_string,
            labels=["Garmin Connect App"]
        )
        logger.info(f"Created the Todoist task: {task.content}")
        return task
    except Exception as error:
        # Log exception with traceback for debugging
        logger.error(f"Error creating Todoist task: {error}", exc_info=True)
        return None
