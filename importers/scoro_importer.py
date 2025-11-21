"""
Import functionality for importing transformed data into Scoro
"""
import re
from typing import Dict, Optional

from clients.scoro_client import ScoroClient
from clients.asana_client import AsanaClient
from models import MigrationSummary
from utils import logger, process_batch
from config import DEFAULT_BATCH_SIZE, TEST_MODE_MAX_TASKS

def import_to_scoro(scoro_client: ScoroClient, transformed_data: Dict, summary: MigrationSummary, 
                     batch_size: int = DEFAULT_BATCH_SIZE, asana_client: Optional[AsanaClient] = None,
                     max_tasks: Optional[int] = TEST_MODE_MAX_TASKS, asana_data: Optional[Dict] = None) -> Dict:
    """
    Import transformed data into Scoro with batch processing support
    
    Args:
        scoro_client: Initialized ScoroClient instance
        transformed_data: Transformed data dictionary
        summary: Migration summary tracker
        batch_size: Number of items to process in each batch
        asana_client: Optional AsanaClient instance for fetching user details by GID
        max_tasks: Optional limit on number of tasks to migrate (for testing). 
                   Set to None to migrate all tasks. Defaults to TEST_MODE_MAX_TASKS from config.
        asana_data: Optional original Asana export data containing users map for GID lookups
    
    Returns:
        Dictionary containing import results
    """
    logger.info("="*60)
    logger.info("Starting import to Scoro")
    logger.info("="*60)
    
    import_results = {
        'project': None,
        'tasks': [],
        'milestones': [],
        'errors': []
    }
    
    try:
        # Get or create company for the project
        # In Scoro, projects must be associated with a company/client record
        # This is different from Asana where projects are organized under portfolios
        company = None
        company_name = transformed_data.get('company_name')
        is_client_project = transformed_data.get('is_client_project', True)
        
        # For client projects, we need a company (use project name as company name)
        # For team member projects, we may still need a company (Scoro requirement)
        if company_name:
            logger.info(f"Getting or creating company: {company_name}...")
            try:
                company = scoro_client.get_or_create_company(company_name)
                company_id = company.get('id') or company.get('company_id') or company.get('client_id') or company.get('contact_id')
                logger.info(f"✓ Company ready: {company.get('name', 'Unknown')} (ID: {company_id})")
            except Exception as e:
                error_msg = f"Failed to get/create company '{company_name}': {e}"
                logger.error(f"✗ {error_msg}")
                import_results['errors'].append(error_msg)
                summary.add_failure(error_msg)
                # Continue anyway - project creation might still work
        else:
            # Try to extract company name from project name or tasks
            project_name = transformed_data.get('project', {}).get('name', '')
            if project_name:
                # Use project name as company name (especially for client projects)
                logger.info(f"No explicit company name, using project name as company: {project_name}")
                try:
                    company = scoro_client.get_or_create_company(project_name)
                    company_id = company.get('id') or company.get('company_id') or company.get('client_id') or company.get('contact_id')
                    logger.info(f"✓ Company ready: {company.get('name', 'Unknown')} (ID: {company_id})")
                except Exception as e:
                    logger.warning(f"Could not create company from project name: {e}")
            else:
                logger.warning("No company name available. Project may fail to create if Scoro requires company association.")
        
        # Create project
        if 'project' in transformed_data:
            logger.info("Creating project in Scoro...")
            try:
                project_data = transformed_data['project'].copy()
                
                # Map 'name' to 'project_name' (Scoro API requirement)
                if 'name' in project_data and 'project_name' not in project_data:
                    project_data['project_name'] = project_data.pop('name')
                
                # Link project to company if we have one
                # In Scoro, projects must be linked to a company/client record
                if company:
                    # Extract company ID - try multiple possible field names
                    company_id = (
                        company.get('id') or 
                        company.get('company_id') or 
                        company.get('client_id') or
                        company.get('contact_id')
                    )
                    if company_id:
                        project_data['company_id'] = company_id
                        logger.info(f"  Linking project to company ID: {company_id}")
                    else:
                        logger.warning(f"  Company record found but no ID available: {company}")
                
                # Resolve and set project manager (PM)
                manager_name = project_data.get('manager_name')
                if manager_name:
                    logger.info(f"  Resolving project manager: {manager_name}...")
                    try:
                        manager = scoro_client.find_user_by_name(manager_name)
                        if manager:
                            manager_id = manager.get('id')
                            if manager_id:
                                project_data['manager_id'] = manager_id
                                manager_full_name = manager.get('full_name') or f"{manager.get('firstname', '')} {manager.get('lastname', '')}".strip()
                                logger.info(f"  ✓ Set project manager: {manager_full_name} (ID: {manager_id})")
                            else:
                                logger.warning(f"  Manager found but no ID available: {manager}")
                        else:
                            logger.warning(f"  Could not find manager '{manager_name}' in Scoro users")
                    except Exception as e:
                        logger.warning(f"  Error resolving manager '{manager_name}': {e}")
                        # Continue without manager_id
                else:
                    logger.debug("  No manager name found in project data")
                
                # Remove manager_name from project_data as it's not a valid Scoro API field
                project_data.pop('manager_name', None)
                
                # Resolve and set project members (project team)
                # Asana project members → Scoro project_users array
                project_members = project_data.get('members', [])
                if project_members:
                    logger.info(f"  Resolving {len(project_members)} project members...")
                    project_user_ids = []
                    resolved_count = 0
                    failed_count = 0
                    
                    for member_name in project_members:
                        if not member_name or not str(member_name).strip():
                            continue
                        
                        try:
                            member = scoro_client.find_user_by_name(str(member_name).strip())
                            if member:
                                member_id = member.get('id')
                                if member_id:
                                    project_user_ids.append(member_id)
                                    member_full_name = member.get('full_name') or f"{member.get('firstname', '')} {member.get('lastname', '')}".strip()
                                    logger.debug(f"    ✓ Resolved member '{member_name}' to user_id: {member_id} ({member_full_name})")
                                    resolved_count += 1
                                else:
                                    logger.warning(f"    Member '{member_name}' found but no ID available")
                                    failed_count += 1
                            else:
                                logger.warning(f"    Could not find member '{member_name}' in Scoro users")
                                failed_count += 1
                        except Exception as e:
                            logger.warning(f"    Error resolving member '{member_name}': {e}")
                            failed_count += 1
                    
                    if project_user_ids:
                        project_data['project_users'] = project_user_ids
                        logger.info(f"  ✓ Set {resolved_count} project members (IDs: {project_user_ids})")
                    
                    if failed_count > 0:
                        logger.warning(f"  ⚠ Failed to resolve {failed_count} project members")
                else:
                    logger.debug("  No project members found in project data")
                
                # Remove members from project_data as it's not a valid Scoro API field (we use project_users)
                project_data.pop('members', None)
                
                project = scoro_client.create_project(project_data)
                import_results['project'] = project
                summary.add_success()
                
                # Extract project ID for logging and later use
                project_id_for_log = (
                    project.get('project_id') or 
                    project.get('id') or
                    project.get('projectId')
                )
                project_name = project.get('project_name') or project.get('name', 'Unknown')
                logger.info(f"✓ Project created successfully: {project_name}")
                if project_id_for_log:
                    logger.debug(f"  Project ID: {project_id_for_log}")
                else:
                    logger.warning(f"  Project ID not found in response. Available keys: {list(project.keys())}")
            except Exception as e:
                error_msg = f"Failed to create project: {e}"
                logger.error(f"✗ {error_msg}")
                import_results['errors'].append(error_msg)
                summary.add_failure(error_msg)
        else:
            logger.warning("No project data found in transformed_data")
        
        # Create milestones (phases) - include them in project modification
        milestones_to_import = transformed_data.get('milestones', [])
        if milestones_to_import and import_results['project']:
            # Extract project ID - try multiple possible field names (Scoro API may use different field names)
            project_id = (
                import_results['project'].get('project_id') or 
                import_results['project'].get('id') or
                import_results['project'].get('projectId')
            )
            if project_id:
                logger.info(f"Adding {len(milestones_to_import)} milestones (phases) to project in Scoro...")
                logger.debug(f"  Using project ID: {project_id}")
                try:
                    # Transform milestones to Scoro phase format
                    phases = []
                    for milestone_data in milestones_to_import:
                        phase_data = {}
                        
                        # Map 'name' to 'title' (Scoro API requirement for phases)
                        phase_data['title'] = milestone_data.get('title') or milestone_data.get('name', 'Unknown')
                        phase_data['type'] = 'milestone'  # Use 'milestone' type for milestones
                        
                        # Add dates if available
                        if milestone_data.get('due_date'):
                            phase_data['end_date'] = milestone_data['due_date']
                        
                        if milestone_data.get('start_date'):
                            phase_data['start_date'] = milestone_data['start_date']
                        
                        phases.append(phase_data)
                        logger.info(f"  - {phase_data['title']}")
                    
                    # Modify project to add phases
                    project_update_data = {'phases': phases}
                    updated_project = scoro_client.create_project(project_update_data, project_id=project_id)
                    
                    # Extract phases from response if available
                    if 'phases' in updated_project:
                        import_results['milestones'] = updated_project['phases']
                    else:
                        # If phases aren't in response, mark them as created anyway
                        import_results['milestones'] = [{'title': p['title']} for p in phases]
                    
                    summary.add_success()
                    logger.info(f"✓ Successfully added {len(phases)} milestones to project")
                except Exception as e:
                    error_msg = f"Failed to add milestones to project: {e}"
                    logger.error(f"✗ {error_msg}")
                    import_results['errors'].append(error_msg)
                    summary.add_failure(error_msg)
            else:
                logger.warning("Cannot add milestones: Project ID not available")
                logger.debug(f"  Project response keys: {list(import_results['project'].keys()) if import_results['project'] else 'No project'}")
        elif milestones_to_import and not import_results['project']:
            logger.warning(f"Cannot create {len(milestones_to_import)} milestones: Project creation failed")
        
        # Create tasks with batch processing
        # Extract project ID - try multiple possible field names (Scoro API may use different field names)
        project_id = None
        if import_results['project']:
            project_id = (
                import_results['project'].get('project_id') or 
                import_results['project'].get('id') or
                import_results['project'].get('projectId')
            )
        
        # Extract company ID from the company we created/found earlier
        # This avoids re-searching for the company (which has pagination limits)
        project_company_id = None
        if company:
            project_company_id = (
                company.get('id') or 
                company.get('company_id') or 
                company.get('client_id') or 
                company.get('contact_id')
            )
            if project_company_id:
                logger.debug(f"Will reuse company ID {project_company_id} for tasks")
        
        tasks_to_import = transformed_data.get('tasks', [])
        
        # Apply test mode limit if specified
        original_task_count = len(tasks_to_import)
        if max_tasks is not None and max_tasks > 0 and len(tasks_to_import) > max_tasks:
            tasks_to_import = tasks_to_import[:max_tasks]
            logger.info(f"⚠ TEST MODE: Limiting task migration to {max_tasks} tasks (out of {original_task_count} total tasks)")
        
        if tasks_to_import:
            logger.info(f"Creating {len(tasks_to_import)} tasks in Scoro (batch size: {batch_size})...")
            
            # Process tasks in batches
            task_batches = process_batch(tasks_to_import, batch_size)
            total_batches = len(task_batches)
            
            for batch_idx, task_batch in enumerate(task_batches, 1):
                logger.info(f"Processing batch {batch_idx}/{total_batches} ({len(task_batch)} tasks)...")
                
                for idx, task_data in enumerate(task_batch, 1):
                    task_name = task_data.get('title', task_data.get('name', 'Unknown'))
                    global_idx = (batch_idx - 1) * batch_size + idx
                    logger.info(f"  [{global_idx}/{len(tasks_to_import)}] Creating task: {task_name}")
                    try:
                        # Extract stories/comments before cleaning task_data
                        stories = task_data.get('stories', [])
                        
                        # Link task to project if project_id is available
                        if project_id:
                            task_data['project_id'] = project_id
                            logger.debug(f"    Linked to project ID: {project_id}")
                        
                        # Resolve name fields to IDs before cleaning task_data
                        # - owner_name -> owner_id (Integer)
                        owner_name = task_data.get('owner_name')
                        if owner_name:
                            try:
                                owner = scoro_client.find_user_by_name(owner_name)
                                if owner:
                                    owner_id = owner.get('id')
                                    if owner_id:
                                        task_data['owner_id'] = owner_id
                                        owner_full_name = owner.get('full_name') or f"{owner.get('firstname', '')} {owner.get('lastname', '')}".strip()
                                        logger.debug(f"    Resolved owner '{owner_name}' to owner_id: {owner_id} ({owner_full_name})")
                                    else:
                                        logger.warning(f"    Owner '{owner_name}' found but no ID available")
                                else:
                                    logger.warning(f"    Could not find owner '{owner_name}' in Scoro users")
                            except Exception as e:
                                logger.warning(f"    Error resolving owner '{owner_name}': {e}")
                        
                        # - assigned_to_name -> related_users (Array of user IDs)
                        assigned_to_name = task_data.get('assigned_to_name')
                        if assigned_to_name:
                            try:
                                # Handle both single name (string) and multiple names (list)
                                assigned_names = assigned_to_name if isinstance(assigned_to_name, list) else [assigned_to_name]
                                related_user_ids = []
                                
                                for name in assigned_names:
                                    if not name or not str(name).strip():
                                        continue
                                    user = scoro_client.find_user_by_name(str(name).strip())
                                    if user:
                                        user_id = user.get('id')
                                        if user_id:
                                            related_user_ids.append(user_id)
                                            user_full_name = user.get('full_name') or f"{user.get('firstname', '')} {user.get('lastname', '')}".strip()
                                            logger.debug(f"    Resolved assigned user '{name}' to user_id: {user_id} ({user_full_name})")
                                        else:
                                            logger.warning(f"    Assigned user '{name}' found but no ID available")
                                    else:
                                        logger.warning(f"    Could not find assigned user '{name}' in Scoro users")
                                
                                if related_user_ids:
                                    task_data['related_users'] = related_user_ids
                                    logger.debug(f"    Set related_users: {related_user_ids}")
                            except Exception as e:
                                logger.warning(f"    Error resolving assigned users '{assigned_to_name}': {e}")
                        
                        # - project_phase_name -> project_phase_id (Integer)
                        project_phase_name = task_data.get('project_phase_name')
                        if project_phase_name and project_id:
                            try:
                                phase = scoro_client.find_phase_by_name(project_phase_name, project_id=project_id)
                                if phase:
                                    phase_id = phase.get('id') or phase.get('phase_id')
                                    if phase_id:
                                        task_data['project_phase_id'] = phase_id
                                        phase_title = phase.get('title') or phase.get('name', 'Unknown')
                                        logger.debug(f"    Resolved phase '{project_phase_name}' to project_phase_id: {phase_id} ({phase_title})")
                                    else:
                                        logger.warning(f"    Phase '{project_phase_name}' found but no ID available")
                                else:
                                    logger.warning(f"    Could not find phase '{project_phase_name}' in project {project_id}")
                            except Exception as e:
                                logger.warning(f"    Error resolving phase '{project_phase_name}': {e}")
                        elif project_phase_name and not project_id:
                            logger.warning(f"    Cannot resolve phase '{project_phase_name}': Project ID not available")
                        
                        # - company_name -> company_id (Integer)
                        # Note: Company is usually set at project level, but can be overridden at task level
                        # First, try to use the company ID from the project (avoids re-searching with pagination issues)
                        company_name = task_data.get('company_name')
                        if company_name:
                            # Check if the task's company matches the project's company
                            # If so, reuse the project_company_id to avoid re-searching (which has pagination limits)
                            if project_company_id and company_name == transformed_data.get('company_name'):
                                task_data['company_id'] = project_company_id
                                logger.debug(f"    Reused project company_id: {project_company_id} for company '{company_name}'")
                            else:
                                # Different company than project - need to search for it
                                try:
                                    company_lookup = scoro_client.find_company_by_name(company_name)
                                    if company_lookup:
                                        company_id = company_lookup.get('id') or company_lookup.get('company_id') or company_lookup.get('client_id') or company_lookup.get('contact_id')
                                        if company_id:
                                            task_data['company_id'] = company_id
                                            logger.debug(f"    Resolved company '{company_name}' to company_id: {company_id}")
                                        else:
                                            logger.warning(f"    Company '{company_name}' found but no ID available")
                                    else:
                                        logger.warning(f"    Could not find company '{company_name}' in Scoro companies")
                                except Exception as e:
                                    logger.warning(f"    Error resolving company '{company_name}': {e}")
                        
                        # Remove fields that Scoro might not accept (metadata and name-only fields)
                        # Exclude: internal tracking fields, name-only fields (already resolved to IDs), 
                        # and fields not in Scoro Tasks API reference
                        # Note: 'stories' and 'calculated_time_entry' are excluded from task creation but will be processed separately
                        task_data_clean = {k: v for k, v in task_data.items() 
                                         if k not in ['asana_gid', 'asana_permalink', 'dependencies', 'num_subtasks', 
                                                      'attachment_count', 'attachment_refs', 'followers',
                                                      'owner_name', 'assigned_to_name', 'project_phase_name', 
                                                      'project_name', 'company_name', 'tags', 'is_milestone', 'stories', 'calculated_time_entry']}
                        
                        # Map 'title' to 'event_name' (Scoro API requirement)
                        if 'title' in task_data_clean and 'event_name' not in task_data_clean:
                            task_data_clean['event_name'] = task_data_clean.pop('title')
                        
                        # Create the task
                        task = scoro_client.create_task(task_data_clean)
                        import_results['tasks'].append(task)
                        summary.add_success()
                        logger.info(f"    ✓ Task created: {task_name}")
                        
                        # Extract task ID from response (try multiple possible field names)
                        # Scoro API may return task ID in different fields
                        scoro_task_id = None
                        for field_name in ['event_id', 'task_id', 'id', 'eventId', 'taskId']:
                            task_id_value = task.get(field_name)
                            if task_id_value is not None:
                                # Convert to int if it's a valid number
                                try:
                                    task_id_int = int(task_id_value)
                                    if task_id_int > 0:  # Valid task IDs should be positive
                                        scoro_task_id = task_id_int
                                        break
                                except (ValueError, TypeError):
                                    continue
                        
                        # Create time entry if task has calculated_time_entry
                        # This happens for completed tasks that had no time entries in Asana
                        calculated_time_entry = task_data.get('calculated_time_entry')
                        if calculated_time_entry and scoro_task_id is not None:
                            try:
                                logger.info(f"    Creating time entry for completed task...")
                                
                                # Prepare time entry data for Scoro API
                                time_entry_data = {
                                    'event_id': scoro_task_id,
                                    'event_type': calculated_time_entry.get('event_type', 'task'),
                                    'time_entry_type': calculated_time_entry.get('time_entry_type', 'task'),
                                    'start_datetime': calculated_time_entry.get('start_datetime'),
                                    'end_datetime': calculated_time_entry.get('end_datetime'),
                                    'duration': calculated_time_entry.get('duration'),
                                    'is_completed': calculated_time_entry.get('is_completed', True),
                                    'completed_datetime': calculated_time_entry.get('completed_datetime'),
                                    'billable_time_type': calculated_time_entry.get('billable_time_type', 'billable'),
                                }
                                
                                # Resolve user_id from user_name if provided
                                user_name = calculated_time_entry.get('user_name')
                                if user_name:
                                    try:
                                        user = scoro_client.find_user_by_name(user_name)
                                        if user:
                                            user_id = user.get('id')
                                            if user_id:
                                                time_entry_data['user_id'] = user_id
                                                logger.debug(f"      Resolved time entry user '{user_name}' to user_id: {user_id}")
                                            else:
                                                logger.warning(f"      Time entry user '{user_name}' found but no ID available")
                                        else:
                                            logger.warning(f"      Could not find time entry user '{user_name}' in Scoro users")
                                    except Exception as e:
                                        logger.warning(f"      Error resolving time entry user '{user_name}': {e}")
                                
                                # Create time entry via Scoro Time Entries API
                                time_entry = scoro_client.create_time_entry(time_entry_data)
                                logger.info(f"    ✓ Time entry created: {calculated_time_entry.get('duration')} hours")
                                logger.debug(f"      Time entry ID: {time_entry.get('time_entry_id', 'Unknown')}")
                                
                                # Now update the task to mark it as completed (if needed)
                                if calculated_time_entry.get('should_complete_task'):
                                    try:
                                        logger.info(f"    Marking task as completed...")
                                        task_completed_at = calculated_time_entry.get('task_completed_at')
                                        
                                        # Prepare task update data
                                        task_update_data = {
                                            'is_completed': True,
                                            'status': 'task_status5',  # Completed status
                                        }
                                        
                                        # Add completion datetime if available
                                        if task_completed_at:
                                            if isinstance(task_completed_at, str):
                                                try:
                                                    if 'T' not in task_completed_at:
                                                        task_completed_at = f"{task_completed_at}T00:00:00"
                                                    task_update_data['datetime_completed'] = task_completed_at
                                                except Exception as e:
                                                    logger.debug(f"      Could not parse datetime_completed: {e}")
                                        
                                        # Update task via Scoro Tasks API
                                        updated_task = scoro_client.create_task(task_update_data, task_id=scoro_task_id)
                                        logger.info(f"    ✓ Task marked as completed")
                                        
                                    except Exception as e:
                                        logger.warning(f"    ⚠ Failed to mark task as completed: {e}")
                                
                            except Exception as e:
                                # Log warning but don't fail the entire task
                                logger.warning(f"    ⚠ Failed to create time entry for task: {e}")
                        elif calculated_time_entry and not scoro_task_id:
                            logger.warning(f"    ⚠ Cannot create time entry: Task ID not available in response")
                        
                        # Create comments separately via Scoro Comments API
                        if stories and scoro_task_id is not None:
                            # Filter only comment-type stories
                            comment_stories = [s for s in stories if isinstance(s, dict) and s.get('type') == 'comment']
                            
                            if comment_stories:
                                logger.info(f"    Creating {len(comment_stories)} comments for task...")
                                comments_created = 0
                                comments_failed = 0
                                
                                for story in comment_stories:
                                    try:
                                        comment_text = story.get('text', '').strip()
                                        if not comment_text:
                                            continue
                                        
                                        # Clean HTML from comment text if present
                                        comment_text = re.sub(r'<[^>]+>', '', comment_text).strip()
                                        if not comment_text:
                                            continue
                                        
                                        # Extract author information
                                        created_by = story.get('created_by', {})
                                        author_name = None
                                        author_email = None
                                        user_gid = None
                                        
                                        if isinstance(created_by, dict):
                                            author_name = created_by.get('name', '')
                                            user_gid = created_by.get('gid')
                                            
                                            # If name is not available but gid is, look up user in Asana export users map first
                                            if not author_name and user_gid and asana_data:
                                                users_map = asana_data.get('users', {})
                                                if user_gid in users_map:
                                                    user_details = users_map[user_gid]
                                                    author_name = user_details.get('name', '')
                                                    author_email = user_details.get('email', '')
                                                    if author_name:
                                                        logger.debug(f"      Found author '{author_name}' (email: {author_email}) from users map for GID: {user_gid}")
                                            
                                            # If still no name and we have asana_client, try API fetch as fallback
                                            if not author_name and user_gid and asana_client is not None:
                                                try:
                                                    user_details = asana_client.get_user_details(str(user_gid))
                                                    if user_details:
                                                        author_name = user_details.get('name', '')
                                                        author_email = user_details.get('email', '')
                                                        if author_name:
                                                            logger.debug(f"      Fetched author name '{author_name}' from Asana API for user GID: {user_gid}")
                                                except Exception as e:
                                                    logger.debug(f"      Could not fetch user details for GID {user_gid}: {e}")
                                        elif hasattr(created_by, 'name'):
                                            author_name = created_by.name
                                            if hasattr(created_by, 'gid'):
                                                user_gid = created_by.gid
                                        
                                        # Resolve user_id from author name or email
                                        user_id = None
                                        if author_name:
                                            try:
                                                user = scoro_client.find_user_by_name(author_name)
                                                if user:
                                                    user_id = user.get('id')
                                                    if user_id is not None:
                                                        logger.debug(f"      Resolved comment author '{author_name}' to user_id: {user_id}")
                                            except Exception as e:
                                                logger.debug(f"      Could not resolve user '{author_name}': {e}")
                                        
                                        # If user_id not found by name, try email
                                        if user_id is None and author_email:
                                            try:
                                                user = scoro_client.find_user_by_name(author_email)
                                                if user:
                                                    user_id = user.get('id')
                                                    if user_id is not None:
                                                        logger.debug(f"      Resolved comment author by email '{author_email}' to user_id: {user_id}")
                                            except Exception as e:
                                                logger.debug(f"      Could not resolve user by email '{author_email}': {e}")
                                        
                                        # Skip comment if user_id is not available or invalid
                                        # API requires user_id with apiKey, and it must be a valid positive integer
                                        if user_id is None or not isinstance(user_id, int) or user_id <= 0:
                                            author_info = author_name or author_email or (f"GID: {user_gid}" if user_gid else "Unknown")
                                            logger.warning(f"      ⚠ Skipping comment: Could not resolve comment author '{author_info}' in Scoro (user_id: {user_id}). Skipping to avoid incorrect attribution.")
                                            comments_failed += 1
                                            continue
                                        
                                        # Create comment via Scoro Comments API
                                        # Module is "tasks", object_id is the task ID
                                        scoro_client.create_comment(
                                            module='tasks',
                                            object_id=scoro_task_id,
                                            comment_text=comment_text,
                                            user_id=user_id
                                        )
                                        comments_created += 1
                                        logger.debug(f"      ✓ Comment created by {author_name}")
                                        
                                    except Exception as e:
                                        comments_failed += 1
                                        logger.warning(f"      ⚠ Failed to create comment: {e}")
                                        # Don't fail the entire task if comment creation fails
                                
                                if comments_created > 0:
                                    logger.info(f"    ✓ Created {comments_created} comments for task")
                                if comments_failed > 0:
                                    logger.warning(f"    ⚠ Failed to create {comments_failed} comments for task")
                            elif stories:
                                logger.debug(f"    No comment-type stories found (found {len(stories)} total stories)")
                        elif stories and not scoro_task_id:
                            logger.warning(f"    ⚠ Cannot create comments: Task ID not available in response")
                            logger.debug(f"    Task response keys: {list(task.keys())}")
                    except Exception as e:
                        error_msg = f"Failed to create task '{task_name}': {e}"
                        logger.error(f"    ✗ {error_msg}")
                        import_results['errors'].append(error_msg)
                        summary.add_failure(error_msg)
        
        logger.info("="*60)
        logger.info(f"✓ Import completed!")
        logger.info(f"  Project: {'Created' if import_results['project'] else 'Failed'}")
        logger.info(f"  Milestones created: {len(import_results['milestones'])}")
        logger.info(f"  Tasks created: {len(import_results['tasks'])}")
        logger.info(f"  Tasks failed: {len([e for e in import_results['errors'] if 'task' in e.lower()])}")
        logger.info(f"  Total errors: {len(import_results['errors'])}")
        logger.info("="*60)
        return import_results
        
    except Exception as e:
        error_msg = f"Error during import to Scoro: {e}"
        logger.error(error_msg)
        summary.add_failure(error_msg)
        raise

