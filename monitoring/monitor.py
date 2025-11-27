#!/usr/bin/env python3
"""
Migration Monitoring System
Receives status updates from migration scripts and displays them in a web dashboard
"""
import csv
import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import threading
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# CSV file path
CSV_FILE = os.path.join(os.path.dirname(__file__), 'migration_status.csv')

# In-memory storage for real-time updates (project GID -> latest status)
project_status = {}

# Lock for thread-safe CSV writing
csv_lock = threading.Lock()


def ensure_csv_header():
    """Ensure CSV file has proper headers"""
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Asana GID', 'Project Name', 'Status'])


def load_from_csv():
    """Load latest status for each project from CSV file"""
    if not os.path.exists(CSV_FILE):
        return
    
    try:
        # Dictionary to track latest entry for each GID
        latest_entries = {}
        
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                gid = row.get('Asana GID', '').strip()
                project_name = row.get('Project Name', 'Unknown Project').strip()
                status = row.get('Status', '').strip()
                timestamp_str = row.get('Timestamp', '').strip()
                
                if gid and status:
                    # Parse timestamp
                    try:
                        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        timestamp = dt.isoformat()
                    except:
                        dt = datetime.now()
                        timestamp = dt.isoformat()
                    
                    # Keep track of latest entry for each GID
                    if gid not in latest_entries:
                        latest_entries[gid] = {
                            'gid': gid,
                            'project_name': project_name,
                            'status': status,
                            'timestamp': timestamp,
                            'datetime': dt
                        }
                    else:
                        # Compare timestamps and keep the latest
                        if dt > latest_entries[gid]['datetime']:
                            latest_entries[gid] = {
                                'gid': gid,
                                'project_name': project_name,
                                'status': status,
                                'timestamp': timestamp,
                                'datetime': dt
                            }
        
        # Convert to project_status format (remove datetime field)
        for gid, entry in latest_entries.items():
            project_status[gid] = {
                'gid': entry['gid'],
                'project_name': entry['project_name'],
                'status': entry['status'],
                'timestamp': entry['timestamp']
            }
        
        print(f"✓ Loaded {len(project_status)} projects from CSV")
    except Exception as e:
        print(f"⚠ Warning: Could not load data from CSV: {e}")
        import traceback
        traceback.print_exc()


def save_to_csv(gid, project_name, status):
    """Save status update to CSV file - updates existing row if GID exists, otherwise adds new row"""
    with csv_lock:
        ensure_csv_header()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Read all existing rows
        rows = []
        gid_found = False
        
        if os.path.exists(CSV_FILE):
            with open(CSV_FILE, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)  # Read header
                if header:
                    rows.append(header)
                
                # Read all data rows, skip any duplicates of the same GID
                for row in reader:
                    if len(row) >= 2 and row[1] == str(gid):  # Check if GID matches (column index 1)
                        # Skip old row with same GID (we'll add updated one)
                        gid_found = True
                        continue
                    else:
                        # Keep existing row (different GID)
                        rows.append(row)
        
        # Add/update row for this GID
        rows.append([timestamp, gid, project_name, status])
        
        # Write all rows back to file
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)


@app.route('/', methods=['GET'])
def dashboard():
    """Serve the monitoring dashboard"""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/status', methods=['GET', 'POST'])
def receive_status():
    """Receive status updates from migration scripts"""
    if request.method == 'GET':
        return jsonify({
            "message": "This endpoint only accepts POST requests",
            "usage": "POST /api/status with JSON body containing 'asana GID', 'status', and 'asana project name'"
        }), 405
    
    try:
        data = request.json
        gid = data.get('asana GID')
        status = data.get('status')
        project_name = data.get('asana project name', 'Unknown Project')
        
        if not gid or not status:
            return jsonify({"error": "Missing required fields: 'asana GID' and 'status'"}), 400
        
        # Update in-memory status
        project_status[gid] = {
            'gid': gid,
            'project_name': project_name,
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save to CSV
        save_to_csv(gid, project_name, status)
        
        print(f"✓ Status update received: {gid} ({project_name}) - {status}")
        print(f"  Current projects in memory: {len(project_status)}")
        print(f"  CSV file: {CSV_FILE}")
        
        return jsonify({
            "received": True,
            "gid": gid,
            "status": status,
            "project_name": project_name
        }), 200
        
    except Exception as e:
        print(f"✗ Error processing status update: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Get all project statuses for the dashboard"""
    # Convert to list format for frontend
    projects = list(project_status.values())
    return jsonify({"projects": projects})


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "projects_tracked": len(project_status)}), 200


