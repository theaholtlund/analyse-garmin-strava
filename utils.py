# Import required libraries
from pathlib import Path
import json

# Import shared configuration and functions from other scripts
from config import logger


def ensure_dir(path):
    """Ensure directory exists."""
    Path(path).mkdir(parents=True, exist_ok=True)
    return Path(path)
