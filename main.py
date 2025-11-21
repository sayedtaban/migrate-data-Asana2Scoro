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


def main():
    """Main execution function"""
    logger.info("\n" + "="*60)
    logger.info("ASANA TO SCORO MIGRATION SCRIPT")
    logger.info("="*60 + "\n")
    
    summary = MigrationSummary()
    
    # Reset task tracker for deduplication at the start of migration
    reset_task_tracker()
    logger.info("Task deduplication tracker reset")
    
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
        
        # Export from Asana
        # You can use either project_name or project_gid (or both)
        # Option 1: Use project GID directly (faster, no search needed)
        project_gid = "1207816263671761"
        workspace_gid = "10447183158961"
        
        # Option 2: Or search by name (uncomment to use instead of GID)
        # project_name = "Van Zeeland Nursery & Landscape"
        project_name = None  # Set to None when using GID
        
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
            return
        
        if not asana_data:
            error_msg = f"✗ Project (GID: {project_gid if project_gid else 'name: ' + project_name}) not found or could not be exported."
            logger.error(error_msg)
            return
        
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
        
        # Save export data to file for inspection
        logger.info("Saving exported data to file...")
        output_file = f"asana_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(asana_data, f, indent=2, default=str)
        logger.info(f"✓ Exported data saved to: {output_file}")
        
        logger.info(f"\n{'='*60}")
        logger.info("Migration process completed")
        logger.info(f"{'='*60}")
        
    except ValueError as e:
        # Handle authentication errors with a clear message
        logger.error(f"Authentication error: {e}")
        logger.error("\nPlease check your .env file and ensure ASANA_ACCESS_TOKEN is set correctly.")
        summary.print_summary()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}")
        summary.print_summary()
        sys.exit(1)


if __name__ == '__main__':
    main()

