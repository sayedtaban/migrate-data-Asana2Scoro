#!/usr/bin/env python3
"""
Test script to send sample requests to the monitoring server
"""
import requests
import time
import sys

def test_monitoring_server(base_url="http://localhost:8002", project_gid="1209020289079877", project_name="Sample Project"):
    """
    Send test requests to the monitoring server
    
    Args:
        base_url: URL of the monitoring server
        project_gid: Sample Asana project GID to use
        project_name: Sample Asana project name to use
    """
    print(f"Testing monitoring server at {base_url}")
    print(f"Using project GID: {project_gid}")
    print(f"Using project name: {project_name}\n")
    
    phases = ["Phase1", "Phase2", "Phase3"]
    
    for phase in phases:
        payload = {
            "asana GID": str(project_gid),
            "status": phase,
            "asana project name": project_name
        }
        
        try:
            print(f"Sending {phase}...")
            response = requests.post(base_url, json=payload, timeout=2)
            print(f"  ✓ Status: {response.status_code}")
            if response.text:
                print(f"  Response: {response.text}")
        except requests.exceptions.ConnectionError:
            print(f"  ✗ Connection failed - Is the server running at {base_url}?")
            return False
        except requests.exceptions.Timeout:
            print(f"  ✗ Request timed out")
            return False
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False
        
        # Small delay between requests
        time.sleep(0.5)
    
    print("\n✓ All test requests sent successfully!")
    return True

if __name__ == "__main__":
    # Allow custom URL, GID, and name via command line
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8002"
    gid = sys.argv[2] if len(sys.argv) > 2 else "1209020289079877"
    name = sys.argv[3] if len(sys.argv) > 3 else "Sample Project"
    
    success = test_monitoring_server(url, gid, name)
    sys.exit(0 if success else 1)

