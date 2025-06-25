# Activity to Garmin

Project to automate the transfer of indoor cycling activities from Intelligent Cycling to Garmin Connect.

## Prerequisites

- **Windows** + [.NET > 4.5](https://dotnet.microsoft.com/en-us/)
- **Python 3.8+**
- Environment variables:
  - `IC_USER`, `IC_PASS` – for Intelligent Cycling login
  - `GC_USER`, `GC_PASS` – for Garmin Connect login
  - (optional) `IC_OUTDIR` – output directory for downloaded activities (default: `./activities`)

## Installation

### 1. C# Application

```bash
cd ICDownload
dotnet add package IntelligentCycling.ApiConnector --version 5.5.0
dotnet publish -c Release -r win-x64 --self-contained=false
vbnet
```

### 2. Python Script: Watch Folder and Upload to Garmin

```bash
cd python-uploader
python3 -m venv venv
source venv/bin/activate
```

### 3. Intall the Requirements

```bash
pip install -r requirements.txt
```

### 4. Run the File

```bash
python upload_watch.py
```
