#!/usr/bin/env python3
"""Create a Garmin Connect token file for local and GitHub Actions use."""

import argparse
import os
from getpass import getpass
from pathlib import Path

from dotenv import load_dotenv
from garminconnect import Garmin


def prompt_mfa():
    """Prompt for the one-time Garmin MFA code."""
    return input("Garmin MFA code: ").strip()


def main():
    """Log in once and save ~/.garminconnect/garmin_tokens.json."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Create a Garmin token store after completing MFA once."
    )
    parser.add_argument(
        "--tokenstore",
        default=os.getenv("GARMINTOKENS")
        or os.getenv("GARMIN_TOKENSTORE", "~/.garminconnect"),
        help="Directory where garmin_tokens.json should be saved.",
    )
    parser.add_argument(
        "--email",
        default=os.getenv("GARMIN_USER") or os.getenv("EMAIL"),
        help="Garmin Connect email. Defaults to GARMIN_USER or EMAIL.",
    )
    args = parser.parse_args()

    tokenstore = Path(args.tokenstore).expanduser()
    tokenstore.mkdir(parents=True, exist_ok=True)

    email = args.email or input("Garmin email: ").strip()
    password = os.getenv("GARMIN_PASS") or os.getenv("PASSWORD") or getpass(
        "Garmin password: "
    )

    client = Garmin(email=email, password=password, prompt_mfa=prompt_mfa)
    client.login(str(tokenstore))

    token_file = tokenstore / "garmin_tokens.json"
    token_file.chmod(0o600)

    print(f"Garmin tokens saved to {token_file}")
    print(
        "Create or update the GitHub secret GARMIN_TOKENS_JSON with that "
        "file's contents."
    )


if __name__ == "__main__":
    main()
