"""
Export functionality for extracting project data from Asana
"""
from datetime import datetime
from typing import Dict, Optional

from clients.asana_client import AsanaClient
from utils import logger
from config import TEST_MODE_MAX_TASKS


def export_asana_project(asana_client: AsanaClient, project_name: Optional[str] = None, 
                         project_gid: Optional[str] = None, workspace_gid: Optional[str] = None,
                         max_tasks: Optional[int] = TEST_MODE_MAX_TASKS) -> Optional[Dict]:
    """
    Export project data from Asana
    
    Args:
        asana_client: Initialized AsanaClient instance
        project_name: Name of the project to export (optional if project_gid is provided)
        project_gid: Direct project GID to export (optional if project_name is provided)
        workspace_gid: Workspace GID (optional, used when searching by name)
        max_tasks: Optional limit on number of tasks to export (for testing).
                   Set to None to export all tasks. Defaults to TEST_MODE_MAX_TASKS from config.
    
    Returns:
        Dictionary containing project data, tasks, sections, etc.
    """
    try:
        # Determine project_gid - either use provided GID or search by name
        if project_gid:
            # Use provided project GID directly
            project_gid = str(project_gid)
            logger.info(f"Starting export using provided project GID: {project_gid}")
            print(f"Starting export using provided project GID: {project_gid}")
            
            logger.info("Step 1/5: Retrieving project details using GID...")
            print("Step 1/5: Retrieving project details using GID...")
            
            
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
        
        # Get sections first (needed to fetch tasks per section)
        step_num = "3/5" if project_name else "2/5"
        logger.info(f"Step {step_num}: Retrieving project sections...")
        sections = asana_client.get_project_sections(project_gid)
        logger.info(f"✓ Found {len(sections)} sections in project")
        
        # Get tasks per section and assign section names
        step_num = "4/5" if project_name else "3/5"
        logger.info(f"Step {step_num}: Retrieving tasks from each section...")
        print(f"Step {step_num}: Retrieving tasks from each section...")
        
        # Track tasks by GID to handle duplicates (if a task appears in multiple sections)
        tasks_by_gid = {}
        
        # Fetch tasks from each section
        for idx, section in enumerate(sections, 1):
            section_gid = section.get('gid', '')
            section_name = section.get('name', 'Unknown')
            
            if not section_gid:
                logger.warning(f"  Section {idx} has no GID, skipping")
                continue
            
            logger.info(f"  [{idx}/{len(sections)}] Fetching tasks from section: '{section_name}' (GID: {section_gid})")
            print(f"  [{idx}/{len(sections)}] Fetching tasks from section: '{section_name}'")
            
            try:
                section_tasks = asana_client.get_tasks_for_section(section_gid)
                logger.info(f"    Found {len(section_tasks)} tasks in section '{section_name}'")
                
                # Assign section name to each task
                for task in section_tasks:
                    task_gid = task.get('gid', '')
                    if task_gid:
                        # If task already exists (from another section), keep the first one
                        # but log it for reference
                        if task_gid in tasks_by_gid:
                            existing_section = tasks_by_gid[task_gid].get('_assigned_section_name', 'Unknown')
                            logger.debug(f"    Task '{task.get('name', 'Unknown')}' (GID: {task_gid}) already found in section '{existing_section}', keeping first assignment")
                        else:
                            # Assign section name to task
                            task['_assigned_section_name'] = section_name
                            task['_assigned_section_gid'] = section_gid
                            tasks_by_gid[task_gid] = task
            except Exception as e:
                logger.warning(f"    ⚠ Error fetching tasks from section '{section_name}': {e}")
                continue
        
        # Convert to list
        tasks = list(tasks_by_gid.values())
        original_task_count = len(tasks)
        
        logger.info(f"✓ Found {len(tasks)} unique tasks across all sections")
        
        # Apply test mode limit if specified
        if max_tasks is not None and max_tasks > 0 and len(tasks) > max_tasks:
            tasks = tasks[:max_tasks]
            logger.info(f"⚠ TEST MODE: Limiting task export to {max_tasks} tasks (out of {original_task_count} total tasks)")
        
        # Get milestones
        step_num = "5/8" if project_name else "4/8"
        logger.info(f"Step {step_num}: Retrieving project milestones...")
        milestones = asana_client.get_project_milestones(project_gid)
        logger.info(f"✓ Found {len(milestones)} milestones in project")
        
        # Get detailed task information with subtasks, dependencies, attachments, and comments
        step_num = "6/8" if project_name else "5/8"
        logger.info(f"Step {step_num}: Retrieving detailed task information...")
        detailed_tasks = []
        total_tasks = len(tasks)
        for idx, task in enumerate(tasks, 1):
            try:
                task_name = task.get('name', task.get('gid', 'Unknown'))
                task_gid = task.get('gid', '')
                logger.info(f"  [{idx}/{total_tasks}] Retrieving details for task: {task_name}")
                print(f"  [{idx}/{total_tasks}] Retrieving details for task: {task_name}")
                
                # Preserve assigned section information before getting details
                assigned_section_name = task.get('_assigned_section_name')
                assigned_section_gid = task.get('_assigned_section_gid')
                
                # Get full detailed task info (includes dependencies, tags, etc.)
                detailed_task = asana_client.get_task_details(task_gid)
                
                # Restore assigned section information (get_task_details may overwrite it)
                if assigned_section_name:
                    detailed_task['_assigned_section_name'] = assigned_section_name
                if assigned_section_gid:
                    detailed_task['_assigned_section_gid'] = assigned_section_gid
                
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
                
                # Get time tracking entries
                time_tracking_entries = asana_client.get_time_tracking_entries(task_gid)
                detailed_task['time_tracking_entries'] = time_tracking_entries
                
                detailed_tasks.append(detailed_task)
                logger.debug(f"    ✓ Retrieved details for task: {task_name} (subtasks: {len(detailed_task.get('subtasks', []))}, attachments: {len(attachments)}, comments: {len(stories)}, time entries: {len(time_tracking_entries)})")
            except Exception as e:
                logger.warning(f"    ⚠ Could not retrieve details for task {task.get('name', task.get('gid'))}: {e}")
                # Fall back to basic task data (assigned section info is already in task)
                task['subtasks'] = []
                task['attachments'] = []
                task['stories'] = []
                task['time_tracking_entries'] = []
                detailed_tasks.append(task)
        
        # Build task dependency map
        step_num = "7/8" if project_name else "6/8"
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
        
        # Gather user information from GIDs
        step_num = "8/8" if project_name else "7/8"
        logger.info(f"Step {step_num}: Gathering user information from Asana...")
        user_gids = set()
        
        # First, add project owner and members to ensure they're always included
        # This is important for TEST MODE where owner/members might not appear in limited task set
        project_owner = project_details.get('owner')
        if project_owner:
            if isinstance(project_owner, dict):
                owner_gid = project_owner.get('gid')
            elif hasattr(project_owner, 'gid'):
                owner_gid = project_owner.gid
            else:
                owner_gid = None
            if owner_gid:
                user_gids.add(owner_gid)
                logger.debug(f"  Added project owner GID to users: {owner_gid}")
        
        project_members = project_details.get('members', [])
        if project_members:
            for member in project_members:
                if isinstance(member, dict):
                    member_gid = member.get('gid')
                elif hasattr(member, 'gid'):
                    member_gid = member.gid
                else:
                    member_gid = None
                if member_gid:
                    user_gids.add(member_gid)
            logger.debug(f"  Added {len(project_members)} project members GIDs to users")
        
        # Collect all user GIDs from tasks (assignees and followers)
        for task in detailed_tasks:
            # Get assignee GID
            assignee = task.get('assignee')
            if assignee:
                if isinstance(assignee, dict):
                    assignee_gid = assignee.get('gid')
                elif hasattr(assignee, 'gid'):
                    assignee_gid = assignee.gid
                else:
                    assignee_gid = None
                if assignee_gid:
                    user_gids.add(assignee_gid)
            
            # Get follower GIDs
            followers = task.get('followers', [])
            if followers:
                for follower in followers:
                    if isinstance(follower, dict):
                        follower_gid = follower.get('gid')
                    elif hasattr(follower, 'gid'):
                        follower_gid = follower.gid
                    else:
                        follower_gid = None
                    if follower_gid:
                        user_gids.add(follower_gid)
            
            # Get user GIDs from stories/comments (created_by)
            stories = task.get('stories', [])
            if stories:
                for story in stories:
                    created_by = story.get('created_by') if isinstance(story, dict) else None
                    if created_by:
                        if isinstance(created_by, dict):
                            creator_gid = created_by.get('gid')
                        elif hasattr(created_by, 'gid'):
                            creator_gid = created_by.gid
                        else:
                            creator_gid = None
                        if creator_gid:
                            user_gids.add(creator_gid)
        
        # Get user details for all unique GIDs
        users_map = {}  # Map GID -> user details
        if user_gids:
            logger.info(f"  Found {len(user_gids)} unique users, retrieving details...")
            for user_gid in user_gids:
                try:
                    user_details = asana_client.get_user_details(user_gid)
                    if user_details:
                        users_map[user_gid] = user_details
                        user_name = user_details.get('name', 'Unknown')
                        logger.debug(f"    ✓ Retrieved user: {user_name} (GID: {user_gid})")
                except Exception as e:
                    logger.warning(f"    ⚠ Could not retrieve user details for GID {user_gid}: {e}")
            logger.info(f"  ✓ Retrieved details for {len(users_map)} users")
        else:
            logger.info("  No users found in tasks")
        
        export_data = {
            'project': project_details,
            'tasks': detailed_tasks,
            'milestones': milestones,
            'sections': sections,
            'dependencies': dependencies_map,
            'users': users_map,  # Add user mapping: GID -> user details
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

