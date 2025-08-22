# Import required libraries
import os
import time
import webbrowser
import datetime
import pandas as pd
import requests
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# Import shared config and functions from other scripts
from config import logger, STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REDIRECT_URI, ACTIVITY_DAYS_RANGE, STRAVA_USER, STRAVA_PASS

# Validate credentials from shared configuration
if not STRAVA_CLIENT_ID or not STRAVA_CLIENT_SECRET:
    raise RuntimeError("Set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in environment file")

TOKEN_PATH = "strava_tokens.json"

def save_tokens(tok):
    """Save Strava API tokens to a local JSON file."""
    with open(TOKEN_PATH, "w") as f:
        json.dump(tok, f)

def authenticate():
    """Perform Strava OAuth authentication and return new tokens."""
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
    """Load existing Strava tokens from file or authenticate if missing."""
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH) as f:
            return json.load(f)
    return authenticate()

def refresh_access(tok):
    """Refresh an expired Strava access token using the refresh token."""
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
    """Fetch the latest Strava activities within the specified number of days."""
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
    """Fetch detailed data streams for a given Strava activity."""
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
    """Download a FIT file from Strava using Selenium by performing a multi-step login."""
    if not STRAVA_USER or not STRAVA_PASS:
        raise RuntimeError("Strava user and password must be set in config.py")

    options = Options()
    # options.add_argument("--headless=new") # Comment out headless to open Chrome for debugging

    download_dir = os.path.join(os.getcwd(), "downloads")
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safeBrowse.enabled": True
    })

    driver = webdriver.Chrome(options=options)
    
    try:
        logger.info("Opening the Strava login page")
        driver.get("https://www.strava.com/login")

        # Add e-mail and click the login button
        logger.info("Entering e-mail on Strava login page")
        email_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "desktop-email"))
        )
        email_field.send_keys(STRAVA_USER)

        logger.info("Sending e-mail on Strava login page")
        login_button_email_stage = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "desktop-login-button"))
        )
        login_button_email_stage.click()

        ### HERE BEGINS LOGIN FUNCTIONALITY THAT DOES NOt WORK ###
        # Click the button to use password instead
        logger.info("Clicking the button to use password instead")
        use_password_btn = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Use password instead')]"))).click()
        use_password_btn.click()

        # Enter the password for Strava login
        logger.info("Entering password on login page")
        password_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, "password"))
        )
        password_field.send_keys(STRAVA_PASS)

        # Click the final login button
        login_button_password_stage = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.Button_primary___8ywh"))
        )
        login_button_password_stage.click()
        
        # Wait for the login to complete and the URL to change to the dashboard
        logger.info("Login successful, navigating to activity page")
        WebDriverWait(driver, 20).until(EC.url_contains("dashboard"))
        
        activity_url = f"https://www.strava.com/activities/{activity_id}"
        driver.get(activity_url)
        
        # Click the export original button
        logger.info("Waiting for 'Export Original' button")
        export_link = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located(
                (By.XPATH, f"//a[contains(@href, '/activities/{activity_id}/export_original')]")
            )
        )
        # Use of ActionsChains to ensure the click is successful
        ActionChains(driver).move_to_element(export_link).click().perform()
        
        logger.info("Download initiated. Waiting for file to appear...")
        start_time = time.time()
        file_path = os.path.join(download_dir, f"{activity_id}.fit")
        while not os.path.exists(file_path):
            time.sleep(1)
            if time.time() - start_time > 60:
                raise TimeoutError("File download timed out.")
        
        logger.info(f"Downloaded activity {activity_id} to {file_path}")
        return file_path
    
        ### HERE ENDS LOGIN FUNCTIONALITY THAT DOES NOT WORK ###
    
    except Exception as e:
        logger.error(f"Error during Selenium download for activity {activity_id}: {e}", exc_info=True)
        return None
    finally:
        driver.quit()
        

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

        if not df.empty:
            first_id = df.iloc[0]["id"]
            download_activity_fit(first_id)