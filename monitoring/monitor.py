"""
Migration Monitoring System
Receives status updates from migration scripts and displays them in a web dashboard
"""
import csv
import json
import os
import subprocess
import sys
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import threading

app = Flask(__name__)
CORS(app)

# In-memory storage for project statuses
projects = {}
projects_lock = threading.Lock()
running_migrations = {}  # Track running migrations: {gid: process}
running_migrations_lock = threading.Lock()

# File paths (relative to script location)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
PROJECT_LIST_CSV = os.path.join(PROJECT_ROOT, "migrated_project_list.csv")
CSV_FILE = os.path.join(SCRIPT_DIR, "migration_status.csv")

# Load project list from CSV
def load_project_list():
    """Load project list from migrated_project_list.csv"""
    project_list = []
    try:
        if os.path.exists(PROJECT_LIST_CSV):
            with open(PROJECT_LIST_CSV, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    gid = row.get('gid', '').strip()
                    name = row.get('name', '').strip()
                    if gid:
                        project_list.append({'gid': gid, 'name': name})
        else:
            print(f"Warning: Project list CSV not found at {PROJECT_LIST_CSV}")
    except Exception as e:
        print(f"Error loading project list: {e}")
    return project_list

# Initialize projects from CSV
def init_projects():
    """Initialize projects from CSV file"""
    project_list = load_project_list()
    with projects_lock:
        for project in project_list:
            gid = project['gid']
            if gid not in projects:
                projects[gid] = {
                    'gid': gid,
                    'name': project['name'],
                    'status': 'Not Started',
                    'last_update': datetime.now().isoformat()
                }

# Ensure CSV file exists with headers
def init_csv():
    """Initialize CSV file with headers if it doesn't exist"""
    if not os.path.exists(CSV_FILE):
        os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Asana GID', 'Project Name', 'Status'])

def save_to_csv(gid, project_name, status):
    """Save status update to CSV file"""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, gid, project_name, status])
    except Exception as e:
        print(f"Error saving to CSV: {e}")

def get_status_color(status):
    """Get color for status"""
    colors = {
        'Not Started': '#6c757d',  # Gray
        'Running': '#007bff',      # Blue
        'Phase1': '#dc3545',       # Red
        'Phase2': '#ffc107',        # Yellow
        'Phase3': '#28a745',        # Green
        'Completed': '#28a745',     # Green
        'Failed': '#dc3545'         # Red
    }
    return colors.get(status, '#6c757d')  # Default gray

def run_migration(gid):
    """Run migration script for a project"""
    try:
        # Run the migration script
        cmd = [sys.executable, 'main.py', gid]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=PROJECT_ROOT  # Use cwd parameter instead of os.chdir
        )
        
        # Store the process
        with running_migrations_lock:
            running_migrations[gid] = process
        
        # Update status to Running
        with projects_lock:
            if gid in projects:
                projects[gid]['status'] = 'Running'
                projects[gid]['last_update'] = datetime.now().isoformat()
        
        # Monitor process in background thread
        def monitor_process():
            try:
                stdout, stderr = process.communicate()
                return_code = process.returncode
                
                # Remove from running migrations
                with running_migrations_lock:
                    running_migrations.pop(gid, None)
                
                # Update status based on return code
                with projects_lock:
                    if gid in projects:
                        if return_code == 0:
                            # Check if we received Phase3 status (completed)
                            if projects[gid]['status'] == 'Phase3':
                                projects[gid]['status'] = 'Completed'
                            else:
                                projects[gid]['status'] = 'Completed'
                        else:
                            projects[gid]['status'] = 'Failed'
                        projects[gid]['last_update'] = datetime.now().isoformat()
                        save_to_csv(gid, projects[gid]['name'], projects[gid]['status'])
            except Exception as e:
                print(f"Error monitoring process for {gid}: {e}")
                with running_migrations_lock:
                    running_migrations.pop(gid, None)
                with projects_lock:
                    if gid in projects:
                        projects[gid]['status'] = 'Failed'
                        projects[gid]['last_update'] = datetime.now().isoformat()
        
        # Start monitoring thread
        thread = threading.Thread(target=monitor_process, daemon=True)
        thread.start()
        
        return True
    except Exception as e:
        print(f"Error running migration for {gid}: {e}")
        with running_migrations_lock:
            running_migrations.pop(gid, None)
        with projects_lock:
            if gid in projects:
                projects[gid]['status'] = 'Failed'
                projects[gid]['last_update'] = datetime.now().isoformat()
        return False

