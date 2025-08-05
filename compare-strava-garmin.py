# Import required libraries
import datetime
import logging
from garmin_connect import fetch_data
from strava import get_latest_activities
from intelligent_cycling import intelligent_cycling_login  # wrap your IC login as function
