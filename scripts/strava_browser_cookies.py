"""Export or restore an authenticated Strava session without printing cookies."""
import json
import os
import sys
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def browser(profile):
    profile.mkdir(mode=0o700, parents=True, exist_ok=True)
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=390,844')
    options.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1')
    options.add_argument(f'--user-data-dir={profile.resolve()}')
    return webdriver.Chrome(options=options)


def export_session(profile, target):
    driver = browser(profile)
    try:
        driver.get('https://www.strava.com/dashboard')
        if not driver.current_url.startswith('https://www.strava.com/dashboard'):
            raise RuntimeError('Strava session not signed in')
        cookies = [c for c in driver.get_cookies() if c.get('domain', '').lstrip('.') in ('strava.com', 'www.strava.com')]
        if not cookies:
            raise RuntimeError('No Strava cookies available')
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(cookies, stream)
        print('Strava session exported to a private file.')
    finally:
        driver.quit()


def restore_session(profile, source):
    cookies = json.loads(Path(source).read_text())
    if not isinstance(cookies, list) or not cookies:
        raise ValueError('Invalid Strava session')
    driver = browser(profile)
    try:
        driver.get('https://www.strava.com/')
        for cookie in cookies:
            domain = cookie.get('domain', '').lstrip('.')
            if domain not in ('strava.com', 'www.strava.com'):
                raise ValueError('Invalid cookie domain')
            cookie = {k: v for k, v in cookie.items() if k in ('name','value','domain','path','secure','httpOnly','expiry','sameSite')}
            driver.add_cookie(cookie)
        driver.get('https://www.strava.com/dashboard')
        if not driver.current_url.startswith('https://www.strava.com/dashboard'):
            raise RuntimeError('Restored Strava session is not authenticated')
        print('Restored Strava session validated.')
    finally:
        driver.quit()


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] not in ('export', 'restore'):
        raise SystemExit('Usage: strava_browser_cookies.py export|restore PROFILE FILE')
    action, profile, path = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    (export_session if action == 'export' else restore_session)(profile, path)
