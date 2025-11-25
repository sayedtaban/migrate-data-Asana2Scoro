"""
Script to list tasks that would be deleted for backup project IDs in config.py
This script does NOT delete anything - it only lists the tasks for verification.
"""
import sys
from typing import List, Dict

from clients.scoro_client import ScoroClient
from config import Backup_Scoro_Project_ID
from utils import logger


def list_backup_project_tasks(scoro_client: ScoroClient, project_id: int) -> List[Dict]:
    """
    List all tasks that belong to a given backup project ID (without deleting)
    
    Args:
        scoro_client: Scoro client instance
        project_id: Project ID to list tasks for
    
    Returns:
        List of task dictionaries that belong to the project
    """
    try:
        logger.info(f"Analyzing tasks for backup project ID: {project_id}")
        
        # Step 0: Get project details to verify
        logger.info(f"Fetching project details for verification...")
        project = scoro_client.get_project(project_id)
        
        if not project:
            logger.error(f"Project {project_id} not found in Scoro.")
            return []
        
        project_name = project.get('project_name') or project.get('name', 'Unknown')
        project_status = project.get('status', 'Unknown')
        project_company = project.get('company_name', 'N/A')
        
        logger.info(f"\n{'='*60}")
        logger.info(f"PROJECT VERIFICATION")
        logger.info(f"{'='*60}")
        logger.info(f"Project ID: {project_id}")
        logger.info(f"Project Name: {project_name}")
        logger.info(f"Status: {project_status}")
        logger.info(f"Company: {project_company}")
        logger.info(f"{'='*60}\n")
        
        # Step 1: List all tasks (fetch all and filter client-side for safety)
        logger.info(f"Fetching all tasks (will filter for project {project_id} client-side)...")
        all_tasks = scoro_client.list_tasks()  # Fetch all tasks without filter
        logger.info(f"Fetched {len(all_tasks)} total tasks from Scoro")
        
        # Filter tasks that belong to this project
        filtered_tasks = []
        skipped_count = 0
        
        for task in all_tasks:
            task_project_id = task.get('project_id')
            task_id = task.get('event_id') or task.get('id') or task.get('task_id')
            task_name = task.get('event_name') or task.get('name', 'Unknown')
            
            # Verify the task belongs to the project
            if task_project_id != project_id:
                skipped_count += 1
                continue
            
            if not task_id:
                logger.warning(f"Task has no ID, skipping: {task_name}")
                skipped_count += 1
                continue
            
            filtered_tasks.append(task)
        
        logger.info(f"Found {len(filtered_tasks)} tasks belonging to project {project_id}")
        logger.info(f"Skipped {skipped_count} tasks from other projects")
        
        return filtered_tasks
            
    except Exception as e:
        logger.error(f"Error listing tasks for project {project_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def main():
    """
    Main function to list tasks that would be deleted (NO DELETION - READ ONLY)
    """
    try:
        # Get backup project IDs from config
        if not Backup_Scoro_Project_ID:
            logger.error("No backup project IDs found in config.py (Backup_Scoro_Project_ID is empty)")
            return 1
        
        logger.info(f"Found {len(Backup_Scoro_Project_ID)} backup project ID(s) to analyze")
        logger.info("NOTE: This script does NOT delete anything - it only lists tasks for verification")
        
        # Initialize Scoro client
        logger.info("Initializing Scoro client...")
        scoro_client = ScoroClient()
        
        # Process each backup project ID
        all_tasks_to_delete = []
        
        for project_id_str in Backup_Scoro_Project_ID:
            try:
                # Convert to integer
                project_id = int(project_id_str)
                logger.info(f"\n{'='*60}")
                logger.info(f"Analyzing backup project ID: {project_id}")
                logger.info(f"{'='*60}")
                
                # Get project name for summary
                project = scoro_client.get_project(project_id)
                project_name = project.get('project_name') or project.get('name', 'Unknown') if project else 'Unknown'
                
                # List tasks for this project
                tasks = list_backup_project_tasks(scoro_client, project_id)
                
                if tasks:
                    logger.info(f"\n{'='*60}")
                    logger.info(f"TASKS THAT WOULD BE DELETED FOR PROJECT {project_id} ({project_name})")
                    logger.info(f"{'='*60}")
                    logger.info(f"Total tasks: {len(tasks)}\n")
                    
                    # Display task list
                    for idx, task in enumerate(tasks, 1):
                        task_id = task.get('event_id') or task.get('id') or task.get('task_id')
                        task_name = task.get('event_name') or task.get('name', 'Unknown')
                        task_status = task.get('status', 'N/A')
                        task_status_name = task.get('status_name', 'N/A')
                        task_project_id = task.get('project_id')
                        is_completed = task.get('is_completed', False)
                        completed_date = task.get('datetime_completed', 'N/A')
                        
                        logger.info(f"{idx}. Task ID: {task_id}")
                        logger.info(f"   Name: {task_name}")
                        logger.info(f"   Status: {task_status} ({task_status_name})")
                        logger.info(f"   Project ID: {task_project_id}")
                        logger.info(f"   Completed: {is_completed}")
                        if completed_date and completed_date != 'N/A':
                            logger.info(f"   Completed Date: {completed_date}")
                        logger.info("")
                    
                    # Store for summary
                    all_tasks_to_delete.extend(tasks)
                else:
                    logger.info(f"No tasks found for project {project_id} ({project_name})")
                    
            except ValueError:
                logger.error(f"Invalid project ID format: {project_id_str} (must be an integer)")
            except Exception as e:
                logger.error(f"Error processing project ID {project_id_str}: {e}")
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("SUMMARY - Tasks That Would Be Deleted")
        logger.info(f"{'='*60}")
        logger.info(f"Total projects analyzed: {len(Backup_Scoro_Project_ID)}")
        logger.info(f"Total tasks that would be deleted: {len(all_tasks_to_delete)}")
        logger.info(f"\nNOTE: No tasks or projects were actually deleted.")
        logger.info(f"This is a READ-ONLY operation for verification purposes.")
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
