# Import required libraries
from pathlib import Path
import logging

# Set up logging for information
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ensure_dir(path):
    """Ensure directory exists."""
    Path(path).mkdir(parents=True, exist_ok=True)
    return Path(path)
