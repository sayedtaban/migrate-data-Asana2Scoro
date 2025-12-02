"""
Check if projects from migration_status.csv exist in Scoro
Returns list of project names that don't exist in Scoro
"""
import csv
import os
import sys
import requests
from typing import List, Set

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.scoro_client import ScoroClient


def read_project_names_from_csv(csv_path: str) -> Set[str]:
    """
    Read project names from the migration_status.csv file
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        Set of unique project names
    """
    project_names = set()
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found: {csv_path}")
        return project_names
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                project_name = row.get('Project Name', '').strip()
                if project_name:  # Skip empty project names
                    project_names.add(project_name)
        
        print(f"Read {len(project_names)} unique project names from CSV")
        return project_names
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return project_names


def get_scoro_project_names(scoro_client: ScoroClient) -> Set[str]:
    """
    Get all project names from Scoro with pagination support
    
    Args:
        scoro_client: Initialized ScoroClient instance
        
    Returns:
        Set of project names in Scoro
    """
    scoro_project_names = set()
    
    try:
        print("Fetching projects from Scoro (with pagination)...")
        
        # Get API credentials from client
        api_key = scoro_client.api_key
        company_name = scoro_client.company_name
        base_url = scoro_client.base_url
        
        endpoint = 'projects/list'
        all_projects = []
        page = 1
        max_pages = 1000  # Safety limit
        per_page = 100
        
        # Base request body
        base_request = {
            "lang": "eng",
            "company_account_id": company_name,
            "apiKey": api_key,
            "request": {}
        }
        
        # Fetch all pages
        while page <= max_pages:
            # Add pagination parameters - always include page and per_page
            request_body = {**base_request}
            request_body["page"] = str(page)
            request_body["per_page"] = str(per_page)
            
            try:
                headers = {'Content-Type': 'application/json'}
                response = requests.post(
                    f'{base_url}{endpoint}',
                    headers=headers,
                    json=request_body
                )
                response.raise_for_status()
                data = response.json()
                
                # Check for errors
                if isinstance(data, dict) and data.get('status') == 'ERROR':
                    error_msg = data.get('messages', {}).get('error', ['Unknown error'])
                    if page > 1:
                        # No more pages
                        break
                    else:
                        print(f"Error from Scoro API: {error_msg}")
                        return scoro_project_names
                
                # Extract projects from response
                page_projects = []
                if isinstance(data, list):
                    page_projects = data
                elif isinstance(data, dict):
                    if 'data' in data and isinstance(data['data'], list):
                        page_projects = data['data']
                    elif 'projects' in data and isinstance(data['projects'], list):
                        page_projects = data['projects']
                
                # Only stop if we get an empty result (no more projects)
                if not page_projects:
                    print(f"  No more projects on page {page}, stopping pagination")
                    break
                
                all_projects.extend(page_projects)
                print(f"  Retrieved {len(page_projects)} projects from page {page} (total: {len(all_projects)})")
                
                # Always try the next page - only stop when we get empty results
                # This ensures we get all projects even if the last page has exactly per_page items
                page += 1
                
            except requests.exceptions.RequestException as e:
                if page == 1:
                    print(f"Error fetching projects from Scoro: {e}")
                    return scoro_project_names
                else:
                    # On later pages, if we get an error, it might mean no more pages
                    # But try to continue - only stop if we've already gotten some projects
                    print(f"  Warning: Error on page {page}: {e}")
                    if len(all_projects) > 0:
                        print(f"  Stopping pagination after retrieving {len(all_projects)} projects")
                        break
                    else:
                        print(f"  No projects retrieved yet, stopping")
                        return scoro_project_names
        
        # Extract project names
        for project in all_projects:
            # Scoro projects can have 'project_name' or 'name' field
            project_name = project.get('project_name') or project.get('name', '')
            if project_name:
                scoro_project_names.add(project_name.strip())
        
        print(f"Found {len(scoro_project_names)} unique projects in Scoro (from {len(all_projects)} total)")
        return scoro_project_names
    except Exception as e:
        print(f"Error fetching projects from Scoro: {e}")
        return scoro_project_names


def find_non_existent_projects(csv_path: str = None) -> List[str]:
    """
    Check which projects from CSV don't exist in Scoro
    
    Args:
        csv_path: Optional path to CSV file. If None, uses default path
        
    Returns:
        List of project names that don't exist in Scoro
    """
    # Default CSV path
    if csv_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(os.path.dirname(script_dir), 'monitoring', 'migration_status.csv')
    
    # Read project names from CSV
    csv_project_names = read_project_names_from_csv(csv_path)
    
    if not csv_project_names:
        print("Warning: No project names found in CSV file")
        return []
    
    # Initialize Scoro client
    try:
        scoro_client = ScoroClient()
    except Exception as e:
        print(f"Error: Failed to initialize Scoro client: {e}")
        return []
    
    # Get project names from Scoro
    scoro_project_names = get_scoro_project_names(scoro_client)
    
    if not scoro_project_names:
        print("Warning: No projects found in Scoro. Returning all CSV project names.")
        return sorted(list(csv_project_names))
    
    # Find projects that don't exist in Scoro
    non_existent = csv_project_names - scoro_project_names
    
    print(f"Found {len(non_existent)} projects that don't exist in Scoro")
    return sorted(list(non_existent))


def main():
    """Main function to run the check"""
    non_existent_projects = find_non_existent_projects()
    
    if non_existent_projects:
        print(f"\n{'='*80}")
        print(f"PROJECTS NOT FOUND IN SCORO ({len(non_existent_projects)} projects):")
        print(f"{'='*80}\n")
        for idx, project_name in enumerate(non_existent_projects, 1):
            print(f"{idx:3d}. {project_name}")
        print(f"\n{'='*80}")
    else:
        print("\n✓ All projects from CSV exist in Scoro!")
    
    return non_existent_projects


if __name__ == "__main__":
    main()
