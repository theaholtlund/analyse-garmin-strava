# Import required libraries
from pathlib import Path
import json


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
