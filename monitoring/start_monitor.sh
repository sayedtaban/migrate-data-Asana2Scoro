#!/bin/bash
# Start the migration monitoring server

echo "Starting Migration Monitoring System..."
echo ""

# Check if Flask is installed
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Flask not found. Installing dependencies..."
    pip install flask flask-cors
fi

# Start the server
python3 monitoring/monitor.py

