# Client-First Association Implementation

## Overview

This document describes the implementation of client/company association for Scoro projects. In Scoro, projects must be linked to company/contact records (clients), which is different from Asana's portfolio-based organization.

## Changes Made

### 1. ScoroClient Enhancements (`clients/scoro_client.py`)

Added new methods to handle company/contact management:

- **`list_companies()`**: Lists all companies in Scoro
- **`find_company_by_name(company_name)`**: Finds an existing company by name
- **`create_company(company_data)`**: Creates a new company in Scoro
- **`get_or_create_company(company_name, additional_data)`**: Gets an existing company or creates a new one if it doesn't exist

These methods handle Scoro API v2's various request formats and response structures.

### 2. Data Transformer Updates (`transformers/data_transformer.py`)

Enhanced the transformation logic to extract and prepare company information:

- **Company Name Extraction**:
  - For **client projects**: Uses the project name as the company name
  - For **team member projects**: Attempts to extract company name from task custom fields (C-Name, Company Name)
  
- **Data Structure Updates**:
  - Added `company_name` field to transformed data
  - Added `is_client_project` flag for reference
  - Company name is stored both in project data and as a separate field for easy access

### 3. Importer Updates (`importers/scoro_importer.py`)

Enhanced the import process to ensure projects are linked to companies:

- **Company Resolution**:
  1. First, tries to use the `company_name` from transformed data
  2. Falls back to project name if no explicit company name is found
  3. Creates or finds the company in Scoro before creating the project

- **Project-Company Linking**:
  - Extracts company ID from the company record
  - Links the project to the company by setting `company_id` in project data
  - Handles various Scoro API field name variations (`company_id`, `client_id`)

## How It Works

### Migration Flow

1. **Export Phase**: Asana project data is exported (no changes)

2. **Transform Phase**:
   - Project type is determined (client vs team member)
   - Company name is extracted:
     - Client projects → project name becomes company name
     - Team member projects → company extracted from task custom fields
   - Company name is stored in transformed data

3. **Import Phase**:
   - Company is resolved (found or created) in Scoro
   - Project is created with `company_id` linking it to the company
   - Tasks and milestones are created and linked to the project

### Key Differences from Asana

| Aspect | Asana | Scoro |
|--------|-------|-------|
| Organization | Portfolios | Companies/Contacts |
| Project Association | Portfolio-based | Client/Company-based |
| Client Records | Not required | Required for projects |

## Error Handling

- If company creation fails, the error is logged but the process continues (project creation might still work)
- If no company name is available, a warning is logged
- Company lookup is case-insensitive and handles whitespace

## Usage

The implementation is automatic - no changes needed to the main migration script. When you run:

```python
python main.py
```

The migration will:
1. Extract company information from Asana data
2. Create or find the company in Scoro
3. Link the project to the company when creating it

## Testing Recommendations

1. **Test with client projects**: Verify that project name becomes company name
2. **Test with team member projects**: Verify company extraction from task custom fields
3. **Test with existing companies**: Verify that existing companies are found and reused
4. **Test with new companies**: Verify that new companies are created correctly
5. **Verify project-company links**: Check in Scoro UI that projects are properly linked to companies

## Notes

- The implementation assumes that for client projects, the project name represents the client/company name
- For team member projects, company information should be available in task custom fields
- If Scoro API requires additional fields for company creation, they can be added via the `additional_data` parameter in `get_or_create_company()`

