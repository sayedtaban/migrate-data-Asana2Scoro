# Quick Start Guide

## 1. Install Dependencies

```bash
pip install flask flask-cors
```

## 2. Start the Monitoring Server

```bash
python monitoring/monitor.py
```

Or use the startup script:
```bash
./monitoring/start_monitor.sh
```

## 3. Open the Dashboard

Open your browser and go to:
```
http://localhost:8002
```

## 4. Run Migrations

The migration script (`main.py`) will automatically send status updates to the monitoring server. Just run your migrations as usual:

```bash
python main.py 1209020289079877
```

## 5. Monitor Progress

Watch the dashboard update in real-time as migrations progress through:
- 🔴 **Phase 1** (Export from Asana)
- 🟡 **Phase 2** (Transform Data)
- 🟢 **Phase 3** (Import to Scoro)

## CSV Logs

All status updates are automatically saved to:
```
monitoring/migration_status.csv
```

## Test the System

Test the monitoring server with sample requests:

```bash
python test_monitoring_server.py
```

Or manually:

```bash
curl -X POST http://localhost:8002 \
  -H "Content-Type: application/json" \
  -d '{"asana GID": "1209020289079877", "status": "Phase1", "asana project name": "Test Project"}'
```