@app.route('/api/debug', methods=['GET'])
def debug():
    """Debug endpoint to check server state"""
    csv_exists = os.path.exists(CSV_FILE)
    csv_size = os.path.getsize(CSV_FILE) if csv_exists else 0
    return jsonify({
        "project_status_count": len(project_status),
        "projects": list(project_status.values()),
        "csv_file": CSV_FILE,
        "csv_exists": csv_exists,
        "csv_size": csv_size
    }), 200


# HTML Dashboard Template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Migration Monitoring Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
            text-align: center;
        }
        
        .header h1 {
            color: #333;
            margin-bottom: 10px;
        }
        
        .header .subtitle {
            color: #666;
            font-size: 14px;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        
        .stat-card .number {
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-card .label {
            color: #666;
            margin-top: 5px;
            font-size: 14px;
        }
        
        .dashboard {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .dashboard-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .dashboard-header h2 {
            color: #333;
        }
        
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }
        
        .refresh-btn:hover {
            background: #5568d3;
        }
        
        .auto-refresh {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .auto-refresh input[type="checkbox"] {
            width: 20px;
            height: 20px;
            cursor: pointer;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        thead {
            background: #f8f9fa;
        }
        
        th, td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }
        
        th {
            font-weight: 600;
            color: #333;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 0.5px;
        }
        
        tbody tr:hover {
            background: #f8f9fa;
        }
        
        .status-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .status-phase1 {
            background: #fee;
            color: #c33;
            border: 2px solid #c33;
        }
        
        .status-phase2 {
            background: #ffebcd;
            color: #b8860b;
            border: 2px solid #b8860b;
        }
        
        .status-phase3 {
            background: #e6ffe6;
            color: #2d5a2d;
            border: 2px solid #2d5a2d;
        }
        
        .status-complete {
            background: #e6f3ff;
            color: #0066cc;
            border: 2px solid #0066cc;
        }
        
        .gid {
            font-family: 'Courier New', monospace;
            font-size: 13px;
            color: #667eea;
            font-weight: 600;
        }
        
        .project-name {
            color: #333;
            font-weight: 500;
        }
        
        .timestamp {
            color: #666;
            font-size: 12px;
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }
        
        .empty-state svg {
            width: 100px;
            height: 100px;
            margin-bottom: 20px;
            opacity: 0.3;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #667eea;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Migration Monitoring Dashboard</h1>
            <div class="subtitle">Real-time tracking of Asana to Scoro migration progress</div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="number" id="total-projects">0</div>
                <div class="label">Total Projects</div>
            </div>
            <div class="stat-card">
                <div class="number" id="phase1-count">0</div>
                <div class="label">Phase 1 (Export)</div>
            </div>
            <div class="stat-card">
                <div class="number" id="phase2-count">0</div>
                <div class="label">Phase 2 (Transform)</div>
            </div>
            <div class="stat-card">
                <div class="number" id="phase3-count">0</div>
                <div class="label">Phase 3 (Import)</div>
            </div>
            <div class="stat-card">
                <div class="number" id="complete-count">0</div>
                <div class="label">Completed</div>
            </div>
        </div>
        
        <div class="dashboard">
            <div class="dashboard-header">
                <h2>Project Status</h2>
                <div class="auto-refresh">
                    <label>
                        <input type="checkbox" id="auto-refresh" checked>
                        Auto-refresh (5s)
                    </label>
                    <button class="refresh-btn" onclick="loadProjects()">🔄 Refresh</button>
                </div>
            </div>
            
            <div id="loading" class="loading">Loading...</div>
            <div id="table-container" style="display: none;">
                <table>
                    <thead>
                        <tr>
                            <th>Asana GID</th>
                            <th>Project Name</th>
                            <th>Status</th>
                            <th>Last Update</th>
                        </tr>
                    </thead>
                    <tbody id="projects-table">
                    </tbody>
                </table>
            </div>
            <div id="empty-state" class="empty-state" style="display: none;">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                <h3>No projects tracked yet</h3>
                <p>Start a migration to see status updates here</p>
            </div>
        </div>
    </div>
    
    <script>
        let autoRefreshInterval = null;
        
        function formatTimestamp(isoString) {
            if (!isoString) return 'N/A';
            const date = new Date(isoString);
            return date.toLocaleString();
        }
        
        function getStatusClass(status) {
            if (status === 'Phase1') return 'status-phase1';
            if (status === 'Phase2') return 'status-phase2';
            if (status === 'Phase3') return 'status-phase3';
            if (status === 'Complete') return 'status-complete';
            return 'status-phase1';
        }
        
        function updateStats(projects) {
            const total = projects.length;
            const phase1 = projects.filter(p => p.status === 'Phase1').length;
            const phase2 = projects.filter(p => p.status === 'Phase2').length;
            const phase3 = projects.filter(p => p.status === 'Phase3').length;
            const complete = projects.filter(p => p.status === 'Complete').length;
            
            document.getElementById('total-projects').textContent = total;
            document.getElementById('phase1-count').textContent = phase1;
            document.getElementById('phase2-count').textContent = phase2;
            document.getElementById('phase3-count').textContent = phase3;
            document.getElementById('complete-count').textContent = complete;
        }
        
        function renderTable(projects) {
            const tbody = document.getElementById('projects-table');
            const loading = document.getElementById('loading');
            const tableContainer = document.getElementById('table-container');
            const emptyState = document.getElementById('empty-state');
            
            if (projects.length === 0) {
                loading.style.display = 'none';
                tableContainer.style.display = 'none';
                emptyState.style.display = 'block';
                return;
            }
            
            loading.style.display = 'none';
            emptyState.style.display = 'none';
            tableContainer.style.display = 'block';
            
            // Sort by timestamp (newest first)
            projects.sort((a, b) => {
                const timeA = new Date(a.timestamp || 0);
                const timeB = new Date(b.timestamp || 0);
                return timeB - timeA;
            });
            
            tbody.innerHTML = projects.map(project => `
                <tr>
                    <td><span class="gid">${project.gid}</span></td>
                    <td><span class="project-name">${project.project_name || 'Unknown Project'}</span></td>
                    <td><span class="status-badge ${getStatusClass(project.status)}">${project.status}</span></td>
                    <td><span class="timestamp">${formatTimestamp(project.timestamp)}</span></td>
                </tr>
            `).join('');
            
            updateStats(projects);
        }
        
        async function loadProjects() {
            try {
                const response = await fetch('/api/projects');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                console.log('Loaded projects:', data.projects.length);
                renderTable(data.projects);
            } catch (error) {
                console.error('Error loading projects:', error);
                const loading = document.getElementById('loading');
                if (loading) {
                    loading.textContent = 'Error loading data: ' + error.message;
                    loading.style.color = '#c33';
                }
            }
        }
        
        function setupAutoRefresh() {
            const checkbox = document.getElementById('auto-refresh');
            
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    startAutoRefresh();
                } else {
                    stopAutoRefresh();
                }
            });
            
            if (checkbox.checked) {
                startAutoRefresh();
            }
        }
        
        function startAutoRefresh() {
            stopAutoRefresh();
            autoRefreshInterval = setInterval(loadProjects, 5000);
        }
        
        function stopAutoRefresh() {
            if (autoRefreshInterval) {
                clearInterval(autoRefreshInterval);
                autoRefreshInterval = null;
            }
        }
        
        // Initialize
        loadProjects();
        setupAutoRefresh();
    </script>
</body>
</html>
"""


if __name__ == '__main__':
    # Ensure CSV file exists
    ensure_csv_header()
    
    # Load existing data from CSV
    load_from_csv()
    
    print("=" * 60)
    print("Migration Monitoring System")
    print("=" * 60)
    print(f"Dashboard: http://localhost:8002")
    print(f"API Endpoint: http://localhost:8002/api/status")
    print(f"CSV File: {CSV_FILE}")
    print(f"Projects loaded: {len(project_status)}")
    print("=" * 60)
    print("\nStarting server...")
    
    app.run(host='0.0.0.0', port=8002, debug=True)
