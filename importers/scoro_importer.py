"""
Import functionality for importing transformed data into Scoro
"""
import html
import re
import time
from typing import Dict, Optional

from clients.scoro_client import ScoroClient
from clients.asana_client import AsanaClient
from models import MigrationSummary
from utils import logger, process_batch, retry_with_backoff
from config import DEFAULT_BATCH_SIZE, TEST_MODE_MAX_TASKS, PROFILE_USERNAME_MAPPING, MAX_RETRIES, RETRY_DELAY


def replace_asana_profile_urls_with_scoro_mentions(
    comment_text: str,
    scoro_client: ScoroClient,
    asana_data: Optional[Dict] = None,
    wrap_in_paragraph: bool = True
) -> str:
    """
    Replace Asana profile URLs in comment text with Scoro user mention HTML.
    
    Asana profile URLs like "https://app.asana.com/0/profile/1206729612623556"
    are replaced with Scoro user mention HTML format:
    <span title="Full Name" class="mceNonEditable js-tinymce-user tinymce-user user-{user_id}">
        @<span class="mceNonEditable">First</span> <span class="mceNonEditable">Last</span>
    </span>
    
    Args:
        comment_text: The comment text that may contain Asana profile URLs
        scoro_client: ScoroClient instance for looking up users
        asana_data: Optional Asana export data containing users map for GID lookups
        wrap_in_paragraph: If True, wrap the result in <p> tags (default: True, for comments)
    
    Returns:
        Comment text with Asana profile URLs replaced by Scoro user mentions
    """
    if not comment_text:
        return comment_text
    
    # Pattern to match Asana profile URLs: https://app.asana.com/0/profile/{GID}
    # This pattern will match URLs even if they're inside HTML tags
    asana_profile_pattern = r'https://app\.asana\.com/0/profile/(\d+)'
    
    # Check if there are any URLs to replace
    urls_found = re.findall(asana_profile_pattern, comment_text)
    if not urls_found:
        # No URLs found, return as-is
        logger.debug(f"      No Asana profile URLs found in comment text")
        return comment_text
    
    logger.info(f"      Found {len(urls_found)} Asana profile URL(s) in comment: {urls_found}")
    logger.debug(f"      Processing comment text for Asana profile URL replacement")
    
    def replace_url(match):
        """Replace a single Asana profile URL with Scoro user mention"""
        gid = match.group(1)
        url = match.group(0)
        
        logger.debug(f"      Attempting to replace Asana profile URL: {url} (GID: {gid})")
        
        # Get user name from PROFILE_USERNAME_MAPPING
        # Note: Profile URL GIDs are different from API user GIDs, so we use the mapping directly
        user_name = None
        logger.debug(f"      Looking up profile GID in PROFILE_USERNAME_MAPPING: {gid}")
        for mapping in PROFILE_USERNAME_MAPPING:
            mapping_url = mapping.get('asana_url', '')
            # Extract GID from mapping URL
            mapping_gid_match = re.search(r'/profile/(\d+)', mapping_url)
            if mapping_gid_match:
                mapping_gid = mapping_gid_match.group(1)
                if str(mapping_gid) == str(gid):
                    user_name = mapping.get('name', '')
                    if user_name:
                        logger.info(f"      Found user name '{user_name}' from PROFILE_USERNAME_MAPPING for profile GID: {gid}")
                        break
        
        # If we don't have a user name, we can't create a proper mention
        # Return the URL as-is (or could return just the name if we had it)
        if not user_name:
            logger.warning(f"      Could not find user name for GID: {gid}, leaving URL as-is")
            return url
        
        # Find the Scoro user by name
        logger.debug(f"      Looking up Scoro user by name: '{user_name}'")
        scoro_user = scoro_client.find_user_by_name(user_name)
        
        # If not found and user_name looks like a first name only (single word, no spaces),
        # try matching against firstname field specifically
        if not scoro_user and ' ' not in user_name.strip():
            logger.debug(f"      Name '{user_name}' appears to be first name only, trying firstname match")
            try:
                users = scoro_client.list_users()
                if users:
                    user_name_lower = user_name.lower().strip()
                    for user in users:
                        firstname = user.get('firstname', '').strip()
                        if firstname and firstname.lower() == user_name_lower:
                            scoro_user = user
                            logger.info(f"      Found Scoro user by firstname match: '{firstname}' -> '{user.get('full_name', '')}' (ID: {user.get('id')})")
                            break
            except Exception as e:
                logger.debug(f"      Error during firstname-only lookup: {e}")
        
        if not scoro_user:
            # Scoro user not found - replace URL with plain name from mapping (no @ mention)
            logger.warning(f"      Could not find Scoro user '{user_name}' for GID: {gid}, replacing URL with plain name")
            # Escape HTML special characters in the name
            user_name_escaped = html.escape(user_name)
            return user_name_escaped
        
        user_id = scoro_user.get('id')
        if not user_id:
            # Scoro user found but no ID - replace URL with plain name from mapping (no @ mention)
            logger.warning(f"      Scoro user '{user_name}' found but no ID available, replacing URL with plain name")
            # Escape HTML special characters in the name
            user_name_escaped = html.escape(user_name)
            return user_name_escaped
        
        logger.debug(f"      Found Scoro user '{user_name}' with ID: {user_id}")
        
        # Get first and last name from Scoro user
        firstname = scoro_user.get('firstname', '').strip()
        lastname = scoro_user.get('lastname', '').strip()
        full_name = scoro_user.get('full_name', '').strip() or f"{firstname} {lastname}".strip()
        
        # If we don't have first/last name, try to split full_name
        if not firstname or not lastname:
            name_parts = full_name.split(maxsplit=1)
            if len(name_parts) >= 2:
                firstname = name_parts[0]
                lastname = name_parts[1]
            elif len(name_parts) == 1:
                firstname = name_parts[0]
                lastname = ''
            else:
                # Fallback: use full_name as firstname
                firstname = full_name
                lastname = ''
        
        # Build Scoro user mention HTML
        # Format: <span title="Full Name" class="mceNonEditable js-tinymce-user tinymce-user user-{user_id}">
        #         @<span class="mceNonEditable">First</span> <span class="mceNonEditable">Last</span>
        #         </span>
        # Escape HTML special characters in names to prevent XSS and HTML breakage
        full_name_escaped = html.escape(full_name)
        firstname_escaped = html.escape(firstname)
        lastname_escaped = html.escape(lastname) if lastname else ''
        
        mention_html = (
            f'<span title="{full_name_escaped}" class="mceNonEditable js-tinymce-user tinymce-user user-{user_id}">'
            f'@<span class="mceNonEditable">{firstname_escaped}</span>'
        )
        if lastname:
            mention_html += f' <span class="mceNonEditable">{lastname_escaped}</span>'
        mention_html += '</span>'
        
        logger.debug(f"      Replaced Asana profile URL (GID: {gid}) with Scoro mention for '{full_name}' (user_id: {user_id})")
        return mention_html
    
    # Replace all Asana profile URLs in the comment text
    result = re.sub(asana_profile_pattern, replace_url, comment_text)
    
    # Check if any replacements were made
    if result != comment_text:
        logger.info(f"      Successfully replaced Asana profile URL(s) in comment")
    else:
        logger.warning(f"      No replacements made - URLs may not have been matched or users not found")
    
    # Wrap in <p> tags if requested (for comments, but not necessarily for descriptions)
    if wrap_in_paragraph:
        result = result.strip()
        if result:
            # Check if the result is already wrapped in <p> tags
            # (could happen if the original comment had HTML structure)
            if not (result.startswith('<p>') and result.endswith('</p>')):
                # Wrap in <p> tags to ensure proper HTML structure
                result = f'<p>{result}</p>'
    
    return result


