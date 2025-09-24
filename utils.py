# Import required libraries
from pathlib import Path
import json

# Import shared configuration and functions from other scripts
from config import logger


def ensure_dir(path):
    """Ensure directory exists."""
    Path(path).mkdir(parents=True, exist_ok=True)
    return Path(path)


def safe_json_write(given_path, data, indent=2):
    """Write JSON safely (atomic-ish) to a file path."""
    path = Path(given_path)
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    tmp.replace(path)
    logger.info("Wrote JSON to %s", path)
    return path


def human_readable_duration(seconds):
    """Return a short human-readable duration string in hours and minutes."""
    try:
        seconds = int(seconds or 0)
    except Exception:
        return "0s"
    hours, rem = divmod(seconds, 3600)
    minutes, _ = divmod(rem, 60)
    if hours:
        return f"{hours}h{minutes:02d}m"
    if minutes:
        return f"{minutes}m"
    return f"{seconds}s"
