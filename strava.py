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

# Import shared configuration and functions from other scripts
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
    response = requests.post("https://www.strava.com/api/v3/oauth/token", data={
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": token["refresh_token"],
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


def download_multiple_activities(activities_df, download_dir=None):
    """Download multiple FIT files from Strava using Selenium with a single login session."""
    if not STRAVA_USER or not STRAVA_PASS:
        raise RuntimeError("Strava user and password must be set in config.py")

    options = Options()
    # Run headless in CI (enable if needed)
    # options.add_argument("--headless=new")
    options.add_argument("--window-size=390,844")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Ensure a unique Chrome user data directory for each run
    import tempfile
    user_data_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={user_data_dir}")

    # Mobile user agent to get mobile Strava pages
    options.add_argument(
        "--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
    )

    # Configure automatic downloads
    options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })

    driver = webdriver.Chrome(options=options)
    downloaded_files = []
    
    try:
        # Log in to Strava profile
        logger.info("Opening the Strava login page")
        driver.get("https://www.strava.com/login")

        # Handle cookie banner if present
        try:
            logger.info("Checking for cookie banner")
            cookie_accept = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-cy='accept-cookies'], .CookieBanner button, button[id*='cookie'], button[class*='cookie']"))
            )
            cookie_accept.click()
            logger.info("Cookie banner accepted")
            time.sleep(1)
        except:
            logger.info("No cookie banner found or already accepted")

        # Enter e-mail for the login page
        logger.info("Entering e-mail on Strava login page")
        email_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "mobile-email"))
        )
        email_field.send_keys(STRAVA_USER)

        # Click the login button to proceed to password stage
        logger.info("Sending e-mail on Strava login page")
        login_button_email_stage = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "mobile-login-button"))
        )
        driver.execute_script("arguments[0].click();", login_button_email_stage)

        # Wait for the OTP page to load and click button to use password instead
        logger.info("Waiting for OTP page and clicking button to use password instead")
        use_password_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='use-password-cta'] button"))
        )
        driver.execute_script("arguments[0].click();", use_password_btn)

        # Enter the password to log in to Strava
        logger.info("Entering password on login page")
        password_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-cy='password']"))
        )
        password_field.send_keys(STRAVA_PASS)

        # Click the final login button
        logger.info("Clicking final login button")
        login_button_password_stage = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit'].Button_primary___8ywh"))
        )
        driver.execute_script("arguments[0].click();", login_button_password_stage)
        
        # Wait for the login to complete
        logger.info("Waiting for login to complete")
        WebDriverWait(driver, 30).until(EC.url_contains("dashboard"))
        logger.info("Login successful, starting activity downloads")
        
        # Download each relevant activity file
        for index, row in activities_df.iterrows():
            activity_id = row["id"]
            activity_name = row["name"]
            
            try:
                logger.info(f"Downloading activity {index + 1}/{len(activities_df)}: {activity_name} (ID: {activity_id})")
                
                # Navigate to activity page
                activity_url = f"https://www.strava.com/activities/{activity_id}"
                driver.get(activity_url)
                
                # Click dropdown menu to reveal export options
                dropdown_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.slide-menu.drop-down-menu"))
                )
                ActionChains(driver).move_to_element(dropdown_button).click().perform()
                
                # Click the export file button
                export_link = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//a[contains(@href, '/activities/{activity_id}/export_original')]")
                    )
                )
                ActionChains(driver).move_to_element(export_link).click().perform()
                
                # Wait for file to download
                download_start_time = time.time()
                file_path = None
                while True:
                    files = [f for f in os.listdir(download_dir) if os.path.isfile(os.path.join(download_dir, f))]
                    for filename in files:
                        full_path = os.path.join(download_dir, filename)
                        if os.path.getctime(full_path) > download_start_time:
                            file_path = full_path
                            break
                    if file_path or time.time() - download_start_time > 60:
                        break
                    time.sleep(1)

                if file_path:
                    downloaded_files.append(file_path)
                    logger.info(f"Successfully downloaded: {file_path}")
                else:
                    downloaded_files.append(None)
                    logger.warning(f"Failed to download activity {activity_id}")
                
                # Add short delay between downloads
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error downloading activity {activity_id}: {e}")
                downloaded_files.append(None)
        
        return downloaded_files

    finally:
        driver.quit()


def get_virtual_ride_activities(days=ACTIVITY_DAYS_RANGE):
    """Fetch recent Strava activities filtered for virtual ride type."""
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
