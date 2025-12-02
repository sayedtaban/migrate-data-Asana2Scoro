# This script will assign the correct company to the tasks in the project

import json
import sys
from typing import Dict, List, Optional

from clients.scoro_client import ScoroClient
from transformers.field_extractors import extract_custom_field_value
from utils import logger


def load_asana_data(json_file_path: str) -> Dict:
    """Load Asana export JSON file"""
    try:
        logger.info(f"Loading Asana data from: {json_file_path}")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded Asana data: Project '{data.get('project', {}).get('name', 'Unknown')}' with {len(data.get('tasks', []))} tasks")
        return data
    except Exception as e:
        logger.error(f"Error loading Asana JSON file: {e}")
        raise


def extract_company_name_from_task(task: Dict) -> Optional[str]:
    """Extract company name from task custom fields (C-Name or Company Name)"""
    company_name = extract_custom_field_value(task, 'C-Name') or extract_custom_field_value(task, 'Company Name')
    return company_name


def extract_project_company_name(asana_data: Dict) -> Optional[str]:
    """Extract company name from project - use project name for client projects"""
    project = asana_data.get('project', {})
    project_name = project.get('name', '')
    
    # Check if it's a client project (project name is typically the company name)
    # Also check tasks for C-Name custom field
    tasks = asana_data.get('tasks', [])
    company_list = []
    
    for task in tasks:  # Check first 10 tasks
        company_from_task = extract_company_name_from_task(task)
        if company_from_task:
            company_list.append(company_from_task)
    
    # If all tasks have the same company name, use it
    if len(set(company_list)) == 1 and company_list[0]:
        return company_list[0]
    
    # Otherwise, use project name as company name
    return project_name if project_name else None


def find_scoro_project_by_name(scoro_client: ScoroClient, project_name: str) -> Optional[Dict]:
    """Find a Scoro project by name"""
    try:
        logger.info(f"Searching for Scoro project: '{project_name}'...")
        projects = scoro_client.list_projects()
        
        for project in projects:
            scoro_project_name = project.get('project_name') or project.get('name', '')
            if scoro_project_name.strip() == project_name.strip():
                project_id = project.get('id') or project.get('project_id')
                logger.info(f"  Found Scoro project: '{scoro_project_name}' (ID: {project_id})")
                return project
        
        logger.warning(f"  Scoro project not found: '{project_name}'")
        return None
    except Exception as e:
        logger.error(f"Error finding Scoro project '{project_name}': {e}")
        return None


def find_scoro_task_by_name(scoro_client: ScoroClient, task_name: str, project_id: int) -> Optional[Dict]:
    """Find a Scoro task by name within a project"""
    try:
        tasks = scoro_client.list_tasks(project_id=project_id)
        
        for task in tasks:
            scoro_task_name = task.get('event_name') or task.get('title') or task.get('name', '')
            if scoro_task_name.strip() == task_name.strip():
                task_id = task.get('event_id') or task.get('id') or task.get('task_id')
                logger.debug(f"    Found Scoro task: '{scoro_task_name}' (ID: {task_id})")
                return task
        
        return None
    except Exception as e:
        logger.warning(f"Error finding Scoro task '{task_name}' in project {project_id}: {e}")
        return None


def resolve_company_id(scoro_client: ScoroClient, company_name: str) -> Optional[int]:
    """
    Resolve company name to company_id using the same logic as scoro_importer.py
    Reference: importers/scoro_importer.py:809-840
    """
    if not company_name:
        return None
    
    try:
        logger.info(f"Resolving company: '{company_name}'...")
        
        # Try to find existing company
        company_lookup = scoro_client.find_company_by_name(company_name)
        if company_lookup:
            company_id = (
                company_lookup.get('id') or 
                company_lookup.get('company_id') or 
                company_lookup.get('client_id') or 
                company_lookup.get('contact_id')
            )
            if company_id:
                logger.info(f"  Found company '{company_name}' with ID: {company_id}")
                return company_id
            else:
                logger.warning(f"  Company '{company_name}' found but no ID available")
        else:
            # Create new company if not found
            new_company = scoro_client.get_or_create_company(company_name)
            company_id = (
                new_company.get('id') or 
                new_company.get('company_id') or 
                new_company.get('client_id') or 
                new_company.get('contact_id')
            )
            if company_id:
                logger.info(f"  Created company '{company_name}' with ID: {company_id}")
                return company_id
            else:
                logger.warning(f"  Company '{company_name}' created but no ID available")
        
        return None
    except Exception as e:
        logger.warning(f"Error resolving company '{company_name}': {e}")
        return None


def update_project_company(scoro_client: ScoroClient, project_id: int, company_id: int) -> bool:
    """Update a Scoro project's company_id"""
    try:
        logger.info(f"Updating project {project_id} with company_id: {company_id}")
        project_data = {'company_id': company_id}
        updated_project = scoro_client.create_project(project_data, project_id=project_id)
        logger.info(f"  ✓ Successfully updated project {project_id}")
        return True
    except Exception as e:
        logger.error(f"  ✗ Error updating project {project_id}: {e}")
        return False


def update_task_company(scoro_client: ScoroClient, task_id: int, company_id: int) -> bool:
    """Update a Scoro task's company_id"""
    try:
        logger.debug(f"    Updating task {task_id} with company_id: {company_id}")
        task_data = {'company_id': company_id}
        updated_task = scoro_client.create_task(task_data, task_id=task_id)
        logger.debug(f"    ✓ Successfully updated task {task_id}")
        return True
    except Exception as e:
        logger.warning(f"    ✗ Error updating task {task_id}: {e}")
        return False


