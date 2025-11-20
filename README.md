# Asana to Scoro Migration Script

This Python script migrates project data (tasks, milestones, metadata, assignments, etc.) from Asana to Scoro using their respective public APIs.

## Features

- ✅ Authenticate with both Asana and Scoro APIs
- ✅ Export project details and tasks from Asana
- ✅ List existing projects in Scoro
- ✅ Modular structure for export, transform, and import functions
- ✅ Comprehensive logging and error tracking
- ✅ Migration summary reporting
- ✅ **Category/Activity Type Mapping**: Automatic mapping of 44 Asana categories to Scoro Activity Types
- ✅ **Blank Category Handling**: Tasks with no category automatically map to "Other" (no auto-inference)
- ✅ **Time Task Tracking Removal**: Time Task Tracking field eliminated - only Activity Types are used

## Prerequisites

- Python 3.7 or higher
- Admin/API access to both Asana and Scoro
- API credentials (see Setup below)

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API credentials:**
   - Copy `.env.example` to `.env`
   - Fill in your API credentials:
     ```
     ASANA_ACCESS_TOKEN=your_asana_token
     SCORO_API_KEY=your_scoro_api_key
     SCORO_COMPANY_NAME=your_company_subdomain
     ```

3. **Get API credentials:**
   - **Asana**: Create a Personal Access Token at https://app.asana.com/0/developer-console
   - **Scoro**: Contact Scoro support or your account manager for API key

## Usage

Run the script:
```bash
python asana2scoro_migration.py
```

The script will:
1. Connect to Asana and retrieve the project "Van Zeeland Nursery & Landscape"
2. Connect to Scoro and list existing projects
3. Export project data (saved to JSON file)
4. Transform data with category mapping and field mapping
5. Import transformed data to Scoro
6. Generate a summary report

**Note**: The import to Scoro is currently disabled for safety. Uncomment the import section in `main()` when ready to migrate.

## Project Structure

```
asana2scoro/
├── asana2scoro_migration.py  # Main migration script
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── .env                     # Your API credentials (create this)
└── README.md               # This file
```

## Code Structure

The script is organized into modular classes and functions:

- **`AsanaClient`**: Handles all Asana API interactions
  - `get_project_by_name()`: Find project by name
  - `get_project_details()`: Get detailed project info
  - `get_project_tasks()`: Get all tasks for a project
  - `get_task_details()`: Get detailed task info
  - `get_project_sections()`: Get project sections/columns

- **`ScoroClient`**: Handles all Scoro API interactions
  - `list_projects()`: List existing projects
  - `create_project()`: Create new project
  - `create_task()`: Create new task

- **`export_asana_project()`**: Export project data from Asana
- **`transform_data()`**: Transform Asana data to Scoro format with field mapping
- **`import_to_scoro()`**: Import transformed data into Scoro
- **`smart_map_activity_and_tracking()`**: Maps Asana categories to Scoro Activity Types
- **`smart_map_phase()`**: Maps tasks to project phases based on activity and section

- **`MigrationSummary`**: Tracks migration statistics and errors

## Current Implementation Status

### ✅ Completed
- Asana API authentication and project retrieval
- Scoro API authentication and project listing
- Basic project and task export from Asana
- Logging and error tracking
- Summary reporting
- **Category/Activity Type Mapping**: Complete mapping system with 44 category mappings
- **Data Transformation**: Field mapping and transformation logic implemented
- **Task Deduplication**: Handles duplicate tasks across client and team member projects
- **Project Phase Mapping**: Intelligent phase assignment based on activity type and section
- **User Validation**: User name mapping and validation for Scoro users

## Assumptions

- Project names are unique in Asana workspace
- API keys have necessary permissions
- Field mapping rules are defined in the referenced Google Doc
- Scoro API endpoints follow standard REST conventions

## Category Mapping

The script automatically maps Asana categories to Scoro Activity Types using a comprehensive mapping dictionary. Key features:

- **44 Category Mappings**: All common Asana categories are mapped to their Scoro equivalents
- **Blank Category Handling**: Tasks with no category assigned automatically map to "Other"
- **No Auto-Inference**: Categories are never inferred from task title, section, or assignee - only explicit mappings are used
- **Case-Insensitive Matching**: Handles variations in category name casing

**Important**: The Time Task Tracking field has been eliminated. Only the Activity Types dropdown (category field) is used for categorization.

## Limitations

- Attachments require additional implementation
- Rate limiting not yet implemented
- Error recovery is basic

## Next Steps

1. **Test with sample project**: Verify transformation logic with "Van Zeeland Nursery & Landscape"
2. **Enable import**: Uncomment import section and test with a test project in Scoro
3. **Add error handling**: Implement retry logic and better error messages
4. **Extend functionality**: Add support for attachments and enhanced comment handling

## Logging

The script generates log files with timestamps in the `logs/` folder:
- Format: `logs/migration_YYYYMMDD_HHMMSS.log`
- Contains all API calls, errors, and migration progress
- Also outputs to console

## Output Files

- **Migration log**: `logs/migration_YYYYMMDD_HHMMSS.log`
- **Exported data**: `asana_export_YYYYMMDD_HHMMSS.json`

## Troubleshooting

**Error: "Asana access token not provided"**
- Ensure `.env` file exists and contains `ASANA_ACCESS_TOKEN`

**Error: "Scoro API key not provided"**
- Ensure `.env` file contains both `SCORO_API_KEY` and `SCORO_COMPANY_NAME`

**Error: "Project not found"**
- Verify project name matches exactly (case-sensitive)
- Check that you have access to the project in Asana

**API Rate Limits**
- Currently not handled. Implement rate limiting if you encounter 429 errors.

## Support

For API documentation:
- Asana: https://developers.asana.com/docs
- Scoro: Contact Scoro support for API documentation

