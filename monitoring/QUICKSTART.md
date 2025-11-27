# Quick Start Guide

## 1. Install Dependencies

```bash
pip install flask flask-cors
```

Or install all requirements:
```bash
pip install -r ../requirements.txt
```

## 2. Start the Monitoring Server

```bash
cd monitoring
python monitor.py
```

Or use the startup script:
```bash
./start_monitor.sh
```

## 3. Open the Dashboard

Open your browser and go to:
```
http://localhost:8002
```

## 4. Run Your Migration

In another terminal, run your migration script:
```bash
python main.py 1209020289079877
```

The dashboard will automatically update as each phase completes!

## Features

- ✅ Real-time status updates
- ✅ Color-coded phases (Red/Yellow/Green)
- ✅ CSV logging
- ✅ Statistics dashboard
- ✅ Auto-refresh every 5 seconds

## Testing

Test the server with:
```bash
python ../test_monitoring_server.py
```

