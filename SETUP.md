# Asana to Scoro Migration - Setup Guide

This guide will walk you through setting up the Asana to Scoro migration script from scratch.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [API Credentials Setup](#api-credentials-setup)
4. [Configuration](#configuration)
5. [Testing Your Setup](#testing-your-setup)
6. [Running Your First Migration](#running-your-first-migration)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.7 or higher** installed on your system
  - Check your version: `python --version` or `python3 --version`
  - Download from: https://www.python.org/downloads/

- **Admin/API access** to both Asana and Scoro accounts
  - Asana: You need permission to access projects and create Personal Access Tokens
  - Scoro: You need API credentials from your Scoro account manager

- **Git** (optional, but recommended)
  - Check if installed: `git --version`
  - Download from: https://git-scm.com/downloads

---

## Installation

### Step 1: Clone or Download the Project

**Option A: Using Git (recommended)**
```bash
git clone <repository-url>
cd migrate-data-Asana2Scoro
```

**Option B: Manual Download**
1. Download the project as a ZIP file
2. Extract to your preferred location
3. Navigate to the project directory

### Step 2: Create a Virtual Environment (Recommended)

This isolates the project dependencies from your system Python.

**On Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt when activated.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install all required Python packages including:
- `asana` - Asana Python SDK
- `requests` - HTTP library for Scoro API
- `python-dotenv` - Environment variable management
- `python-dateutil` - Date parsing utilities
- And other supporting libraries

**Verify installation:**
```bash
pip list
```

You should see all packages from `requirements.txt` listed.

---

## API Credentials Setup

### Getting Your Asana Personal Access Token

1. **Log into Asana** at https://app.asana.com
2. **Navigate to** the Developer Console:
   - Click your profile photo in the top right
   - Select "My Profile Settings"
   - Click on "Apps" tab
   - Scroll down to "Personal Access Tokens"
   - Or go directly to: https://app.asana.com/0/developer-console

3. **Create a new token:**
   - Click "+ New access token"
   - Give it a descriptive name (e.g., "Scoro Migration Script")
   - Click "Create token"
   - **IMPORTANT:** Copy the token immediately - you won't be able to see it again!

4. **Save your token securely** - you'll need it in the next step

### Getting Your Scoro API Credentials

1. **Contact Scoro Support** or your account manager
   - Request API access for your account
   - You'll need:
     - API Key
     - Company subdomain (e.g., if your Scoro URL is `yourcompany.scoro.com`, your subdomain is `yourcompany`)

2. **Wait for approval** - Scoro will provide your API credentials

### Creating Your .env File

1. **Create a new file** named `.env` in the project root directory:

```bash
touch .env  # On Linux/Mac
# Or create manually in your text editor on Windows
```

2. **Add your credentials** to the `.env` file:

```env
# Asana API Credentials
ASANA_ACCESS_TOKEN=your_asana_personal_access_token_here

# Scoro API Credentials
SCORO_API_KEY=your_scoro_api_key_here
SCORO_COMPANY_NAME=yourcompany
```

3. **Save the file** and ensure it's in the project root directory

**Security Note:** The `.env` file contains sensitive credentials. Never commit it to version control or share it publicly.

---

## Configuration

### Step 1: Get Your Asana Workspace GID

You need your Asana workspace GID for the migration.

**Option A: From Asana URL**
1. Log into Asana
2. Navigate to any project in your workspace
3. Look at the URL: `https://app.asana.com/0/WORKSPACE_GID/PROJECT_GID`
4. The WORKSPACE_GID is the first long number in the URL

**Option B: Using the Script (Test Connection)**
```bash
python main.py
```
If configured correctly, it will show your workspace information.

### Step 2: Get Your Asana Project GIDs (Recommended Method)

**Finding Project GIDs:**

1. **Navigate to your project** in Asana
2. **Copy the GID from the URL:**
   - URL format: `https://app.asana.com/0/WORKSPACE_GID/PROJECT_GID`
   - The PROJECT_GID is the second long number
3. **Repeat** for all projects you want to migrate

Example:
```
URL: https://app.asana.com/0/10447183158961/1207816263671761
                           ^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^
                           WORKSPACE_GID    PROJECT_GID
```

### Step 3: Configure config.py

Open `config.py` and configure your migration settings:

#### **Option 1: Migrate by Project GIDs (Recommended - Faster)**

```python
# In config.py

# Set migration mode
MIGRATION_MODE = 'gids'

# Add your project GIDs
PROJECT_GIDS = [
    "1207816263671761",  # Van Zeeland Nursery & Landscape
    "1234567890123456",  # Your Second Project
    "9876543210987654",  # Your Third Project
]

# Set your workspace GID
WORKSPACE_GID = "10447183158961"
```

#### **Option 2: Migrate by Project Names**

```python
# In config.py

# Set migration mode
MIGRATION_MODE = 'names'

# Add your project names (must match exactly)
PROJECT_NAMES = [
    "Van Zeeland Nursery & Landscape",
    "Another Project Name",
    "Third Project",
]

# Set your workspace GID
WORKSPACE_GID = "10447183158961"
```

### Step 4: Configure Additional Settings (Optional)

#### Test Mode (Recommended for First Run)

Limit the number of tasks migrated for testing:

```python
# Migrate only first 10 tasks (for testing)
TEST_MODE_MAX_TASKS = 10

# For production - migrate all tasks
TEST_MODE_MAX_TASKS = None
```

#### Date Filtering

Filter tasks by completion date:

```python
from datetime import datetime

# Only migrate tasks completed after July 1, 2025
CUTOFF_DATE = datetime(2025, 7, 1)
```

#### User Mapping

Customize user mappings if needed:

```python
# Add valid Scoro users
VALID_SCORO_USERS = {
    'Austin Koziol', 'Bethany Aeckersberg', 'Cait George', 'Tom Sanpakit',
    # ... add your team members
}

# Map short names to full names
USER_MAPPING = {
    'Austin': 'Austin Koziol',
    'Bethany': 'Bethany Aeckersberg',
    # ... add your mappings
}
```

---

## Testing Your Setup

### Test 1: Check Python and Dependencies

```bash
python --version  # Should be 3.7+
pip list | grep asana  # Should show asana package
pip list | grep dotenv  # Should show python-dotenv
```

### Test 2: Verify .env File

```bash
# Check if .env file exists
ls -la .env  # Linux/Mac
dir .env     # Windows

# Verify it contains your credentials (be careful not to expose them)
cat .env | grep "ASANA_ACCESS_TOKEN"  # Should show the line
```

### Test 3: Test API Connections

Run the script with test mode enabled:

```python
# In config.py, set:
TEST_MODE_MAX_TASKS = 1  # Migrate only 1 task
```

```bash
python main.py
```

**What to look for:**
- ✓ "Asana client initialized successfully"
- ✓ "Asana connection test successful"
- ✓ "Connected to Scoro. Found X existing projects."

If you see errors, check the [Troubleshooting](#troubleshooting) section.

---

## Running Your First Migration

### Step 1: Enable Test Mode

For your first run, use test mode to verify everything works:

```python
# In config.py
TEST_MODE_MAX_TASKS = 10  # Migrate only 10 tasks
```

### Step 2: Configure One Project

Start with a single project:

```python
# In config.py
MIGRATION_MODE = 'gids'
PROJECT_GIDS = [
    "1207816263671761",  # Your test project
]
```

### Step 3: Run the Migration

```bash
python main.py
```

### Step 4: Review the Results

**Check the console output:**
- Migration summary
- Success/failure counts
- Deduplication statistics

**Check the log file:**
```bash
# Logs are saved in the logs/ directory
ls -lah logs/
cat logs/migration_YYYYMMDD_HHMMSS.log
```

**Check the exported data:**
```bash
# JSON exports are saved in the project root
ls -lah asana_export_*.json
```

**Check Scoro:**
- Log into Scoro
- Verify the project was created
- Verify tasks were imported correctly
- Check task details, assignments, and comments

### Step 5: Disable Test Mode for Production

Once you've verified everything works:

```python
# In config.py
TEST_MODE_MAX_TASKS = None  # Migrate all tasks
```

### Step 6: Add All Your Projects

```python
# In config.py
PROJECT_GIDS = [
    "1207816263671761",
    "1234567890123456",
    "9876543210987654",
    # ... add all your projects
]
```

### Step 7: Run Full Migration

```bash
python main.py
```

---

## Troubleshooting

### Error: "Asana access token not provided"

**Problem:** The script can't find your Asana token.

**Solutions:**
1. Verify `.env` file exists in the project root
2. Check the file contains: `ASANA_ACCESS_TOKEN=your_token_here`
3. Ensure no extra spaces around the `=` sign
4. Make sure you're running the script from the project root directory

### Error: "Asana connection test failed"

**Problem:** Your Asana token is invalid or expired.

**Solutions:**
1. Create a new Personal Access Token at: https://app.asana.com/0/developer-console
2. Update your `.env` file with the new token
3. Ensure the token has proper permissions

### Error: "Scoro API key not provided"

**Problem:** Scoro credentials are missing or incorrect.

**Solutions:**
1. Verify your `.env` file contains both:
   - `SCORO_API_KEY=your_key`
   - `SCORO_COMPANY_NAME=yourcompany`
2. Contact Scoro support to verify your API credentials
3. Check for typos in your company subdomain

### Error: "No module named 'asana'" or similar

**Problem:** Dependencies not installed properly.

**Solutions:**
```bash
# Activate your virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Error: "Project not found"

**Problem:** Project GID or name is incorrect.

**Solutions:**
1. **For GID mode:**
   - Verify the GID in the Asana URL
   - Ensure it's the project GID, not the workspace GID
   
2. **For name mode:**
   - Check the project name matches exactly (case-sensitive)
   - Verify you have access to the project in Asana

### Rate Limiting / 429 Errors

**Problem:** Too many API requests.

**Solutions:**
1. Increase rate limit delay in `config.py`:
```python
RATE_LIMIT_DELAY = 0.2  # Increase from 0.1 to 0.2 seconds
```

2. Reduce batch size:
```python
DEFAULT_BATCH_SIZE = 25  # Reduce from 50 to 25
```

### Migration Runs But No Tasks Imported

**Problem:** Tasks are being filtered out.

**Solutions:**
1. Check the CUTOFF_DATE in `config.py`:
```python
# If you want all tasks, use an old date
CUTOFF_DATE = datetime(2020, 1, 1)
```

2. Check the logs for filtering reasons:
```bash
grep -i "filter" logs/migration_*.log
grep -i "skip" logs/migration_*.log
```

### Script Crashes or Hangs

**Problem:** Network issues or API problems.

**Solutions:**
1. Check your internet connection
2. Verify Asana and Scoro APIs are operational
3. Try again with a smaller batch (enable TEST_MODE_MAX_TASKS)
4. Check logs for specific errors

---

## Getting Help

If you continue to experience issues:

1. **Check the logs:**
   - `logs/migration_YYYYMMDD_HHMMSS.log` contains detailed information

2. **Review the documentation:**
   - `README.md` - Full feature documentation
   - `workflow.md` - Migration workflow details
   - `docs/` folder - Additional technical documentation

3. **API Documentation:**
   - Asana: https://developers.asana.com/docs
   - Scoro: Contact Scoro support for API documentation

4. **Common Issues:**
   - Ensure you're using Python 3.7+
   - Verify all dependencies are installed
   - Check that API credentials are valid
   - Make sure project GIDs/names are correct

---

## Next Steps

Once your setup is complete and tested:

1. Read the full [README.md](README.md) for feature details
2. Review [workflow.md](workflow.md) for migration process details
3. Customize category mappings in `transformers/mappers.py` if needed
4. Set up regular backups of your Asana data using the export feature

**Happy migrating! 🚀**

