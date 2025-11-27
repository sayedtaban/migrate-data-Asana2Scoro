# Project and Task Assignment Details

## Overview

This document explains how user assignments work for **Projects** and **Tasks** in the Scoro migration, including the fields used, how they're resolved, and potential issues.

---

## Project Assignment

### Fields Used

1. **`project_users`** (Array of Integer user IDs)
   - **Purpose**: Lists all team members assigned to the project
   - **Source**: Asana project members
   - **Scoro API Field**: `project_users`
   - **Location in Code**: `importers/scoro_importer.py` lines 345-383

2. **`manager_id`** (Integer user ID)
   - **Purpose**: The project manager/owner
   - **Source**: Asana project manager (from custom fields or project owner)
   - **Scoro API Field**: `manager_id`
   - **Location in Code**: `importers/scoro_importer.py` lines 318-337

### How Project Assignment Works

```python
# 1. Resolve Project Manager
manager_name = project_data.get('manager_name')
if manager_name:
    manager = scoro_client.find_user_by_name(manager_name)
    if manager:
        project_data['manager_id'] = manager.get('id')

# 2. Resolve Project Members (Team)
project_members = project_data.get('members', [])
for member_name in project_members:
    member = scoro_client.find_user_by_name(member_name)
    if member:
        project_user_ids.append(member.get('id'))

if project_user_ids:
    project_data['project_users'] = project_user_ids
```

### Key Points

- **No active status check**: Project assignments don't validate if users are active
- **Fallback behavior**: If a user isn't found, it's skipped with a warning
- **Multiple users**: `project_users` is an array, can contain multiple user IDs

---

## Task Assignment

### Fields Used

1. **`owner_id`** (Integer user ID)
   - **Purpose**: The task owner/creator
   - **Source**: Asana task creator (`created_by`)
   - **Scoro API Field**: `owner_id`
   - **Location in Code**: `importers/scoro_importer.py` lines 701-722
   - **Fallback**: Defaults to user_id `1` (Tom Sanpakit) if not found

2. **`related_users`** (Array of Integer user IDs)
   - **Purpose**: Task assignees (people the task is assigned to)
   - **Source**: Asana task assignees (`assignee` or `assignees`)
   - **Scoro API Field**: `related_users`
   - **Location in Code**: `importers/scoro_importer.py` lines 724-758
   - **Fallback**: Defaults to `[1]` (Tom Sanpakit) if no assignees found
   - **Important**: According to Scoro API docs: "If empty array is submitted then task is set as unassigned"

### How Task Assignment Works

```python
# 1. Resolve Task Owner
owner_name = task_data.get('owner_name')
if owner_name:
    owner = scoro_client.find_user_by_name(owner_name)
    if owner:
        task_data['owner_id'] = owner.get('id')

# Fallback for owner_id
if not task_data.get('owner_id'):
    task_data['owner_id'] = 1  # Tom Sanpakit

# 2. Resolve Task Assignees
assigned_to_name = task_data.get('assigned_to_name')
if assigned_to_name:
    assigned_names = assigned_to_name if isinstance(assigned_to_name, list) else [assigned_to_name]
    related_user_ids = []
    
    for name in assigned_names:
        user = scoro_client.find_user_by_name(name)
        if user:
            related_user_ids.append(user.get('id'))
    
    if related_user_ids:
        task_data['related_users'] = related_user_ids

# Fallback for related_users
if not task_data.get('related_users'):
    task_data['related_users'] = [1]  # Tom Sanpakit
```

### Key Points

- **No active status check**: Task assignments don't validate if users are active
- **Required fields**: Both `owner_id` and `related_users` are always set (with fallbacks)
- **Multiple assignees**: `related_users` is an array, can contain multiple user IDs
- **Not for followers**: `related_users` is only for assignees, not followers/collaborators

---

## The Error: "User with id 25 [related_users] not found"

### Error Details

**Error Message**: `Scoro API error: ['User with id 25 [related_users] not found']`

**Context**:
- Task: `[Exscape] COPY - (5) StoryBranded Job Descriptions`
- User ID 25: Lindsey Cartwright
- Status in CSV: `is_active=0`, `status=inactive`
- The code successfully found and cached user ID 25 from `users/list` API
- The `tasks/modify` API rejected the task creation

### Root Cause Analysis

**The Real Issue**: API inconsistency between `users/list` and `tasks/modify`

1. **`users/list` API Behavior**
   - Returns 35 users (including inactive users like ID 25 and 27)
   - May include recently deleted users or users in "soft deleted" state
   - The user lookup cache contains these users

2. **`tasks/modify` API Behavior**
   - Validates user IDs more strictly when creating tasks
   - Rejects user IDs that don't exist in the active database
   - Returns error: "User with id X [related_users] not found"

