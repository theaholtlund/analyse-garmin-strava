# Import required libraries
import os
import time
import json
from pathlib import Path


def ensure_dir(path):
    """Ensure directory exists."""
    Path(path).mkdir(parents=True, exist_ok=True)
    return Path(path)


def safe_json_write(given_path, data, logger, indent=2):
    """Write JSON safely (atomic-ish) to a file path."""
    path = Path(given_path)
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    tmp.replace(path)
    logger.info("Wrote JSON to %s", path)
    return path

def save_debug_screenshot(driver, logger, DEBUG_SCREENSHOTS, label="screenshot"):
    """Capture screenshot with Selenium and save to current directory, if activated."""
    if DEBUG_SCREENSHOTS != "ON":
        return

    filename = f"{label}_{int(time.time())}.png"
    path = os.path.join(os.getcwd(), filename)
    driver.save_screenshot(path)
    logger.info("Saved screenshot: %s", path)
    return path
