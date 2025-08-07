# Import required libraries
import os
import logging
from dotenv import load_dotenv

# Load environment variables from environment file
load_dotenv()

# Set how many days back to fetch activities
ACTIVITY_DAYS_RANGE = 14

# Load the credentials from Garmin
GARMIN_USER = os.getenv("GARMIN_USER")
GARMIN_PASS = os.getenv("GARMIN_PASS")

# Load the credentials from Strava
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