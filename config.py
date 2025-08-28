# Import required libraries
import os
import logging
from dotenv import load_dotenv

# Load environment variables from environment file
load_dotenv()

# Set up logging for information
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Detect whether running inside GitHub Actions
RUNNING_THROUGH_GITHUB = os.getenv("GITHUB_ACTIONS", "").lower() == "true"

# Path to logo used in plots
LOGO_PATH = "graphics/app-logo-1.png"

# Set how many days back to fetch activities
ACTIVITY_DAYS_RANGE = 30

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
    "multisport" : "triatlon",
    "bouldering": "buldring",
    "yoga": "yoga",
    "rowing": "roing",
    "elliptical": "ellipsemaskin",
    "other": "annet"
}

# Load the credentials from Garmin
GARMIN_USER = os.getenv("GARMIN_USER")
GARMIN_PASS = os.getenv("GARMIN_PASS")

# Load the credentials from Strava
STRAVA_USER = os.getenv("STRAVA_USER")
STRAVA_PASS = os.getenv("STRAVA_PASS")
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI", "http://localhost")

# Load the credentials from Intelligent Cycling
IC_USER = os.getenv("IC_USER")
IC_PASS = os.getenv("IC_PASS")

# Load the credentials from Todoist
TODOIST_SECTION_ID = os.getenv("TODOIST_SECTION_ID")
TODOIST_PROJECT_ID = os.getenv("TODOIST_PROJECT_ID")
TODOIST_API_TOKEN = os.getenv("TODOIST_API_TOKEN")
