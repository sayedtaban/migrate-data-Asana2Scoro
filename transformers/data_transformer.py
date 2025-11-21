"""
Main data transformation logic for converting Asana data to Scoro format

Field names in this transformer match the Scoro API v2 format:
- Tasks API fields: event_name, is_completed, is_personal, start_datetime, 
  datetime_due, datetime_completed, duration_planned, duration_actual, 
  activity_type, priority_id, description, company_id, project_id, 
  project_phase_id, owner_id, related_users, status, etc.
- Projects API fields: project_name, description, company_id, is_personal, 
  is_private, date, deadline, duration, status, manager_id, phases, etc.

Reference: Scoro API Reference.md
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
    extract_priority
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
        
        # Extract Project Manager/Owner from Asana project
        # Priority: ALWAYS use Asana Project Owner as Scoro Project Manager
        # Asana Project Owner → Scoro Project Manager (manager_id)
        pm_name = None
        users_map = asana_data.get('users', {})
        
        # Get project owner from project.owner field - this is the authoritative source
        project_owner = project.get('owner')
        owner_gid = None
        owner_name_from_owner_field = None
        
        if project_owner:
            if isinstance(project_owner, dict):
                owner_gid = project_owner.get('gid')
                owner_name_from_owner_field = project_owner.get('name')  # Try to get name directly
            elif hasattr(project_owner, 'gid'):
                owner_gid = project_owner.gid
                owner_name_from_owner_field = getattr(project_owner, 'name', None)
            
            # Try method 1: Get name directly from owner field
            if owner_name_from_owner_field:
                pm_name = owner_name_from_owner_field
                logger.info(f"  Found project owner name from project.owner field: {pm_name} (GID: {owner_gid})")
            # Try method 2: Look up in users map
            elif owner_gid and owner_gid in users_map:
                owner_details = users_map[owner_gid]
                pm_name = owner_details.get('name', '')
                if pm_name:
                    logger.info(f"  Found project owner from users map: {pm_name} (GID: {owner_gid})")
            # Try method 3: Search tasks for owner name
            elif owner_gid:
                logger.info(f"  Project owner GID {owner_gid} not in users map, searching all tasks...")
                tasks = asana_data.get('tasks', [])
                
                # Search all tasks to find this user's name
                for task in tasks:  
                    if pm_name:  # Already found, can break
                        break
                    
                    # Check assignee
                    assignee = task.get('assignee')
                    if assignee:
                        assignee_gid = None
                        assignee_name = None
                        if isinstance(assignee, dict):
                            assignee_gid = assignee.get('gid')
                            assignee_name = assignee.get('name')
                        elif hasattr(assignee, 'gid'):
                            assignee_gid = assignee.gid
                            assignee_name = getattr(assignee, 'name', None)
                        
                        if assignee_gid == owner_gid and assignee_name:
                            pm_name = assignee_name
                            logger.info(f"  ✓ Found project owner from task assignee: {pm_name} (GID: {owner_gid})")
                            break
                    
                    # Check created_by
                    created_by = task.get('created_by')
                    if created_by:
                        created_by_gid = None
                        created_by_name = None
                        if isinstance(created_by, dict):
                            created_by_gid = created_by.get('gid')
                            created_by_name = created_by.get('name')
                        elif hasattr(created_by, 'gid'):
                            created_by_gid = created_by.gid
                            created_by_name = getattr(created_by, 'name', None)
                        
                        if created_by_gid == owner_gid and created_by_name:
                            pm_name = created_by_name
                            logger.info(f"  ✓ Found project owner from task created_by: {pm_name} (GID: {owner_gid})")
                            break
                    
                    # Check followers/collaborators in stories
                    for story in task.get('stories', []):
                        if pm_name:
                            break
                        story_created_by = story.get('created_by')
                        if story_created_by:
                            story_gid = None
                            story_name = None
                            if isinstance(story_created_by, dict):
                                story_gid = story_created_by.get('gid')
                                story_name = story_created_by.get('name')
                            elif hasattr(story_created_by, 'gid'):
                                story_gid = story_created_by.gid
                                story_name = getattr(story_created_by, 'name', None)
                            
                            if story_gid == owner_gid and story_name:
                                pm_name = story_name
                                logger.info(f"  ✓ Found project owner from story author: {pm_name} (GID: {owner_gid})")
                                break
                
                if not pm_name:
                    logger.warning(f"  ⚠ Could not find name for project owner GID {owner_gid}")
                    logger.warning(f"  ⚠ Project will be created without a manager assigned")
        else:
            logger.warning(f"  ⚠ No project owner found in Asana project data")
            logger.warning(f"  ⚠ Project will be created without a manager assigned")
        
        # Extract project members for reference
        # Asana project members → Scoro project team members
        project_members = []
        members_list = project.get('members', [])
        if members_list:
            tasks = asana_data.get('tasks', [])
            
            for member in members_list:
                member_gid = None
                if isinstance(member, dict):
                    member_gid = member.get('gid')
                elif hasattr(member, 'gid'):
                    member_gid = member.gid
                
                if not member_gid:
                    continue
                
                member_name = None
                
                # Look up member name in users map first
                if member_gid in users_map:
                    member_details = users_map[member_gid]
                    member_name = member_details.get('name', '')
                    if member_name:
                        logger.debug(f"    Found member from users map: {member_name} (GID: {member_gid})")
                else:
                    # Member not in users map - try to find name from tasks
                    logger.debug(f"    Member GID {member_gid} not in users map, searching tasks...")
                    for task in tasks:
                        # Check assignee
                        assignee = task.get('assignee')
                        if assignee:
                            assignee_gid = None
                            assignee_name = None
                            if isinstance(assignee, dict):
                                assignee_gid = assignee.get('gid')
                                assignee_name = assignee.get('name')
                            elif hasattr(assignee, 'gid'):
                                assignee_gid = assignee.gid
                                assignee_name = getattr(assignee, 'name', None)
                            
                            if assignee_gid == member_gid and assignee_name:
                                member_name = assignee_name
                                logger.debug(f"    Found member from task assignee: {member_name} (GID: {member_gid})")
                                break
                        
                        # Check created_by if not found in assignee
                        if not member_name:
                            created_by = task.get('created_by')
                            if created_by:
                                created_by_gid = None
                                created_by_name = None
                                if isinstance(created_by, dict):
                                    created_by_gid = created_by.get('gid')
                                    created_by_name = created_by.get('name')
                                elif hasattr(created_by, 'gid'):
                                    created_by_gid = created_by.gid
                                    created_by_name = getattr(created_by, 'name', None)
                                
                                if created_by_gid == member_gid and created_by_name:
                                    member_name = created_by_name
                                    logger.debug(f"    Found member from task created_by: {member_name} (GID: {member_gid})")
                                    break
                    
                    if not member_name:
                        logger.debug(f"    Could not find name for member GID {member_gid} in users map or tasks")
                
                # Add unique member names to the list
                    if member_name and member_name not in project_members:
                        project_members.append(member_name)
            
            if project_members:
                logger.info(f"  Found {len(project_members)} project members: {', '.join(project_members[:5])}" + 
                           (f" and {len(project_members) - 5} more" if len(project_members) > 5 else ""))
            else:
                logger.debug(f"  No project members found (checked {len(members_list)} member GIDs)")
        
        # Transform project with comprehensive fields matching Scoro API format
        # Reference: Scoro API Reference.md - Projects API fields
        transformed_project = {
            'project_name': project_name,  # Scoro API uses 'project_name'
        }
        
        # Add company name to project data for reference
        if company_name:
            transformed_project['company_name'] = company_name
        
        # Add PM name to project data for reference (will be resolved to manager_id during import)
        if pm_name:
            transformed_project['manager_name'] = pm_name
        
        # Add project members for reference
        if project_members:
            transformed_project['members'] = project_members
        
        # Add project metadata matching Scoro API format
        # Map Asana "Project Overview" (stored in 'notes' field) to Scoro project description/details field
        project_overview = project.get('overview') or project.get('notes') or project.get('description')
        if project_overview:
            project_description = re.sub(r'<[^>]+>', '', str(project_overview))
            # Convert newlines to HTML line breaks for Scoro API
            project_description = project_description.replace('\n', '<br>')
            transformed_project['description'] = project_description
        
        # Map dates to Scoro API format (date field for start, deadline for due)
        if project.get('start_on') or project.get('created_at'):
            start_date = project.get('start_on') or project.get('created_at')
            if isinstance(start_date, str) and 'T' in start_date:
                start_date = start_date.split('T')[0]
            transformed_project['date'] = start_date  # Scoro API uses 'date' for project start/creation date
        
        if project.get('due_date') or project.get('due_on'):
            due_date = project.get('due_date') or project.get('due_on')
            if isinstance(due_date, str) and 'T' in due_date:
                due_date = due_date.split('T')[0]
            transformed_project['deadline'] = due_date  # Scoro API uses 'deadline' not 'due_date'
        
        # Note: Scoro API doesn't have 'completed_date' field for projects
        # Project completion is indicated by status field (e.g., 'completed')
        
        # Scoro project fields
        transformed_project['is_personal'] = False  # Scoro API uses Boolean, default to False (not personal)
        transformed_project['is_private'] = False  # Scoro API uses Boolean, default to False (not private)
        
        # Keep legacy fields for backward compatibility with importer
        if project.get('created_at'):
            transformed_project['created_at'] = project.get('created_at')
        if project.get('modified_at'):
            transformed_project['modified_at'] = project.get('modified_at')
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
        if pm_name:
            logger.info(f"  PM/Manager: {pm_name}")
        else:
            logger.info(f"  PM/Manager: Not found")
        if project_members:
            logger.info(f"  Project members: {len(project_members)} member(s)")
        
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
                    milestone_description = re.sub(r'<[^>]+>', '', str(milestone.get('notes', '')))
                    # Convert newlines to HTML line breaks for Scoro API
                    milestone_description = milestone_description.replace('\n', '<br>')
                    transformed_milestone['description'] = milestone_description
                
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
            # Extract assignee information - prefer name from users map if available
            assignee = None
            assignee_gid = None
            assignee_obj = task.get('assignee')
            if assignee_obj:
                # Get GID first
                if isinstance(assignee_obj, dict):
                    assignee_gid = assignee_obj.get('gid')
                    assignee = assignee_obj.get('name', '')
                elif hasattr(assignee_obj, 'gid'):
                    assignee_gid = assignee_obj.gid
                    assignee = assignee_obj.name if hasattr(assignee_obj, 'name') else None
                else:
                    assignee = str(assignee_obj) if assignee_obj else None
                
                # If we have users map, try to get name from there (more reliable)
                users_map = asana_data.get('users', {})
                if assignee_gid and assignee_gid in users_map:
                    user_details = users_map[assignee_gid]
                    assignee = user_details.get('name', assignee)
                    logger.debug(f"    Using user name from users map: {assignee} (GID: {assignee_gid})")
                
                # Normalize empty strings to None
                if not assignee or not str(assignee).strip():
                    assignee = None
                else:
                    assignee = str(assignee).strip()
            
            # Get due date - Scoro API uses datetime_due (ISO8601 format)
            datetime_due = task.get('due_on') or task.get('due_at')
            if datetime_due:
                if isinstance(datetime_due, str):
                    try:
                        # Keep full datetime format for Scoro API (ISO8601)
                        if 'T' not in datetime_due:
                            # If only date, add time component
                            datetime_due = f"{datetime_due}T00:00:00"
                    except Exception as e:
                        logger.debug(f"    Could not parse datetime_due: {datetime_due}, error: {e}")
                        datetime_due = None
                else:
                    # If it's not a string, try to convert or set to None
                    datetime_due = None
            else:
                datetime_due = None
            
            # July 1 rule: exclude tasks created before cutoff if no assignee or due date
            if created_date < CUTOFF_DATE:
                if not assignee or not datetime_due:
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
            # Note: Project Manager (PM Name) is already handled at project level via manager_id
            # For task-level fields:
            # - owner_id should be the TASK ASSIGNEE (the person responsible for THIS task)
            # - related_users should include followers/collaborators
            
            # Task owner_id comes from task assignee (the person assigned to this specific task)
            task_owner = validate_user(assignee, default_to_tom=False)
            
            # PM Name is for reference only (project manager is set at project level)
            pm_for_reference = validate_user(pm_name, default_to_tom=True) if pm_name else None
            
            # Get estimated/actual time (if available in custom fields)
            # NOTE: Must extract this BEFORE setting completion status because Scoro requires
            # completed tasks to have time entries
            estimated_time = extract_custom_field_value(task, 'Estimated time') or extract_custom_field_value(task, 'Estimated Time')
            actual_time = extract_custom_field_value(task, 'Actual time') or extract_custom_field_value(task, 'Actual Time')
            
            # Get completion status
            # IMPORTANT: Scoro requires that tasks marked as done must have time entries.
            # If a task was completed in Asana but has no actual_time, calculate it from created_at to completed_at
            completed = task.get('completed', False)
            completed_at = task.get('completed_at')
            has_actual_time = actual_time and str(actual_time).strip()
            
            # If task is completed but has no actual time, calculate duration and create time entry
            calculated_time_entry = None
            if completed and completed_at and not has_actual_time:
                try:
                    # Parse created_at and completed_at timestamps
                    created_at_str = str(created_at).strip()
                    completed_at_str = str(completed_at).strip()
                    
                    # Parse timestamps
                    if 'T' in created_at_str:
                        if created_at_str.endswith('Z'):
                            created_dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        else:
                            created_dt = datetime.fromisoformat(created_at_str)
                    else:
                        created_dt = datetime.strptime(created_at_str.split()[0], '%Y-%m-%d')
                    
                    if 'T' in completed_at_str:
                        if completed_at_str.endswith('Z'):
                            completed_dt = datetime.fromisoformat(completed_at_str.replace('Z', '+00:00'))
                        else:
                            completed_dt = datetime.fromisoformat(completed_at_str)
                    else:
                        completed_dt = datetime.strptime(completed_at_str.split()[0], '%Y-%m-%d')
                    
                    # Calculate duration
                    duration = completed_dt - created_dt
                    total_seconds = int(duration.total_seconds())
                    
                    # Convert to HH:MM:SS format (Scoro expects Time format HH:ii:ss)
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    actual_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    
                    # Create time entry object for Scoro Time Entries API
                    # Reference: Scoro API Reference.md - Time Entries API
                    calculated_time_entry = {
                        'start_datetime': created_at_str,  # ISO8601 format
                        'end_datetime': completed_at_str,  # ISO8601 format
                        'duration': actual_time,  # HH:MM:SS format
                        'is_completed': True,  # Mark as completed
                        'completed_datetime': completed_at_str,  # ISO8601 format
                        'event_type': 'task',  # This is a task time entry
                        'time_entry_type': 'task',  # Time entry type
                        'billable_time_type': 'billable',  # Default to billable
                    }
                    
                    # Add user_id reference (will be resolved by importer)
                    if assignee:
                        calculated_time_entry['user_name'] = assignee  # Store name, importer will resolve to user_id
                    
                    logger.info(f"    ✓ Created time entry for completed task: {actual_time} (from {created_at} to {completed_at})")
                    has_actual_time = True
                except Exception as e:
                    logger.warning(f"    ⚠ Could not calculate time entry for completed task: {e}")
                    has_actual_time = False
            
            # Determine initial task status based on whether we have a calculated time entry
            # IMPORTANT: If we have a calculated_time_entry, we must create the task as "planned" first,
            # then create the time entry, and finally update the task to "completed".
            # This is because Scoro rejects creating tasks as completed without existing time entries.
            if completed and completed_at and has_actual_time and not calculated_time_entry:
                # Task is completed AND has time entries (from Asana) - safe to mark as completed immediately
                status = 'task_status5'  # Scoro site has 5 statuses: task_status5 = Completed
                is_completed = True  # Scoro API uses Boolean
                datetime_completed = completed_at
                if isinstance(datetime_completed, str):
                    try:
                        # Keep full datetime format for Scoro API (ISO8601)
                        if 'T' not in datetime_completed:
                            # If only date, add time component
                            datetime_completed = f"{datetime_completed}T00:00:00"
                    except Exception as e:
                        logger.debug(f"    Could not parse datetime_completed: {datetime_completed}, error: {e}")
                        datetime_completed = None
            elif completed and completed_at and has_actual_time and calculated_time_entry:
                # Task is completed but has calculated time entry - create as "planned" first
                # We'll create the time entry and then update the task to "completed" in the importer
                status = 'task_status1'  # Scoro site has 5 statuses: task_status1 = Planned
                is_completed = False  # Create as not completed initially
                datetime_completed = None  # Don't set completion datetime yet
                # Store completion info in the calculated_time_entry for later update
                calculated_time_entry['should_complete_task'] = True
                calculated_time_entry['task_completed_at'] = completed_at
                logger.debug(f"    Task will be marked as completed after time entry creation")
            elif completed and completed_at and not has_actual_time:
                # Task was completed in Asana but could not calculate time entries
                # Set to planned status (not in-progress, since it's actually completed but we couldn't calculate time)
                status = 'task_status1'  # Scoro site has 5 statuses: task_status1 = Planned
                is_completed = False  # Don't mark as completed
                datetime_completed = None  # Don't set completion datetime
                logger.warning(f"    ⚠ Task was completed in Asana but could not calculate time entries - setting to planned status")
            else:
                status = 'task_status1'  # Scoro site has 5 statuses: task_status1 = Planned
                is_completed = False  # Scoro API uses Boolean
                datetime_completed = None
            
            # Get start date - Scoro API uses start_datetime (ISO8601 format)
            start_datetime = task.get('start_on') or task.get('start_at')
            if start_datetime:
                if isinstance(start_datetime, str):
                    try:
                        # Keep full datetime format for Scoro API (ISO8601)
                        if 'T' not in start_datetime:
                            # If only date, add time component
                            start_datetime = f"{start_datetime}T00:00:00"
                    except Exception as e:
                        logger.debug(f"    Could not parse start_datetime: {start_datetime}, error: {e}")
                        start_datetime = None
                else:
                    start_datetime = None
            else:
                start_datetime = None
            
            # Map Asana task overview/description (stored in 'notes' or 'html_notes' field) to Scoro task "Description" field
            # At task level: Overview goes to "Description" field
            description = task.get('overview') or task.get('notes', '') or task.get('html_notes', '')
            if description:
                description = str(description).strip()
                if description:
                    # Clean HTML if present
                    description = re.sub(r'<[^>]+>', '', description)
                    # Convert newlines to HTML line breaks for Scoro API
                    # Scoro expects HTML formatting for line breaks in descriptions
                    description = description.replace('\n', '<br>')
                else:
                    description = None
            else:
                description = None
            
            # Extract stories/comments for separate processing (not mixed with description)
            # Comments will be created separately via Scoro Comments API
            stories = task.get('stories', [])
            
            # Get company name (from custom field or project)
            company = extract_custom_field_value(task, 'C-Name') or extract_custom_field_value(task, 'Company Name')
            if not company:
                company = project_name
            
            # Extract tags
            tags = extract_tags(task)
            
            # Extract priority and convert to priority_id
            # Scoro API: priority_id Integer - 1=high, 2=normal, 3=low
            priority_str = extract_priority(task, title)
            priority_id = None
            if priority_str:
                priority_lower = priority_str.lower()
                if 'high' in priority_lower:
                    priority_id = 1
                elif 'low' in priority_lower:
                    priority_id = 3
                else:
                    priority_id = 2  # Default to normal/medium
            
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
            
            # Get followers - extract names from users map if available
            followers = task.get('followers', [])
            follower_names = []
            users_map = asana_data.get('users', {})
            if followers:
                for follower in followers:
                    follower_name = None
                    follower_gid = None
                    
                    if isinstance(follower, dict):
                        follower_gid = follower.get('gid')
                        follower_name = follower.get('name', '')
                    elif hasattr(follower, 'gid'):
                        follower_gid = follower.gid
                        follower_name = follower.name if hasattr(follower, 'name') else None
                    else:
                        follower_name = str(follower) if follower else None
                    
                    # If we have users map, try to get name from there (more reliable)
                    if follower_gid and follower_gid in users_map:
                        user_details = users_map[follower_gid]
                        follower_name = user_details.get('name', follower_name)
                    
                    if follower_name and str(follower_name).strip():
                        follower_names.append(str(follower_name).strip())
            
            # Get permalink for reference
            permalink = task.get('permalink_url', '')
            
            # Build comprehensive Scoro task data structure matching Scoro API format
            # Reference: Scoro API Reference.md - Tasks API fields
            transformed_task = {
                'title': title,  # Will be mapped to 'event_name' in importer
                'is_completed': is_completed,  # Scoro API uses Boolean 'is_completed'
                'is_personal': False,  # Scoro API uses Boolean 'is_personal', default to False (not personal)
            }
            
            # Add optional fields only if they have values, matching Scoro API field names
            if description:
                transformed_task['description'] = description
            if start_datetime:
                transformed_task['start_datetime'] = start_datetime  # Scoro API uses 'start_datetime' (ISO8601)
            if datetime_due:
                transformed_task['datetime_due'] = datetime_due  # Scoro API uses 'datetime_due' (ISO8601)
            if estimated_time:
                transformed_task['duration_planned'] = estimated_time  # Scoro API uses 'duration_planned' (Time HH:ii:ss)
                # Set billable_time_type to 'billable' so billable_hours equals duration_planned
                transformed_task['billable_time_type'] = 'billable'  # Scoro API: 'billable' sets billable_hours = duration_planned
            if actual_time:
                transformed_task['duration_actual'] = actual_time  # Scoro API uses 'duration_actual' (Time HH:ii:ss)
            if activity_type:
                transformed_task['activity_type'] = activity_type  # Scoro API uses 'activity_type' (String)
            if status:
                transformed_task['status'] = status  # Scoro API uses 'status' (task_status1-4)
            if datetime_completed:
                transformed_task['datetime_completed'] = datetime_completed  # Scoro API uses 'datetime_completed' (ISO8601)
            if priority_id:
                transformed_task['priority_id'] = priority_id  # Scoro API uses 'priority_id' (Integer: 1=high, 2=normal, 3=low)
            
            # Set owner_id (task assignee) - the person responsible for THIS specific task
            # According to Scoro API: owner_id is "User ID of the user that is responsible for the event"
            # This should be the task assignee, NOT the project manager
            if task_owner:
                transformed_task['owner_name'] = task_owner  # Store name, importer will resolve to owner_id
                logger.debug(f"    Task assignee (owner_id): {task_owner}")
            
            # Set related_users (followers/collaborators)
            # These are additional people following/collaborating on this task
            related_users_list = []
            
            # Add followers to related_users
            if follower_names:
                for follower_name in follower_names:
                    validated_follower = validate_user(follower_name, default_to_tom=False)
                    if validated_follower:
                        # Optionally exclude the task owner from related_users to avoid duplication
                        # (since owner_id already represents the assignee)
                        if validated_follower != task_owner or not task_owner:
                            if validated_follower not in related_users_list:
                                related_users_list.append(validated_follower)
                                logger.debug(f"    Task follower: {validated_follower}")
            
            # Store related_users as a list (importer will resolve each name to user_id)
            if related_users_list:
                transformed_task['assigned_to_name'] = related_users_list  # Store as list, importer will resolve to related_users array
                logger.debug(f"    Task related_users (followers): {related_users_list}")
            
            # Log project manager for reference (already set at project level)
            if pm_for_reference:
                logger.debug(f"    Project manager (set at project level): {pm_for_reference}")
            if project_name:
                transformed_task['project_name'] = project_name  # Store name, importer will resolve to project_id
            if project_phase:
                transformed_task['project_phase_name'] = project_phase  # Store name, importer will resolve to project_phase_id
            if company:
                transformed_task['company_name'] = company  # Store name, importer will resolve to company_id
            
            # Additional Scoro API fields that may be populated later or left empty
            # These fields are available in Scoro API but may not be available from Asana:
            # activity_id (Integer), quote_line_id (Integer), invoice_id (Integer),
            # order_id (Integer), purchase_order_id (Integer), rent_order_id (Integer),
            # bill_id (Integer), billable_hours (Time), billable_time_type (String),
            # created_user (Integer), modified_user (Integer), owner_email (String),
            # custom_fields (Object), tags (Array), permissions (Array)
            
            # Metadata fields for internal use (not sent to API but useful for tracking)
            # These fields are excluded in the importer before sending to Scoro API
            if tags:
                transformed_task['tags'] = tags  # Stored for reference, excluded from API request
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
            
            # Store stories/comments for separate comment creation via Scoro Comments API
            if stories:
                transformed_task['stories'] = stories
            
            # Store calculated time entry for completed tasks without time entries
            # This will be created via Scoro Time Entries API after the task is created
            if calculated_time_entry:
                transformed_task['calculated_time_entry'] = calculated_time_entry
                logger.debug(f"    Added calculated time entry to task: {calculated_time_entry['duration']}")
            
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

