# Import required libraries
import os
import time
import random
import webbrowser
import datetime
import pandas as pd
import requests
import json
import tempfile
import shutil
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

# Import shared configuration and functions
from utils import safe_json_write, save_debug_screenshot
from config import logger, check_strava_credentials, ACTIVITY_DAYS_RANGE, DEBUG_SCREENSHOTS

# Token storage path
TOKEN_PATH = "strava_tokens.json"

# Retrieve credentials and check at the same time
creds = check_strava_credentials()
STRAVA_USER = creds["STRAVA_USER"]
STRAVA_PASS = creds["STRAVA_PASS"]
STRAVA_CLIENT_ID = creds["STRAVA_CLIENT_ID"]
STRAVA_CLIENT_SECRET = creds["STRAVA_CLIENT_SECRET"]
STRAVA_REDIRECT_URI = creds["STRAVA_REDIRECT_URI"]


def save_tokens(token_data):
    """Save Strava API tokens to a local JSON file."""
    safe_json_write(TOKEN_PATH, token_data, logger)


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
    code = input("Paste the code parameter from the URL after approval: ").strip()

    response = requests.post(
        "https://www.strava.com/api/v3/oauth/token",
        data={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        })
    
    response.raise_for_status()
    token = response.json()
    
    save_tokens(token)
    return token


def load_tokens():
    """Load existing Strava tokens from file, environment or authenticate if missing."""
    # Use the CI environment variables if present
    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        if all(os.getenv(v) for v in ["STRAVA_ACCESS_TOKEN", "STRAVA_REFRESH_TOKEN", "STRAVA_EXPIRES_AT"]):
            return {
                "access_token": os.environ["STRAVA_ACCESS_TOKEN"],
                "refresh_token": os.environ["STRAVA_REFRESH_TOKEN"],
                "expires_at": int(os.environ["STRAVA_EXPIRES_AT"]),
                "token_type": "Bearer"
            }

    # Use local token file if it exists
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH) as f:
            return json.load(f)

    # Fallback to interactive authenticate, only works locally
    return authenticate()


def refresh_access(token):
    """Refresh an expired Strava access token using the refresh token."""
    response = requests.post(
        "https://www.strava.com/api/v3/oauth/token",
        data={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        },
    )
    response.raise_for_status()
    new_token = response.json()
    save_tokens(new_token)
    return new_token


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
    current_timestamp = datetime.datetime.now(datetime.timezone.utc).timestamp()
    if token.get("expires_at", 0) < current_timestamp:
        token = refresh_access(token)

    headers = {"Authorization": f"Bearer {token['access_token']}"}
    response = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}/streams",
        headers=headers,
        params={"keys": ",".join(types), "key_by_type": True}
    )
    response.raise_for_status()
    return response.json()


def save_playwright_screenshot(page, logger, debug_enabled, name):
    """Save a screenshot using Playwright page object if debug is enabled."""
    if debug_enabled:
        try:
            screenshot_path = f"{name}.png"
            page.screenshot(path=screenshot_path)
            logger.info("Screenshot saved: %s", screenshot_path)
        except Exception as e:
            logger.warning("Failed to save screenshot %s: %s", name, e)


