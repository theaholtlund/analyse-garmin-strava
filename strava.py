# Import required libraries
import os
import time
import webbrowser
import datetime
import logging
import pandas as pd
from dotenv import load_dotenv
import requests
import json

# Set how many days back to fetch activities
ACTIVITY_DAYS_RANGE = 14

# Set up configuration
load_dotenv()
CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI", "http://localhost")

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("Set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in environment file")

# Set up logging for information
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN_PATH = "strava_tokens.json"

def save_tokens(tok):
    with open(TOKEN_PATH, "w") as f:
        json.dump(tok, f)

def authenticate():
    url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        "&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        "&approval_prompt=force"
        "&scope=activity:read_all,profile:read_all"
    )
    logger.info("Opening browser for Strava OAuth flow")
    webbrowser.open(url)
    code = input("Paste the code parameter from the URL after approve: ").strip()
    resp = requests.post("https://www.strava.com/api/v3/oauth/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code"
    })

    resp.raise_for_status()
    tok = resp.json()

    save_tokens(tok)
    return tok

def load_tokens():
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH) as f:
            return json.load(f)
    return authenticate()

def refresh_access(tok):
    resp = requests.post("https://www.strava.com/api/v3/oauth/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": tok["refresh_token"],
    })
    resp.raise_for_status()
    new = resp.json()
    save_tokens(new)
    return new

def get_latest_activities(days=ACTIVITY_DAYS_RANGE):
    tok = load_tokens()
    now_ts = datetime.datetime.now(datetime.timezone.utc).timestamp()
    if tok["expires_at"] < now_ts:
        tok = refresh_access(tok)

    headers = {"Authorization": f"Bearer {tok['access_token']}"}

    after = int((datetime.datetime.now() - datetime.timedelta(days=days)).timestamp())

    activities = []
    page = 1
    per_page = 50 # This is the Strava max

    while True:
        params = {
            "after": after,
            "page": page,
            "per_page": per_page
        }
        r = requests.get("https://www.strava.com/api/v3/athlete/activities",
                         headers=headers, params=params)
        r.raise_for_status()
        page_data = r.json()

        if not page_data:
            break

        activities.extend(page_data)
        page += 1
        time.sleep(0.2) # API rate limit safety

    if not activities:
        return pd.DataFrame()

    return pd.DataFrame(activities)

def get_stream(activity_id, types=("heartrate", "cadence", "distance", "time")):
    tok = load_tokens()
    headers = {"Authorization": f"Bearer {tok['access_token']}"}
    r = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}/streams",
        headers=headers,
        params={"keys": ",".join(types), "key_by_type": True}
    )
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    logger.info(f"Fetching activities from the past {ACTIVITY_DAYS_RANGE} days")
    df = get_latest_activities()

    if df.empty:
        print("No activities found")
    else:
        # Ensure required columns exist
        expected_cols = ["id", "name", "type", "start_date_local"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None # Fill missing with None

        df["start_date_local"] = pd.to_datetime(df["start_date_local"], errors='coerce')
        df["start_date_local"] = df["start_date_local"].dt.strftime("%d-%m-%Y %H:%M")
        df = df.rename(columns={"start_date_local": "activity start time"})

        # Select relevant columns
        out_df = df[["name", "type", "activity start time"]]

        # Calculate max width for each column
        col_widths = {col: max(out_df[col].astype(str).map(len).max(), len(col)) for col in out_df.columns}

        # Create header row, left aligned
        header = "  ".join(f"{col:<{col_widths[col]}}" for col in out_df.columns)
        print(header)

        # Print rows with left-aligned columns
        for _, row in out_df.iterrows():
            print("  ".join(f"{str(val):<{col_widths[col]}}" for col, val in row.items()))
