"""Set up a persistent, separate Chrome profile for Strava downloads."""
import os
import sys
from pathlib import Path
from time import monotonic, sleep

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

load_dotenv()
profile = Path(os.getenv('STRAVA_CHROME_PROFILE', 'outputs/strava-browser-profile')).expanduser().resolve()
profile.mkdir(parents=True, exist_ok=True, mode=0o700)
os.chmod(profile, 0o700)
options = Options()
options.add_argument(f'--user-data-dir={profile}')
# Match the profile's user agent to the one used for downloads.
options.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1')
options.add_argument('--window-size=390,844')
driver = webdriver.Chrome(options=options)
try:
    driver.get('https://www.strava.com/login')
    print('Log in to Strava in the Chrome window. Complete any verification there.', flush=True)
    deadline = monotonic() + 300
    while monotonic() < deadline:
        if 'strava.com/dashboard' in driver.current_url:
            print('Strava session saved. The browser will now close.', flush=True)
            break
        sleep(1)
    else:
        print('Login not completed within five minutes.', file=sys.stderr)
        sys.exit(1)
finally:
    driver.quit()
