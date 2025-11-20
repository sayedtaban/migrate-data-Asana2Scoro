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
        
        # Extract PM (Project Manager) name from tasks
        # Check tasks for PM Name custom field to determine the project manager
        pm_name = None
        tasks = asana_data.get('tasks', [])
        pm_counts = {}  # Track PM name frequency
        
        # Check all tasks for PM Name
        for task in tasks:
            task_pm = extract_custom_field_value(task, 'PM Name') or extract_custom_field_value(task, 'PM')
            if task_pm and task_pm.strip():
                task_pm = task_pm.strip()
                # Validate and normalize the PM name
                validated_pm = validate_user(task_pm, default_to_tom=False)
                if validated_pm:  # Only count if validation returns a valid name
                    pm_counts[validated_pm] = pm_counts.get(validated_pm, 0) + 1
        
        # Determine the most common PM, or use the first one found
        if pm_counts:
            # Get the PM with the highest count
            pm_name = max(pm_counts.items(), key=lambda x: x[1])[0]
            logger.info(f"  Found PM from task custom fields: {pm_name} (appears in {pm_counts[pm_name]} tasks)")
        else:
            logger.debug(f"  No PM name found in task custom fields")
        
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
        
        # Add project metadata matching Scoro API format
        # Map Asana "Project Overview" (stored in 'notes' field) to Scoro project description/details field
        project_overview = project.get('overview') or project.get('notes') or project.get('description')
        if project_overview:
            transformed_project['description'] = re.sub(r'<[^>]+>', '', str(project_overview))
        
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
            logger.info(f"  PM/Manager: Not found in task custom fields")
        
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
            responsible = validate_user(pm_name, default_to_tom=True)
            assigned_to = validate_user(assignee, default_to_tom=False)
            
            # Get estimated/actual time (if available in custom fields)
            # NOTE: Must extract this BEFORE setting completion status because Scoro requires
            # completed tasks to have time entries
            estimated_time = extract_custom_field_value(task, 'Estimated time') or extract_custom_field_value(task, 'Estimated Time')
            actual_time = extract_custom_field_value(task, 'Actual time') or extract_custom_field_value(task, 'Actual Time')
            
            # Get completion status
            # IMPORTANT: Scoro requires that tasks marked as done must have time entries.
            # If a task was completed in Asana but has no actual_time, we cannot mark it as completed.
            completed = task.get('completed', False)
            completed_at = task.get('completed_at')
            has_actual_time = actual_time and str(actual_time).strip()
            
            if completed and completed_at and has_actual_time:
                # Task is completed AND has time entries - safe to mark as completed
                status = 'task_status4'  # Scoro API uses task_status1-4, using task_status4 for completed
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
            elif completed and completed_at and not has_actual_time:
                # Task was completed in Asana but has no time entries
                # Scoro won't accept it as completed, so set to in-progress status instead
                status = 'task_status2'  # Use task_status2 (in-progress) instead of completed
                is_completed = False  # Don't mark as completed
                datetime_completed = None  # Don't set completion datetime
                logger.debug(f"    ⚠ Task was completed in Asana but has no time entries - setting to in-progress status instead")
            else:
                status = 'task_status1'  # Scoro API uses task_status1-4, using task_status1 for planned/in-progress
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
            if responsible:
                transformed_task['owner_name'] = responsible  # Store name, importer will resolve to owner_id
            if assigned_to:
                transformed_task['assigned_to_name'] = assigned_to  # Store name, importer will resolve to related_users array
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

