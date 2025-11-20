"""
Import functionality for importing transformed data into Scoro
"""
from typing import Dict

from clients.scoro_client import ScoroClient
from models import MigrationSummary
from utils import logger, process_batch
from config import DEFAULT_BATCH_SIZE


def import_to_scoro(scoro_client: ScoroClient, transformed_data: Dict, summary: MigrationSummary, 
                     batch_size: int = DEFAULT_BATCH_SIZE) -> Dict:
    """
    Import transformed data into Scoro with batch processing support
    
    Args:
        scoro_client: Initialized ScoroClient instance
        transformed_data: Transformed data dictionary
        summary: Migration summary tracker
        batch_size: Number of items to process in each batch
    
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
        tasks_to_import = transformed_data.get('tasks', [])
        
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
                        # Link task to project if project_id is available
                        if project_id:
                            task_data['project_id'] = project_id
                            logger.debug(f"    Linked to project ID: {project_id}")
                        
                        # Remove fields that Scoro might not accept (metadata and name-only fields)
                        # Exclude: internal tracking fields, name-only fields (need ID resolution), 
                        # and fields not in Scoro Tasks API reference
                        task_data_clean = {k: v for k, v in task_data.items() 
                                         if k not in ['asana_gid', 'asana_permalink', 'dependencies', 'num_subtasks', 
                                                      'attachment_count', 'attachment_refs', 'followers',
                                                      'owner_name', 'assigned_to_name', 'project_phase_name', 
                                                      'project_name', 'company_name', 'tags', 'is_milestone']}
                        
                        # Map 'title' to 'event_name' (Scoro API requirement)
                        if 'title' in task_data_clean and 'event_name' not in task_data_clean:
                            task_data_clean['event_name'] = task_data_clean.pop('title')
                        
                        # TODO: Resolve user names to IDs
                        # - owner_name -> owner_id (Integer)
                        # - assigned_to_name -> related_users (Array of user IDs)
                        # - project_phase_name -> project_phase_id (Integer)
                        # - company_name -> company_id (Integer)
                        # For now, these fields are removed. ID resolution needs to be implemented.
                        
                        task = scoro_client.create_task(task_data_clean)
                        import_results['tasks'].append(task)
                        summary.add_success()
                        logger.info(f"    ✓ Task created: {task_name}")
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

