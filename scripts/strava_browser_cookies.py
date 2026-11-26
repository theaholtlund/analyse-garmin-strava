"""Restore the Strava session stored in a GitHub Actions secret."""
import json
import sys
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def restore_session(profile, source):
    cookies = json.loads(Path(source).read_text())
    if not isinstance(cookies, list) or not cookies:
        raise ValueError('Invalid Strava session')
    profile = Path(profile).resolve()
    profile.mkdir(mode=0o700, parents=True, exist_ok=True)
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=390,844')
    options.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1')
    options.add_argument(f'--user-data-dir={profile}')
    driver = webdriver.Chrome(options=options)
    try:
        driver.get('https://www.strava.com/')
        for cookie in cookies:
            if cookie.get('domain', '').lstrip('.') not in ('strava.com', 'www.strava.com'):
                raise ValueError('Invalid cookie domain')
            driver.add_cookie({k: v for k, v in cookie.items() if k in ('name', 'value', 'domain', 'path', 'secure', 'httpOnly', 'expiry', 'sameSite')})
        driver.get('https://www.strava.com/dashboard')
        if not driver.current_url.startswith('https://www.strava.com/dashboard'):
            raise RuntimeError('Strava session is not authenticated')
        print('Strava session restored.')
    finally:
        driver.quit()


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] != 'restore':
        raise SystemExit('Usage: strava_browser_cookies.py restore PROFILE FILE')
    restore_session(sys.argv[2], sys.argv[3])