def process_project_and_tasks(scoro_client: ScoroClient, asana_data: Dict) -> Dict:
    """
    Process Asana project and tasks to update Scoro company assignments
    
    Returns:
        Dictionary with statistics about the update process
    """
    stats = {
        'projects_found': 0,
        'projects_updated': 0,
        'tasks_processed': 0,
        'tasks_updated': 0,
        'errors': []
    }
    
    # Extract Asana project information
    asana_project = asana_data.get('project', {})
    asana_project_name = asana_project.get('name', '')
    
    if not asana_project_name:
        error_msg = "Asana project name not found"
        logger.error(error_msg)
        stats['errors'].append(error_msg)
        return stats
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing Asana Project: '{asana_project_name}'")
    logger.info(f"{'='*60}\n")
    
    # Extract project company name
    project_company_name = extract_project_company_name(asana_data)
    logger.info(f"Project company name: '{project_company_name}'")
    
    # Find matching Scoro project
    scoro_project = find_scoro_project_by_name(scoro_client, asana_project_name)
    if not scoro_project:
        error_msg = f"Scoro project not found: '{asana_project_name}'"
        logger.error(error_msg)
        stats['errors'].append(error_msg)
        return stats
    
    stats['projects_found'] = 1
    scoro_project_id = scoro_project.get('id') or scoro_project.get('project_id')
    
    # Resolve project company_id
    project_company_id = None
    if project_company_name:
        project_company_id = resolve_company_id(scoro_client, project_company_name)
        if project_company_id:
            # Update project company
            if update_project_company(scoro_client, scoro_project_id, project_company_id):
                stats['projects_updated'] = 1
                logger.info(f"✓ Project company updated successfully\n")
        else:
            logger.warning(f"Could not resolve company for project: '{project_company_name}'")
    
    # Process tasks
    asana_tasks = asana_data.get('tasks', [])
    logger.info(f"Processing {len(asana_tasks)} tasks...")
    
    for idx, asana_task in enumerate(asana_tasks, 1):
        task_name = asana_task.get('name', '')
        if not task_name:
            continue
        
        stats['tasks_processed'] += 1
        
        # Extract company name from task
        task_company_name = extract_company_name_from_task(asana_task)
        
        # Use project company if task doesn't have its own company
        if not task_company_name:
            task_company_name = project_company_name
        
        if not task_company_name:
            logger.debug(f"  Task {idx}/{len(asana_tasks)}: '{task_name}' - No company name found, skipping")
            continue
        
        # Find matching Scoro task
        scoro_task = find_scoro_task_by_name(scoro_client, task_name, scoro_project_id)
        if not scoro_task:
            logger.debug(f"  Task {idx}/{len(asana_tasks)}: '{task_name}' - Scoro task not found, skipping")
            continue
        
        scoro_task_id = scoro_task.get('event_id') or scoro_task.get('id') or scoro_task.get('task_id')
        if not scoro_task_id:
            logger.warning(f"  Task {idx}/{len(asana_tasks)}: '{task_name}' - Scoro task has no ID, skipping")
            continue
        
        # Resolve company_id for task
        # Reference: importers/scoro_importer.py:809-840
        # Check if task's company matches project's company
        if project_company_id and task_company_name == project_company_name:
            # Reuse project company_id
            task_company_id = project_company_id
            logger.debug(f"  Task {idx}/{len(asana_tasks)}: '{task_name}' - Reusing project company_id: {task_company_id}")
        else:
            # Different company than project - need to search for it
            task_company_id = resolve_company_id(scoro_client, task_company_name)
            if not task_company_id:
                logger.warning(f"  Task {idx}/{len(asana_tasks)}: '{task_name}' - Could not resolve company: '{task_company_name}'")
                continue
        
        # Update task company
        if update_task_company(scoro_client, scoro_task_id, task_company_id):
            stats['tasks_updated'] += 1
            if idx % 10 == 0:
                logger.info(f"  Progress: {idx}/{len(asana_tasks)} tasks processed, {stats['tasks_updated']} updated")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Summary:")
    logger.info(f"  Projects found: {stats['projects_found']}")
    logger.info(f"  Projects updated: {stats['projects_updated']}")
    logger.info(f"  Tasks processed: {stats['tasks_processed']}")
    logger.info(f"  Tasks updated: {stats['tasks_updated']}")
    if stats['errors']:
        logger.info(f"  Errors: {len(stats['errors'])}")
    logger.info(f"{'='*60}\n")
    
    return stats


def main():
    """Main function"""
    if len(sys.argv) < 2:
        logger.error("Usage: python assign_correct_company.py <asana_export_json_file>")
        logger.error("Example: python assign_correct_company.py asana_export_Valley_Deck_&_Patio_20251202_000555.json")
        sys.exit(1)
    
    json_file_path = sys.argv[1]
    
    try:
        # Initialize Scoro client
        logger.info("Initializing Scoro client...")
        scoro_client = ScoroClient()
        
        # Load Asana data
        asana_data = load_asana_data(json_file_path)
        
        # Process project and tasks
        stats = process_project_and_tasks(scoro_client, asana_data)
        
        # Print final summary
        if stats['errors']:
            logger.error(f"\nCompleted with {len(stats['errors'])} errors:")
            for error in stats['errors']:
                logger.error(f"  - {error}")
        else:
            logger.info("\n✓ All updates completed successfully!")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
