"""
Main entry point for Asana to Scoro migration script
"""
import sys
import json
from datetime import datetime

from clients import AsanaClient, ScoroClient
from models import MigrationSummary
from exporters import export_asana_project
from transformers import transform_data, reset_task_tracker, get_deduplication_stats
from importers import import_to_scoro
from utils import logger
from config import PROJECT_GIDS, PROJECT_NAMES, WORKSPACE_GID, MIGRATION_MODE


def migrate_single_project(asana_client, scoro_client, project_gid=None, project_name=None, workspace_gid=None):
    """
    Migrate a single project from Asana to Scoro
    
    Args:
        asana_client: Initialized Asana client
        scoro_client: Initialized Scoro client
        project_gid: Asana project GID (optional)
        project_name: Asana project name (optional)
        workspace_gid: Asana workspace GID
        
    Returns:
        dict: Migration results with 'success' (bool) and 'summary' (MigrationSummary)
    """
    summary = MigrationSummary()
    project_identifier = project_gid if project_gid else project_name
    
    try:
        # Export from Asana
        logger.info(f"\n{'='*60}")
        logger.info(f"PHASE 1: EXPORT FROM ASANA")
        logger.info(f"{'='*60}")
        
        if project_gid:
            logger.info(f"\nExporting project from Asana using GID: {project_gid}...")
            logger.info(f"Using project GID: {project_gid}, workspace GID: {workspace_gid}")
            asana_data = export_asana_project(asana_client, project_gid=project_gid, workspace_gid=workspace_gid)
        elif project_name:
            logger.info(f"\nExporting project from Asana: '{project_name}'...")
            asana_data = export_asana_project(asana_client, project_name=project_name, workspace_gid=workspace_gid)
        else:
            logger.error("Either project_gid or project_name must be provided")
            return {'success': False, 'summary': summary, 'project': project_identifier}
        
        if not asana_data:
            error_msg = f"✗ Project (GID: {project_gid if project_gid else 'name: ' + project_name}) not found or could not be exported."
            logger.error(error_msg)
            return {'success': False, 'summary': summary, 'project': project_identifier}
        
        logger.info(f"✓ Successfully exported project with {len(asana_data.get('tasks', []))} tasks")
        
        # Display project details
        if asana_data.get('project'):
            proj = asana_data['project']
            logger.info("Project Details Retrieved:")
            logger.info(f"  Name: {proj.get('name', 'N/A')}")
            logger.info(f"  GID: {proj.get('gid', 'N/A')}")
            logger.info(f"  Created: {proj.get('created_at', 'N/A')}")
            logger.info(f"  Modified: {proj.get('modified_at', 'N/A')}")
        
        # Transform data
        logger.info(f"\n{'='*60}")
        logger.info(f"PHASE 2: TRANSFORM DATA")
        logger.info(f"{'='*60}")
        logger.info("\nTransforming data...")
        transformed_data = transform_data(asana_data, summary)
        logger.info("✓ Data transformation completed")
        
        # Import to Scoro
        logger.info(f"\n{'='*60}")
        logger.info(f"PHASE 3: IMPORT TO SCORO")
        logger.info(f"{'='*60}")
        logger.info("\n" + "-"*60)
        logger.info("NOTE: Import to Scoro is currently enabled.")
        logger.info("-"*60)
        
        logger.info("\nImporting to Scoro...")
        import_results = import_to_scoro(scoro_client, transformed_data, summary, asana_data=asana_data)
        logger.info("✓ Import completed")
        
        # Print summary
        logger.info(f"\n{'='*60}")
        logger.info("Generating migration summary...")
        logger.info(f"{'='*60}")
        summary.print_summary()
        
        # Save export data to file for inspection
        # logger.info("Saving exported data to file...")
        # project_name_safe = proj.get('name', project_identifier).replace(' ', '_').replace('/', '_')
        # output_file = f"asana_export_{project_name_safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        # with open(output_file, 'w', encoding='utf-8') as f:
        #     json.dump(asana_data, f, indent=2, default=str)
        # logger.info(f"✓ Exported data saved to: {output_file}")
        
        return {
            'success': True,
            'summary': summary,
            'project': proj.get('name', project_identifier),
            'project_gid': proj.get('gid', project_gid)
        }
        
    except Exception as e:
        logger.error(f"Error migrating project {project_identifier}: {e}")
        return {'success': False, 'summary': summary, 'project': project_identifier, 'error': str(e)}