3. **The Mismatch**
   - `users/list` finds user ID 25 → cached successfully
   - `tasks/modify` tries to use user ID 25 → rejects it as "not found"
   - This suggests the user was **deleted from Scoro** but still appears in `users/list` response
   - OR `users/list` includes deleted/inactive users that `tasks/modify` doesn't accept

### Evidence from Logs

```
12:02:05 - Retrieved 35 users from Scoro
12:09:44 - Found user by full_name: Lindsey Cartwright (ID: 25)
12:09:44 - Set related_users (assignees only): [25]
12:09:44 - ERROR: User with id 25 [related_users] not found
```

**Multiple affected users**:
- User ID 25 (Lindsey Cartwright) - 1 task failed
- User ID 27 (Matteo Banfo) - 6 tasks failed (owner_id and related_users)

### Possible Causes

1. **User Actually Deleted from Scoro**
   - User ID 25 was deleted from Scoro after the CSV export
   - `users/list` may return stale data or include deleted users
   - `tasks/modify` validates against current database and rejects deleted users

2. **API Filtering Difference**
   - `users/list` might not filter by deletion status
   - `tasks/modify` might only accept users that exist in active database
   - Inactive users might be acceptable, but deleted users are not

3. **Soft Delete vs Hard Delete**
   - Users might be "soft deleted" (marked as deleted but still in database)
   - `users/list` returns soft-deleted users
   - `tasks/modify` only accepts non-deleted users

### Current Code Behavior

The code does **NOT** check:
- User `is_active` status before assignment
- Whether the user still exists in Scoro
- User permissions or accessibility

The code only:
- Looks up users by name
- Caches the result
- Uses the cached user ID

### User Lookup Cache

The `find_user_by_name()` method caches users:
- **Cache location**: `scoro_client._user_lookup_cache`
- **Cache key**: Lowercase user name
- **Cache value**: User dictionary (or None if not found)
- **Problem**: Cache doesn't expire or validate against current Scoro state

---

## Comparison: Comments vs Tasks

### Comments (Has Active Check)

```python
# Lines 1193-1217 in scoro_importer.py
user_obj = scoro_client.find_user_by_name(author_name)
if user_obj:
    is_active_raw = user_obj.get('is_active')
    # Check if user is active
    if isinstance(is_active_raw, str):
        is_active = is_active_raw.lower() in ('1', 'true', 'yes')
    elif isinstance(is_active_raw, int):
        is_active = bool(is_active_raw)
    
    # Skip comment if user is inactive
    if not is_active:
        logger.warning(f"⚠ Skipping comment: User is inactive")
```

### Tasks (No Active Check)

```python
# Lines 737-751 in scoro_importer.py
user = scoro_client.find_user_by_name(name)
if user:
    user_id = user.get('id')
    if user_id:
        related_user_ids.append(user_id)  # No is_active check!
```

---

## Recommendations

1. **Validate User IDs Before Task Creation**
   - Since `users/list` may return users that `tasks/modify` rejects, we need to validate
   - Try to verify user exists by checking if user ID is in the current users list
   - OR catch the error and retry with fallback

2. **Handle Invalid Users Gracefully**
   - When `tasks/modify` rejects a user ID, catch the error
   - Remove the invalid user from `related_users` or `owner_id`
   - Use fallback (Tom Sanpakit, user_id: 1) if no valid users remain
   - Log which users were rejected and why
   - Continue migration instead of failing

3. **Better Error Handling for Task Creation**
   - Wrap task creation in try-except
   - If error contains "User with id X not found":
     - Remove that user ID from the assignment
     - Retry task creation
     - If still fails, use fallback user

4. **User Validation Strategy**
   - Option A: Validate user IDs exist in current `users/list` before assignment
   - Option B: Let API reject invalid users and handle gracefully
   - Option C: Check user `is_active` and `status` fields before assignment
   - **Recommended**: Option B (handle API errors) since it's most reliable

---

## Scoro API Documentation Reference

From `docs/Scoro API Reference.md`:

- **`related_users`**: "Array of user IDs that the task is assigned to. If empty array is submitted then task is set as unassigned."
- **`related_users_emails`**: "Array of user emails that the task is assigned to."

**Note**: The API documentation doesn't explicitly state that inactive users cannot be assigned, but the error suggests there may be restrictions.

---

## Summary

| Field | Type | Purpose | Active Check? | Fallback |
|-------|------|---------|---------------|----------|
| `project_users` | Array[Int] | Project team members | ❌ No | Skip if not found |
| `manager_id` | Int | Project manager | ❌ No | Skip if not found |
| `owner_id` | Int | Task owner | ❌ No | User ID 1 (Tom) |
| `related_users` | Array[Int] | Task assignees | ❌ No | `[1]` (Tom) |

**The error occurs because user ID 25 was found in the cache but doesn't exist (or isn't accessible) in the current Scoro instance when the task is created.**