@app.route('/', methods=['GET'])
def dashboard():
    """Serve the monitoring dashboard"""
    html_template = """
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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
            text-align: center;
        }
        
        .header h1 {
            color: #333;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #666;
            font-size: 1.1em;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        
        .stat-card h3 {
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        
        .stat-card .value {
            color: #333;
            font-size: 2.5em;
            font-weight: bold;
        }
        
        .projects-container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .projects-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }
        
        .projects-header h2 {
            color: #333;
            font-size: 1.8em;
        }
        
        .refresh-info {
            color: #666;
            font-size: 0.9em;
        }
        
        .projects-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .projects-table thead {
            background: #f8f9fa;
        }
        
        .projects-table th {
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #dee2e6;
        }
        
        .projects-table td {
            padding: 15px;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .projects-table tbody tr:hover {
            background: #f8f9fa;
        }
        
        .status-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9em;
            color: white;
            text-align: center;
            min-width: 100px;
        }
        
        .status-not-started {
            background-color: #6c757d;
        }
        
        .status-running {
            background-color: #007bff;
        }
        
        .status-phase1 {
            background-color: #dc3545;
        }
        
        .status-phase2 {
            background-color: #ffc107;
            color: #333;
        }
        
        .status-phase3 {
            background-color: #28a745;
        }
        
        .status-completed {
            background-color: #28a745;
        }
        
        .status-failed {
            background-color: #dc3545;
        }
        
        .gid-cell {
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #666;
        }
        
        .project-name-cell {
            font-weight: 500;
            color: #333;
        }
        
        .run-button {
            background: #28a745;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: 600;
            font-size: 0.9em;
            transition: background 0.3s;
        }
        
        .run-button:hover:not(:disabled) {
            background: #218838;
        }
        
        .run-button:disabled {
            background: #6c757d;
            cursor: not-allowed;
            opacity: 0.6;
        }
        
        .run-button.running {
            background: #007bff;
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
        
        .empty-state h3 {
            font-size: 1.5em;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Migration Monitoring Dashboard</h1>
            <p>Real-time status tracking for Asana to Scoro migrations</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>Total Projects</h3>
                <div class="value" id="total-projects">0</div>
            </div>
            <div class="stat-card">
                <h3>Not Started</h3>
                <div class="value" id="not-started-count" style="color: #6c757d;">0</div>
            </div>
            <div class="stat-card">
                <h3>Running</h3>
                <div class="value" id="running-count" style="color: #007bff;">0</div>
            </div>
            <div class="stat-card">
                <h3>Phase 1 (Export)</h3>
                <div class="value" id="phase1-count" style="color: #dc3545;">0</div>
            </div>
            <div class="stat-card">
                <h3>Phase 2 (Transform)</h3>
                <div class="value" id="phase2-count" style="color: #ffc107;">0</div>
            </div>
            <div class="stat-card">
                <h3>Phase 3 (Import)</h3>
                <div class="value" id="phase3-count" style="color: #28a745;">0</div>
            </div>
            <div class="stat-card">
                <h3>Completed</h3>
                <div class="value" id="completed-count" style="color: #28a745;">0</div>
            </div>
        </div>
        
        <div class="projects-container">
            <div class="projects-header">
                <h2>Project Status</h2>
                <div class="refresh-info">
                    Auto-refreshing every 2 seconds
                </div>
            </div>
            
            <div id="projects-content">
                <div class="empty-state">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="12" y1="8" x2="12" y2="12"/>
                        <line x1="12" y1="16" x2="12.01" y2="16"/>
                    </svg>
                    <h3>Loading projects...</h3>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function updateDashboard() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    updateStats(data);
                    updateProjectsTable(data.all_projects);
                })
                .catch(error => {
                    console.error('Error fetching status:', error);
                });
        }
        
        function updateStats(data) {
            document.getElementById('total-projects').textContent = data.total_projects;
            document.getElementById('not-started-count').textContent = data.not_started_count || 0;
            document.getElementById('running-count').textContent = data.running_count || 0;
            document.getElementById('phase1-count').textContent = data.phase1_count || 0;
            document.getElementById('phase2-count').textContent = data.phase2_count || 0;
            document.getElementById('phase3-count').textContent = data.phase3_count || 0;
            document.getElementById('completed-count').textContent = data.completed_count || 0;
        }
        
        function runMigration(gid) {
            const button = event.target;
            const originalText = button.textContent;
            button.disabled = true;
            button.textContent = 'Starting...';
            button.classList.add('running');
            
            fetch('/api/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ gid: gid })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    button.textContent = 'Running...';
                } else {
                    button.disabled = false;
                    button.textContent = originalText;
                    button.classList.remove('running');
                    alert('Error: ' + (data.error || 'Failed to start migration'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                button.disabled = false;
                button.textContent = originalText;
                button.classList.remove('running');
                alert('Error starting migration');
            });
        }
        
        function updateProjectsTable(allProjects) {
            const container = document.getElementById('projects-content');
            
            if (!allProjects || allProjects.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"/>
                            <line x1="12" y1="8" x2="12" y2="12"/>
                            <line x1="12" y1="16" x2="12.01" y2="16"/>
                        </svg>
                        <h3>No projects found</h3>
                    </div>
                `;
                return;
            }
            
            let html = `
                <table class="projects-table">
                    <thead>
                        <tr>
                            <th>Action</th>
                            <th>Asana GID</th>
                            <th>Project Name</th>
                            <th>Status</th>
                            <th>Last Update</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            allProjects.forEach(project => {
                const status = project.status || 'Not Started';
                const statusClass = `status-${status.toLowerCase().replace(/\s+/g, '-')}`;
                const lastUpdate = project.last_update ? new Date(project.last_update).toLocaleString() : 'N/A';
                
                // Escape HTML to prevent XSS
                const escapedGid = (project.gid || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
                const escapedName = (project.name || 'N/A').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
                const escapedStatus = status.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
                
                const isRunning = status === 'Running' || status === 'Phase1' || status === 'Phase2' || status === 'Phase3';
                const isCompleted = status === 'Completed';
                const isFailed = status === 'Failed';
                
                const buttonClass = isRunning ? 'run-button running' : 'run-button';
                html += `
                    <tr>
                        <td>
                            <button class="${buttonClass}" 
                                    onclick="runMigration('${escapedGid}')" 
                                    ${isRunning || isCompleted ? 'disabled' : ''}>
                                ${isRunning ? 'Running...' : isCompleted ? 'Completed' : isFailed ? 'Failed - Retry' : 'Run'}
                            </button>
                        </td>
                        <td class="gid-cell">${escapedGid}</td>
                        <td class="project-name-cell">${escapedName}</td>
                        <td>
                            <span class="status-badge ${statusClass}">${escapedStatus}</span>
                        </td>
                        <td>${lastUpdate}</td>
                    </tr>
                `;
            });
            
            html += `
                    </tbody>
                </table>
            `;
            
            container.innerHTML = html;
        }
        
        // Initial load
        updateDashboard();
        
        // Auto-refresh every 2 seconds
        setInterval(updateDashboard, 2000);
    </script>
</body>
</html>
    """
    return render_template_string(html_template)

