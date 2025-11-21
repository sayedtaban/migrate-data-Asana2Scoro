# Asana to Scoro Migration Script

This Python script migrates project data (tasks, milestones, metadata, assignments, etc.) from Asana to Scoro using their respective public APIs.

---

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Multi-Project Migration](#multi-project-migration)
  - [Configuration Options](#configuration-options)
- [Project Structure](#project-structure)
- [Code Structure](#code-structure)
- [What's New in This Version](#whats-new-in-this-version)
- [Implementation Status](#implementation-status)
- [Migration Workflow](#migration-workflow)
- [Category Mapping](#category-mapping)
- [Task Deduplication](#task-deduplication)
- [Configuration Details](#configuration-details)
- [Performance Considerations](#performance-considerations)
- [Logging & Output](#logging--output)
- [Best Practices](#best-practices)
- [Known Limitations](#known-limitations)
- [Future Enhancements](#future-enhancements)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)
- [FAQ](#frequently-asked-questions-faq)
- [Support & Resources](#support--resources)

---

## Features

### Core Functionality
- ✅ **Multi-Project Migration**: Migrate multiple projects in one run (by GID or name)
- ✅ **Dual API Integration**: Authenticate with both Asana and Scoro APIs
- ✅ **Complete Data Export**: Export projects, tasks, sections, custom fields, and metadata from Asana
- ✅ **Smart Data Import**: Create projects and tasks in Scoro with proper relationships
- ✅ **Modular Architecture**: Separate modules for export, transform, and import functions

### Data Transformation & Mapping
- ✅ **Category/Activity Type Mapping**: Automatic mapping of 44+ Asana categories to Scoro Activity Types
- ✅ **Blank Category Handling**: Tasks with no category automatically map to "Other" (no auto-inference)
- ✅ **Time Task Tracking Removal**: Time Task Tracking field eliminated - only Activity Types are used
- ✅ **Smart User Mapping**: Automatic validation and mapping of user names to Scoro users
- ✅ **Project Phase Mapping**: Intelligent phase assignment based on task context
- ✅ **Date Filtering**: Filter tasks by completion date (configurable cutoff date)

### Deduplication & Quality
- ✅ **Task Deduplication**: Prevent duplicate tasks across client and team member projects
- ✅ **Client Project Detection**: Automatic distinction between client and team member projects
- ✅ **Data Validation**: Comprehensive validation of fields and relationships

### Performance & Reliability
- ✅ **Rate Limiting**: Built-in rate limiting and exponential backoff for both APIs
- ✅ **Retry Logic**: Automatic retries for failed API calls
- ✅ **Batch Processing**: Efficient batch processing of large task sets
- ✅ **Connection Testing**: Verify API connectivity before migration starts

### Monitoring & Reporting
- ✅ **Comprehensive Logging**: Detailed logs with timestamps for all operations
- ✅ **Migration Summary Reports**: Success/failure statistics and error tracking
- ✅ **Deduplication Statistics**: Track duplicate tasks across projects
- ✅ **JSON Export**: Save raw Asana data for inspection and backup
- ✅ **Progress Tracking**: Real-time progress updates during migration

### Configuration & Testing
- ✅ **Test Mode**: Limit number of tasks for testing (configurable)
- ✅ **Flexible Configuration**: Environment-based configuration with .env file
- ✅ **User Customization**: Customize user mappings, date filters, and batch sizes
- ✅ **Multiple Migration Modes**: Choose between GID or name-based project selection

## Prerequisites

- Python 3.7 or higher
- Admin/API access to both Asana and Scoro
- API credentials (see Setup below)

## Quick Start

For detailed setup instructions, see **[SETUP.md](SETUP.md)** - a comprehensive step-by-step guide.

### Brief Setup Summary

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create `.env` file** with your API credentials:
   ```env
   ASANA_ACCESS_TOKEN=your_asana_token
   SCORO_API_KEY=your_scoro_api_key
   SCORO_COMPANY_NAME=your_company_subdomain
   ```

3. **Get API credentials:**
   - **Asana**: Create a Personal Access Token at https://app.asana.com/0/developer-console
   - **Scoro**: Contact Scoro support or your account manager for API key

4. **Configure projects** in `config.py`:
   - Set `MIGRATION_MODE` to `'gids'` or `'names'`
   - Add your project GIDs or names
   - Set your `WORKSPACE_GID`

5. **Run the migration:**
   ```bash
   python main.py
   ```

**→ For complete setup instructions, troubleshooting, and best practices, see [SETUP.md](SETUP.md)**

## Usage

### Multi-Project Migration

The script now supports migrating multiple projects at once. Configure your projects in `config.py`:

**Option 1: Migrate by Project GIDs (Recommended - Faster)**
```python
# In config.py
MIGRATION_MODE = 'gids'
PROJECT_GIDS = [
    "1207816263671761",  # Project 1
    "1234567890123456",  # Project 2
    "9876543210987654",  # Project 3
]
WORKSPACE_GID = "10447183158961"
```

**Option 2: Migrate by Project Names**
```python
# In config.py
MIGRATION_MODE = 'names'
PROJECT_NAMES = [
    "Van Zeeland Nursery & Landscape",
    "Another Project Name",
    "Third Project",
]
WORKSPACE_GID = "10447183158961"
```

Run the migration script:
```bash
python main.py
```

The script will:
1. Connect to Asana and Scoro APIs
2. Loop through each configured project
3. For each project:
   - Export project data from Asana (saved to JSON file with timestamp)
   - Transform data with category mapping, field mapping, and deduplication
   - Import transformed data to Scoro
   - Generate a summary report
4. Display overall migration statistics for all projects

**Configuration Options** (in `config.py`):
- **Multi-Project Mode**: Set `MIGRATION_MODE` to `'gids'` or `'names'`
- **Project Lists**: Configure `PROJECT_GIDS` or `PROJECT_NAMES` with your projects
- **Workspace GID**: Set `WORKSPACE_GID` to your Asana workspace identifier
- **Test Mode**: Set `TEST_MODE_MAX_TASKS` to limit migration (e.g., 10 tasks for testing)
- **Date Filtering**: Configure `CUTOFF_DATE` to filter tasks by completion date
- **User Mapping**: Customize `USER_MAPPING` and `VALID_SCORO_USERS`

## Project Structure

```
migrate-data-Asana2Scoro/
├── main.py                      # Main migration script entry point
├── config.py                    # Configuration and constants
├── models.py                    # Data models and summary tracking
├── utils.py                     # Logging and utility functions
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── .env                         # Your API credentials (create this)
├── README.md                    # This file
├── workflow.md                  # Detailed workflow documentation
├── clients/                     # API client implementations
│   ├── __init__.py
│   ├── asana_client.py         # Asana API client
│   └── scoro_client.py         # Scoro API client
├── exporters/                   # Data export modules
│   ├── __init__.py
│   └── asana_exporter.py       # Asana project export logic
├── transformers/                # Data transformation modules
│   ├── __init__.py
│   ├── data_transformer.py     # Main transformation logic
│   ├── mappers.py              # Category and field mapping
│   ├── field_extractors.py    # Field extraction utilities
│   └── deduplication.py        # Task deduplication logic
├── importers/                   # Data import modules
│   ├── __init__.py
│   └── scoro_importer.py       # Scoro data import logic
├── tests/                       # Test files
│   └── test_project_managers.py
├── docs/                        # Documentation
│   ├── Migration Rules & Field Mapping.md
│   ├── Scoro API Reference.md
│   └── [other documentation files]
└── logs/                        # Migration log files
    └── migration_YYYYMMDD_HHMMSS.log
```

## Code Structure

The codebase is organized into a modular architecture:

### Core Modules

- **`main.py`**: Main entry point orchestrating the migration process
- **`config.py`**: Centralized configuration (rate limiting, user mapping, test mode)
- **`models.py`**: Data models (`MigrationSummary`, etc.)
- **`utils.py`**: Logging setup and utility functions

### Clients (`clients/`)

- **`AsanaClient`** (`asana_client.py`): Asana API interactions
  - `test_connection()`: Verify API connectivity
  - `get_project_by_name()`: Find project by name
  - `get_project_by_gid()`: Get project by GID
  - `get_project_tasks()`: Retrieve all tasks with pagination
  - `get_task_details()`: Get detailed task information
  - `get_project_sections()`: Get project sections/columns
  - `get_users()`: Retrieve workspace users

- **`ScoroClient`** (`scoro_client.py`): Scoro API interactions
  - `list_projects()`: List existing projects
  - `get_project_by_name()`: Find project by name
  - `create_project()`: Create new project
  - `create_task()`: Create new task
  - `add_task_comment()`: Add comments to tasks
  - `get_users()`: Retrieve Scoro users
  - Rate limiting and retry logic built-in

### Exporters (`exporters/`)

- **`export_asana_project()`** (`asana_exporter.py`): Comprehensive Asana data export
  - Handles both project GID and name-based lookups
  - Exports tasks, sections, custom fields, and metadata

### Transformers (`transformers/`)

- **`transform_data()`** (`data_transformer.py`): Main transformation pipeline
  - Field mapping and data restructuring
  - Date handling and validation
  - User assignment mapping

- **`mappers.py`**: Category and phase mapping logic
  - `smart_map_activity_and_tracking()`: Maps Asana categories to Scoro Activity Types
  - `smart_map_phase()`: Intelligent phase assignment
  - 44+ category mappings

- **`deduplication.py`**: Task deduplication system
  - Prevents duplicate tasks across client and team member projects
  - Tracks processed tasks by unique identifiers

- **`field_extractors.py`**: Field extraction utilities
  - Parses custom fields and metadata

### Importers (`importers/`)

- **`import_to_scoro()`** (`scoro_importer.py`): Scoro data import
  - Project creation and linking
  - Task creation with proper relationships
  - Comment and metadata import
  - Error handling and rollback support

## What's New in This Version

### Latest Features & Improvements

- **🚀 Multi-Project Migration**: Migrate multiple projects in a single run
  - Support for both GID-based and name-based project selection
  - Overall migration summary across all projects
  - Individual project tracking and error reporting

- **🔍 Smart Deduplication System**: Prevent duplicate tasks across projects
  - Automatic detection of client vs. team member projects
  - Track and report deduplication statistics
  - Global task tracker across multiple project migrations

- **📊 Enhanced Reporting**: Comprehensive migration statistics
  - Per-project success/failure tracking
  - Deduplication statistics (client vs. team member projects)
  - Detailed error logs with timestamps
  - JSON export of raw Asana data for auditing

- **⚙️ Flexible Configuration**: Multiple migration modes and options
  - Choose between GID or name-based project migration
  - Test mode with configurable task limits
  - Date filtering to migrate only recent tasks
  - Customizable user mappings and validation

- **🛡️ Improved Reliability**: Better error handling and API management
  - Connection testing before migration starts
  - Rate limiting with exponential backoff
  - Automatic retry logic for failed API calls
  - Comprehensive validation at every step

- **📝 Better Documentation**: Complete setup and troubleshooting guides
  - New [SETUP.md](SETUP.md) with step-by-step instructions
  - Troubleshooting section for common issues
  - API credential setup guides
  - Configuration examples and best practices

## Implementation Status

### ✅ Fully Implemented
- ✅ Multi-project migration (by GID or name)
- ✅ Complete API integration (Asana & Scoro)
- ✅ Task deduplication system
- ✅ Category/Activity type mapping (44+ mappings)
- ✅ User mapping and validation
- ✅ Date filtering and test mode
- ✅ Rate limiting and retry logic
- ✅ Comprehensive logging and reporting
- ✅ Project phase mapping
- ✅ Comment and metadata preservation
- ✅ Connection testing
- ✅ Batch processing

## Assumptions

- Project names are unique in Asana workspace
- API keys have necessary permissions
- Field mapping rules are defined in the referenced Google Doc
- Scoro API endpoints follow standard REST conventions

## Category Mapping

The script automatically maps Asana categories to Scoro Activity Types using a comprehensive mapping dictionary defined in `transformers/mappers.py`.

### Key Features

- **44+ Category Mappings**: All common Asana categories are mapped to their Scoro equivalents
- **Blank Category Handling**: Tasks with no category assigned automatically map to "Other"
- **No Auto-Inference**: Categories are never inferred from task title, section, or assignee - only explicit mappings are used
- **Case-Insensitive Matching**: Handles variations in category name casing

### Example Mappings

| Asana Category | Scoro Activity Type |
|----------------|---------------------|
| Account Management | Project Management |
| Website Design | Website - New |
| Website Updates | Website - SEO |
| SEO Services | SEO |
| Social Posting | Social Posting |
| Google Ads | Google Ads |
| Facebook Ads | Facebook Ads |
| Brochure | Brochure |
| Onboarding | Onboarding |
| Videography | Videography |
| Email | Email |
| ... and 34+ more | ... |

### Customizing Mappings

To add or modify category mappings, edit `transformers/mappers.py`:

```python
CATEGORY_MAPPING = {
    'Your Asana Category': 'Your Scoro Activity Type',
    # Add more mappings as needed
}
```

**Important**: The Time Task Tracking field has been eliminated. Only the Activity Types dropdown (category field) is used for categorization.

## Task Deduplication

The migration script includes a smart deduplication system to prevent duplicate tasks when migrating multiple projects.

### How It Works

1. **Task Tracking**: Each task is tracked by its unique Asana GID
2. **Project Type Detection**: Automatically distinguishes between:
   - **Client Projects**: Named after clients/companies
   - **Team Member Projects**: Personal projects (e.g., "Austin's Tasks")
3. **Priority System**: Client projects take precedence over team member projects
4. **Statistics**: Reports deduplication metrics at the end of migration

### Why Deduplication Matters

In Asana, the same task can appear in multiple projects:
- A client project (e.g., "Van Zeeland Nursery")
- A team member's personal project (e.g., "Lena's Tasks")

Without deduplication, migrating both projects would create duplicate tasks in Scoro. The deduplication system ensures each task is migrated only once.

### Deduplication Report Example

```
DEDUPLICATION STATISTICS
Total unique tasks seen: 150
  - From client projects: 120
  - From team member projects: 30
Deduplication: 150 unique tasks (120 client, 30 team member)
```

### Customizing Deduplication

Project type detection is based on naming patterns in `transformers/deduplication.py`. Customize if needed:

```python
# Team member project indicators
team_member_indicators = [
    "'s project",
    "'s tasks",
    "'s workspace",
    " personal",
]
```

## Configuration Details

### Test Mode
Set `TEST_MODE_MAX_TASKS` in `config.py` to limit the number of tasks migrated:
- `None`: Migrate all tasks (production mode)
- `10`: Migrate only first 10 tasks (testing)

### Date Filtering
Configure `CUTOFF_DATE` in `config.py` to filter tasks by completion date:
```python
CUTOFF_DATE = datetime(2025, 7, 1)  # Only migrate tasks completed after this date
```

### User Mapping
Customize `USER_MAPPING` and `VALID_SCORO_USERS` in `config.py` to map Asana users to Scoro users:
- `VALID_SCORO_USERS`: Set of valid Scoro user full names
- `USER_MAPPING`: Dictionary mapping short names to full Scoro names

### Rate Limiting
Configure API rate limiting in `config.py`:
- `RATE_LIMIT_DELAY`: Delay between API calls (default: 0.1s)
- `MAX_RETRIES`: Maximum retry attempts (default: 3)
- `RETRY_BACKOFF`: Exponential backoff multiplier (default: 2)

## Known Limitations

### Current Limitations

- **Attachments**: File attachments are not migrated (requires additional file handling)
- **Subtasks**: Complex subtask hierarchies are flattened
- **Custom Field Types**: Some advanced custom field types may have limited support
- **Task Dependencies**: Direct task dependencies are not preserved (use sections/phases instead)
- **Recurring Tasks**: Recurrence patterns are not migrated

### Filtering Defaults

- **Date Cutoff**: Tasks before the configured `CUTOFF_DATE` are filtered out (default: July 1, 2025)
- **Incomplete Tasks**: Only completed tasks are migrated by default (can be customized)

### API Constraints

- **Rate Limits**: Both Asana and Scoro APIs have rate limits (handled automatically)
- **Batch Sizes**: Large projects may require longer migration times
- **Timeout**: Very large task lists (1000+) may require multiple runs

## Performance Considerations

### Optimization Tips

1. **Use GID Mode**: Migrating by project GID is faster than by name (skips search)
2. **Test Mode First**: Always test with `TEST_MODE_MAX_TASKS = 10` before full migration
3. **Adjust Rate Limits**: If experiencing timeouts, increase `RATE_LIMIT_DELAY` in `config.py`
4. **Batch Processing**: For very large projects (500+ tasks), consider splitting into multiple runs

### Typical Migration Times

- **Small Project** (10-50 tasks): 1-3 minutes
- **Medium Project** (50-200 tasks): 3-10 minutes
- **Large Project** (200-500 tasks): 10-30 minutes
- **Extra Large Project** (500+ tasks): 30+ minutes

*Times vary based on network speed, API performance, and number of comments per task.*

## Future Enhancements

### Planned Features

1. **Attachment Migration**: Download and upload file attachments
2. **Enhanced Dependency Mapping**: Preserve task dependencies and relationships
3. **Incremental Updates**: Update existing Scoro tasks instead of creating new ones
4. **Rollback Support**: Ability to undo migrations and restore previous state
5. **Dry Run Mode**: Preview what would be migrated without making changes
6. **Progress Bar**: Real-time visual progress indicator
7. **Email Notifications**: Send summary reports via email after migration

### Potential Improvements

- **Parallel Processing**: Migrate multiple projects simultaneously
- **Resume Support**: Resume interrupted migrations from last checkpoint
- **Conflict Resolution**: Better handling of naming conflicts
- **Custom Webhooks**: Trigger custom actions on migration events
- **Advanced Filtering**: More granular filtering options (by tag, assignee, etc.)

## Logging & Output

### Log Files

The script generates comprehensive log files with timestamps in the `logs/` directory:

**Format:** `logs/migration_YYYYMMDD_HHMMSS.log`

**Contents:**
- 🔌 All API calls and responses
- 🔄 Data transformation decisions
- 🗺️ Category and user mapping results
- ⚠️ Errors, warnings, and issues
- 📊 Migration statistics and summaries
- 🔍 Deduplication tracking
- ✅ Success/failure indicators

**Output:** Logs are written to both file and console for real-time monitoring.

### Log Levels

- **INFO**: Normal operations, progress updates, summaries
- **WARNING**: Non-critical issues, fallback actions
- **ERROR**: Failed operations, API errors, validation failures

### Example Log Output

```
==============================================================
ASANA TO SCORO MIGRATION SCRIPT
==============================================================

Initializing API clients...
✓ Asana client initialized successfully
Testing Asana API connection...
✓ Asana connection test successful
✓ Connected to Scoro. Found 45 existing projects.

==============================================================
MIGRATING 3 PROJECT(S) BY GID
==============================================================

############################################################
PROJECT 1/3: GID 1207816263671761
############################################################

==============================================================
PHASE 1: EXPORT FROM ASANA
==============================================================
✓ Successfully exported project with 125 tasks

==============================================================
PHASE 2: TRANSFORM DATA
==============================================================
✓ Data transformation completed

==============================================================
PHASE 3: IMPORT TO SCORO
==============================================================
✓ Import completed

==============================================================
MIGRATION SUMMARY
==============================================================
Total Items Attempted: 125
Succeeded: 122
Failed: 3
```

### Export Files

Each migration creates JSON export files for backup and auditing:

**Format:** `asana_export_[PROJECT_NAME]_YYYYMMDD_HHMMSS.json`

**Contents:**
- Complete project metadata
- All task details and custom fields
- Sections and organizational structure
- User assignments and comments
- Timestamps and relationships

**Usage:**
- Backup of original Asana data
- Audit trail for compliance
- Debugging and troubleshooting
- Data analysis and reporting

### Output Directory Structure

```
migrate-data-Asana2Scoro/
├── logs/
│   ├── migration_20251121_143027.log
│   ├── migration_20251121_150815.log
│   └── migration_20251121_160808.log
├── asana_export_VanZeeland_20251121_143027.json
├── asana_export_AnotherProject_20251121_143105.json
└── asana_export_ThirdProject_20251121_143142.json
```

### Viewing Logs

**View the latest log:**
```bash
ls -lt logs/ | head -n 1
cat logs/migration_YYYYMMDD_HHMMSS.log
```

**Search for errors:**
```bash
grep -i "error" logs/migration_*.log
grep -i "failed" logs/migration_*.log
```

**Search for specific project:**
```bash
grep -i "project name" logs/migration_*.log
```

**View deduplication statistics:**
```bash
grep -A 5 "DEDUPLICATION STATISTICS" logs/migration_*.log
```

## Migration Workflow

### Step-by-Step Process

The migration follows a three-phase approach for each project:

#### Phase 1: Export from Asana

1. **Connect to Asana API** using your Personal Access Token
2. **Locate project** by GID or name
3. **Export project data**:
   - Project metadata (name, description, dates)
   - All tasks with complete details
   - Custom fields and values
   - Sections/columns structure
   - User assignments
   - Comments and notes
4. **Save to JSON** for backup and auditing

#### Phase 2: Transform Data

1. **Map categories** using the category mapping dictionary (44+ mappings)
2. **Validate users** against Scoro user list
3. **Deduplicate tasks** across multiple projects
4. **Map project phases** based on sections and activity types
5. **Transform fields** according to field mapping rules:
   - Convert dates to Scoro format
   - Map custom fields
   - Structure comments
   - Validate relationships
6. **Apply filters**:
   - Date cutoff filtering
   - Test mode limiting (if enabled)

#### Phase 3: Import to Scoro

1. **Create or locate project** in Scoro
2. **Associate client** (if configured)
3. **Assign project manager**
4. **Create tasks** in batches:
   - Set task names and descriptions
   - Assign users
   - Set activity types (categories)
   - Set project phases
   - Add dates and status
5. **Add comments** to tasks
6. **Track results** and errors

### Multi-Project Migration

When migrating multiple projects:

1. **Initialize once**: Connect to both APIs
2. **Reset deduplication tracker** at start
3. **Loop through projects**:
   - Export → Transform → Import for each
   - Track results per project
4. **Generate reports**:
   - Per-project summaries
   - Overall migration statistics
   - Deduplication statistics

### Error Handling

- **API Failures**: Automatic retry with exponential backoff
- **Validation Errors**: Logged and tracked, migration continues
- **Missing Data**: Falls back to defaults (e.g., "Other" category, "Tom Sanpakit" user)
- **Rate Limits**: Automatic delay and retry

## Documentation

### Main Documentation

- **[README.md](README.md)** (this file): Overview and feature documentation
- **[SETUP.md](SETUP.md)**: Complete setup guide with troubleshooting
- **[workflow.md](workflow.md)**: Detailed workflow documentation

### Technical Documentation

Additional documentation is available in the `docs/` directory:

- **[Migration Rules & Field Mapping.md](docs/Migration%20Rules%20&%20Field%20Mapping.md)**: Complete field mapping specifications
- **[Scoro API Reference.md](docs/Scoro%20API%20Reference.md)**: Scoro API endpoint documentation
- **[CLIENT_ASSOCIATION_IMPLEMENTATION.md](docs/CLIENT_ASSOCIATION_IMPLEMENTATION.md)**: Client association logic details
- **[REFACTORING_SUMMARY.md](docs/REFACTORING_SUMMARY.md)**: Code refactoring history and decisions
- **[BUG_FIX_PROJECT_ASSIGNMENT.md](docs/BUG_FIX_PROJECT_ASSIGNMENT.md)**: Project assignment bug fixes

### Code Documentation

- **Inline Comments**: Detailed comments throughout the codebase
- **Function Docstrings**: Description of parameters, return values, and behavior
- **Module Docstrings**: Overview of each module's purpose

## Best Practices

### Before Migration

1. **Test with Small Dataset First**
   ```python
   # In config.py
   TEST_MODE_MAX_TASKS = 10
   ```

2. **Backup Your Data**
   - The script creates JSON exports automatically
   - Keep these files as backup records

3. **Verify API Credentials**
   - Test connections before full migration
   - Ensure you have proper permissions in both systems

4. **Review Category Mappings**
   - Check `transformers/mappers.py`
   - Add any custom categories your organization uses

5. **Customize User Mappings**
   - Update `VALID_SCORO_USERS` in `config.py`
   - Add `USER_MAPPING` entries for short names

### During Migration

1. **Monitor the Console Output**
   - Watch for errors and warnings
   - Note any validation issues

2. **Don't Interrupt the Process**
   - Let the migration complete fully
   - Interrupting may cause incomplete data

3. **Check Logs in Real-Time**
   ```bash
   tail -f logs/migration_*.log
   ```

### After Migration

1. **Review the Summary Report**
   - Check success/failure counts
   - Review any errors logged

2. **Verify in Scoro**
   - Log into Scoro
   - Spot-check projects and tasks
   - Verify assignments and categories

3. **Audit the Data**
   - Review JSON export files
   - Compare Asana vs. Scoro data
   - Document any discrepancies

4. **Save the Logs**
   - Archive log files for future reference
   - Keep for compliance and auditing

### Recommended Migration Strategy

1. **Phase 1: Single Test Project**
   - Migrate one small project with `TEST_MODE_MAX_TASKS = 10`
   - Verify all data looks correct in Scoro

2. **Phase 2: Full Test Project**
   - Migrate the same project fully (`TEST_MODE_MAX_TASKS = None`)
   - Verify complete migration works properly

3. **Phase 3: Multiple Projects**
   - Add more projects to the configuration
   - Run multi-project migration
   - Monitor deduplication statistics

4. **Phase 4: Production Migration**
   - Migrate all remaining projects
   - Archive all logs and exports
   - Document the process

## Troubleshooting

For comprehensive troubleshooting, see **[SETUP.md - Troubleshooting Section](SETUP.md#troubleshooting)**.

### Quick Reference

**Error: "Asana access token not provided"**
- Ensure `.env` file exists in project root
- Verify `ASANA_ACCESS_TOKEN` is set correctly
- No spaces around the `=` sign

**Error: "Asana connection test failed"**
- Token may be invalid or expired
- Create new token at https://app.asana.com/0/developer-console
- Check token has proper permissions

**Error: "Scoro API key not provided"**
- Ensure both `SCORO_API_KEY` and `SCORO_COMPANY_NAME` are set
- Contact Scoro support to verify credentials

**Error: "Project not found"**
- For GID mode: Verify the GID from Asana URL
- For name mode: Check exact name (case-sensitive)
- Ensure you have access to the project

**No tasks imported / All tasks filtered out**
- Check `CUTOFF_DATE` in `config.py`
- Review logs for filter reasons
- Verify tasks have completion dates

**Rate limiting / 429 errors**
- Increase `RATE_LIMIT_DELAY` in `config.py`
- Reduce `DEFAULT_BATCH_SIZE`
- Wait a few minutes and retry

**Script crashes or hangs**
- Check internet connection
- Try with smaller batch size
- Enable `TEST_MODE_MAX_TASKS` to test
- Review logs for specific errors

### Getting Help

1. **Check the logs**: `logs/migration_*.log` contains detailed information
2. **Review documentation**: See [SETUP.md](SETUP.md) for detailed troubleshooting
3. **API Documentation**:
   - Asana: https://developers.asana.com/docs
   - Scoro: Contact Scoro support

## Frequently Asked Questions (FAQ)

### General Questions

**Q: How long does a migration take?**  
A: It depends on project size:
- Small (10-50 tasks): 1-3 minutes
- Medium (50-200 tasks): 3-10 minutes
- Large (200-500 tasks): 10-30 minutes
- Extra Large (500+ tasks): 30+ minutes

**Q: Can I migrate the same project multiple times?**  
A: Yes, but it will create duplicate tasks in Scoro. The script doesn't update existing tasks, only creates new ones.

**Q: Will this delete or modify anything in Asana?**  
A: No. The script only reads from Asana, never writes or deletes.

**Q: What happens if the migration is interrupted?**  
A: Any tasks already created in Scoro will remain. You can resume by migrating the project again (but this may create duplicates).

**Q: Can I undo a migration?**  
A: Not automatically. You would need to manually delete the migrated project/tasks in Scoro. Keep the JSON exports as backup.

### Configuration Questions

**Q: Should I use GID or name mode?**  
A: GID mode is recommended - it's faster and more reliable. Use name mode only if you don't have GIDs readily available.

**Q: How do I find my Workspace GID?**  
A: Look at any Asana project URL: `https://app.asana.com/0/WORKSPACE_GID/PROJECT_GID`. The first long number is your workspace GID.

**Q: Can I migrate only specific tasks?**  
A: Yes, use `CUTOFF_DATE` to filter by completion date, or `TEST_MODE_MAX_TASKS` to limit the count.

**Q: How do I customize category mappings?**  
A: Edit `transformers/mappers.py` and add your custom mappings to the `CATEGORY_MAPPING` dictionary.

### Data Questions

**Q: Are attachments migrated?**  
A: Not currently. This is a planned future enhancement.

**Q: Are subtasks migrated?**  
A: Yes, but they're migrated as regular tasks, not as hierarchical subtasks.

**Q: Are comments preserved?**  
A: Yes, comments are migrated and added to the tasks in Scoro.

**Q: What happens to tasks without a category?**  
A: They're automatically assigned the "Other" category.

**Q: What happens if a user doesn't exist in Scoro?**  
A: The task is assigned to "Tom Sanpakit" as a fallback (configurable in code).

### Technical Questions

**Q: Do I need to keep the script running?**  
A: Yes, the script must run to completion. Don't close the terminal or turn off your computer.

**Q: Can I run multiple migrations simultaneously?**  
A: Not recommended. Run them sequentially to avoid rate limiting and data conflicts.

**Q: What Python version do I need?**  
A: Python 3.7 or higher. Check with `python --version`.

**Q: Can I run this on Windows/Mac/Linux?**  
A: Yes, the script is cross-platform and works on all operating systems.

**Q: How much memory/disk space do I need?**  
A: Minimal. Even large projects (500+ tasks) use less than 100MB of memory and disk space.

### Deduplication Questions

**Q: What is task deduplication?**  
A: It prevents the same task from being migrated twice when it appears in multiple projects (e.g., a client project and a team member's project).

**Q: How does it determine which project to use?**  
A: Client projects take precedence over team member projects.

**Q: Can I disable deduplication?**  
A: Not currently, but you can modify `transformers/deduplication.py` to customize the logic.

**Q: How do I know how many tasks were deduplicated?**  
A: Check the "DEDUPLICATION STATISTICS" section in the console output or log file.

## Support & Resources

### Documentation Resources

- **[SETUP.md](SETUP.md)**: Complete setup guide with troubleshooting
- **[README.md](README.md)**: This file - feature overview and usage
- **[workflow.md](workflow.md)**: Detailed workflow documentation
- **`docs/` directory**: Technical documentation and specifications

### API Documentation

- **Asana API**: https://developers.asana.com/docs
  - Authentication guide
  - API reference
  - Rate limits and best practices

- **Scoro API**: Contact Scoro support or your account manager
  - API key request
  - Endpoint documentation
  - Technical support

### Getting Help

1. **Check the logs**: Detailed error messages in `logs/migration_*.log`
2. **Review troubleshooting**: See [SETUP.md - Troubleshooting](SETUP.md#troubleshooting)
3. **Search the FAQ**: Common questions answered above
4. **Check configuration**: Verify `config.py` and `.env` settings

### Reporting Issues

When reporting issues, please include:

- Python version (`python --version`)
- Error messages from console and log files
- Configuration (without sensitive credentials)
- Steps to reproduce the issue
- Expected vs. actual behavior

### Version Information

- **Python Required**: 3.7 or higher
- **Dependencies**: See `requirements.txt`
- **Asana SDK**: Uses official `asana` Python package
- **Scoro API**: Uses `requests` library for HTTP calls

---

## Contributing

### Code Style

- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Comment complex logic

### Adding Features

1. Create feature in appropriate module (`clients/`, `transformers/`, `importers/`)
2. Add configuration options to `config.py` if needed
3. Update documentation (README.md, SETUP.md)
4. Test thoroughly with test mode before production

### Reporting Bugs

Please include:
- Python version
- Error messages and stack traces
- Configuration (sanitized of credentials)
- Steps to reproduce

---

## License

This project is provided as-is for internal use. Please ensure compliance with Asana and Scoro API terms of service.

---

## Acknowledgments

- **Asana**: For providing a comprehensive API for project management data
- **Scoro**: For work management platform integration
- **Python Community**: For excellent libraries and tools

---

## Quick Links

📚 **Documentation**
- [SETUP.md](SETUP.md) - Complete setup guide
- [workflow.md](workflow.md) - Workflow details
- [docs/](docs/) - Technical documentation

🔧 **Configuration Files**
- `config.py` - Main configuration
- `.env` - API credentials (create from instructions)
- `requirements.txt` - Python dependencies

📂 **Key Modules**
- `main.py` - Entry point
- `clients/` - API clients
- `transformers/` - Data transformation
- `importers/` - Scoro import logic

🔍 **Troubleshooting**
- [SETUP.md - Troubleshooting](SETUP.md#troubleshooting)
- [FAQ](#frequently-asked-questions-faq)
- `logs/` - Migration logs

---

**Ready to migrate? Start with [SETUP.md](SETUP.md) for complete setup instructions!** 🚀
