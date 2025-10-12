# Playwright Setup Instructions

## Local Development Setup

After installing the Python dependencies, you need to install the Playwright browsers:

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers (Chromium)
python -m playwright install chromium
```

Alternatively, to install all Playwright browsers with system dependencies:

```bash
python -m playwright install --with-deps
```

## Running the Playwright Version

```bash
# Run the sync with default settings (headless mode)
python strava_garmin_sync_playwright.py

# Run with visible browser window for debugging
python strava_garmin_sync_playwright.py --no-headless

# Dry run (don't upload to Garmin)
python strava_garmin_sync_playwright.py --dry-run

# Limit number of activities
python strava_garmin_sync_playwright.py --limit 5

# Combine options (visible browser, dry run, limit 3 activities)
python strava_garmin_sync_playwright.py --no-headless --dry-run --limit 3
```

## GitHub Actions

The GitHub Actions workflow (`.github/workflows/virtual_ride_sync_playwright.yml`) automatically installs Playwright browsers as part of the CI/CD pipeline, so no manual setup is required in the cloud environment.

## Troubleshooting

If you see an error like:
```
Executable doesn't exist at /path/to/chromium
```

Run the installation command:
```bash
python -m playwright install chromium
```

This will download and install the Chromium browser to your local cache.