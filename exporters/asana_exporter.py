"""
Export functionality for extracting project data from Asana
"""
from datetime import datetime
from typing import Dict, Optional

from clients.asana_client import AsanaClient
from utils import logger


def export_asana_project(asana_client: AsanaClient, project_name: Optional[str] = None, 
                         project_gid: Optional[str] = None, workspace_gid: Optional[str] = None) -> Optional[Dict]:
    """
    Export project data from Asana
    
    Args:
        asana_client: Initialized AsanaClient instance
        project_name: Name of the project to export (optional if project_gid is provided)
        project_gid: Direct project GID to export (optional if project_name is provided)
        workspace_gid: Workspace GID (optional, used when searching by name)
    
    Returns:
        Dictionary containing project data, tasks, sections, etc.
    """
    try:
        # Determine project_gid - either use provided GID or search by name
        if project_gid:
            # Use provided project GID directly
            project_gid = str(project_gid)
            logger.info(f"Starting export using provided project GID: {project_gid}")
            logger.info("Step 1/5: Retrieving project details using GID...")
            project_details = asana_client.get_project_details(project_gid)
            logger.info(f"✓ Retrieved project: {project_details.get('name', 'Unknown')} (GID: {project_gid})")
            logger.debug(f"project_details: {project_details}")
        elif project_name:
            # Search for project by name
            logger.info(f"Starting export of Asana project: {project_name}")
            logger.info(f"Step 1/5: Searching for project '{project_name}'...")
            if workspace_gid:
                workspace_gid = str(workspace_gid)
            project = asana_client.get_project_by_name(project_name, workspace_gid)
            if not project:
                logger.error(f"Project '{project_name}' not found in Asana")
                return None
            
            project_gid = project['gid']
            logger.info(f"✓ Found project: {project.get('name', 'Unknown')} (GID: {project_gid})")
            
            # Get detailed project information
            logger.info("Step 2/5: Retrieving detailed project information...")
            project_details = asana_client.get_project_details(project_gid)
            logger.info(f"✓ Retrieved project details: {project_details.get('name', 'Unknown')}")
        else:
            logger.error("Either project_name or project_gid must be provided")
            raise ValueError("Either project_name or project_gid must be provided")
        
        # Get all tasks
        step_num = "3/5" if project_name else "2/5"
        logger.info(f"Step {step_num}: Retrieving project tasks...")
        tasks = asana_client.get_project_tasks(project_gid)
        logger.info(f"✓ Found {len(tasks)} tasks in project")
        
        # Get sections
        step_num = "4/5" if project_name else "3/5"
        logger.info(f"Step {step_num}: Retrieving project sections...")
        sections = asana_client.get_project_sections(project_gid)
        logger.info(f"✓ Found {len(sections)} sections in project")
        
        # Get milestones
        step_num = "5/7" if project_name else "4/7"
        logger.info(f"Step {step_num}: Retrieving project milestones...")
        milestones = asana_client.get_project_milestones(project_gid)
        logger.info(f"✓ Found {len(milestones)} milestones in project")
        
        # Get detailed task information with subtasks, dependencies, attachments, and comments
        step_num = "6/7" if project_name else "5/7"
        logger.info(f"Step {step_num}: Retrieving detailed task information...")
        detailed_tasks = []
        total_tasks = len(tasks)
        for idx, task in enumerate(tasks, 1):
            try:
                task_name = task.get('name', task.get('gid', 'Unknown'))
                task_gid = task.get('gid', '')
                logger.info(f"  [{idx}/{total_tasks}] Retrieving details for task: {task_name}")
                
                # Get full detailed task info (includes dependencies, tags, etc.)
                detailed_task = asana_client.get_task_details(task_gid)
                
                # Get subtasks if this is a parent task
                if detailed_task.get('num_subtasks', 0) > 0:
                    subtasks = asana_client.get_subtasks(task_gid)
                    detailed_task['subtasks'] = subtasks
                
                # Get attachments
                attachments = asana_client.get_task_attachments(task_gid)
                detailed_task['attachments'] = attachments
                
                # Get stories/comments
                stories = asana_client.get_task_stories(task_gid)
                detailed_task['stories'] = stories
                
                detailed_tasks.append(detailed_task)
                logger.debug(f"    ✓ Retrieved details for task: {task_name} (subtasks: {len(detailed_task.get('subtasks', []))}, attachments: {len(attachments)}, comments: {len(stories)})")
            except Exception as e:
                logger.warning(f"    ⚠ Could not retrieve details for task {task.get('name', task.get('gid'))}: {e}")
                # Fall back to basic task data
                task['subtasks'] = []
                task['attachments'] = []
                task['stories'] = []
                detailed_tasks.append(task)
        
        # Build task dependency map
        step_num = "7/7" if project_name else "6/7"
        logger.info(f"Step {step_num}: Building task dependency relationships...")
        dependencies_map = {}
        for task in detailed_tasks:
            task_gid = task.get('gid', '')
            if task_gid:
                dependencies = task.get('dependencies', [])
                dependents = task.get('dependents', [])
                dependencies_map[task_gid] = {
                    'dependencies': [dep.get('gid') if isinstance(dep, dict) else str(dep) for dep in dependencies] if dependencies else [],
                    'dependents': [dep.get('gid') if isinstance(dep, dict) else str(dep) for dep in dependents] if dependents else []
                }
        
        export_data = {
            'project': project_details,
            'tasks': detailed_tasks,
            'milestones': milestones,
            'sections': sections,
            'dependencies': dependencies_map,
            'exported_at': datetime.now().isoformat()
        }
        
        logger.info("="*60)
        logger.info(f"✓ Export completed successfully!")
        logger.info(f"  Project: {project_details.get('name', 'Unknown')}")
        logger.info(f"  Tasks: {len(detailed_tasks)}")
        logger.info(f"  Milestones: {len(milestones)}")
        logger.info(f"  Sections: {len(sections)}")
        logger.info(f"  Task dependencies: {sum(len(deps.get('dependencies', [])) for deps in dependencies_map.values())}")
        logger.info("="*60)
        return export_data
        
    except Exception as e:
        logger.error(f"Error exporting Asana project: {e}")
        raise

