# Project Manager Workflow and Logic in Scoro Migration

This document explains the complete workflow and logic for setting the project manager when migrating projects from Asana to Scoro.

## Overview

The migration process extracts the **PM Name custom field value** from Asana tasks and maps it to the **Scoro Project Manager** (`manager_id`). The workflow consists of three main phases:

1. **Extraction Phase** (in `transformers/data_transformer.py`)
2. **Resolution Phase** (in `importers/scoro_importer.py`)
3. **API Submission Phase** (in `clients/scoro_client.py`)

---

## Phase 1: Extraction from Asana Data

**Location:** `transformers/data_transformer.py` (lines 89-120)

### Logic Flow

The system extracts the project manager name from the **"PM Name" custom field** in Asana tasks:

#### Search Strategy
```python
# Search through all tasks to find a custom field with name "PM Name"
for task in tasks:
    custom_fields = task.get('custom_fields', [])
    for field in custom_fields:
        if field.get('name', '').lower() == 'pm name':
            display_value = field.get('display_value')
            if display_value and str(display_value).strip():
                pm_name = str(display_value).strip()
                break
```

#### Key Points:
1. **Field Name:** Must be exactly "PM Name" (case-insensitive)
2. **Value Source:** Uses `display_value` from the custom field
3. **Value Type:** The `display_value` contains the **first name** of the user
4. **Search Order:** Searches through all tasks and uses the **first non-null display_value** found
5. **Field Type:** Typically an enum field where `display_value` shows the selected option name

#### Example Custom Field Structure:
```json
{
  "name": "PM Name",
  "display_value": "Austin",
  "enum_value": {
    "name": "Austin",
    "gid": "1208975589873882"
  },
  "type": "enum"
}
```

### Output

After extraction, the project manager first name is stored in the transformed project data:
```python
if pm_name:
    transformed_project['manager_name'] = pm_name
```

**Note:** At this stage, only the `manager_name` (string, first name) is stored. The actual Scoro user ID will be resolved later using the first name lookup.

---

## Phase 2: Resolution to Scoro User ID

**Location:** `importers/scoro_importer.py` (lines 319-342)

### Logic Flow

Before creating the project in Scoro, the system resolves the manager name to a Scoro user ID:

```python
manager_name = project_data.get('manager_name')
if manager_name:
    logger.info(f"  Resolving project manager: {manager_name}...")
    try:
        manager = scoro_client.find_user_by_name(manager_name)
        if manager:
            manager_id = manager.get('id')
            if manager_id:
                project_data['manager_id'] = manager_id
                logger.info(f"  ✓ Set project manager: {manager_full_name} (ID: {manager_id})")
```

### User Lookup Strategy

**Location:** `clients/scoro_client.py` (lines 1190-1250)

The `find_user_by_name()` method uses multiple matching strategies. Since the PM Name field contains only the **first name**, the lookup prioritizes firstname matching:

1. **Full Name Match**
   ```python
   full_name = user.get('full_name', '')
   if full_name and full_name.lower().strip() == user_name_lower:
       return user
   ```

2. **Firstname + Lastname Match**
   ```python
   combined_name = f"{firstname} {lastname}".lower().strip()
   if combined_name == user_name_lower:
       return user
   ```

3. **Firstname-Only Match** (primary for PM Name)
   - If the name appears to be first name only (single word, no spaces)
   - Matches against the `firstname` field specifically
   - This is the most common match for PM Name values

4. **Email Match**
   ```python
   email = user.get('email', '')
   if email and email.lower().strip() == user_name_lower:
       return user
   ```

### Caching

The system uses a lookup cache (`_user_lookup_cache`) to avoid repeated API calls for the same user name.

### Error Handling

- If manager is not found: Logs a warning and continues without `manager_id`
- If manager is found but has no ID: Logs a warning and continues without `manager_id`
- If an exception occurs: Logs a warning and continues without `manager_id`

### Cleanup

After resolution, the temporary `manager_name` field is removed:
```python
# Remove manager_name from project_data as it's not a valid Scoro API field
project_data.pop('manager_name', None)
```

---

## Phase 3: API Submission to Scoro

**Location:** `clients/scoro_client.py` (lines 228-276)

### Request Body Construction

The project data (including `manager_id`) is wrapped in a Scoro API v2 request:

```python
def _build_request_body(self, request_data: Dict) -> Dict:
    return {
        "lang": "eng",
        "company_account_id": self.company_name,
        "apiKey": self.api_key,
        "request": request_data  # Contains manager_id here
    }
```

### API Endpoint

- **Create:** `POST /api/v2/projects/modify`
- **Update:** `POST /api/v2/projects/modify/{project_id}`

### Request Format

The `request` object contains the project data with `manager_id`:

