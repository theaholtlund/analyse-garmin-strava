# PoC: Intelligent Cycling → Garmin Connect

## Overview

Minimal proof‑of‑concept to show:

- Login to Intelligent Cycling via `.NET` SDK
- Fetch one activity ID if available
- Login to Garmin Connect using an unofficial `.NET` client
- Retrieve Garmin user display name as proof of connection

## Prerequisites

- .NET 7 SDK installed
- Create a plain `.env` file in the project root with:

```
IC_USER=your_intelligent_cycling_email@example.com
IC_PASS=your_intelligent_cycling_password
GARMIN_USER=your_garmin_email@example.com
GARMIN_PASS=your_garmin_password
```

## Files

- `PoC.csproj`: defines project and dependencies
- `Program.cs`: PoC logic
- `.env`: environment variables for credentials

## Build & Run

```bash
# Download all project dependencies (NuGet packages and tools) as defined in .csproj file
dotnet restore
# Build (if needed) and execute the application in one step; automatically restores packages if missing
dotnet run
```

Console output expected:

```
[IC] Found activity ID: 12345
[Garmin] Connected as: Your Name
```

(or message about no new IC activities)

## Notes & Considerations

- `IntelligentCycling.ApiConnector` v6.0.0 supports login and fetching metadata but does not upload to Garmin. :contentReference[oaicite:2]{index=2}
- `Unofficial.Garmin.Connect` v0.8.1 is an **unofficial client** that mimics Garmin’s web interface; intended for personal automation only. :contentReference[oaicite:3]{index=3}
- Garmin does not offer official API for individuals; for official Activity API you must join Garmin Connect Developer Program, pass privacy policy requirements, and be approved as business use. :contentReference[oaicite:4]{index=4}

## Next Steps

1. Use `ICClient.DownloadActivity(activity.Id, path)` to save `.fit` files
2. If approved for Garmin official Activity API, implement upload of `.fit` files via REST
3. Potentially automate transfer using the unofficial client (with caution)
4. Add proper error handling, token refresh, MFA support, asynchronous file operations

```

```
