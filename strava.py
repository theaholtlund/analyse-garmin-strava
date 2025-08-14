# Import required libraries
import os
import time
import webbrowser
import datetime
import pandas as pd
import requests
import json

# Import shared config and functions from other scripts
from config import logger, STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REDIRECT_URI, ACTIVITY_DAYS_RANGE

# Validate credentials from shared configuration
if not STRAVA_CLIENT_ID or not STRAVA_CLIENT_SECRET:
    raise RuntimeError("Set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in environment file")

TOKEN_PATH = "strava_tokens.json"

def save_tokens(tok):
    with open(TOKEN_PATH, "w") as f:
        json.dump(tok, f)

def authenticate():
    url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_CLIENT_ID}"
        "&response_type=code"
        f"&redirect_uri={STRAVA_REDIRECT_URI}"
        "&approval_prompt=force"
        "&scope=activity:read_all,profile:read_all"
    )
    logger.info("Opening browser for Strava OAuth flow")
    webbrowser.open(url)
    code = input("Paste the code parameter from the URL after approve: ").strip()
    response = requests.post("https://www.strava.com/api/v3/oauth/token", data={
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code"
    })

    response.raise_for_status()
    token = response.json()

    save_tokens(token)
    return token

def load_tokens():
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH) as f:
            return json.load(f)
    return authenticate()

def refresh_access(tok):
    response = requests.post("https://www.strava.com/api/v3/oauth/token", data={
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": tok["refresh_token"],
    })
    response.raise_for_status()
    new = response.json()
    save_tokens(new)
    return new

def get_latest_activities(days=ACTIVITY_DAYS_RANGE):
    token = load_tokens()
    current_timestamp = datetime.datetime.now(datetime.timezone.utc).timestamp()
    if token["expires_at"] < current_timestamp:
        token = refresh_access(token)

    headers = {"Authorization": f"Bearer {token['access_token']}"}

    after = int((datetime.datetime.now() - datetime.timedelta(days=days)).timestamp())

    activities = []
    page = 1
    per_page = 50 # This is the Strava max

    while True:
        params = {"after": after, "page": page, "per_page": per_page}
        response = requests.get("https://www.strava.com/api/v3/athlete/activities",
                         headers=headers, params=params)
        response.raise_for_status()
        page_data = response.json()

        if not page_data:
            break

        activities.extend(page_data)
        page += 1
        time.sleep(0.2) # API rate limit safety

    if not activities:
        return pd.DataFrame()

    return pd.DataFrame(activities)

def get_stream(activity_id, types=("heartrate", "cadence", "distance", "time")):
    token = load_tokens()
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    response = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}/streams",
        headers=headers,
        params={"keys": ",".join(types), "key_by_type": True}
    )
    response.raise_for_status()
    return response.json()

def download_activity_fit(activity_id): # FOR WIP FUNCTIONALITY
    """Download FIT file of Strava activity."""
    token = load_tokens()
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/export_original"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    # Create a downloads directory if it does not exist
    os.makedirs("downloads", exist_ok=True)
    file_path = f"downloads/strava_activity_{activity_id}.fit"
    with open(file_path, "wb") as f:
        f.write(response.content)
    logger.info(f"Downloaded activity {activity_id} to {file_path}")
    return file_path

def get_virtual_ride_activities(days=ACTIVITY_DAYS_RANGE): # FOR WIP FUNCTIONALITY
    """Fetch recent Strava activities filtered for Virtual Ride type."""
    df = get_latest_activities(days=days)
    if df.empty:
        return pd.DataFrame()
    return df[df['type'] == 'VirtualRide'].copy()

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
        output_df = df[["name", "type", "activity start time"]]

        # Calculate max width for each column
        column_widths = {col: max(output_df[col].astype(str).map(len).max(), len(col)) for col in output_df.columns}

        # Create header row, left aligned
        header = "  ".join(f"{col:<{column_widths[col]}}" for col in output_df.columns)
        print(header)

        # Print rows with left-aligned columns
        for _, row in output_df.iterrows():
            print("  ".join(f"{str(val):<{column_widths[col]}}" for col, val in row.items()))
