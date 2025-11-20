"""
Main data transformation logic for converting Asana data to Scoro format
"""
import re
from datetime import datetime
from typing import Dict, List, Optional, Any

from config import CUTOFF_DATE
from models import MigrationSummary
from utils import logger
from transformers.field_extractors import (
    extract_custom_field_value,
    extract_tags,
    extract_priority,
    format_comments_for_description
)
from transformers.mappers import (
    smart_map_phase,
    smart_map_activity_and_tracking,
    validate_user
)
from transformers.deduplication import (
    is_client_project,
    get_seen_tasks,
    set_seen_tasks
)


def transform_data(asana_data: Dict, summary: MigrationSummary, seen_tasks_tracker: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict:
    """
    Transform Asana data to Scoro format according to field mapping and business rules
    
    Args:
        asana_data: Exported Asana project data
        summary: Migration summary tracker
        seen_tasks_tracker: Optional dictionary to track seen tasks across multiple projects.
                          If None, uses module-level _seen_tasks tracker.
                          Key: task_gid, Value: {'project_name': str, 'is_client_project': bool, 'task_data': dict}
    
    Returns:
        Transformed data dictionary ready for Scoro import
    """
    # Use provided tracker or module-level tracker
    if seen_tasks_tracker is not None:
        set_seen_tasks(seen_tasks_tracker)
    task_tracker = get_seen_tasks()
    
    logger.info("="*60)
    logger.info("Starting data transformation from Asana to Scoro format")
    logger.info("="*60)
    
    try:
        project = asana_data.get('project', {})
        project_name = project.get('name', 'Unknown Project')
        is_client = is_client_project(project_name)
        project_type = "CLIENT" if is_client else "TEAM MEMBER"
        
        logger.info(f"Transforming project data... (Type: {project_type})")
        
        # Extract company name from project
        # For client projects, use project name as company name
        # For team member projects, try to extract from tasks' custom fields
        company_name = None
        if is_client:
            # Client projects: use project name as company name
            company_name = project_name
        else:
            # For team member projects, try to extract company from tasks' custom fields
            # Check first few tasks for company information
            tasks = asana_data.get('tasks', [])
            for task in tasks[:10]:  # Check first 10 tasks
                company_from_task = extract_custom_field_value(task, 'C-Name') or extract_custom_field_value(task, 'Company Name')
                if company_from_task:
                    company_name = company_from_task
                    logger.info(f"  Found company name from task custom field: {company_name}")
                    break
        
        # Transform project with comprehensive fields
        transformed_project = {
            'name': project_name,
        }
        
        # Add company name to project data for reference
        if company_name:
            transformed_project['company_name'] = company_name
        
        # Add project metadata
        # Map Asana "Project Overview" (stored in 'notes' field) to Scoro project description/details field
        project_overview = project.get('overview') or project.get('notes') or project.get('description')
        if project_overview:
            transformed_project['description'] = re.sub(r'<[^>]+>', '', str(project_overview))
        if project.get('created_at'):
            transformed_project['created_at'] = project.get('created_at')
        if project.get('modified_at'):
            transformed_project['modified_at'] = project.get('modified_at')
        if project.get('due_date') or project.get('due_on'):
            due_date = project.get('due_date') or project.get('due_on')
            if isinstance(due_date, str) and 'T' in due_date:
                due_date = due_date.split('T')[0]
            transformed_project['due_date'] = due_date
        if project.get('start_on'):
            start_date = project.get('start_on')
            if isinstance(start_date, str) and 'T' in start_date:
                start_date = start_date.split('T')[0]
            transformed_project['start_date'] = start_date
        if project.get('completed'):
            transformed_project['completed'] = project.get('completed')
        if project.get('archived'):
            transformed_project['archived'] = project.get('archived')
        
        transformed_data = {
            'project': transformed_project,
            'company_name': company_name,  # Store separately for easy access (may be None)
            'is_client_project': is_client,  # Store for reference
            'tasks': [],
            'milestones': []
        }
        logger.info(f"✓ Project transformed: {project_name} ({project_type})")
        if company_name:
            logger.info(f"  Company name: {company_name}")
        else:
            logger.info(f"  Company name: Will be extracted from project name during import")
        
        # Transform milestones
        milestones_to_transform = asana_data.get('milestones', [])
        if milestones_to_transform:
            logger.info(f"Transforming {len(milestones_to_transform)} milestones...")
            for milestone in milestones_to_transform:
                milestone_name = milestone.get('name', 'Unknown')
                milestone_due = milestone.get('due_on') or milestone.get('due_at')
                milestone_completed = milestone.get('completed', False)
                
                transformed_milestone = {
                    'name': milestone_name,
                    'completed': milestone_completed,
                }
                
                if milestone_due:
                    if isinstance(milestone_due, str) and 'T' in milestone_due:
                        milestone_due = milestone_due.split('T')[0]
                    transformed_milestone['due_date'] = milestone_due
                
                if milestone.get('notes'):
                    transformed_milestone['description'] = re.sub(r'<[^>]+>', '', str(milestone.get('notes', '')))
                
                transformed_data['milestones'].append(transformed_milestone)
            logger.info(f"✓ Transformed {len(transformed_data['milestones'])} milestones")
        
        # Transform tasks
        tasks_to_transform = asana_data.get('tasks', [])
        logger.info(f"Transforming {len(tasks_to_transform)} tasks...")
        
        tasks_written = 0
        tasks_excluded = 0
        tasks_duplicated_skipped = 0
        tasks_replaced = 0
        filled_activity = 0
        filled_phase = 0
        
        for idx, task in enumerate(tasks_to_transform, 1):
            task_name = task.get('name', 'Unknown')
            task_gid = task.get('gid', '')
            
            logger.info(f"  [{idx}/{len(tasks_to_transform)}] Transforming task: {task_name}")
            
            # Extract basic task data
            title = task.get('name', '').strip()
            if not title:
                continue
            
            # Deduplication logic: Check if task already exists
            if task_gid and task_gid in task_tracker:
                existing_task_info = task_tracker[task_gid]
                existing_project = existing_task_info.get('project_name', 'Unknown')
                existing_is_client = existing_task_info.get('is_client_project', False)
                
                # If current project is team member and existing is client, skip this task
                if not is_client and existing_is_client:
                    tasks_duplicated_skipped += 1
                    logger.debug(f"    ⚠ Skipping duplicate task from team member project (already exists in client project '{existing_project}'): {task_name}")
                    continue
                
                # If current project is client and existing is team member, replace it
                if is_client and not existing_is_client:
                    tasks_replaced += 1
                    logger.info(f"    ↻ Replacing task from team member project with client project version: {task_name}")
                    # Continue processing to replace the task
                # If both are client projects or both are team member projects, keep the first one
                elif is_client == existing_is_client:
                    tasks_duplicated_skipped += 1
                    logger.debug(f"    ⚠ Skipping duplicate task (already exists in '{existing_project}'): {task_name}")
                    continue
            
            # Get created date for July 1 rule
            created_at = task.get('created_at', '')
            created_date = None
            if created_at and str(created_at).strip():
                try:
                    created_at_str = str(created_at).strip()
                    # Parse ISO format date
                    if 'T' in created_at_str:
                        # Handle timezone indicators
                        if created_at_str.endswith('Z'):
                            created_date = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        else:
                            created_date = datetime.fromisoformat(created_at_str)
                        # Convert to naive datetime for comparison with CUTOFF_DATE
                        if created_date.tzinfo is not None:
                            created_date = created_date.replace(tzinfo=None)
                    else:
                        # Date only format
                        date_part = created_at_str.split()[0] if created_at_str.split() else created_at_str
                        created_date = datetime.strptime(date_part, '%Y-%m-%d')
                except Exception as e:
                    logger.debug(f"    Could not parse created_at: {created_at}, error: {e}")
                    created_date = datetime(2020, 1, 1)
            else:
                created_date = datetime(2020, 1, 1)
            
            # July 1 rule: exclude tasks created before cutoff if no assignee or due date
            assignee = None
            assignee_obj = task.get('assignee')
            if assignee_obj:
                if isinstance(assignee_obj, dict):
                    assignee = assignee_obj.get('name', '')
                elif hasattr(assignee_obj, 'name'):
                    assignee = assignee_obj.name
                # Normalize empty strings to None
                if not assignee or not str(assignee).strip():
                    assignee = None
                else:
                    assignee = str(assignee).strip()
            
            due_date = task.get('due_on') or task.get('due_at')
            if due_date:
                if isinstance(due_date, str):
                    # Format date for Scoro (YYYY-MM-DD)
                    try:
                        if 'T' in due_date:
                            due_date = due_date.split('T')[0]
                        else:
                            due_date = due_date.split()[0] if due_date.split() else due_date
                    except Exception as e:
                        logger.debug(f"    Could not parse due_date: {due_date}, error: {e}")
                        due_date = None
                else:
                    # If it's not a string, try to convert or set to None
                    due_date = None
            else:
                due_date = None
            
            # July 1 rule: exclude tasks created before cutoff if no assignee or due date
            if created_date < CUTOFF_DATE:
                if not assignee or not due_date:
                    tasks_excluded += 1
                    logger.debug(f"    ⚠ Excluded task (July 1 rule): {task_name}")
                    continue
            
            # Extract custom fields (PM Name, Category, etc.)
            # Note: Time Task Tracking field has been eliminated - only Activity Types are used
            pm_name = extract_custom_field_value(task, 'PM Name') or extract_custom_field_value(task, 'PM')
            category = extract_custom_field_value(task, 'Category') or extract_custom_field_value(task, 'Activity Type')
            
            # Get section from memberships
            section = None
            memberships = task.get('memberships', [])
            if memberships:
                for membership in memberships:
                    if isinstance(membership, dict):
                        project_membership = membership.get('project', {})
                        if project_membership:
                            section_obj = membership.get('section')
                            if section_obj:
                                if isinstance(section_obj, dict):
                                    section = section_obj.get('name', '')
                                elif hasattr(section_obj, 'name'):
                                    section = section_obj.name
                            break
            
            # Map activity type using category mapping
            activity_type = smart_map_activity_and_tracking(title, category, section)
            if not category:
                filled_activity += 1
            
            # Map project phase
            if not section:
                filled_phase += 1
            project_phase = smart_map_phase(title, activity_type, section)
            
            # Map users
            responsible = validate_user(pm_name, default_to_tom=True)
            assigned_to = validate_user(assignee, default_to_tom=False)
            
            # Get completion status
            completed = task.get('completed', False)
            completed_at = task.get('completed_at')
            if completed and completed_at:
                status = 'Completed'
                done = True
                completed_date = completed_at
                if isinstance(completed_date, str):
                    try:
                        if 'T' in completed_date:
                            completed_date = completed_date.split('T')[0]
                        else:
                            completed_date = completed_date.split()[0] if completed_date.split() else completed_date
                    except Exception as e:
                        logger.debug(f"    Could not parse completed_date: {completed_date}, error: {e}")
                        completed_date = None
            else:
                status = 'Planned'
                done = False
                completed_date = None
            
            # Get start date
            start_date = task.get('start_on') or task.get('start_at')
            if start_date:
                if isinstance(start_date, str):
                    try:
                        if 'T' in start_date:
                            start_date = start_date.split('T')[0]
                        else:
                            start_date = start_date.split()[0] if start_date.split() else start_date
                    except Exception as e:
                        logger.debug(f"    Could not parse start_date: {start_date}, error: {e}")
                        start_date = None
                else:
                    start_date = None
            else:
                start_date = None
            
            # Map Asana task overview/description (stored in 'notes' or 'html_notes' field) to Scoro task "Description" field
            # At task level: Overview goes to "Description" field
            description = task.get('overview') or task.get('notes', '') or task.get('html_notes', '')
            if description:
                description = str(description).strip()
                if description:
                    # Clean HTML if present
                    description = re.sub(r'<[^>]+>', '', description)
                else:
                    description = None
            else:
                description = None
            
            # Append comments/stories to description if available
            stories = task.get('stories', [])
            if stories:
                comments_text = format_comments_for_description(stories)
                if comments_text:
                    if description:
                        description = f"{description}\n\n--- Comments ---\n{comments_text}"
                    else:
                        description = f"--- Comments ---\n{comments_text}"
            
            # Get estimated/actual time (if available in custom fields)
            estimated_time = extract_custom_field_value(task, 'Estimated time') or extract_custom_field_value(task, 'Estimated Time')
            actual_time = extract_custom_field_value(task, 'Actual time') or extract_custom_field_value(task, 'Actual Time')
            
            # Get company name (from custom field or project)
            company = extract_custom_field_value(task, 'C-Name') or extract_custom_field_value(task, 'Company Name')
            if not company:
                company = project_name
            
            # Extract tags
            tags = extract_tags(task)
            
            # Extract priority
            priority = extract_priority(task, title)
            
            # Get dependencies (for reference, may need to be handled separately in Scoro)
            dependencies = task.get('dependencies', [])
            dependents = task.get('dependents', [])
            dependency_gids = []
            if dependencies:
                for dep in dependencies:
                    if isinstance(dep, dict):
                        dep_gid = dep.get('gid', '')
                    else:
                        dep_gid = str(dep)
                    if dep_gid:
                        dependency_gids.append(dep_gid)
            
            # Get subtasks count
            subtasks = task.get('subtasks', [])
            num_subtasks = len(subtasks) if subtasks else task.get('num_subtasks', 0)
            
            # Get attachments count and references
            attachments = task.get('attachments', [])
            attachment_count = len(attachments) if attachments else 0
            attachment_refs = []
            if attachments:
                for att in attachments:
                    if isinstance(att, dict):
                        att_name = att.get('name', '')
                        att_url = att.get('download_url') or att.get('view_url', '')
                        if att_name or att_url:
                            attachment_refs.append(f"{att_name} ({att_url})" if att_name and att_url else (att_name or att_url))
            
            # Check if this is a milestone
            resource_subtype = task.get('resource_subtype', '')
            is_milestone = resource_subtype == 'milestone'
            
            # Get followers
            followers = task.get('followers', [])
            follower_names = []
            if followers:
                for follower in followers:
                    if isinstance(follower, dict):
                        follower_name = follower.get('name', '')
                    elif hasattr(follower, 'name'):
                        follower_name = follower.name
                    else:
                        follower_name = str(follower)
                    if follower_name:
                        follower_names.append(follower_name)
            
            # Get permalink for reference
            permalink = task.get('permalink_url', '')
            
            # Build comprehensive Scoro task data structure
            transformed_task = {
                'title': title,
                'done': done,
                'priority': priority,
                'personal': False,
            }
            
            # Add optional fields only if they have values
            if description:
                transformed_task['description'] = description
            if start_date:
                transformed_task['start_datetime'] = start_date
            if due_date:
                transformed_task['due_date'] = due_date
            if estimated_time:
                transformed_task['planned_duration'] = estimated_time
            if actual_time:
                transformed_task['done_duration'] = actual_time
            if activity_type:
                transformed_task['activity_type'] = activity_type
            if status:
                transformed_task['status'] = status
            if completed_date:
                transformed_task['completed_date'] = completed_date
            if responsible:
                transformed_task['responsible'] = responsible
            if assigned_to:
                transformed_task['assigned_to'] = assigned_to
            if project_name:
                transformed_task['project'] = project_name
            if project_phase:
                transformed_task['project_phase'] = project_phase
            if company:
                transformed_task['company'] = company
            if tags:
                transformed_task['tags'] = tags  # Scoro may support tags
            if dependency_gids:
                transformed_task['dependencies'] = dependency_gids  # May need special handling
            if num_subtasks > 0:
                transformed_task['num_subtasks'] = num_subtasks
            if attachment_count > 0:
                transformed_task['attachment_count'] = attachment_count
                if attachment_refs:
                    transformed_task['attachment_refs'] = attachment_refs
            if is_milestone:
                transformed_task['is_milestone'] = True
            if follower_names:
                transformed_task['followers'] = follower_names
            if permalink:
                transformed_task['asana_permalink'] = permalink  # Keep reference to original
            
            # Store Asana GID for reference and deduplication
            if task_gid:
                transformed_task['asana_gid'] = task_gid
            
            transformed_data['tasks'].append(transformed_task)
            tasks_written += 1
            
            # Track this task for deduplication
            if task_gid:
                task_tracker[task_gid] = {
                    'project_name': project_name,
                    'is_client_project': is_client,
                    'task_data': transformed_task
                }
            
            logger.debug(f"    ✓ Task transformed: {task_name}")
        
        logger.info("="*60)
        logger.info(f"✓ Transformation completed successfully!")
        logger.info(f"  Tasks written: {tasks_written}")
        logger.info(f"  Tasks excluded (July 1 rule): {tasks_excluded}")
        logger.info(f"  Tasks skipped (duplicates from team member projects): {tasks_duplicated_skipped}")
        logger.info(f"  Tasks replaced (client project over team member): {tasks_replaced}")
        logger.info(f"  Phases intelligently filled: {filled_phase}")
        logger.info(f"  Activity types filled: {filled_activity}")
        logger.info("="*60)
        return transformed_data
        
    except Exception as e:
        error_msg = f"Error transforming data: {e}"
        logger.error(error_msg)
        logger.exception("Full error details:")
        summary.add_failure(error_msg)
        raise