```json
{
  "lang": "eng",
  "company_account_id": "companyname",
  "apiKey": "API_hash",
  "request": {
    "project_name": "Project Name",
    "manager_id": 123,  // Scoro user ID
    // ... other project fields
  }
}
```

### Scoro API Field

According to Scoro API documentation:
- **Field Name:** `manager_id`
- **Type:** Integer
- **Description:** Project manager ID
- **Alternative:** `manager_email` (String) can also be used

---

## Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    ASANA TASK DATA                           │
│  task.custom_fields = [                                     │
│    {                                                        │
│      "name": "PM Name",                                     │
│      "display_value": "Austin",  ← First name                │
│      "enum_value": {...}                                    │
│    }                                                        │
│  ]                                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           PHASE 1: EXTRACTION                                │
│  transformers/data_transformer.py                           │
│                                                              │
│  1. Search all tasks for custom field "PM Name"            │
│  2. Extract display_value (first name)                     │
│  3. Use first non-null display_value found                 │
│                                                              │
│  Output: manager_name = "Austin"  ← First name only        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           TRANSFORMED PROJECT DATA                           │
│  {                                                           │
│    "project_name": "My Project",                            │
│    "manager_name": "Austin"  ← First name, not ID          │
│  }                                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           PHASE 2: RESOLUTION                                │
│  importers/scoro_importer.py                                │
│                                                              │
│  1. Get manager_name from project_data                      │
│  2. Call scoro_client.find_user_by_name("Austin")         │
│  3. Match by firstname (primary) or full name              │
│  4. Extract user ID from Scoro user object                 │
│  5. Set project_data['manager_id'] = 123                   │
│  6. Remove manager_name (not valid Scoro field)            │
│                                                              │
│  Output: manager_id = 123                                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           PHASE 3: API SUBMISSION                            │
│  clients/scoro_client.py                                    │
│                                                              │
│  1. Build request body with manager_id                     │
│  2. POST to /api/v2/projects/modify                        │
│  3. Scoro creates/updates project with manager              │
│                                                              │
│  Result: Project created with manager_id = 123              │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Points

### 1. **Source of Truth**
- **Asana "PM Name" Custom Field** → **Scoro Project Manager**
- The `display_value` from the "PM Name" custom field in tasks is the authoritative source
- The `display_value` contains the **first name** of the user

### 2. **Name-to-ID Resolution**
- The system works with first names during transformation
- Resolution to Scoro user ID happens just before API submission
- Firstname matching is prioritized since PM Name contains only first names
- This allows for better error handling and logging

### 3. **Fallback Behavior**
- If "PM Name" field is not found or has no display_value, the project is still created
- Warnings are logged but the migration continues
- This prevents migration failures due to missing custom fields

### 4. **Field Naming**
- **Asana:** `custom_fields[].display_value` where `name == "PM Name"` (string, first name)
- **Transformation:** `manager_name` (string, first name, temporary)
- **Scoro API:** `manager_id` (integer, final)

### 5. **User Matching**
- Multiple matching strategies ensure high success rate
- **Firstname matching is primary** for PM Name values
- Case-insensitive matching
- Supports full name, first+last name, email, and firstname-only

---

## Error Scenarios and Handling

| Scenario | Behavior | Log Level |
|----------|----------|-----------|
| No "PM Name" custom field found | Project created without manager | WARNING |
| "PM Name" field has null/empty display_value | Project created without manager | WARNING |
| Manager first name not found in Scoro | Project created without manager | WARNING |
| Manager found but no ID | Project created without manager | WARNING |
| Exception during resolution | Project created without manager | WARNING |

---

## Code References

- **Extraction:** `transformers/data_transformer.py:89-120`
- **Custom Field Extraction:** `transformers/field_extractors.py:32-72` (supports display_value)
- **Resolution:** `importers/scoro_importer.py:319-342`
- **User Lookup:** `clients/scoro_client.py:1190-1250`
- **API Submission:** `clients/scoro_client.py:228-276`
- **API Documentation:** `docs/Scoro API Reference.md:185`

---

## Testing

To verify project manager assignment:

1. Check migration logs for:
   - `"Found PM Name from custom field: {first_name}"`
   - `"Resolving project manager: {first_name}..."`
   - `"✓ Set project manager: {full_name} (ID: {id})"`

2. Verify in Scoro:
   - Navigate to the migrated project
   - Check the "Project Manager" field
   - Should match the user whose first name appears in the "PM Name" custom field

3. Common issues:
   - **Manager not set:** 
     - Check if "PM Name" custom field exists in tasks
     - Verify display_value is not null/empty
     - Check if user exists in Scoro with matching first name
   - **Wrong manager:** 
     - Verify the display_value in "PM Name" field is correct
     - Check user name mapping in `PROFILE_USERNAME_MAPPING` config
     - Ensure firstname matching is working correctly
   - **Manager ID mismatch:** Verify user lookup cache is working correctly

