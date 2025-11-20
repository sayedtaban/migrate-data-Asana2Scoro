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
                company_id = company.get('id') or company.get('company_id') or company.get('client_id')
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
                    company_id = company.get('id') or company.get('company_id') or company.get('client_id')
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
                
                # Link project to company if we have one
                # In Scoro, projects must be linked to a company/client record
                if company:
                    # Extract company ID - try multiple possible field names
                    company_id = (
                        company.get('id') or 
                        company.get('company_id') or 
                        company.get('client_id')
                    )
                    if company_id:
                        project_data['company_id'] = company_id
                        logger.info(f"  Linking project to company ID: {company_id}")
                    else:
                        logger.warning(f"  Company record found but no ID available: {company}")
                
                project = scoro_client.create_project(project_data)
                import_results['project'] = project
                summary.add_success()
                logger.info(f"✓ Project created successfully: {project.get('name', 'Unknown')}")
            except Exception as e:
                error_msg = f"Failed to create project: {e}"
                logger.error(f"✗ {error_msg}")
                import_results['errors'].append(error_msg)
                summary.add_failure(error_msg)
        else:
            logger.warning("No project data found in transformed_data")
        
        # Create milestones
        milestones_to_import = transformed_data.get('milestones', [])
        if milestones_to_import:
            logger.info(f"Creating {len(milestones_to_import)} milestones in Scoro...")
            project_id = import_results['project'].get('id') if import_results['project'] else None
            
            for idx, milestone_data in enumerate(milestones_to_import, 1):
                milestone_name = milestone_data.get('name', 'Unknown')
                logger.info(f"  [{idx}/{len(milestones_to_import)}] Creating milestone: {milestone_name}")
                try:
                    if project_id:
                        milestone_data['project_id'] = project_id
                    
                    milestone = scoro_client.create_milestone(milestone_data)
                    import_results['milestones'].append(milestone)
                    summary.add_success()
                    logger.info(f"    ✓ Milestone created: {milestone_name}")
                except Exception as e:
                    error_msg = f"Failed to create milestone '{milestone_name}': {e}"
                    logger.error(f"    ✗ {error_msg}")
                    import_results['errors'].append(error_msg)
                    summary.add_failure(error_msg)
        
        # Create tasks with batch processing
        project_id = import_results['project'].get('id') if import_results['project'] else None
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
                        
                        # Remove fields that Scoro might not accept
                        task_data_clean = {k: v for k, v in task_data.items() 
                                         if k not in ['asana_gid', 'asana_permalink', 'dependencies', 'num_subtasks', 
                                                      'attachment_count', 'attachment_refs', 'followers']}
                        
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

