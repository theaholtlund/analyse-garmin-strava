# Import required libraries
import os
import logging
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from environment file
load_dotenv()

# Ensure project directories exist
Path("graphics").mkdir(exist_ok=True)

# Set up logging for information
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Detect whether running inside GitHub Actions
RUNNING_THROUGH_GITHUB = os.getenv("GITHUB_ACTIONS", "").lower() == "true"

# Path to logo used in plots
LOGO_PATH = "graphics/app-logo-1.png"

# Set how many days back to fetch activities
ACTIVITY_DAYS_RANGE = int(os.getenv("ACTIVITY_DAYS_RANGE", 7))

# Mapping the Garmin Connect activity types to Norwegian names
ACTIVITY_TYPE_TRANSLATIONS = {
    "running": "løping",
    "treadmill_running": "løping på tredemølle",
    "track_running": "baneløping",
    "trail_running": "terrengløping",
    "road_biking": "landeveissykling",
    "indoor_cycling": "innendørssykling",
    "strength_training": "styrketrening",
    "walking": "gåtur",
    "lap_swimming": "bassengsvømming",
    "open_water_swimming": "utendørssvømming",
    "hiking": "fottur",
    "multisport": "triatlon",
    "bouldering": "buldring",
    "yoga": "yoga",
    "pilates": "pilates",
    "rowing": "roing",
    "cardio": "cardio",
    "elliptical": "ellipsemaskin",
    "downhill_skiing": "slalåm",
    "snowboarding": "snowboarding",
    "cross_country_classic_skiing": "klassisk langrenn",
    "other": "annet"
}


def load_env(var_name, default=None):
    """Load an environment variable, log a warning if it is not set and return its value."""
    value = os.getenv(var_name, default)
    if value in (None, ""):
        logger.warning("Environment variable '%s' is not set", var_name)
    return value


def get_strava_credentials():
    """Return the credentials needed for Strava functionality."""
    return {
        "STRAVA_USER": load_env("STRAVA_USER"),
        "STRAVA_PASS": load_env("STRAVA_PASS"),
        "STRAVA_CLIENT_ID": load_env("STRAVA_CLIENT_ID"),
        "STRAVA_CLIENT_SECRET": load_env("STRAVA_CLIENT_SECRET"),
        "STRAVA_REDIRECT_URI": load_env("STRAVA_REDIRECT_URI", "http://localhost")
    }


def check_strava_credentials():
    """Check if Strava credentials are set and log a warning if any are missing."""
    creds = get_strava_credentials()
    missing = [k for k, v in creds.items() if not v]
    if missing:
        logger.warning(f"Missing credential for Strava: {missing}")
    return creds


def get_garmin_credentials():
    """Return the credentials needed for Garmin Connect functionality."""
    return {
        "GARMIN_USER": load_env("GARMIN_USER"),
        "GARMIN_PASS": load_env("GARMIN_PASS")
    }


def check_garmin_credentials():
    """Check if Garmin Connect credentials are set and log a warning if any are missing."""
    creds = get_garmin_credentials()
    missing = [k for k, v in creds.items() if not v]
    if missing:
        logger.warning("Missing credential for Garmin Connect: %s", missing)
    return creds


def get_mowl_credentials():
    """Return the credentials needed for MOWL Cycling functionality."""
    return {
        "MOWL_USER": load_env("MOWL_USER"),
        "MOWL_PASS": load_env("MOWL_PASS")
    }


def check_mowl_credentials():
    """Check if MOWL Cycling credentials are set and log a warning if any are missing."""
    creds = get_mowl_credentials()
    missing = [k for k, v in creds.items() if not v]
    if missing:
        logger.warning("Missing credential for MOWL Cycling: %s", missing)
    return creds


def get_todoist_credentials():
    """Return the credentials needed for Todoist functionality."""
    return {
        "TODOIST_SECTION_ID": load_env("TODOIST_SECTION_ID"),
        "TODOIST_PROJECT_ID": load_env("TODOIST_PROJECT_ID"),
        "TODOIST_API_TOKEN": load_env("TODOIST_API_TOKEN")
    }


def check_todoist_credentials():
    """Check if Todoist credentials are set and log a warning if any are missing."""
    creds = get_todoist_credentials()
    missing = [k for k, v in creds.items() if not v]
    if missing:
        logger.warning("Missing credential for Todoist: %s", missing)
    return creds
