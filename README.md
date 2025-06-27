# Activity to Garmin

Project to automate the transfer of indoor cycling activities from Intelligent Cycling to Garmin Connect.

## Prerequisites

- **Windows** + [.NET > 4.5](https://dotnet.microsoft.com/en-us/)
- **Python 3.8+**
- Environment variables:
  - `IC_USER`, `IC_PASS` – for Intelligent Cycling login
  - `GC_USER`, `GC_PASS` – for Garmin Connect login
  - (optional) `IC_OUTDIR` – output directory for downloaded activities (default: `./activities`)

### 1. Clone the repo

```bash
git clone https://github.com/theaholtlund/activity-to-garmin.git
cd activity-to-garmin/intelligent-cycling
```

### 2. Add the credentials to environment file

```bash
echo "IC_USER=your_email" >> .env
echo "IC_PASS=your_password" >> .env
```

### 3. C# Application

```bash
cd ICDownload
dotnet add package IntelligentCycling.ApiConnector --version 5.5.0
dotnet publish -c Release -r win-x64 --self-contained=false
vbnet
```

### 4. Python Script: Watch Folder and Upload to Garmin

```bash
cd python-uploader
python3 -m venv venv
source venv/bin/activate
```

### 5. Intall the Requirements

```bash
pip install -r requirements.txt
```

### 6. Run the File

```bash
python upload_watch.py
```
