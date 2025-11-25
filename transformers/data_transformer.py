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
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from config import CUTOFF_DATE
from models import MigrationSummary
from utils import logger
from transformers.field_extractors import (
    extract_custom_field_value,
    extract_tags,
    extract_priority,
    extract_time_field_value,
    convert_minutes_to_hhmmss
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
            'milestones': [],
            'phases': []  # Phases from Asana sections (different from milestones)
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
        
        # Transform sections to phases
        # Asana sections (columns) should be migrated as Scoro phases (type="phase")
        # This is different from milestones which are migrated as type="milestone"
        # Also create a mapping of section GID to section name for task assignment
        section_name_map = {}  # Map section GID to section name for task phase assignment
        sections_to_transform = asana_data.get('sections', [])
        if sections_to_transform:
            logger.info(f"Transforming {len(sections_to_transform)} sections to phases...")
            print(f"Transforming {len(sections_to_transform)} sections to phases...")
            for section in sections_to_transform:
                section_name = section.get('name', 'Unknown')
                section_gid = section.get('gid', '')
                
                # Store mapping for task assignment
                if section_gid:
                    section_name_map[section_gid] = section_name
                
                # Create phase from section
                # Sections don't have dates in Asana, so we won't set start_date/end_date
                transformed_phase = {
                    'name': section_name,
                    'type': 'phase',  # Sections become regular phases (not milestones)
                }
                
                # Store section GID for reference (optional, for debugging)
                if section_gid:
                    transformed_phase['section_gid'] = section_gid
                
                # Sections might have created_at, but we typically don't use it for phase dates
                # If needed, we could extract it, but it's usually not meaningful for phase dates
                
                transformed_data['phases'].append(transformed_phase)
                logger.debug(f"  - {section_name} (GID: {section_gid})")
                print(f"  - {section_name} (GID: {section_gid})")
            logger.info(f"✓ Transformed {len(transformed_data['phases'])} sections to phases")
        
        # Add "Misc" phase as default for tasks without sections
        # Check if "Misc" phase already exists (avoid duplicates)
        misc_exists = False
        for phase in transformed_data['phases']:
            phase_name = phase.get('name', '')
            if phase_name.lower().strip() == 'misc':
                misc_exists = True
                break
        
        if not misc_exists:
            misc_phase = {
                'name': 'Misc',
                'type': 'phase',
            }
            transformed_data['phases'].append(misc_phase)
            logger.info("✓ Added default 'Misc' phase for tasks without sections")
        
        # Store section name mapping for use in task transformation
        transformed_data['section_name_map'] = section_name_map
        
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
            print(f"  [{idx}/{len(tasks_to_transform)}] Transforming task: {task_name}")
            
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
            # This is critical: tasks should be assigned to the phase that corresponds to their Asana section
            section = None
            section_gid = None
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
                                    section_gid = section_obj.get('gid', '')
                                elif hasattr(section_obj, 'name'):
                                    section = section_obj.name
                                    section_gid = getattr(section_obj, 'gid', '')
                            break
            
            # Map activity type using category mapping
            activity_type = smart_map_activity_and_tracking(title, category, section)
            if not category:
                filled_activity += 1
            
            # Map project phase
            # Priority: Use section name directly (since sections become phases with the same name)
            # If no section, assign to "Misc" phase (default phase created for tasks without sections)
            if section:
                # Use section name directly - this matches the phase name created from the section
                project_phase = section.strip()
                logger.debug(f"    Task assigned to section/phase: {project_phase}")
            else:
                # Assign to "Misc" phase if no section (don't use smart_map_phase)
                filled_phase += 1
                project_phase = 'Misc'
                logger.debug(f"    Task assigned to 'Misc' phase (no section)")
            
            # Map users
            # Note: Project Manager (PM Name) is already handled at project level via manager_id
            # For task-level fields:
            # - owner_id should be the TASK CREATOR (created_by) if available, otherwise TASK ASSIGNEE
            # - related_users should include the assignee
            
            # Extract created_by information - prefer name from users map if available
            created_by_name = None
            created_by_gid = None
            created_by_obj = task.get('created_by')
            if created_by_obj:
                # Get GID first
                if isinstance(created_by_obj, dict):
                    created_by_gid = created_by_obj.get('gid')
                    created_by_name = created_by_obj.get('name', '')
                elif hasattr(created_by_obj, 'gid'):
                    created_by_gid = created_by_obj.gid
                    created_by_name = created_by_obj.name if hasattr(created_by_obj, 'name') else None
                else:
                    created_by_name = str(created_by_obj) if created_by_obj else None
                
                # If we have users map, try to get name from there (more reliable)
                users_map = asana_data.get('users', {})
                if created_by_gid and created_by_gid in users_map:
                    user_details = users_map[created_by_gid]
                    created_by_name = user_details.get('name', created_by_name)
                    logger.debug(f"    Using created_by name from users map: {created_by_name} (GID: {created_by_gid})")
                
                # Normalize empty strings to None
                if not created_by_name or not str(created_by_name).strip():
                    created_by_name = None
                else:
                    created_by_name = str(created_by_name).strip()
            
            # Task owner_id comes from task creator (created_by) if available, otherwise from assignee
            # If created_by is null, fall back to assignee
            if created_by_name:
                task_owner = validate_user(created_by_name, default_to_tom=False)
                logger.debug(f"    Task owner from created_by: {task_owner} (GID: {created_by_gid})")
            else:
                # Fall back to assignee if created_by is null or invalid
                task_owner = validate_user(assignee, default_to_tom=False)
                logger.debug(f"    Task owner from assignee (created_by is null): {task_owner}")
            
            # PM Name is for reference only (project manager is set at project level)
            pm_for_reference = validate_user(pm_name, default_to_tom=True) if pm_name else None
            
            # Get estimated/actual time (if available in custom fields)
            # NOTE: Must extract this BEFORE setting completion status because Scoro requires
            # completed tasks to have time entries
            # Asana stores time as number_value in minutes, convert to HH:ii:ss format
            estimated_time = extract_time_field_value(task, 'Estimated time') or extract_time_field_value(task, 'Estimated Time')
            
            # Extract actual time from time tracking entries (preferred) or custom fields
            # IMPORTANT: Use Asana Time Tracking Entries API data for accurate actual time
            completed = task.get('completed', False)
            completed_at = task.get('completed_at')
            time_tracking_entries = task.get('time_tracking_entries', [])
            
            # Process time tracking entries from Asana API
            calculated_time_entries = []
            total_duration_minutes = 0
            actual_time = None
            
            if time_tracking_entries:
                for entry in time_tracking_entries:
                    try:
                        # Extract data from time tracking entry
                        duration_minutes = entry.get('duration_minutes', 0)
                        if duration_minutes and duration_minutes > 0:
                            total_duration_minutes += int(duration_minutes)
                            
                            # Get end_datetime (created_at is the end time in Asana)
                            end_datetime_str = entry.get('created_at', '')
                            if not end_datetime_str:
                                continue
                            
                            # Parse end_datetime
                            if 'T' in end_datetime_str:
                                if end_datetime_str.endswith('Z'):
                                    end_dt = datetime.fromisoformat(end_datetime_str.replace('Z', '+00:00'))
                                else:
                                    end_dt = datetime.fromisoformat(end_datetime_str)
                            else:
                                end_dt = datetime.strptime(end_datetime_str.split()[0], '%Y-%m-%d')
                            
                            # Calculate start_datetime from end_datetime - duration
                            start_dt = end_dt - timedelta(minutes=int(duration_minutes))
                            start_datetime_str = start_dt.isoformat()
                            
                            # Convert duration to HH:ii:ss format
                            duration_hhmmss = convert_minutes_to_hhmmss(duration_minutes)
                            
                            # Get user name from created_by
                            user_name = None
                            created_by = entry.get('created_by', {})
                            if isinstance(created_by, dict):
                                user_name = created_by.get('name', '')
                            
                            # Create time entry object for Scoro Time Entries API
                            time_entry = {
                                'start_datetime': start_datetime_str,  # ISO8601 format
                                'end_datetime': end_datetime_str,  # ISO8601 format (created_at from Asana)
                                'duration': duration_hhmmss,  # HH:ii:ss format
                                'is_completed': completed,  # Based on task.completed status
                                'completed_datetime': completed_at if completed else None,  # ISO8601 format
                                'event_type': 'task',  # This is a task time entry
                                'time_entry_type': 'task',  # Time entry type
                                'billable_time_type': 'billable',  # Default to billable
                            }
                            
                            # Add user_name if available (will be resolved by importer)
                            if user_name:
                                time_entry['user_name'] = user_name
                            
                            calculated_time_entries.append(time_entry)
                    except Exception as e:
                        logger.warning(f"    ⚠ Could not process time tracking entry: {e}")
                        continue
                
                # Calculate total actual_time from all entries
                if total_duration_minutes > 0:
                    actual_time = convert_minutes_to_hhmmss(total_duration_minutes)
                    logger.info(f"    ✓ Found {len(calculated_time_entries)} time tracking entries, total duration: {actual_time}")
            
            # Fallback: Extract from custom fields or task-level actual_time_minutes if no tracking entries
            if not actual_time:
                actual_time = extract_time_field_value(task, 'Actual time') or extract_time_field_value(task, 'Actual Time')
                if not actual_time and task.get('actual_time_minutes') is not None:
                    actual_time = convert_minutes_to_hhmmss(task.get('actual_time_minutes'))
            
            # has_actual_time is True if we have actual_time value OR we have time tracking entries
            has_actual_time = (actual_time and str(actual_time).strip()) or len(calculated_time_entries) > 0
            
            # Determine initial task status
            # IMPORTANT: All tasks are created as "planned" (task_status1) first,
            # then time entries are created, and finally the status is updated based on:
            # - If completed AND has calculated_time_entries → task_status9 (Completed)
            #   (If completed but no time entries, a 00:00 time entry is created automatically)
            # - If has calculated_time_entries AND not completed → task_status3 (In progress)
            # - If no calculated_time_entries AND not completed → task_status1 (Planned)
            # This is because Scoro rejects creating tasks as completed without existing time entries.
            
            # Always create tasks as "planned" initially
            status = 'task_status1'  # Scoro site: task_status1 = Planned
            is_completed = False  # Create as not completed initially
            datetime_completed = None  # Don't set completion datetime yet
            
            # Store completion info for later status update in importer
            has_calculated_time_entries = len(calculated_time_entries) > 0
            
            # If task is completed but has no time entries, create a 00:00 time entry
            # This allows us to mark the task as completed in Scoro (which requires time entries)
            if completed and completed_at and not has_calculated_time_entries:
                # Create a dummy 00:00 time entry for completed tasks without time tracking
                # Use completion datetime for the time entry
                completion_dt = None
                try:
                    if isinstance(completed_at, str):
                        if 'T' in completed_at:
                            completion_dt = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                        else:
                            # Date only, use completion date at 00:00:00
                            completion_dt = datetime.strptime(completed_at.split()[0], '%Y-%m-%d')
                    else:
                        completion_dt = completed_at
                except Exception as e:
                    logger.debug(f"    Could not parse completed_at: {completed_at}, error: {e}")
                    # Fallback to current datetime
                    completion_dt = datetime.now()
                
                # Use completion datetime for both start and end (00:00 duration)
                completion_datetime_str = completion_dt.isoformat()
                
                # Get user name from assignee for time entry (assignee is the one doing the work)
                assigned_user = validate_user(assignee, default_to_tom=False)
                user_name = assigned_user if assigned_user else None
                
                # Create 00:00 time entry
                dummy_time_entry = {
                    'start_datetime': completion_datetime_str,  # ISO8601 format
                    'end_datetime': completion_datetime_str,  # ISO8601 format (same as start for 00:00)
                    'duration': '00:00:00',  # HH:ii:ss format - zero duration
                    'is_completed': True,  # Task is completed
                    'completed_datetime': completion_datetime_str,  # ISO8601 format
                    'event_type': 'task',  # This is a task time entry
                    'time_entry_type': 'task',  # Time entry type
                    'billable_time_type': 'billable',  # Default to billable
                }
                
                # Add user_name if available (will be resolved by importer)
                if user_name:
                    dummy_time_entry['user_name'] = user_name
                
                calculated_time_entries.append(dummy_time_entry)
                has_calculated_time_entries = True
                logger.info(f"    Created 00:00 time entry for completed task without time tracking")
            
            if completed and completed_at and has_calculated_time_entries:
                # Store completion info in the time entries for later update
                for time_entry in calculated_time_entries:
                    time_entry['should_complete_task'] = True
                    time_entry['task_completed_at'] = completed_at
                logger.debug(f"    Task will be marked as completed (task_status9) after time entry creation")
            elif has_calculated_time_entries and not completed:
                logger.debug(f"    Task will be marked as in progress (task_status3) after time entry creation")
            
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
            description = task.get('notes', '')
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
            
            # Set owner_id - the person responsible for THIS specific task
            # According to Scoro API: owner_id is "User ID of the user that is responsible for the event"
            # This should be the task creator (created_by) if available, otherwise the task assignee
            # NOT the project manager
            if task_owner:
                transformed_task['owner_name'] = task_owner  # Store name, importer will resolve to owner_id
                logger.debug(f"    Task owner (owner_id): {task_owner}")
            
            # Set related_users - ONLY the primary assignee should be in related_users
            # According to Scoro API: related_users is "Array of user IDs that the task is assigned to"
            # This should contain ONLY the assignee, NOT followers/collaborators
            # Followers/collaborators are NOT supported as assignees in Scoro
            # Note: related_users is always the assignee, even if owner_id comes from created_by
            assigned_user = validate_user(assignee, default_to_tom=False)
            if assigned_user:
                # Only the primary assignee goes into related_users
                transformed_task['assigned_to_name'] = [assigned_user]  # Store as list, importer will resolve to related_users array
                logger.debug(f"    Task related_users (assignee only): {assigned_user}")
            
            # Note: Followers/collaborators from Asana are NOT migrated to Scoro
            # Scoro's related_users field is for assignees only, not followers
            if follower_names:
                logger.debug(f"    Task followers (not migrated to Scoro): {follower_names}")
            
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
            if calculated_time_entries:
                transformed_task['calculated_time_entries'] = calculated_time_entries
                logger.debug(f"    Added {len(calculated_time_entries)} calculated time entries to task")
            
            # Store completion info for status update in importer
            # These fields help the importer determine the final status after time entries are created
            transformed_task['_asana_completed'] = completed
            transformed_task['_asana_completed_at'] = completed_at
            transformed_task['_has_calculated_time_entries'] = has_calculated_time_entries
            
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

