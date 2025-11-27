# Migration Monitoring System

A real-time web dashboard for monitoring Asana to Scoro migration progress.

## Features

- 📊 **Real-time Dashboard**: Web-based UI showing all project migrations
- 📝 **CSV Logging**: Automatically saves all status updates to `migration_status.csv`
- 🎨 **Color-coded Status**: Visual indicators for each phase
  - 🔴 **Phase1** (Red): Export from Asana
  - 🟡 **Phase2** (Yellow): Transform Data
  - 🟢 **Phase3** (Green): Import to Scoro
- 📈 **Statistics**: Live counts of projects in each phase
- 🔄 **Auto-refresh**: Dashboard updates every 5 seconds

## Installation

Make sure you have the required dependencies:

```bash
pip install flask flask-cors
```

## Usage

### Start the Monitoring Server

```bash
cd monitoring
python monitor.py
```

The server will start on `http://localhost:8002`

### Access the Dashboard

Open your browser and navigate to:
```
http://localhost:8002
```

### API Endpoint

The migration scripts send POST requests to:
```
POST http://localhost:8002/api/status
Content-Type: application/json

{
  "asana GID": "1209020289079877",
  "status": "Phase1",
  "asana project name": "My Project Name"
}
```

## Dashboard Features

- **Total Projects**: Shows the number of projects being tracked
- **Phase Counts**: Displays how many projects are in each phase
- **Project Table**: Lists all projects with:
  - Asana GID
  - Project Name
  - Current Status (color-coded)
  - Last Update Timestamp
- **Auto-refresh**: Automatically updates every 5 seconds (can be toggled)
- **Manual Refresh**: Click the refresh button to update immediately

## CSV File

All status updates are automatically saved to `migration_status.csv` with the following format:

```csv
Timestamp,Asana GID,Project Name,Status
2025-11-27 10:30:15,1209020289079877,My Project Name,Phase1
2025-11-27 10:30:20,1209020289079877,My Project Name,Phase2
2025-11-27 10:30:25,1209020289079877,My Project Name,Phase3
```

## API Endpoints

### POST `/api/status`
Receive status updates from migration scripts.

**Request:**
```json
{
  "asana GID": "1209020289079877",
  "status": "Phase1",
  "asana project name": "My Project Name"
}
```

**Response:**
```json
{
  "received": true,
  "gid": "1209020289079877",
  "status": "Phase1",
  "project_name": "My Project Name"
}
```

### GET `/api/projects`
Get all current project statuses.

**Response:**
```json
{
  "projects": [
    {
      "gid": "1209020289079877",
      "project_name": "My Project Name",
      "status": "Phase1",
      "timestamp": "2025-11-27T10:30:15.123456"
    }
  ]
}
```

### GET `/api/health`
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "projects_tracked": 5
}
```

## Testing

You can test the monitoring server using the test script:

```bash
python test_monitoring_server.py
```

Or manually with curl:

```bash
curl -X POST http://localhost:8002/api/status \
  -H "Content-Type: application/json" \
  -d '{
    "asana GID": "1209020289079877",
    "status": "Phase1",
    "asana project name": "Test Project"
  }'
```

## Notes

- The server stores project status in memory for real-time updates
- CSV file is thread-safe and can handle concurrent writes
- If the server restarts, it will continue logging to CSV but will lose in-memory status until new updates arrive
- The dashboard shows the latest status for each project GID

