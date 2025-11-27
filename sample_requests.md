# Sample Migration Status Requests

This document shows example HTTP requests that will be sent to `localhost:8002` during migration.

## Request Format

**Method:** POST  
**URL:** `http://localhost:8002`  
**Content-Type:** `application/json`  
**Timeout:** 2 seconds

## Sample Payloads

### Phase 1: Export from Asana
```json
{
  "asana GID": "1209020289079877",
  "status": "Phase1",
  "asana project name": "My Project Name"
}
```

### Phase 2: Transform Data
```json
{
  "asana GID": "1209020289079877",
  "status": "Phase2",
  "asana project name": "My Project Name"
}
```

### Phase 3: Import to Scoro
```json
{
  "asana GID": "1209020289079877",
  "status": "Phase3",
  "asana project name": "My Project Name"
}
```

## Testing with cURL

You can test your monitoring server with these curl commands:

```bash
# Phase 1
curl -X POST http://localhost:8002 \
  -H "Content-Type: application/json" \
  -d '{"asana GID": "1209020289079877", "status": "Phase1", "asana project name": "My Project Name"}'

# Phase 2
curl -X POST http://localhost:8002 \
  -H "Content-Type: application/json" \
  -d '{"asana GID": "1209020289079877", "status": "Phase2", "asana project name": "My Project Name"}'

# Phase 3
curl -X POST http://localhost:8002 \
  -H "Content-Type: application/json" \
  -d '{"asana GID": "1209020289079877", "status": "Phase3", "asana project name": "My Project Name"}'
```

## Testing with Python

```python
import requests

# Phase 1
response = requests.post(
    "http://localhost:8002",
    json={
        "asana GID": "1209020289079877",
        "status": "Phase1",
        "asana project name": "My Project Name"
    }
)
print(f"Status: {response.status_code}")

# Phase 2
response = requests.post(
    "http://localhost:8002",
    json={
        "asana GID": "1209020289079877",
        "status": "Phase2",
        "asana project name": "My Project Name"
    }
)
print(f"Status: {response.status_code}")

# Phase 3
response = requests.post(
    "http://localhost:8002",
    json={
        "asana GID": "1209020289079877",
        "status": "Phase3",
        "asana project name": "My Project Name"
    }
)
print(f"Status: {response.status_code}")
```

## Example Server Endpoint (Flask)

Here's a simple Flask server example that could receive these requests:

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['POST'])
def receive_status():
    data = request.json
    asana_gid = data.get('asana GID')
    status = data.get('status')
    project_name = data.get('asana project name')
    
    print(f"Received update: Project {asana_gid} ({project_name}) - {status}")
    
    # Store in database, update GUI, etc.
    # Your monitoring logic here
    
    return jsonify({"received": True}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8002, debug=True)
```

## Example Server Endpoint (FastAPI)

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class StatusUpdate(BaseModel):
    asana_GID: str  # Note: FastAPI converts spaces to underscores
    status: str
    asana_project_name: str  # Note: FastAPI converts spaces to underscores

@app.post("/")
async def receive_status(update: StatusUpdate):
    print(f"Received update: Project {update.asana_GID} ({update.asana_project_name}) - {update.status}")
    
    # Your monitoring logic here
    
    return {"received": True}
```

## Request Sequence Example

When you run:
```bash
python main.py 1209020289079877
```

Your server will receive these requests in sequence:

1. **Phase 1** (Export starts)
   ```json
   {
     "asana GID": "1209020289079877",
     "status": "Phase1",
     "asana project name": "My Project Name"
   }
   ```

2. **Phase 2** (Transform starts)
   ```json
   {
     "asana GID": "1209020289079877",
     "status": "Phase2",
     "asana project name": "My Project Name"
   }
   ```

3. **Phase 3** (Import starts)
   ```json
   {
     "asana GID": "1209020289079877",
     "status": "Phase3",
     "asana project name": "My Project Name"
   }
   ```

## Notes

- The `asana GID` field contains the project GID as a string
- The `asana project name` field contains the project name (always included)
- The `status` field will be exactly: `"Phase1"`, `"Phase2"`, or `"Phase3"`
- Requests are sent synchronously but with a 2-second timeout
- If the server is unavailable, the migration continues (errors are logged at debug level)
- Each project migration sends 3 requests (one per phase)
- The project name is retrieved from Asana after export, so it's always the actual project name