@app.route('/', methods=['POST'])
def receive_status():
    """Receive status updates from migration scripts"""
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        gid = data.get('asana GID')
        status = data.get('status')
        project_name = data.get('asana project name', 'Unknown Project')
        
        if not gid or not status:
            return jsonify({"error": "Missing required fields: 'asana GID' and 'status'"}), 400
        
        # Update in-memory storage
        with projects_lock:
            if gid not in projects:
                projects[gid] = {
                    'gid': gid,
                    'name': project_name,
                    'status': status,
                    'last_update': datetime.now().isoformat()
                }
            else:
                projects[gid]['status'] = status
                projects[gid]['name'] = project_name  # Update name if changed
                projects[gid]['last_update'] = datetime.now().isoformat()
        
        # Save to CSV
        save_to_csv(gid, project_name, status)
        
        print(f"✓ Status update received: {project_name} ({gid}) - {status}")
        
        return jsonify({
            "received": True,
            "gid": gid,
            "status": status,
            "project_name": project_name
        }), 200
        
    except Exception as e:
        print(f"Error processing status update: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/run', methods=['POST'])
def run_migration_api():
    """API endpoint to trigger migration"""
    try:
        data = request.json
        gid = data.get('gid')
        
        if not gid:
            return jsonify({"error": "Missing 'gid' field"}), 400
        
        # Check if already running
        with running_migrations_lock:
            if gid in running_migrations:
                process = running_migrations[gid]
                if process.poll() is None:  # Still running
                    return jsonify({"error": "Migration already running"}), 400
        
        # Check if project exists in the list
        project_list = load_project_list()
        project_exists = any(p['gid'] == gid for p in project_list)
        if not project_exists:
            return jsonify({"error": "Project not found in project list"}), 404
        
        # Initialize project if not already in projects dict
        with projects_lock:
            if gid not in projects:
                project_info = next((p for p in project_list if p['gid'] == gid), None)
                if project_info:
                    projects[gid] = {
                        'gid': gid,
                        'name': project_info['name'],
                        'status': 'Not Started',
                        'last_update': datetime.now().isoformat()
                    }
        
        # Start migration
        success = run_migration(gid)
        
        if success:
            return jsonify({"success": True, "message": "Migration started"}), 200
        else:
            return jsonify({"error": "Failed to start migration"}), 500
            
    except Exception as e:
        print(f"Error in run_migration_api: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current status of all projects"""
    with projects_lock:
        projects_copy = projects.copy()
    
    # Get all projects (from CSV list)
    all_projects_list = load_project_list()
    all_projects = []
    
    for project in all_projects_list:
        gid = project['gid']
        if gid in projects_copy:
            all_projects.append(projects_copy[gid])
        else:
            # Project not yet initialized
            all_projects.append({
                'gid': gid,
                'name': project['name'],
                'status': 'Not Started',
                'last_update': None
            })
    
    # Calculate statistics
    total = len(all_projects)
    not_started = sum(1 for p in all_projects if p['status'] == 'Not Started')
    running = sum(1 for p in all_projects if p['status'] == 'Running')
    phase1 = sum(1 for p in all_projects if p['status'] == 'Phase1')
    phase2 = sum(1 for p in all_projects if p['status'] == 'Phase2')
    phase3 = sum(1 for p in all_projects if p['status'] == 'Phase3')
    completed = sum(1 for p in all_projects if p['status'] == 'Completed')
    failed = sum(1 for p in all_projects if p['status'] == 'Failed')
    
    return jsonify({
        "total_projects": total,
        "not_started_count": not_started,
        "running_count": running,
        "phase1_count": phase1,
        "phase2_count": phase2,
        "phase3_count": phase3,
        "completed_count": completed,
        "failed_count": failed,
        "all_projects": all_projects
    })

@app.route('/api/export', methods=['GET'])
def export_csv():
    """Export current status as CSV"""
    from io import StringIO
    
    with projects_lock:
        projects_copy = projects.copy()
    
    # Create CSV using csv module for proper escaping
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Asana GID', 'Project Name', 'Status', 'Last Update'])
    
    # Write data rows
    all_projects_list = load_project_list()
    for project in all_projects_list:
        gid = project['gid']
        if gid in projects_copy:
            p = projects_copy[gid]
            writer.writerow([
                p['gid'],
                p['name'],
                p['status'],
                p['last_update']
            ])
        else:
            writer.writerow([
                gid,
                project['name'],
                'Not Started',
                ''
            ])
    
    csv_content = output.getvalue()
    output.close()
    
    return csv_content, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=migration_status_export.csv'
    }

if __name__ == '__main__':
    # Initialize CSV file
    init_csv()
    
    # Initialize projects from CSV
    init_projects()
    
    print("=" * 60)
    print("Migration Monitoring System")
    print("=" * 60)
    print(f"Dashboard: http://localhost:8002")
    print(f"API Endpoint: http://localhost:8002/ (POST)")
    print(f"Run Migration: http://localhost:8002/api/run (POST)")
    print(f"Status API: http://localhost:8002/api/status (GET)")
    print(f"CSV Export: http://localhost:8002/api/export (GET)")
    print(f"CSV File: {CSV_FILE}")
    print(f"Project List: {PROJECT_LIST_CSV}")
    print(f"Loaded {len(projects)} projects from CSV")
    print("=" * 60)
    print("\nServer starting...\n")
    
    # Run Flask app
    app.run(host='0.0.0.0', port=8002, debug=True, threaded=True)