def update_task_status_with_retry(
    scoro_client: ScoroClient,
    task_id: int,
    task_update_data: Dict,
    max_retries: int = MAX_RETRIES,
    retry_delay: float = RETRY_DELAY
) -> Optional[Dict]:
    """
    Update task status with retry logic to ensure completion status is properly set.
    
    Args:
        scoro_client: Scoro client instance
        task_id: Scoro task ID
        task_update_data: Task update data dictionary
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        Updated task dictionary if successful, None otherwise
    """
    retries = 0
    current_delay = retry_delay
    
    while retries < max_retries:
        try:
            updated_task = scoro_client.create_task(task_update_data, task_id=task_id)
            return updated_task
        except Exception as e:
            retries += 1
            if retries >= max_retries:
                logger.error(f"    ✗ Failed to update task status after {max_retries} retries: {e}")
                return None
            
            logger.error(f"    ⚠ Failed to update task status (attempt {retries}/{max_retries}): {e}")
            time.sleep(current_delay)
            current_delay *= 2  # Exponential backoff
    
    return None


def import_to_scoro(scoro_client: ScoroClient, transformed_data: Dict, summary: MigrationSummary, 
                     batch_size: int = DEFAULT_BATCH_SIZE, asana_client: Optional[AsanaClient] = None,
                     max_tasks: Optional[int] = TEST_MODE_MAX_TASKS, asana_data: Optional[Dict] = None,
                     project_gid: Optional[str] = None) -> Dict:
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
        project_gid: Optional Asana project GID for logging purposes
    
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
        'phases': [],  # Phases from Asana sections (different from milestones)
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
                        logger.error(f"  ⚠ Failed to resolve {failed_count} project members")
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
                print(f"✓ Project created successfully: {project_name}")
                if project_id_for_log:
                    logger.debug(f"  Project ID: {project_id_for_log}")
                    print(f"  Project ID: {project_id_for_log}")
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
                    # Get existing phases to preserve them
                    existing_project = scoro_client.get_project(project_id)
                    existing_phases = existing_project.get('phases', []) if existing_project else []
                    if not isinstance(existing_phases, list):
                        existing_phases = []
                    
                    # Transform milestones to Scoro phase format
                    new_phases = []
                    for milestone_data in milestones_to_import:
                        milestone_name = milestone_data.get('title') or milestone_data.get('name', 'Unknown')
                        
                        # Check if milestone already exists (avoid duplicates)
                        milestone_name_lower = milestone_name.lower().strip()
                        milestone_exists = False
                        for existing_phase in existing_phases:
                            existing_title = existing_phase.get('title', '') or existing_phase.get('name', '')
                            if existing_title.lower().strip() == milestone_name_lower:
                                logger.debug(f"  Milestone '{milestone_name}' already exists, skipping")
                                milestone_exists = True
                                break
                        
                        if not milestone_exists:
                            phase_data = {}
                            
                            # Map 'name' to 'title' (Scoro API requirement for phases)
                            phase_data['title'] = milestone_name
                            phase_data['type'] = 'milestone'  # Use 'milestone' type for milestones
                            
                            # Add dates if available
                            if milestone_data.get('due_date'):
                                phase_data['end_date'] = milestone_data['due_date']
                            
                            if milestone_data.get('start_date'):
                                phase_data['start_date'] = milestone_data['start_date']
                            
                            new_phases.append(phase_data)
                            logger.info(f"  - {phase_data['title']}")
                    
                    if new_phases:
                        # Combine existing phases with new milestones
                        all_phases = existing_phases + new_phases
                        
                        # Modify project to add phases
                        project_update_data = {'phases': all_phases}
                        updated_project = scoro_client.create_project(project_update_data, project_id=project_id)
                    else:
                        logger.info(f"✓ All {len(milestones_to_import)} milestones already exist in project")
                        updated_project = existing_project
                    
                        # Extract phases from response if available
                        if 'phases' in updated_project:
                            import_results['milestones'] = updated_project['phases']
                        else:
                            # If phases aren't in response, mark them as created anyway
                            if new_phases:
                                import_results['milestones'] = [{'title': p['title']} for p in new_phases]
                            else:
                                import_results['milestones'] = existing_phases
                        
                        # Clear phase cache for this project so tasks can find the newly created phases
                        if hasattr(scoro_client, '_phases_cache'):
                            cache_key = project_id if project_id else 'all'
                            if cache_key in scoro_client._phases_cache:
                                del scoro_client._phases_cache[cache_key]
                            logger.debug(f"  Cleared phase cache for project {project_id} to ensure fresh phase lookup")
                    
                    if new_phases:
                        summary.add_success()
                        logger.info(f"✓ Successfully added {len(new_phases)} milestones to project")
                except Exception as e:
                    error_msg = f"Failed to add milestones to project: {e}"
                    logger.error(f"✗ {error_msg}")
                    import_results['errors'].append(error_msg)
                    summary.add_failure(error_msg)
            else:
                logger.error("Cannot add milestones: Project ID not available")
                logger.debug(f"  Project response keys: {list(import_results['project'].keys()) if import_results['project'] else 'No project'}")
        elif milestones_to_import and not import_results['project']:
            logger.warning(f"Cannot create {len(milestones_to_import)} milestones: Project creation failed")
        
        # Create phases from sections (Asana sections → Scoro phases with type="phase")
        phases_to_import = transformed_data.get('phases', [])
        if phases_to_import and import_results['project']:
            # Extract project ID - try multiple possible field names (Scoro API may use different field names)
            project_id = (
                import_results['project'].get('project_id') or 
                import_results['project'].get('id') or
                import_results['project'].get('projectId')
            )
            if project_id:
                logger.info(f"Adding {len(phases_to_import)} phases from sections to project in Scoro...")
                print(f"Adding {len(phases_to_import)} phases from sections to project in Scoro...")
                print(f"  Using project ID: {project_id}")
                logger.debug(f"  Using project ID: {project_id}")
                try:
                    # Get existing phases to preserve them
                    existing_project = scoro_client.get_project(project_id)
                    existing_phases = existing_project.get('phases', []) if existing_project else []
                    if not isinstance(existing_phases, list):
                        existing_phases = []
                    
                    # Transform sections to Scoro phase format
                    new_phases = []
                    for phase_data in phases_to_import:
                        phase_name = phase_data.get('name', 'Unknown')
                        
                        # Check if phase already exists (avoid duplicates)
                        phase_name_lower = phase_name.lower().strip()
                        phase_exists = False
                        for existing_phase in existing_phases:
                            existing_title = existing_phase.get('title', '') or existing_phase.get('name', '')
                            if existing_title.lower().strip() == phase_name_lower:
                                logger.debug(f"  Phase '{phase_name}' already exists, skipping")
                                phase_exists = True
                                break
                        
                        if not phase_exists:
                            scoro_phase = {
                                'title': phase_name,
                                'type': 'phase'  # Sections become regular phases (not milestones)
                            }
                            
                            # Sections typically don't have dates, but if they do, add them
                            if phase_data.get('start_date'):
                                scoro_phase['start_date'] = phase_data['start_date']
                            if phase_data.get('end_date'):
                                scoro_phase['end_date'] = phase_data['end_date']
                            
                            new_phases.append(scoro_phase)
                            logger.info(f"  - {phase_name}")
                            print(f"  - {phase_name}")
                    
                    if new_phases:
                        # Combine existing phases with new phases
                        all_phases = existing_phases + new_phases
                        
                        # Modify project to add phases
                        project_update_data = {'phases': all_phases}
                        updated_project = scoro_client.create_project(project_update_data, project_id=project_id)
                        
                        # Extract phases from response if available
                        if 'phases' in updated_project:
                            # Update import_results to track phases separately from milestones
                            if 'phases' not in import_results:
                                import_results['phases'] = []
                            import_results['phases'] = updated_project['phases']
                        
                        # Clear phase cache for this project so tasks can find the newly created phases
                        if hasattr(scoro_client, '_phases_cache'):
                            cache_key = project_id if project_id else 'all'
                            if cache_key in scoro_client._phases_cache:
                                del scoro_client._phases_cache[cache_key]
                            logger.debug(f"  Cleared phase cache for project {project_id} to ensure fresh phase lookup")
                        
                        summary.add_success()
                        logger.info(f"✓ Successfully added {len(new_phases)} phases from sections to project")
                    else:
                        logger.info(f"✓ All {len(phases_to_import)} phases from sections already exist in project")
                except Exception as e:
                    error_msg = f"Failed to add phases from sections to project: {e}"
                    logger.error(f"✗ {error_msg}")
                    import_results['errors'].append(error_msg)
                    summary.add_failure(error_msg)
            else:
                logger.warning("Cannot add phases from sections: Project ID not available")
                logger.debug(f"  Project response keys: {list(import_results['project'].keys()) if import_results['project'] else 'No project'}")
        elif phases_to_import and not import_results['project']:
            logger.warning(f"Cannot create {len(phases_to_import)} phases from sections: Project creation failed")
        
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
        
        # Pre-load caches for performance optimization
        logger.info("Pre-loading caches to optimize performance...")
        try:
            scoro_client.preload_users_cache()
        except Exception as e:
            logger.warning(f"Failed to pre-load users cache: {e}")
        
        try:
            scoro_client.preload_companies_cache()
        except Exception as e:
            logger.warning(f"Failed to pre-load companies cache: {e}")
        
        # Fetch and cache activities to avoid repeated API calls for each task
        logger.info("Fetching activities from Scoro for activity type resolution...")
        try:
            activities = scoro_client.list_activities()
            activity_name_to_id = {}
            for activity in activities:
                name = activity.get('name') or activity.get('activity_name') or activity.get('title', '')
                activity_id = activity.get('id') or activity.get('activity_id')
                if name and activity_id:
                    activity_name_to_id[name.strip()] = activity_id
                    activity_name_to_id[name.strip().lower()] = activity_id  # Also store lowercase for case-insensitive lookup
            logger.info(f"✓ Cached {len(activities)} activities from Scoro")
            if activities:
                logger.debug(f"  Sample activities: {list(activity_name_to_id.keys())[:5]}")
        except Exception as e:
            logger.warning(f"Failed to fetch activities from Scoro: {e}")
            logger.warning("Activity type migration will not work without activities list")
            activity_name_to_id = {}
        
        tasks_to_import = transformed_data.get('tasks', [])
        
        # Separate parent tasks from subtasks
        parent_tasks = []
        subtasks = []
        for task in tasks_to_import:
            if task.get('is_subtask', False):
                subtasks.append(task)
            else:
                parent_tasks.append(task)
        
        logger.info(f"Found {len(parent_tasks)} parent task(s) and {len(subtasks)} subtask(s)")
        
        # Apply test mode limit if specified (only to parent tasks for now)
        original_parent_count = len(parent_tasks)
        if max_tasks is not None and max_tasks > 0 and len(parent_tasks) > max_tasks:
            parent_tasks = parent_tasks[:max_tasks]
            logger.info(f"⚠ TEST MODE: Limiting parent task migration to {max_tasks} tasks (out of {original_parent_count} total parent tasks)")
            # Also filter subtasks to only include those whose parents are being migrated
            parent_asana_gids = {task.get('asana_gid') for task in parent_tasks if task.get('asana_gid')}
            subtasks = [st for st in subtasks if st.get('parent_asana_gid') in parent_asana_gids]
            logger.info(f"  Filtered subtasks to {len(subtasks)} subtask(s) for migrated parents")
        
        # Mapping: asana_gid -> scoro_task_id (for linking subtasks to parents)
        asana_gid_to_scoro_id = {}
        
        if parent_tasks:
            logger.info(f"Creating {len(parent_tasks)} parent tasks in Scoro (batch size: {batch_size})...")
            
            # Process parent tasks in batches
            task_batches = process_batch(parent_tasks, batch_size)
            total_batches = len(task_batches)
            
            for batch_idx, task_batch in enumerate(task_batches, 1):
                gid_info = f" [GID: {project_gid}]" if project_gid else ""
                logger.info(f"Processing batch {batch_idx}/{total_batches} ({len(task_batch)} tasks){gid_info}...")
                
                for idx, task_data in enumerate(task_batch, 1):
                    task_name = task_data.get('title', task_data.get('name', 'Unknown'))
                    global_idx = (batch_idx - 1) * batch_size + idx
                    gid_info = f" [GID: {project_gid}]" if project_gid else ""
                    logger.info(f"  [{global_idx}/{len(tasks_to_import)}] Creating task: {task_name}{gid_info}")
                    print(f"  [{global_idx}/{len(tasks_to_import)}] Creating task: {task_name}{gid_info}")
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
                        
                        # Ensure owner_id is set - use To Be Assigned (user_id: 37) as fallback if not available
                        if not task_data.get('owner_id'):
                            task_data['owner_id'] = 37
                            logger.debug(f"    No owner_id available. Setting fallback owner_id to 37 (To Be Assigned)")
                        
                        # - assigned_to_name -> related_users (Array of user IDs)
                        # NOTE: assigned_to_name should contain ONLY the primary assignee (not followers)
                        # Scoro's related_users field is for assignees only, not followers/collaborators
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
                                            logger.debug(f"    Resolved assignee '{name}' to user_id: {user_id} ({user_full_name})")
                                        else:
                                            logger.warning(f"    Assignee '{name}' found but no ID available")
                                    else:
                                        logger.warning(f"    Could not find assignee '{name}' in Scoro users")
                                
                                if related_user_ids:
                                    task_data['related_users'] = related_user_ids
                                    logger.debug(f"    Set related_users (assignees only): {related_user_ids}")
                            except Exception as e:
                                logger.warning(f"    Error resolving assignees '{assigned_to_name}': {e}")
                        
                        # Ensure related_users (assignees) is set - use To Be Assigned (user_id: 37) as fallback if not available
                        if not task_data.get('related_users'):
                            task_data['related_users'] = [37]
                            logger.debug(f"    No assignees available. Setting fallback related_users to [37] (To Be Assigned)")
                        
                        # - project_phase_name -> project_phase_id (Integer)
                        project_phase_name = task_data.get('project_phase_name')
                        if project_phase_name:
                            logger.info(f"    Task phase assignment: Looking for phase '{project_phase_name}' in project {project_id}")
                        if project_phase_name and project_id:
                            try:
                                phase = scoro_client.find_phase_by_name(project_phase_name, project_id=project_id)
                                if phase:
                                    phase_id = phase.get('id') or phase.get('phase_id')
                                    if phase_id:
                                        task_data['project_phase_id'] = phase_id
                                        phase_title = phase.get('title') or phase.get('name', 'Unknown')
                                        logger.info(f"    ✓ Task assigned to phase: '{phase_title}' (ID: {phase_id}) for phase name: '{project_phase_name}'")
                                    else:
                                        logger.warning(f"    Phase '{project_phase_name}' found but no ID available")
                                else:
                                    # Phase not found - fallback to "Misc" phase
                                    logger.warning(f"    ⚠ Could not find phase '{project_phase_name}' in project {project_id} - falling back to 'Misc' phase")
                                    misc_phase = scoro_client.find_phase_by_name('Misc', project_id=project_id)
                                    if misc_phase:
                                        misc_phase_id = misc_phase.get('id') or misc_phase.get('phase_id')
                                        if misc_phase_id:
                                            task_data['project_phase_id'] = misc_phase_id
                                            logger.info(f"    ✓ Task assigned to fallback phase: 'Misc' (ID: {misc_phase_id})")
                                        else:
                                            logger.warning(f"    'Misc' phase found but no ID available")
                                    else:
                                        logger.warning(f"    ⚠ Could not find 'Misc' phase either - task will be created without phase assignment")
                            except Exception as e:
                                logger.warning(f"    Error resolving phase '{project_phase_name}': {e}")
                                # Try to fallback to Misc on error as well
                                try:
                                    misc_phase = scoro_client.find_phase_by_name('Misc', project_id=project_id)
                                    if misc_phase:
                                        misc_phase_id = misc_phase.get('id') or misc_phase.get('phase_id')
                                        if misc_phase_id:
                                            task_data['project_phase_id'] = misc_phase_id
                                            logger.info(f"    ✓ Task assigned to fallback phase: 'Misc' (ID: {misc_phase_id}) after error")
                                except Exception as e2:
                                    logger.warning(f"    Error resolving fallback 'Misc' phase: {e2}")
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
                                        new_company = scoro_client.get_or_create_company(company_name)
                                        logger.warning(f"    Could not find company '{company_name}' in Scoro companies and created new company")
                                        company_id = new_company.get('id') or new_company.get('company_id') or new_company.get('client_id') or new_company.get('contact_id')
                                        logger.debug(f"new company is create: {company_id}")
                                        if company_id:
                                            task_data['company_id'] = company_id
                                            logger.debug(f"    Resolved company '{company_name}' to company_id: {company_id}")
                                        else:
                                            logger.warning(f"    Company '{company_name}' found but no ID available")
                                except Exception as e:
                                    logger.warning(f"    Error resolving company '{company_name}': {e}")
                        
                        # - activity_type -> activity_id (Integer)
                        # Scoro API requires activity_id (integer) not activity_type (string)
                        activity_type_name = task_data.get('activity_type')
                        if activity_type_name:
                            # Try exact match first
                            activity_id = activity_name_to_id.get(activity_type_name.strip())
                            
                            # Try case-insensitive match if exact match fails
                            if not activity_id:
                                activity_id = activity_name_to_id.get(activity_type_name.strip().lower())
                            
                            if activity_id:
                                task_data['activity_id'] = activity_id
                                logger.debug(f"    Resolved activity type '{activity_type_name}' to activity_id: {activity_id}")
                            else:
                                logger.warning(f"    Could not find activity '{activity_type_name}' in Scoro activities")
                                logger.debug(f"    Available activities: {list(activity_name_to_id.keys())[:10]}")
                        
                        # Apply URL transformation to description field if present
                        # This replaces Asana profile URLs with Scoro user mentions
                        if 'description' in task_data and task_data.get('description'):
                            description = task_data.get('description', '')
                            if description:
                                # Apply URL transformation to description
                                # Note: wrap_in_paragraph=False because descriptions may already have HTML structure
                                description = replace_asana_profile_urls_with_scoro_mentions(
                                    description,
                                    scoro_client,
                                    asana_data,
                                    wrap_in_paragraph=False
                                )
                                task_data['description'] = description
                                logger.debug(f"    Applied URL transformation to task description")
                        
                        # Remove fields that Scoro might not accept (metadata and name-only fields)
                        # Exclude: internal tracking fields, name-only fields (already resolved to IDs), 
                        # and fields not in Scoro Tasks API reference
                        # Note: 'stories' and 'calculated_time_entries' are excluded from task creation but will be processed separately
                        # Note: 'activity_type' (string) is excluded because we're using 'activity_id' (integer) instead
                        # Note: '_asana_*' fields are metadata for status update logic, not sent to API
                        task_data_clean = {k: v for k, v in task_data.items() 
                                         if k not in ['asana_gid', 'asana_permalink', 'dependencies', 'num_subtasks', 
                                                      'attachment_count', 'attachment_refs', 'followers',
                                                      'owner_name', 'assigned_to_name', 'project_phase_name', 
                                                      'project_name', 'company_name', 'tags', 'is_milestone', 'stories', 
                                                      'calculated_time_entries', 'activity_type',
                                                      '_asana_completed', '_asana_completed_at', '_has_calculated_time_entries']}
                        
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
                                        logger.debug(f"    Extracted task ID from field '{field_name}': {scoro_task_id}")
                                        break
                                except (ValueError, TypeError):
                                    continue
                        
                        # If task ID still not found, log warning and try to extract from nested data
                        if scoro_task_id is None:
                            logger.warning(f"    ⚠ Task ID not found in standard fields, checking nested data...")
                            # Try to extract from nested 'data' field
                            if isinstance(task, dict) and 'data' in task:
                                data = task.get('data', {})
                                for field_name in ['event_id', 'task_id', 'id', 'eventId', 'taskId']:
                                    task_id_value = data.get(field_name)
                                    if task_id_value is not None:
                                        try:
                                            task_id_int = int(task_id_value)
                                            if task_id_int > 0:
                                                scoro_task_id = task_id_int
                                                logger.debug(f"    Extracted task ID from nested data field '{field_name}': {scoro_task_id}")
                                                break
                                        except (ValueError, TypeError):
                                            continue
                            
                            if scoro_task_id is None:
                                logger.error(f"    ✗ Could not extract task ID from response. Task may not be properly created.")
                                logger.debug(f"    Response keys: {list(task.keys()) if isinstance(task, dict) else 'Not a dict'}")
                        
                        # Store mapping of asana_gid -> scoro_task_id for subtask linking
                        task_asana_gid = task_data.get('asana_gid')
                        if task_asana_gid and scoro_task_id:
                            asana_gid_to_scoro_id[task_asana_gid] = scoro_task_id
                            logger.debug(f"    Stored parent task mapping: asana_gid {task_asana_gid} -> scoro_task_id {scoro_task_id}")
                        
                        # Create time entries if task has calculated_time_entries
                        # These are from Asana Time Tracking Entries API
                        calculated_time_entries = task_data.get('calculated_time_entries', [])
                        
                        # Get completion info from task data
                        asana_completed = task_data.get('_asana_completed', False)
                        asana_completed_at = task_data.get('_asana_completed_at')
                        has_calculated_time_entries = task_data.get('_has_calculated_time_entries', len(calculated_time_entries) > 0)
                        
                        # Track if time entries were successfully created
                        time_entries_created_successfully = False
                        
                        if calculated_time_entries and scoro_task_id is not None:
                            try:
                                logger.info(f"    Creating {len(calculated_time_entries)} time entries for task...")
                                
                                # Create each time entry
                                for idx, calculated_time_entry in enumerate(calculated_time_entries, 1):
                                    # Prepare time entry data for Scoro API
                                    time_entry_data = {
                                        'event_id': scoro_task_id,
                                        'event_type': calculated_time_entry.get('event_type', 'task'),
                                        'time_entry_type': calculated_time_entry.get('time_entry_type', 'task'),
                                        'start_datetime': calculated_time_entry.get('start_datetime'),
                                        'end_datetime': calculated_time_entry.get('end_datetime'),
                                        'duration': calculated_time_entry.get('duration'),
                                        'is_completed': calculated_time_entry.get('is_completed', False),  # Based on task.completed
                                        'completed_datetime': calculated_time_entry.get('completed_datetime'),
                                        'billable_time_type': calculated_time_entry.get('billable_time_type', 'billable'),
                                    }
                                    
                                    # Resolve user_id from user_name if provided
                                    user_name = calculated_time_entry.get('user_name')
                                    user_id = None
                                    if user_name:
                                        try:
                                            user = scoro_client.find_user_by_name(user_name)
                                            if user:
                                                user_id = user.get('id')
                                                if user_id:
                                                    time_entry_data['user_id'] = user_id
                                                    logger.debug(f"      [{idx}/{len(calculated_time_entries)}] Resolved time entry user '{user_name}' to user_id: {user_id}")
                                                else:
                                                    logger.warning(f"      [{idx}/{len(calculated_time_entries)}] Time entry user '{user_name}' found but no ID available")
                                            else:
                                                logger.warning(f"      [{idx}/{len(calculated_time_entries)}] Could not find time entry user '{user_name}' in Scoro users")
                                        except Exception as e:
                                            logger.warning(f"      [{idx}/{len(calculated_time_entries)}] Error resolving time entry user '{user_name}': {e}")
                                    
                                    # Fallback: Use task's owner_id if user_id is not set (required by Scoro API when using apiKey)
                                    # This is especially useful for 00:00 time entries created for completed tasks without time tracking
                                    if not user_id:
                                        owner_id = task_data.get('owner_id')
                                        if owner_id:
                                            time_entry_data['user_id'] = owner_id
                                            logger.debug(f"      [{idx}/{len(calculated_time_entries)}] Using task owner_id {owner_id} as fallback for time entry user")
                                        else:
                                            # Final fallback: Use To Be Assigned (user_id: 37) if no user_id or owner_id available
                                            task_data['owner_id'] = 37
                                            time_entry_data['user_id'] = 37
                                            logger.debug(f"      [{idx}/{len(calculated_time_entries)}] No user_id or owner_id available. Setting owner_id and using fallback user_id 37 (To Be Assigned) for time entry")
                                    
                                    # Create time entry via Scoro Time Entries API
                                    time_entry = scoro_client.create_time_entry(time_entry_data)
                                    logger.info(f"    ✓ [{idx}/{len(calculated_time_entries)}] Time entry created: {calculated_time_entry.get('duration')}")
                                    logger.debug(f"      Time entry ID: {time_entry.get('time_entry_id', 'Unknown')}")
                                
                                time_entries_created_successfully = True
                                
                            except Exception as e:
                                # Log warning but don't fail the entire task
                                logger.error(f"    ⚠ Failed to create time entries for task: {e}")
                                # For completed tasks, we'll still attempt status update as fallback
                                if asana_completed:
                                    logger.info(f"    Will attempt status update for completed task despite time entry creation failure")
                        elif calculated_time_entries and not scoro_task_id:
                            logger.error(f"    ⚠ Cannot create time entries: Task ID not available in response")
                            # For completed tasks, we'll still attempt status update as fallback
                            if asana_completed:
                                logger.info(f"    Will attempt status update for completed task despite missing task ID")
                        
                        # Update task status based on new algorithm:
                        # - If completed AND has calculated_time_entries → task_status9 (Completed)
                        # - If has calculated_time_entries AND not completed → task_status3 (In progress)
                        # - If no calculated_time_entries AND not completed → task_status1 (Planned) - no update needed
                        # FIX: Also attempt status update for completed tasks even if time entry creation failed
                        try:
                            task_update_data = {}
                            should_update_status = False
                            
                            # Check if we should update status to completed
                            # For completed tasks, attempt update if:
                            # 1. Time entries were created successfully, OR
                            # 2. Time entry creation failed but task is marked completed (fallback)
                            if asana_completed:
                                if time_entries_created_successfully or has_calculated_time_entries:
                                    # Task is completed AND has time entries (or attempted) → task_status9 (Completed)
                                    logger.info(f"    Updating task status to completed (task_status9)...")
                                    task_update_data = {
                                        'is_completed': True,
                                        'status': 'task_status9',  # Completed status
                                    }
                                    should_update_status = True
                                    
                                    # Add completion datetime if available
                                    if asana_completed_at:
                                        if isinstance(asana_completed_at, str):
                                            try:
                                                if 'T' not in asana_completed_at:
                                                    asana_completed_at = f"{asana_completed_at}T00:00:00"
                                                task_update_data['datetime_completed'] = asana_completed_at
                                            except Exception as e:
                                                logger.debug(f"      Could not parse datetime_completed: {e}")
                                elif not time_entries_created_successfully:
                                    # Fallback: Attempt to mark as completed even without time entries
                                    # This handles edge cases where time entry creation failed
                                    logger.warning(f"    ⚠ Attempting to mark completed task without time entries (fallback mode)")
                                    task_update_data = {
                                        'is_completed': True,
                                        'status': 'task_status9',  # Completed status
                                    }
                                    should_update_status = True
                                    
                                    if asana_completed_at:
                                        if isinstance(asana_completed_at, str):
                                            try:
                                                if 'T' not in asana_completed_at:
                                                    asana_completed_at = f"{asana_completed_at}T00:00:00"
                                                task_update_data['datetime_completed'] = asana_completed_at
                                            except Exception as e:
                                                logger.debug(f"      Could not parse datetime_completed: {e}")
                            elif has_calculated_time_entries and not asana_completed:
                                # Task has time entries AND not completed → task_status3 (In progress)
                                logger.info(f"    Updating task status to in progress (task_status3)...")
                                task_update_data = {
                                    'status': 'task_status3',  # In progress status
                                }
                                should_update_status = True
                            
                            # Update task status if needed (with retry logic)
                            if should_update_status and scoro_task_id is not None:
                                updated_task = update_task_status_with_retry(
                                    scoro_client,
                                    scoro_task_id,
                                    task_update_data
                                )
                                if updated_task:
                                    status_name = 'completed' if asana_completed else 'in progress'
                                    logger.info(f"    ✓ Task status updated to {status_name}")
                                else:
                                    logger.error(f"    ✗ Failed to update task status after retries")
                            elif should_update_status and scoro_task_id is None:
                                logger.error(f"    ✗ Cannot update task status: Task ID not available")
                                
                        except Exception as e:
                            logger.error(f"    ✗ Failed to update task status: {e}")
                        
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
                                        # This removes HTML formatting but preserves plain text URLs
                                        comment_text = re.sub(r'<[^>]+>', '', comment_text).strip()
                                        if not comment_text:
                                            continue
                                        
                                        # Replace Asana profile URLs with Scoro user mentions
                                        # This adds HTML user mention spans to the comment
                                        comment_text = replace_asana_profile_urls_with_scoro_mentions(
                                            comment_text,
                                            scoro_client,
                                            asana_data
                                        )
                                        
                                        # Check if comment is empty after processing (e.g., only HTML was stripped)
                                        # Remove <p> tags for checking, then re-add if needed
                                        comment_text_check = re.sub(r'<[^>]+>', '', comment_text).strip()
                                        if not comment_text_check:
                                            logger.debug(f"      Skipping comment: Empty after processing")
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
                                        user_obj = None
                                        if author_name:
                                            try:
                                                user_obj = scoro_client.find_user_by_name(author_name)
                                                if user_obj:
                                                    user_id = user_obj.get('id')
                                                    if user_id is not None:
                                                        logger.debug(f"      Resolved comment author '{author_name}' to user_id: {user_id}")
                                            except Exception as e:
                                                logger.debug(f"      Could not resolve user '{author_name}': {e}")
                                        
                                        # If user_id not found by name, try email
                                        if user_id is None and author_email:
                                            try:
                                                user_obj = scoro_client.find_user_by_name(author_email)
                                                if user_obj:
                                                    user_id = user_obj.get('id')
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
                                        
                                        # Check if user is active - Scoro Comments API requires is_active=1 (true)
                                        # For users, "inactive" means is_active=0 (false), which disables API operations
                                        # The "status" field is for organizing data items, not user activation
                                        if user_obj:
                                            is_active_raw = user_obj.get('is_active')
                                            logger.debug(f"      User object is_active value: {is_active_raw} (type: {type(is_active_raw)})")
                                            
                                            # Convert to boolean: 0/False = inactive, 1/True = active
                                            # Also handle string representations like "1" or "0"
                                            if isinstance(is_active_raw, str):
                                                is_active = is_active_raw.lower() in ('1', 'true', 'yes')
                                            elif isinstance(is_active_raw, int):
                                                is_active = bool(is_active_raw)
                                            elif is_active_raw is None:
                                                is_active = False  # Default to inactive if not specified
                                                logger.warning(f"      ⚠ User object missing is_active field, defaulting to inactive")
                                            else:
                                                is_active = bool(is_active_raw)
                                            
                                            logger.debug(f"      User is_active check result: {is_active}")
                                            
                                            # Skip comment if user is inactive (is_active=0)
                                            if not is_active:
                                                author_info = author_name or author_email or (f"GID: {user_gid}" if user_gid else "Unknown")
                                                logger.warning(f"      ⚠ Skipping comment: Comment author '{author_info}' (user_id: {user_id}) is inactive in Scoro (is_active={is_active_raw}). Comments API requires active users (is_active=1).")
                                                comments_failed += 1
                                                continue
                                        else:
                                            logger.warning(f"      ⚠ User object is None, cannot check is_active status")
                                            comments_failed += 1
                                            continue
                                        
                                        # Create comment via Scoro Comments API
                                        # Module is "tasks", object_id is the task ID
                                        try:
                                            scoro_client.create_comment(
                                                module='tasks',
                                                object_id=scoro_task_id,
                                                comment_text=comment_text,
                                                user_id=user_id
                                            )
                                            comments_created += 1
                                            logger.debug(f"      ✓ Comment created by {author_name}")
                                        except ValueError as e:
                                            # Handle Scoro API errors specifically
                                            error_msg = str(e)
                                            if "not found or is inactive" in error_msg.lower():
                                                # User might have become inactive between user list fetch and comment creation
                                                # Or the Comments API has stricter validation than other APIs
                                                author_info = author_name or author_email or (f"GID: {user_gid}" if user_gid else "Unknown")
                                                is_active_value = user_obj.get('is_active') if user_obj else 'unknown'
                                                logger.warning(f"      ⚠ Failed to create comment: Scoro Comments API rejected user_id {user_id} ({author_info}). User has is_active={is_active_value} in user list, but API reports user as inactive. This may indicate the user was deactivated or the Comments API has additional requirements.")
                                            else:
                                                logger.warning(f"      ⚠ Failed to create comment: {error_msg}")
                                            comments_failed += 1
                                        except Exception as e:
                                            comments_failed += 1
                                            logger.warning(f"      ⚠ Failed to create comment: {e}")
                                            # Don't fail the entire task if comment creation fails
                                    except Exception as e:
                                        # Catch any other errors in comment processing (e.g., missing fields, etc.)
                                        comments_failed += 1
                                        logger.warning(f"      ⚠ Error processing comment: {e}")
                                
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
                        print(f"Failed to create task '{task_name}': {e}")
                        logger.error(f"    ✗ {error_msg}")
                        import_results['errors'].append(error_msg)
                        summary.add_failure(error_msg)
            
            # Now create subtasks as regular (top-level) tasks
            # Note: Subtasks are migrated as regular tasks (not as subtasks) due to Scoro permission restrictions
            # They will be placed in the same phase as their parent task
            if subtasks:
                logger.info("="*60)
                logger.info(f"Creating {len(subtasks)} former subtask(s) as regular tasks in Scoro...")
                logger.info("="*60)
                
                subtask_batches = process_batch(subtasks, batch_size)
                total_subtask_batches = len(subtask_batches)
                
                for batch_idx, subtask_batch in enumerate(subtask_batches, 1):
                    gid_info = f" [GID: {project_gid}]" if project_gid else ""
                    logger.info(f"Processing subtask batch {batch_idx}/{total_subtask_batches} ({len(subtask_batch)} tasks){gid_info}...")
                    
                    for idx, subtask_data in enumerate(subtask_batch, 1):
                        subtask_name = subtask_data.get('title', subtask_data.get('name', 'Unknown'))
                        global_idx = (batch_idx - 1) * batch_size + idx
                        gid_info = f" [GID: {project_gid}]" if project_gid else ""
                        logger.info(f"  [{global_idx}/{len(subtasks)}] Creating task (formerly subtask): {subtask_name}{gid_info}")
                        print(f"  [{global_idx}/{len(subtasks)}] Creating task (formerly subtask): {subtask_name}{gid_info}")
                        
                        try:
                            # Note: Parent lookup is optional - we create as regular task regardless
                            # Phase information is already inherited from parent during transformation
                            parent_asana_gid = subtask_data.get('parent_asana_gid')
                            if parent_asana_gid:
                                parent_scoro_id = asana_gid_to_scoro_id.get(parent_asana_gid)
                                if parent_scoro_id:
                                    logger.debug(f"    Parent task exists (scoro_task_id: {parent_scoro_id}), phase inherited from parent during transformation")
                                else:
                                    logger.debug(f"    Parent task not found in created tasks, but continuing with phase from transformation")
                            
                            # Extract stories/comments before cleaning subtask_data
                            subtask_stories = subtask_data.get('stories', [])
                            
                            # Link task to project (inherited from parent)
                            if project_id:
                                subtask_data['project_id'] = project_id
                                logger.debug(f"    Inherited project_id from parent: {project_id}")
                            
                            # NOTE: NOT setting parent_id - creating as regular task due to permission restrictions
                            
                            # Resolve name fields to IDs (similar to parent tasks)
                            # - owner_name -> owner_id
                            owner_name = subtask_data.get('owner_name')
                            if owner_name:
                                try:
                                    owner = scoro_client.find_user_by_name(owner_name)
                                    if owner:
                                        owner_id = owner.get('id')
                                        if owner_id:
                                            subtask_data['owner_id'] = owner_id
                                            logger.debug(f"    Resolved subtask owner '{owner_name}' to owner_id: {owner_id}")
                                        else:
                                            logger.warning(f"    Subtask owner '{owner_name}' found but no ID available")
                                    else:
                                        logger.warning(f"    Could not find subtask owner '{owner_name}' in Scoro users")
                                except Exception as e:
                                    logger.warning(f"    Error resolving subtask owner '{owner_name}': {e}")
                            
                            # Ensure owner_id is set
                            if not subtask_data.get('owner_id'):
                                subtask_data['owner_id'] = 37
                                logger.debug(f"    No subtask owner_id available. Setting fallback to 37 (To Be Assigned)")
                            
                            # - assigned_to_name -> related_users
                            assigned_to_name = subtask_data.get('assigned_to_name')
                            if assigned_to_name:
                                try:
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
                                                logger.debug(f"    Resolved subtask assignee '{name}' to user_id: {user_id}")
                                            else:
                                                logger.warning(f"    Subtask assignee '{name}' found but no ID available")
                                        else:
                                            logger.warning(f"    Could not find subtask assignee '{name}' in Scoro users")
                                    
                                    if related_user_ids:
                                        subtask_data['related_users'] = related_user_ids
                                except Exception as e:
                                    logger.warning(f"    Error resolving subtask assignees '{assigned_to_name}': {e}")
                            
                            # Ensure related_users is set
                            if not subtask_data.get('related_users'):
                                subtask_data['related_users'] = [37]
                                logger.debug(f"    No subtask assignees available. Setting fallback to [37] (To Be Assigned)")
                            
                            # - project_phase_name -> project_phase_id (inherited from parent, but resolve if needed)
                            project_phase_name = subtask_data.get('project_phase_name')
                            if project_phase_name and project_id:
                                try:
                                    phase = scoro_client.find_phase_by_name(project_phase_name, project_id=project_id)
                                    if phase:
                                        phase_id = phase.get('id') or phase.get('phase_id')
                                        if phase_id:
                                            subtask_data['project_phase_id'] = phase_id
                                            logger.debug(f"    Resolved subtask phase '{project_phase_name}' to phase_id: {phase_id}")
                                        else:
                                            logger.warning(f"    Subtask phase '{project_phase_name}' found but no ID available")
                                    else:
                                        logger.warning(f"    Could not find subtask phase '{project_phase_name}' in project {project_id}")
                                except Exception as e:
                                    logger.warning(f"    Error resolving subtask phase '{project_phase_name}': {e}")
                            
                            # - company_name -> company_id (inherited from parent)
                            company_name = subtask_data.get('company_name')
                            if company_name:
                                # Reuse project_company_id if it matches
                                if project_company_id and company_name == transformed_data.get('company_name'):
                                    subtask_data['company_id'] = project_company_id
                                    logger.debug(f"    Reused project company_id for subtask: {project_company_id}")
                                else:
                                    try:
                                        company_lookup = scoro_client.find_company_by_name(company_name)
                                        if company_lookup:
                                            company_id = company_lookup.get('id') or company_lookup.get('company_id') or company_lookup.get('client_id') or company_lookup.get('contact_id')
                                            if company_id:
                                                subtask_data['company_id'] = company_id
                                                logger.debug(f"    Resolved subtask company '{company_name}' to company_id: {company_id}")
                                            else:
                                                logger.warning(f"    Subtask company '{company_name}' found but no ID available")
                                        else:
                                            logger.warning(f"    Could not find subtask company '{company_name}' in Scoro companies")
                                    except Exception as e:
                                        logger.warning(f"    Error resolving subtask company '{company_name}': {e}")
                            
                            # - activity_type -> activity_id
                            activity_type_name = subtask_data.get('activity_type')
                            if activity_type_name:
                                activity_id = activity_name_to_id.get(activity_type_name.strip())
                                if not activity_id:
                                    activity_id = activity_name_to_id.get(activity_type_name.strip().lower())
                                
                                if activity_id:
                                    subtask_data['activity_id'] = activity_id
                                    logger.debug(f"    Resolved subtask activity type '{activity_type_name}' to activity_id: {activity_id}")
                                else:
                                    logger.warning(f"    Could not find subtask activity '{activity_type_name}' in Scoro activities")
                            
                            # Apply URL transformation to description if present
                            if 'description' in subtask_data and subtask_data.get('description'):
                                description = subtask_data.get('description', '')
                                if description:
                                    description = replace_asana_profile_urls_with_scoro_mentions(
                                        description,
                                        scoro_client,
                                        asana_data,
                                        wrap_in_paragraph=False
                                    )
                                    subtask_data['description'] = description
                            
                            # Remove metadata fields (same as parent tasks)
                            # Note: parent_id is NOT included (we're creating as regular task, not subtask)
                            subtask_data_clean = {k: v for k, v in subtask_data.items() 
                                                 if k not in ['asana_gid', 'asana_permalink', 'dependencies', 'num_subtasks', 
                                                              'attachment_count', 'attachment_refs', 'followers',
                                                              'owner_name', 'assigned_to_name', 'project_phase_name', 
                                                              'project_name', 'company_name', 'tags', 'is_milestone', 'stories', 
                                                              'calculated_time_entries', 'activity_type',
                                                              '_asana_completed', '_asana_completed_at', '_has_calculated_time_entries',
                                                              'parent_asana_gid', 'is_subtask', 'parent_id']}
                            
                            # Map 'title' to 'event_name'
                            if 'title' in subtask_data_clean and 'event_name' not in subtask_data_clean:
                                subtask_data_clean['event_name'] = subtask_data_clean.pop('title')
                            
                            # Create the task (as regular task, not subtask)
                            task = scoro_client.create_task(subtask_data_clean)
                            import_results['tasks'].append(task)
                            summary.add_success()
                            logger.info(f"    ✓ Task created (formerly subtask): {subtask_name}")
                            
                            # Extract task ID
                            scoro_task_id = None
                            for field_name in ['event_id', 'task_id', 'id', 'eventId', 'taskId']:
                                task_id_value = task.get(field_name)
                                if task_id_value is not None:
                                    try:
                                        task_id_int = int(task_id_value)
                                        if task_id_int > 0:
                                            scoro_task_id = task_id_int
                                            logger.debug(f"    Extracted task ID from field '{field_name}': {scoro_task_id}")
                                            break
                                    except (ValueError, TypeError):
                                        continue
                            
                            # Create time entries for task (same logic as parent tasks)
                            subtask_calculated_time_entries = subtask_data.get('calculated_time_entries', [])
                            subtask_asana_completed = subtask_data.get('_asana_completed', False)
                            subtask_asana_completed_at = subtask_data.get('_asana_completed_at')
                            subtask_has_calculated_time_entries = subtask_data.get('_has_calculated_time_entries', len(subtask_calculated_time_entries) > 0)
                            
                            if subtask_calculated_time_entries and scoro_task_id is not None:
                                try:
                                    logger.info(f"    Creating {len(subtask_calculated_time_entries)} time entries for task...")
                                    
                                    for idx, time_entry in enumerate(subtask_calculated_time_entries, 1):
                                        time_entry_data = {
                                            'event_id': scoro_task_id,
                                            'event_type': time_entry.get('event_type', 'task'),
                                            'time_entry_type': time_entry.get('time_entry_type', 'task'),
                                            'start_datetime': time_entry.get('start_datetime'),
                                            'end_datetime': time_entry.get('end_datetime'),
                                            'duration': time_entry.get('duration'),
                                            'is_completed': time_entry.get('is_completed', False),
                                            'completed_datetime': time_entry.get('completed_datetime'),
                                            'billable_time_type': time_entry.get('billable_time_type', 'billable'),
                                        }
                                        
                                        user_name = time_entry.get('user_name')
                                        user_id = None
                                        if user_name:
                                            try:
                                                user = scoro_client.find_user_by_name(user_name)
                                                if user:
                                                    user_id = user.get('id')
                                                    if user_id:
                                                        time_entry_data['user_id'] = user_id
                                            except Exception as e:
                                                logger.warning(f"      [{idx}/{len(subtask_calculated_time_entries)}] Error resolving time entry user '{user_name}': {e}")
                                        
                                        if not user_id:
                                            owner_id = subtask_data.get('owner_id')
                                            if owner_id:
                                                time_entry_data['user_id'] = owner_id
                                            else:
                                                time_entry_data['user_id'] = 1
                                        
                                        scoro_client.create_time_entry(time_entry_data)
                                        logger.info(f"    ✓ [{idx}/{len(subtask_calculated_time_entries)}] Time entry created: {time_entry.get('duration')}")
                                    
                                except Exception as e:
                                    logger.error(f"    ⚠ Failed to create time entries for task: {e}")
                            
                            # Update task status (same logic as parent tasks)
                            try:
                                subtask_update_data = {}
                                should_update_status = False
                                
                                if subtask_asana_completed and subtask_has_calculated_time_entries:
                                    subtask_update_data['status'] = 'task_status9'  # Completed
                                    subtask_update_data['is_completed'] = True
                                    if subtask_asana_completed_at:
                                        subtask_update_data['datetime_completed'] = subtask_asana_completed_at
                                    should_update_status = True
                                elif subtask_has_calculated_time_entries and not subtask_asana_completed:
                                    subtask_update_data['status'] = 'task_status3'  # In progress
                                    should_update_status = True
                                
                                # Update task status if needed (with retry logic - same as parent tasks)
                                if should_update_status and scoro_task_id is not None:
                                    updated_task = update_task_status_with_retry(
                                        scoro_client,
                                        scoro_task_id,
                                        subtask_update_data
                                    )
                                    if updated_task:
                                        status_name = 'completed' if subtask_asana_completed else 'in progress'
                                        logger.info(f"    ✓ Task status updated to {status_name}")
                                    else:
                                        logger.error(f"    ✗ Failed to update task status after retries")
                                elif should_update_status and scoro_task_id is None:
                                    logger.error(f"    ✗ Cannot update task status: Task ID not available")
                            except Exception as e:
                                logger.warning(f"    ⚠ Failed to update task status: {e}")
                            
                            # Create comments for task (same logic as parent tasks)
                            if subtask_stories and scoro_task_id:
                                comments_created = 0
                                comments_failed = 0
                                
                                for story in subtask_stories:
                                    try:
                                        story_type = story.get('type', '').lower()
                                        if story_type != 'comment':
                                            continue
                                        
                                        comment_text = story.get('text', '').strip()
                                        if not comment_text:
                                            continue
                                        
                                        comment_text = re.sub(r'<[^>]+>', '', comment_text).strip()
                                        if not comment_text:
                                            continue
                                        
                                        comment_text = replace_asana_profile_urls_with_scoro_mentions(
                                            comment_text,
                                            scoro_client,
                                            asana_data
                                        )
                                        
                                        comment_text_check = re.sub(r'<[^>]+>', '', comment_text).strip()
                                        if not comment_text_check:
                                            continue
                                        
                                        created_by = story.get('created_by', {})
                                        author_name = None
                                        if isinstance(created_by, dict):
                                            author_name = created_by.get('name', '')
                                        
                                        user_id = None
                                        if author_name:
                                            try:
                                                user_obj = scoro_client.find_user_by_name(author_name)
                                                if user_obj:
                                                    user_id = user_obj.get('id')
                                            except Exception:
                                                pass
                                        
                                        if user_id and user_id > 0:
                                            try:
                                                scoro_client.create_comment(
                                                    module='tasks',
                                                    object_id=scoro_task_id,
                                                    comment_text=comment_text,
                                                    user_id=user_id
                                                )
                                                comments_created += 1
                                            except Exception:
                                                comments_failed += 1
                                        else:
                                            comments_failed += 1
                                    except Exception:
                                        comments_failed += 1
                                
                                if comments_created > 0:
                                    logger.info(f"    ✓ Created {comments_created} comments for task")
                                if comments_failed > 0:
                                    logger.warning(f"    ⚠ Failed to create {comments_failed} comments for task")
                        
                        except Exception as e:
                            error_msg = f"Failed to create task (formerly subtask) '{subtask_name}': {e}"
                            print(f"Failed to create task (formerly subtask) '{subtask_name}': {e}")
                            logger.error(f"    ✗ {error_msg}")
                            import_results['errors'].append(error_msg)
                            summary.add_failure(error_msg)
        
        logger.info("="*60)
        logger.info(f"✓ Import completed!")
        logger.info(f"  Project: {'Created' if import_results['project'] else 'Failed'}")
        logger.info(f"  Milestones created: {len(import_results['milestones'])}")
        logger.info(f"  Phases created (from sections): {len(import_results.get('phases', []))}")
        logger.info(f"  Parent tasks created: {len(parent_tasks)}")
        logger.info(f"  Former subtasks created as regular tasks: {len(subtasks)}")
        logger.info(f"  Total tasks created: {len(import_results['tasks'])}")
        logger.info(f"  Tasks failed: {len([e for e in import_results['errors'] if 'task' in e.lower() or 'subtask' in e.lower()])}")
        logger.info(f"  Total errors: {len(import_results['errors'])}")
        logger.info("="*60)
        return import_results
        
    except Exception as e:
        error_msg = f"Error during import to Scoro: {e}"
        logger.error(error_msg)
        summary.add_failure(error_msg)
        raise

