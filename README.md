# Activity to Garmin

Project to automate the transfer of indoor cycling activities from Intelligent Cycling to Garmin Connect.

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

### 2. Intall the Requirements

```bash
pip install -r requirements.txt
```