def main():
    """Main execution function"""
    logger.info("\n" + "="*60)
    logger.info("ASANA TO SCORO MIGRATION SCRIPT")
    logger.info("="*60 + "\n")
    
    # Reset task tracker for deduplication at the start of migration
    reset_task_tracker()
    logger.info("Task deduplication tracker reset")
    
    # Track results for all projects
    all_results = []
    
    try:
        # Initialize clients
        logger.info("="*60)
        logger.info("Starting migration process")
        logger.info("="*60)
        logger.info("Initializing API clients...")
        try:
            asana_client = AsanaClient()
            logger.info("✓ Asana client initialized successfully")
            
            # Test the connection
            logger.info("Testing Asana API connection...")
            if not asana_client.test_connection():
                logger.error("✗ Asana connection test failed")
                logger.error("\nPossible issues:")
                logger.error("  1. Your ASANA_ACCESS_TOKEN may be invalid or expired")
                logger.error("  2. The token may not have the required permissions")
                logger.error("  3. Check that your .env file is in the correct location")
                logger.error("\nTo fix:")
                logger.error("  - Create a new Personal Access Token at: https://app.asana.com/0/developer-console")
                logger.error("  - Update your .env file with the new token")
                return
            logger.info("✓ Asana connection test successful")
            
        except ValueError as e:
            logger.error(f"Authentication Error: {e}")
            logger.error("\nPlease ensure your .env file contains a valid ASANA_ACCESS_TOKEN.")
            logger.error("You can create a Personal Access Token at: https://app.asana.com/0/developer-console")
            return
        
        scoro_client = ScoroClient()
        
        # Test Scoro connection by listing projects
        logger.info("Testing Scoro connection...")
        try:
            scoro_projects = scoro_client.list_projects()
            logger.info(f"✓ Connected to Scoro. Found {len(scoro_projects)} existing projects.")
            if scoro_projects:
                logger.info("  Sample projects:")
                for proj in scoro_projects[:5]:  # Show first 5
                    logger.info(f"    - {proj.get('name', 'Unknown')}")
        except Exception as e:
            logger.error(f"✗ Error connecting to Scoro: {e}")
        
        # Determine which projects to migrate
        if MIGRATION_MODE == 'gids':
            if not PROJECT_GIDS:
                logger.error("No project GIDs configured. Please add project GIDs to config.py")
                return
            
            logger.info(f"\n{'='*60}")
            logger.info(f"MIGRATING {len(PROJECT_GIDS)} PROJECT(S) BY GID")
            logger.info(f"{'='*60}")
            
            for idx, project_gid in enumerate(PROJECT_GIDS, 1):
                logger.info(f"\n{'#'*60}")
                logger.info(f"PROJECT {idx}/{len(PROJECT_GIDS)}: GID {project_gid}")
                logger.info(f"{'#'*60}")
                
                result = migrate_single_project(
                    asana_client,
                    scoro_client,
                    project_gid=project_gid,
                    workspace_gid=WORKSPACE_GID
                )
                all_results.append(result)
                
                if result['success']:
                    logger.info(f"✓ Successfully migrated project: {result.get('project', project_gid)}")
                else:
                    logger.error(f"✗ Failed to migrate project: {result.get('project', project_gid)}")
                    if 'error' in result:
                        logger.error(f"  Error: {result['error']}")
        
        elif MIGRATION_MODE == 'names':
            if not PROJECT_NAMES:
                logger.error("No project names configured. Please add project names to config.py")
                return
            
            logger.info(f"\n{'='*60}")
            logger.info(f"MIGRATING {len(PROJECT_NAMES)} PROJECT(S) BY NAME")
            logger.info(f"{'='*60}")
            
            for idx, project_name in enumerate(PROJECT_NAMES, 1):
                logger.info(f"\n{'#'*60}")
                logger.info(f"PROJECT {idx}/{len(PROJECT_NAMES)}: {project_name}")
                logger.info(f"{'#'*60}")
                
                result = migrate_single_project(
                    asana_client,
                    scoro_client,
                    project_name=project_name,
                    workspace_gid=WORKSPACE_GID
                )
                all_results.append(result)
                
                if result['success']:
                    logger.info(f"✓ Successfully migrated project: {result.get('project', project_name)}")
                else:
                    logger.error(f"✗ Failed to migrate project: {result.get('project', project_name)}")
                    if 'error' in result:
                        logger.error(f"  Error: {result['error']}")
        else:
            logger.error(f"Invalid MIGRATION_MODE: {MIGRATION_MODE}. Must be 'gids' or 'names'")
            return
        
        # Print deduplication statistics
        dedup_stats = get_deduplication_stats()
        if dedup_stats['total_tasks_seen'] > 0:
            logger.info("\n" + "="*60)
            logger.info("DEDUPLICATION STATISTICS")
            logger.info("="*60)
            logger.info(f"Total unique tasks seen: {dedup_stats['total_tasks_seen']}")
            logger.info(f"  - From client projects: {dedup_stats['client_project_tasks']}")
            logger.info(f"  - From team member projects: {dedup_stats['team_member_project_tasks']}")
            logger.info(f"Deduplication: {dedup_stats['total_tasks_seen']} unique tasks "
                       f"({dedup_stats['client_project_tasks']} client, "
                       f"{dedup_stats['team_member_project_tasks']} team member)")
            logger.info("="*60)
        
        # Print overall summary
        logger.info(f"\n{'='*60}")
        logger.info("OVERALL MIGRATION SUMMARY")
        logger.info(f"{'='*60}")
        
        successful_migrations = sum(1 for r in all_results if r['success'])
        failed_migrations = len(all_results) - successful_migrations
        
        logger.info(f"Total projects: {len(all_results)}")
        logger.info(f"  ✓ Successful: {successful_migrations}")
        logger.info(f"  ✗ Failed: {failed_migrations}")
        
        if all_results:
            logger.info("\nProject Details:")
            for idx, result in enumerate(all_results, 1):
                status = "✓" if result['success'] else "✗"
                project_name = result.get('project', 'Unknown')
                logger.info(f"  {idx}. {status} {project_name}")
                if not result['success'] and 'error' in result:
                    logger.info(f"       Error: {result['error']}")
        
        logger.info(f"\n{'='*60}")
        logger.info("Migration process completed")
        logger.info(f"{'='*60}")
        
    except ValueError as e:
        # Handle authentication errors with a clear message
        logger.error(f"Authentication error: {e}")
        logger.error("\nPlease check your .env file and ensure ASANA_ACCESS_TOKEN is set correctly.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