def human_delay(min_seconds=0.5, max_seconds=2.0):
    """Add a realistic human-like delay."""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def download_multiple_activities(activities_df, download_dir=None, headless=True):
    """Download multiple FIT files from Strava using Playwright with a single login session."""
    if not STRAVA_USER or not STRAVA_PASS:
        raise RuntimeError("Strava username and password must be set in config.py")

    downloaded_files = []
    
    # Create stealth instance
    stealth = Stealth()
    
    with sync_playwright() as p:
        # Launch browser with mobile emulation and stealth settings
        browser = p.chromium.launch(
            headless=headless,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        # Create context with mobile viewport and realistic user agent
        context = browser.new_context(
            viewport={'width': 390, 'height': 844},
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) '
                      'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            accept_downloads=True,
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation'],
            # Extra stealth settings
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
            }
        )
        
        # Apply stealth to entire context (all pages from this context will have stealth)
        stealth.apply_stealth_sync(context)
        
        page = context.new_page()
        
        try:
            # Log in to Strava profile
            logger.info("Opening the Strava login page")
            page.goto("https://www.strava.com/login", wait_until="domcontentloaded")
            human_delay(1, 2)  # Wait like a human would

            # Handle cookie banner if present
            try:
                logger.info("Checking for cookie banner")
                save_playwright_screenshot(page, logger, DEBUG_SCREENSHOTS, "before_cookie_banner")
                cookie_button = page.locator("button[data-cy='accept-cookies'], .CookieBanner button, button[id*='cookie'], button[class*='cookie']").first
                if cookie_button.is_visible(timeout=5000):
                    human_delay(0.3, 0.8)
                    cookie_button.click()
                    logger.info("Cookie banner accepted")
                    human_delay(0.5, 1.5)
            except PlaywrightTimeoutError:
                logger.info("No cookie banner found or already accepted")

            # Enter e-mail for the login page
            logger.info("Entering e-mail on Strava login page")
            email_field = page.locator("#mobile-email").first
            email_field.wait_for(state="visible", timeout=20000)
            human_delay(0.5, 1.0)
            
            # Type email character by character like a human
            email_field.click()
            human_delay(0.2, 0.5)
            for char in STRAVA_USER:
                email_field.type(char, delay=random.uniform(50, 150))
            human_delay(0.5, 1.5)

            # Click the login button to proceed to password stage
            logger.info("Sending e-mail on Strava login page")
            save_playwright_screenshot(page, logger, DEBUG_SCREENSHOTS, "before_username_submit")
            login_button_email_stage = page.locator("#mobile-login-button").first
            
            # Click normally first (more human-like)
            login_button_email_stage.click()
            human_delay(2, 4)  # Wait for page transition
            save_playwright_screenshot(page, logger, DEBUG_SCREENSHOTS, "after_email_submit")

            # Wait for the OTP page to load and click button to use password instead
            logger.info("Waiting for OTP page and clicking button to use password instead")
            save_playwright_screenshot(page, logger, DEBUG_SCREENSHOTS, "before_use_password")
            
            # Try to find the use password button with a longer timeout
            try:
                use_password_btn = page.locator("[data-testid='use-password-cta'] button").first
                use_password_btn.wait_for(state="visible", timeout=30000)
                save_playwright_screenshot(page, logger, DEBUG_SCREENSHOTS, "found_use_password_btn")
                human_delay(0.5, 1.5)
                use_password_btn.click()
                human_delay(1, 2)
            except PlaywrightTimeoutError:
                logger.error("Could not find 'use password' button after 30 seconds")
                save_playwright_screenshot(page, logger, DEBUG_SCREENSHOTS, "timeout_waiting_for_password_btn")
                raise

            # Enter the password to log in to Strava
            logger.info("Entering password on login page")
            password_field = page.locator("input[data-cy='password']").first
            password_field.wait_for(state="visible", timeout=20000)
            human_delay(0.5, 1.0)
            
            # Type password character by character like a human
            password_field.click()
            human_delay(0.2, 0.5)
            for char in STRAVA_PASS:
                password_field.type(char, delay=random.uniform(50, 150))
            human_delay(0.8, 1.5)

            # Click the final login button
            logger.info("Clicking final login button")
            login_button_password_stage = page.locator("button[type='submit'].Button_primary___8ywh").first
            login_button_password_stage.click()
            human_delay(1, 2)
            
            # Wait for the login to complete
            logger.info("Waiting for login to complete")
            page.wait_for_url("**/dashboard**", timeout=30000)
            logger.info("Login successful, starting activity downloads")
            
            # Download each relevant activity file
            for index, row in activities_df.iterrows():
                activity_id = row["id"]
                activity_name = row["name"]
                
                try:
                    logger.info("Downloading activity %d/%d: %s (ID: %s)", index + 1, len(activities_df), activity_name, activity_id)
                    
                    # Navigate to activity page
                    activity_url = f"https://www.strava.com/activities/{activity_id}"
                    page.goto(activity_url, wait_until="domcontentloaded")
                    
                    # Click dropdown menu to reveal export options
                    dropdown_button = page.locator("button.slide-menu.drop-down-menu").first
                    dropdown_button.wait_for(state="visible", timeout=15000)
                    dropdown_button.click()
                    
                    # Set up download promise before clicking
                    download_start_time = time.time()
                    
                    # Click the export file button and wait for download
                    with page.expect_download(timeout=60000) as download_info:
                        export_link = page.locator(f"a[href*='/activities/{activity_id}/export_original']").first
                        export_link.wait_for(state="visible", timeout=15000)
                        export_link.click()
                    
                    download = download_info.value
                    
                    # Save the downloaded file to the specified directory
                    file_path = os.path.join(download_dir, download.suggested_filename)
                    download.save_as(file_path)
                    
                    downloaded_files.append(file_path)
                    logger.info("Successfully downloaded: %s", file_path)
                    
                    # Add short delay between downloads
                    time.sleep(2)
                    
                except PlaywrightTimeoutError as e:
                    logger.error("Timeout downloading activity %s: %s", activity_id, e)
                    downloaded_files.append(None)
                except Exception as e:
                    logger.error("Error downloading activity %s: %s", activity_id, e, exc_info=True)
                    downloaded_files.append(None)
            
            return downloaded_files

        finally:
            context.close()
            browser.close()


def get_virtual_ride_activities(days=ACTIVITY_DAYS_RANGE):
    """Fetch recent Strava activities filtered for virtual ride type."""
    df = get_latest_activities(days=days)
    if df.empty:
        return pd.DataFrame()
    return df[df['type'] == 'VirtualRide'].copy()


if __name__ == "__main__":
    logger.info("Fetching activities from the past %s days", ACTIVITY_DAYS_RANGE)
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