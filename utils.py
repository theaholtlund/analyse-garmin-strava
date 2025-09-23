# Import required libraries
from pathlib import Path
import json

# Import shared configuration and functions from other scripts
from config import logger


def ensure_dir(path):
    """Ensure directory exists."""
    Path(path).mkdir(parents=True, exist_ok=True)
    return Path(path)


def safe_json_write(path, data, indent=2):
    p = Path(path)
    ensure_dir(p.parent)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    tmp.replace(p)
    return p


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
