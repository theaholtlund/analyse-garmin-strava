"""Read the signed-in athlete's activity list using the dedicated Chrome session."""
import datetime as dt
import os
import re
from pathlib import Path
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def recent_rides(days, marker, activity_id=None, include_all=False):
    profile = Path(os.getenv('STRAVA_CHROME_PROFILE', 'outputs/strava-browser-profile')).expanduser().resolve()
    if not profile.is_dir():
        raise RuntimeError('Set up the Strava browser session first')
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=1200,900')
    options.add_argument(f'--user-data-dir={profile}')
    driver = webdriver.Chrome(options=options)
    try:
        driver.get('https://www.strava.com/athlete/training')
        if urlparse(driver.current_url).path != '/athlete/training':
            raise RuntimeError('Strava browser session unavailable')
        result = []
        # Include a buffer day for timezone differences. Stop only once a full
        # page is older, and fail rather than silently skip after 100 pages.
        cutoff = dt.date.today() - dt.timedelta(days=days + 1)
        for _ in range(100):
            rows = WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'tr.training-activity-row')))
            dates = []
            for row in rows:
                date_text = row.find_element(By.CSS_SELECTOR, '.view-col.col-date').text
                match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_text)
                if not match:
                    raise RuntimeError('Unknown Strava date format; cannot safely filter activities')
                month, day, year = map(int, match.groups())
                try:
                    date = dt.date(year, month, day)
                except ValueError as exc:
                    raise RuntimeError('Unknown Strava date format') from exc
                dates.append(date)
                if date < cutoff:
                    continue
                anchor = row.find_element(By.CSS_SELECTOR, '.view-col.col-title a[data-field-name="name"]')
                activity_match = re.fullmatch(r'/activities/(\d+)', urlparse(anchor.get_attribute('href')).path)
                sport = row.find_element(By.CSS_SELECTOR, '.view-col.col-type').text
                if not activity_match or sport not in ('Virtual Ride', 'Ride'):
                    continue
                ident = int(activity_match.group(1))
                name = anchor.text.strip()
                if include_all or (activity_id and ident == activity_id) or (not activity_id and marker and marker.casefold() in name.casefold()):
                    result.append({'id': ident, 'name': name, 'date': date.isoformat()})
            if dates and max(dates) < cutoff:
                break
            next_buttons = driver.find_elements(By.CSS_SELECTOR, 'button.next_page')
            if not next_buttons or not next_buttons[0].is_enabled():
                break
            previous = rows[0]
            next_buttons[0].click()
            WebDriverWait(driver, 20).until(EC.staleness_of(previous))
        else:
            raise RuntimeError('Too many Strava pages; refusing to silently skip activities')
        return result
    finally:
        driver.quit()


def delete_confirmed_watch_copy(activity_id, mowl_id, mowl_file, strava_watch_file, garmin_watch_file):
    """Delete a Strava copy only after its FIT matches the known Garmin device/session."""
    from mowl_sync import fit_device_identity
    from merge_cycling_fit import read_fit
    activity_id, mowl_id = str(activity_id), str(mowl_id)
    if not activity_id.isdigit() or not mowl_id.isdigit() or activity_id == mowl_id:
        raise ValueError('Invalid or protected activity ID')
    if fit_device_identity(strava_watch_file) != fit_device_identity(garmin_watch_file):
        raise ValueError('Strava FIT does not match the Garmin original')
    mowl, _ = read_fit(mowl_file)
    watch, _ = read_fit(garmin_watch_file)
    start, end = max(min(mowl), min(watch)), min(max(mowl), max(watch))
    duration = min((max(mowl) - min(mowl)).total_seconds(), (max(watch) - min(watch)).total_seconds())
    if duration <= 0 or (end - start).total_seconds() < 0.8 * duration:
        raise ValueError('The MOWL and Garmin recordings do not overlap sufficiently')
    profile = Path(os.getenv('STRAVA_CHROME_PROFILE', 'outputs/strava-browser-profile')).expanduser().resolve()
    if not profile.is_dir():
        raise RuntimeError('Strava browser session is unavailable')
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=1200,900')
    options.add_argument(f'--user-data-dir={profile}')
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(f'https://www.strava.com/activities/{mowl_id}')
        if (urlparse(driver.current_url).path != f'/activities/{mowl_id}' or
                len(driver.find_elements(By.CSS_SELECTOR, f'a[data-method="delete"][href="/activities/{mowl_id}"]')) != 1):
            raise RuntimeError('Protected MOWL activity cannot be verified')
        driver.get(f'https://www.strava.com/activities/{activity_id}')
        if urlparse(driver.current_url).path != f'/activities/{activity_id}':
            raise RuntimeError('Watch activity cannot be verified')
        links = driver.find_elements(By.CSS_SELECTOR, f'a[data-method="delete"][href="/activities/{activity_id}"]')
        if len(links) != 1:
            raise RuntimeError('Cannot identify the exact Strava delete action')
        driver.execute_script('arguments[0].click()', links[0])
        alert = WebDriverWait(driver, 10).until(EC.alert_is_present())
        if 'restore an activity for 30 days' not in alert.text:
            alert.dismiss()
            raise RuntimeError('Unexpected Strava confirmation; deletion cancelled')
        alert.accept()
        WebDriverWait(driver, 20).until(lambda d: urlparse(d.current_url).path != f'/activities/{activity_id}')
        driver.get(f'https://www.strava.com/activities/{activity_id}')
        if driver.find_elements(By.CSS_SELECTOR, f'a[data-method="delete"][href="/activities/{activity_id}"]'):
            raise RuntimeError('Watch activity still appears to be present')
        driver.get(f'https://www.strava.com/activities/{mowl_id}')
        if (urlparse(driver.current_url).path != f'/activities/{mowl_id}' or
                len(driver.find_elements(By.CSS_SELECTOR, f'a[data-method="delete"][href="/activities/{mowl_id}"]')) != 1):
            raise RuntimeError('Could not verify protected MOWL activity after deletion')
    finally:
        driver.quit()
