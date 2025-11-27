# Migration Monitoring System

A real-time web dashboard for monitoring Asana to Scoro migration progress.

## Features

- 📊 **Real-time Dashboard**: Web-based UI that auto-refreshes every 2 seconds
- 📝 **CSV Logging**: Automatically saves all status updates to `migration_status.csv`
- 🎨 **Color-coded Status**: 
  - 🔴 Red for Phase 1 (Export)
  - 🟡 Yellow for Phase 2 (Transform)
  - 🟢 Green for Phase 3 (Import)
- 📈 **Statistics**: Shows total projects and counts per phase
- 🔄 **Auto-refresh**: Dashboard updates automatically without page reload

## Installation

Install required dependencies:

```bash
pip install flask flask-cors
```

Or add to your `requirements.txt`:
```
flask
flask-cors
```

## Usage

### Start the Monitoring Server

```bash
python monitoring/monitor.py
```

The server will start on `http://localhost:8002`

### Access the Dashboard

Open your web browser and navigate to:
```
http://localhost:8002
```

### API Endpoints

1. **POST /** - Receive status updates
   ```bash
   curl -X POST http://localhost:8002 \
     -H "Content-Type: application/json" \
     -d '{
       "asana GID": "1209020289079877",
       "status": "Phase1",
       "asana project name": "My Project Name"
     }'
   ```

2. **GET /api/status** - Get current status of all projects
   ```bash
   curl http://localhost:8002/api/status
   ```

3. **GET /api/export** - Export current status as CSV
   ```bash
   curl http://localhost:8002/api/export -o export.csv
   ```

## CSV File

All status updates are automatically saved to:
```
monitoring/migration_status.csv
```

The CSV file contains:
- Timestamp
- Asana GID
- Project Name
- Status

## Dashboard Features

- **Statistics Cards**: Shows total projects and counts for each phase
- **Projects Table**: Displays all projects with:
  - Asana GID
  - Project Name
  - Current Status (color-coded)
  - Last Update Time
- **Auto-refresh**: Updates every 2 seconds automatically
- **Responsive Design**: Works on desktop and mobile devices

## Integration

The monitoring system is automatically integrated with the migration script (`main.py`). When you run:

```bash
python main.py 1209020289079877
```

The migration script will send status updates to the monitoring server at each phase.

## Testing

Use the test script to verify the monitoring server:

```bash
python test_monitoring_server.py
```

Or test manually:

```bash
# Phase 1
curl -X POST http://localhost:8002 \
  -H "Content-Type: application/json" \
  -d '{"asana GID": "1209020289079877", "status": "Phase1", "asana project name": "Test Project"}'

# Phase 2
curl -X POST http://localhost:8002 \
  -H "Content-Type: application/json" \
  -d '{"asana GID": "1209020289079877", "status": "Phase2", "asana project name": "Test Project"}'

# Phase 3
curl -X POST http://localhost:8002 \
  -H "Content-Type: application/json" \
  -d '{"asana GID": "1209020289079877", "status": "Phase3", "asana project name": "Test Project"}'
```

## Troubleshooting

### Server won't start

- Check if port 8002 is already in use
- Ensure Flask is installed: `pip install flask flask-cors`

### Dashboard not updating

- Check browser console for errors
- Verify the server is running
- Check network tab to see if API calls are being made

### CSV file not created

- Check file permissions in the `monitoring/` directory
- Ensure the directory exists

## Architecture

- **Flask Server**: Handles HTTP requests and serves the dashboard
- **In-memory Storage**: Keeps project statuses in memory for fast access
- **CSV Logging**: Persistent storage of all status updates
- **WebSocket Alternative**: Uses polling (2-second intervals) for real-time updates

## Future Enhancements

Potential improvements:
- WebSocket support for true real-time updates
- Historical data visualization
- Export to other formats (JSON, Excel)
- Email/Slack notifications
- Project filtering and search
- Status history timeline

