# Bug Fix: Tasks Created in Wrong Project (Project 33 Instead of Project 104)

## Problem Description

Tasks for **Van Zeeland Nursery & Landscape (Project ID 104)** were being created in **Starbucks Landscaping (Project ID 33)** instead.

### What the Log Showed:
- Line 368: `✓ Project created successfully: Van Zeeland Nursery & Landscape`
- Line 369: `Project ID: 104`
- Line 385: `Linked to project ID: 104`
- Line 392: `Found phase by title: Website Design (ID: 240)`

But in Scoro, the tasks appeared in Project 33, not Project 104.

---

## Root Cause Analysis

### Investigation Results:

1. **Phase 240 ("Website Design") belongs to Project 33, NOT Project 104**
   ```
   Phase 240: Title='Website Design', Project ID=33
   ```

2. **Project 104 has NO phases**
   - The migration log claimed to create 7 milestones (lines 370-380)
   - But these phases don't actually exist in Scoro for project 104
   - The phase creation likely succeeded but phases aren't visible in the phases/list API (pagination/caching issue)

3. **Scoro API Filter Not Working**
   - When calling `projectPhases/list` with filter `{"project_id": 104}`, the API returns **ALL 100 phases from ALL projects**, not filtered by project 104
   - This caused the code to find phase 240 ("Website Design") globally instead of within project 104

4. **Scoro API Behavior: Phase Overrides Project**
   - From Scoro API documentation:
     > "If project phase ID is in input, then related project ID is automatically populated."
   - This means when you set `project_phase_id = 240`, Scoro **automatically changes** `project_id` to match the phase's project (33), **overriding** the explicitly set `project_id = 104`

### The Bug Flow:
```
1. Code sets: task_data['project_id'] = 104 (Van Zeeland)
2. Code searches for phase "Website Design" with project_id=104
3. Scoro API returns ALL phases (ignores filter)
4. Code finds phase 240 ("Website Design") which belongs to project 33
5. Code sets: task_data['project_phase_id'] = 240
6. Scoro API automatically changes project_id to 33 (phase's project)
7. Task ends up in Project 33 (Starbucks) instead of Project 104 (Van Zeeland)
```

---

## The Fix

### File: `clients/scoro_client.py`
### Function: `find_phase_by_name()`

**Added client-side filtering** to ensure phases are only matched within the correct project:

```python
# IMPORTANT: Filter phases by project_id here because Scoro API may not honor the filter
# and return phases from all projects. This prevents matching phases from wrong projects.
if project_id is not None:
    phases = [p for p in phases if p.get('project_id') == project_id]
    if not phases:
        logger.debug(f"No phases found for project ID {project_id} after filtering")
        return None
    logger.debug(f"Filtered to {len(phases)} phases for project ID {project_id}")
```

### What This Fix Does:

1. **Before the fix**: 
   - Searched globally across all 100 phases
   - Found phase 240 from project 33
   - Tasks ended up in wrong project

2. **After the fix**:
   - Filters phases to only those belonging to the specified project_id
   - Won't find "Website Design" in project 104 (because it doesn't exist there)
   - No `project_phase_id` is set
   - Tasks stay in project 104 (correct project)

### Test Results:

```
=== TEST 1: Search for "Website Design" in project 104 ===
✅ CORRECT: Phase 'Website Design' not found in project 104 (as expected)

=== TEST 2: Search for "Website Design" in project 33 ===
✅ CORRECT: Found phase: ID=240, Title=Website Design, Project=33
```

---

## Remaining Issues

### 1. **Project 104 Has No Phases**
   - The milestones supposedly created aren't visible in Scoro
   - This may be due to:
     - Scoro API pagination limits (only returns first 100 phases)
     - API caching issues
     - Phases created but not properly indexed
   
   **Impact**: Tasks in project 104 won't have phase assignments

### 2. **Tasks Have Wrong Phase Names**
   - Tasks reference `project_phase_name: "Website Design"` 
   - But project 104's milestones should be:
     - "[Van Zeeland] Go-Live Complete"
     - "[Van Zeeland] Core Pages"
     - "[Van Zeeland] Core Page Review"
     - "[Van Zeeland] Core Pages Complete"
     - "[Van Zeeland] Rest of Site Build"
     - "[Van Zeeland] Full Site Review"
     - "[Van Zeeland] Full Site Complete"
   
   **Impact**: This is a data transformation issue - the wrong phase name is being mapped during transformation

---

## Recommendations

### Short Term (Completed ✅):
- ✅ Fix phase lookup to filter by project_id (prevents wrong project assignment)
- ✅ Add logging to show which project a phase belongs to

### Medium Term (TODO):
1. **Fix Data Transformation**:
   - Investigate why tasks have `project_phase_name: "Website Design"` instead of the actual Van Zeeland milestone names
   - Check the `transformers/` code to see how phase names are mapped

2. **Fix Milestone Creation**:
   - Verify if milestones are actually created in Scoro
   - If not, fix the milestone creation logic
   - If yes, fix the phase listing to handle pagination

3. **Add Validation**:
   - After creating milestones, verify they exist before creating tasks
   - Warn if a task references a phase that doesn't exist in its project

### Long Term:
- Consider implementing Scoro API pagination handling for phases/list endpoint
- Add comprehensive logging for all phase resolutions
- Create a pre-flight check that validates all phase names exist in target project before migration

---

## Testing Commands

To verify the fix works:

```bash
cd /home/ubuntu/Documents/dev/migrate-data-Asana2Scoro
source .venv/bin/activate

# Test 1: Verify phase 240 belongs to project 33
python << 'EOF'
from clients.scoro_client import ScoroClient
client = ScoroClient()
all_phases = client.list_project_phases()
phase_240 = [p for p in all_phases if p.get('id') == 240][0]
print(f"Phase 240: Project ID={phase_240.get('project_id')}, Title={phase_240.get('title')}")
EOF

# Test 2: Verify "Website Design" not found in project 104
python << 'EOF'
from clients.scoro_client import ScoroClient
client = ScoroClient()
phase = client.find_phase_by_name("Website Design", project_id=104)
print(f"Phase found in project 104: {phase is not None}")  # Should be False
EOF
```

---

## Date
Fixed: November 21, 2025

## Author
AI Assistant (Claude)

