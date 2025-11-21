Based on the provided comprehensive documentation of the Scoro API, here is an in-depth reference specifically related to **Projects** API requests:

---

### Scoro API Requests Reference for Projects

#### Base URL format:
```
https://#companyname#.scoro.com/api/v2/projects
```
Where `#companyname#` is your Scoro account's subdomain.

---

### Common Authentication and Headers:
- Use either **apiKey** or **user_token** for authorization in the request body.
- Include `company_account_id` to specify the business entity.
- Optional `lang` parameter sets the response language (defaults to site or user default).
- Example HTTP Header for public integrations:
  ```
  scoro-app-id: AppId
  ```
- All requests are HTTPS POST with JSON payload.

---

### Available API Actions for Projects

#### 1. **Get List of Projects**
- **Request:**
```json
{
  "lang": "eng",
  "company_account_id": "tutorial",
  "apiKey": "API_hash",
  "request": {}
}
```
- **Description:** Retrieve all projects for the specified company account.
- **Response:** Returns a list of projects with metadata and pagination support.

---

#### 2. **Get Projects with Bookmark or Basic Data**
- Request can include bookmarks for pagination or filters.
- Example with user_token and bookmark:
```json
{
  "lang": "eng",
  "company_account_id": "tutorial",
  "user_token": "USER_TOKEN",
  "request": {},
  "bookmark": {
    "bookmark_id": "111"
  }
}
```
- Can also specify `"basic_data": "1"` to limit response data to essentials.

---

#### 3. **Create or Modify a Project**
- **Request:**
```json
{
  "lang": "eng",
  "company_account_id": "tutorial",
  "apiKey": "API_hash",
  "request": {
    "project_name": "Project Name",
    "company_id": 34,
    "is_private": 0,
    "status": "inprogress",
    "manager_id": 10,
    "deadline": "2019-12-01",
    "duration": "00:10:00",
    "phases": [
      {
        "id": 25,
        "type": "phase",
        "title": "Phase 1",
        "start_date": "2019-11-01",
        "end_date": "2019-11-10"
      }
    ],
    "project_accounts": [
      { "id": "company_account_1" },
      { "id": "company_account_2" }
    ]
  }
}
```
- **Description:** Creates or updates a project with detailed info including phases, accounts, status, manager, and deadlines.

---

#### 4. **Pagination and Filtering**
- Use parameters `"page"` and `"per_page"` to paginate results.
- Filters can be applied inside the request body to narrow project search (e.g., filtering by status, manager, dates).
- Example filtering by fields `"bookmark_users"` and `"bookmark_projects"`:
```json
{
  "lang": "eng",
  "company_account_id": "tutorial",
  "page": "1",
  "per_page": "50",
  "request": {
    "fields": [
      "bookmark_users",
      "bookmark_projects"
    ]
  }
}
```

---

#### 5. **Get Project Phases**
- **Request:**
```json
{
  "apiKey": "API_hash",
  "lang": "eng",
  "company_account_id": "tutorial",
  "request": {}
}
```
- **Endpoint:** `/projects/phases`
- **Description:** Fetch all phases for projects, including phase id, title, start and end dates.
- **Response Example:**
```json
{
  "status": "OK",
  "statusCode": 200,
  "data": [
    {
      "id": 1,
      "project_id": 3,
      "type": "phase",
      "title": "Analysis",
      "start_date": "2020-03-04",
      "end_date": "2020-03-18"
    },
    {
      "id": 2,
      "project_id": 3,
      "type": "phase",
      "title": "Development",
      "start_date": "2020-03-19",
      "end_date": "2020-07-22"
    }
  ]
}
```

---

#### 6. **Additional Project-related Data**
- Project data can be retrieved alongside related modules like tasks, calendar events, invoices, prepayments, bills, quotes, orders, files, and budgets.
- Example response for combined modules includes empty or populated lists under `"projects"` key.

---

### Notes on Usage:
- All requests must be sent as HTTP POST with JSON payload.
- API supports detailed filtering and pagination for efficient data retrieval.
- For public integrations, the `scoro-app-id` HTTP header is mandatory.
- Proper error handling is essential, especially for authorization failures (`401 Unauthorized`) or rate limiting (`429 Too Many Requests`).
- Deleted projects or phases can be included in responses by setting `"include_deleted": "1"`.

---
### Projects
Name : Type : Description
project_id : Integer : Project ID
no : Integer : Project number.
project_name : String : Project name.
description : String : Project description.
company_id : Integer : Related company ID.
company_name : String : Related company name. Only available for user based API
is_personal : Boolean : If project is personal or business related.
is_private : Boolean : If project is public or only for project members
color : String : Project color identifier. Format is in hex "#ffffff"
status : String : Project status. Possible values: pending, inprogress, cancelled, completed, future, additional1, additional2, additional3, additional4
status_name : String : Status name. Available in view request.
manager_id : Integer : Project manager ID.
manager_email : String : Project manager email.
date : Date (YYYY-mm-dd) : Project start date.
deadline : Date (YYYY-mm-dd) : Project deadline.
duration : Time (HH:ii:ss) : Project estimated duration.
phases : array : Project phases. Phases will be only filled for view requests.
account_id : String : Related account that created the project.
budget_type : String : Project budget type. Possible values when creating a new project: quote, simple. Cannot be modified.
project_type : String : Project type. Possible values: regular, retainer, internal. Supports filtering. Cannot be modified.
retainer_id : int : Retainer Id. Given if project is of type "retainer". Cannot be modified.
modified_date : Datetime (YYYY-mm-dd HH:ii:ss) : The date when project was last modified.
deleted_date : Datetime (DATE_ISO8601 - Y-m-d\TH:i:sP) : The date when project was deleted.
tags : Array : Array of project tags. Not used on list requests.
permissions : Array : Object user permissions. Used only for user based API
project_users : Array : Project related users. It is used only for modify and view requests.
project_customer_portal_users : Array : Project related customer portal users. It is used only for view requests.
project_accounts : Array : Project related accounts. Project is shared between those accounts.
stripDescription : Boolean : Deprecated Can use this argument on view requests. Strips HTML from project description field. Default value for this is true.
is_role_based : Boolean : If project is role based or service based. Available if roles are turned on.
local_price_list_id : Integer : Local price list ID. Available for role based projects.
custom_fields : Object : Custom fields. Only filled on view requests.
is_deleted : Boolean : Is deleted. Use 'include_deleted = 1' in request object to get deleted objects to response as well.

### Summary

To interact with the **Projects** module in Scoro API, use the endpoint:

```
https://#companyname#.scoro.com/api/v2/projects
```

Send POST requests with JSON bodies including your `apiKey` or `user_token`, `company_account_id`, and relevant request parameters. You can fetch project lists, create or update projects, retrieve project phases, and apply filters or pagination. The API supports detailed project management integration with phases and related business data, making it a robust tool for managing projects programmatically within Scoro.

---

If you need a sample cURL request to get projects:

```bash
curl -X POST "https://#companyname#.scoro.com/api/v2/projects" \
-H "Content-Type: application/json" \
-d '{
  "apiKey": "API_hash",
  "lang": "eng",
  "company_account_id": "tutorial",
  "request": {}
}'
```

This will return the list of projects for the specified company account.

---

This detailed reference should enable you to efficiently work with the Scoro Projects API endpoints for retrieving, creating, modifying, and managing projects and their phases.



The Scoro API offers comprehensive support for managing **tasks** via HTTP POST requests to the endpoint:

```
https://#companyname#.scoro.com/api/v2/tasks
```

where `#companyname#` is your Scoro subdomain. To interact with tasks, you need to provide authentication using either `apiKey` or `user_token` along with the `company_account_id`. The API supports JSON-formatted requests and responses.

### Key Task-Related API Operations

1. **Retrieve Tasks List**  
   You can fetch tasks with optional pagination and filtering.  
   Example request body:  
   ```json
   {
     "lang": "eng",
     "company_account_id": "tutorial",
     "user_token": "USER_TOKEN",
     "request": {},
     "bookmark": {"bookmark_id": "111"}
   }
   ```  
   This returns a paginated list of tasks with metadata about users, statuses, and other filters.

2. **Retrieve Basic Task Data**  
   Adding `"basic_data": "1"` in the request limits the response to essential task fields, optimizing data transfer.

3. **Create or Modify Tasks**  
   You can create or update tasks by sending detailed JSON in the `request` object, including fields like `event_name`, `status`, `manager_id`, `deadline`, and subtasks (using `"include_subtasks": 1`).  
   Example:  
   ```json
   {
     "lang": "eng",
     "company_account_id": "tutorial",
     "apiKey": "API_hash",
     "request": {
       "event_name": "New Task Name"
     }
   }
   ```

4. **Complete Tasks**  
   Tasks can be marked as completed by sending a `completed_datetime` field in the request.

5. **Filter Tasks**  
   The API supports filtering tasks by various criteria such as name, status, modified date, or custom fields, enabling targeted queries.

6. **Manage Task Comments**  
   Comments related to tasks can be retrieved or added using the `comments` module. For example, to fetch comments for a specific task (`object_id`):  
   ```json
   {
     "user_token": "USER_API_token",
     "lang": "eng",
     "company_account_id": "tutorial",
     "request": {
       "module": "tasks",
       "object_id": "123"
     }
   }
   ```  
   Adding comments requires specifying the task and comment text.

7. **Task Bookmarks and Filtering**  
   User-based bookmarks support tracking filtered task views. Bookmarks can be utilized in requests to handle large lists efficiently.

8. **Bulk Task Updates**  
   You can update multiple tasks by sending an array of task IDs and their updated fields.

### Important Considerations

- **Rate Limiting:** The API restricts request rates (e.g., 40 requests per 2 seconds for Pro plans). Exceeding limits causes `HTTP 429 Too Many Requests` errors. Handle these with retries and backoff logic.  
- **Authentication:** Always include `apiKey` or `user_token`. For public integrations, include the `scoro-app-id` header. Missing or invalid keys return 401 or 403 errors.  
- **Response Structure:** All responses include a `status` (`OK` or `ERROR`), `statusCode`, and optionally `messages` or `data`.  
- **Timezone and Date Formats:** Dates use ISO8601 format (`YYYY-MM-DDTHH:MM:SS+0000`). Timezone defaults to site setting unless specified.

### Sample cURL Request to Fetch Tasks

```bash
curl -X POST "https://#companyname#.scoro.com/api/v2/tasks" \
-H "Content-Type: application/json" \
-d '{
  "apiKey": "API_hash",
  "lang": "eng",
  "company_account_id": "tutorial",
  "request": {}
}'
```

---

### Summary

The Scoro API’s **tasks module** provides versatile endpoints for listing, creating, updating, and completing tasks, including support for subtasks, comments, bookmarks, and filtering. Tasks can be managed securely with authentication tokens and handle large datasets efficiently via pagination and filtering. Proper error handling for authorization and rate limits is essential to maintain smooth integration. This makes the tasks API suitable for detailed task management automation and integration with your existing workflows or applications.


### Tasks
Name : Type : Description
is_completed : Boolean : Is completed.
datetime_completed : Datetime (DATE_ISO8601 - Y-m-d\TH:i:sP) : Tasks completion time. Has value if task is completed.
assigned_to : Integer : Deprecated User ID of the user performing the assigned task.
related_users : Array : Array of user IDs that the task is assigned to. If empty array is submitted then task is set as unassigned.
related_users_emails : Array : Array of user emails that the task is assigned to.
duration_actual : Time (HH:ii:ss) : Tasks actual duration. This field is read only - it is calculated based on task time entries.
start_datetime : Datetime (DATE_ISO8601 - Y-m-d\TH:i:sP) : Tasks start date.
datetime_due : Datetime (DATE_ISO8601 - Y-m-d\TH:i:sP) : Tasks due date.
status : String : Possible values: task_status1, task_status2, task_status3, task_status4.
status_name : String : Status name. Available in view request.
time_entries : Array : Array of tasks' time entries. Populated only on view requests.
sortorder : Integer : Task sort order in list.
quote_line_id : Integer : Related quote line ID.
priority_id : Integer : Priority of the task. Possible values: 1 -> high, 2 -> normal, 3 -> low.
ete_id : Integer : Task time entry ID. Value will be filled only when task time entry is fetched separately in the user based list request, else its value will be 0.
parent_id : Integer|null : Task's parent task ID, filterable, cannot be modified. Field is usable only when "Subtasks" feature is enabled. Subtask inherits the following parent's values which cannot be modified for subtask: project_id, project_phase_id, person_id, company_id, quote_id, quote_line_id, and is_personal. Use 'include_subtasks = 1' in request object to get subtask objects to response as well. By default, subtasks are not included.
subtask_ids : array : Task's subtasks' IDs given as an array. Not filterable. Field is usable only when "Subtasks" feature is enabled. Use 'include_subtasks = 1' in request object to get subtask objects to response as well. By default, subtasks are not included, only subtask_ids will be given.
activity_id : Integer : Activity ID
activity_type : String : Activity type. Not filterable.
event_id : Integer : Event ID
event_name : String : Event name.
description : String : Event description.
is_personal : Boolean : If event is personal or work related.
project_id : Integer : Related project ID.
project_phase_id : Integer : Related project phase ID. If project phase ID is in input, then related project ID is automatically populated.
project_name : String : Related project name. Used only for user based API.
company_id : Integer : Related company ID.
company_name : String : Related company name
person_id : Integer : Related person ID.
person_name : String : Related person name. Used only for user based API.
invoice_id : Integer : Related invoice ID.
order_id : Integer : Related order ID.
quote_id : Integer : Related quote ID.
purchase_order_id : Integer : Related purchase order ID.
rent_order_id : Integer : Related rental order ID.
bill_id : Integer : Related bill ID.
duration_planned : Time (HH:ii:ss) : Events or tasks planned duration. Rounded to the nearest minute.
billable_hours : Time (HH:ii:ss) : Events billable duration. Rounded to nearest minute.
billable_time_type : String : Billable time type. Defines the rules for billable_hours field. Optional (if field not provided then 'custom' is used).
Possible values: billable, non_billable, custom.

billable: billable_hours will be set same as duration_planned.
non_billable: billable_hours will be set to 0.
custom: billable_hours will be used as defined.

owner_id : Integer : User ID of the user that is responsible for the event.
created_user : Integer : User ID of the user who created the event.
modified_user : Integer : User ID of the user who modified the event.
owner_email : String : User email of the user that is responsible for the event.
modified_date : Datetime (DATE_ISO8601 - Y-m-d\TH:i:sP) : The date when event was last modified.
created_date : Datetime (DATE_ISO8601 - Y-m-d\TH:i:sP) : Created date. Cannot be modified through API.
permissions : Array : Object user permissions. Used only for user based API
custom_fields : Object : Custom fields. Only filled on view requests.
is_deleted : Boolean : Is deleted. Use 'include_deleted = 1' in request object to get deleted objects to response as well.
deleted_date : Datetime (DATE_ISO8601 - Y-m-d\TH:i:sP) : The date when object was deleted.

### Users
Name : Type : Description
id : Integer : User ID.
username : String : Username.
firstname : String : First name.
lastname : String : Last name.
full_name : String : User full name.
initials : String : Initials.
email : String : Email address.
is_active : Boolean : Deprecated If user is active or deactivated.
status : String : User status. Possible values: active, inactive, pending, awaiting
birthday : Date (YYYY-mm-dd) : Users birthday.
category : String : User category. Possible values: user, admin or customer portal. Default values: user, admin.
position : String : User job/position.
user_picture : String : User profile image URL. Available only for "list" and "view" actions
role_id : Integer : User permission set ID.
user_groups_ids : Array : User groups ID-s.
country_id : String : User country ID.
gsm : String : User phone number.
timezone : String : User timezone
availability : Array : Current availability rule for the user. Contains array of weekdays and corresponding availability on that day in seconds. Possible values are monday, tuesday, wednesday, thursday, friday, saturday, sunday, holiday.
modified_date : Datetime (DATE_ISO8601 - Y-m-d\TH:i:sP) : The date when user was last modified.

https://#companyname#.scoro.com/api/v2/users/list
Description:
Getting users list with user token. Returns array of user objects.
Example request body:

{
    "lang": "eng",
    "company_account_id": "tutorial",
    "user_token": "USER_TOKEN",
    "request": {}
}

Example response body:

{
    "status": "OK",
    "statusCode": "200",
    "messages": null,
    "data": [
        {
            "id": 1,
            "username": "test",
            "firstname": "test",
            "lastname": "test",
            "initials": "T1",
            "email": "test[at]scoro.com",
            "is_active": 1,
            "status": "active",
            "birthday": "1970-01-01",
            "position": "Manager",
            "category": "admin",
            "availability": {
                "monday": 3600,
                "tuesday": 14400,
                "holiday": 0
            }
        },
        {
            "id": 2,
            "username": "test2",
            "firstname": "test2",
            "lastname": "test2",
            "initials": "T2",
            "email": "test2[at]scoro.com",
            "is_active": 1,
            "status": "active",
            "birthday": "1980-01-01",
            "position": "Manager 2",
            "category": "admin",
            "availability": {
                "monday": 3600,
                "tuesday": 14400,
                "holiday": 0
            }
        }
    ]
}



### Comments
This API endpoint supports requests authenticated by either user_token or apiKey.

Name : Type : Description
comment_id : String : Comment id
parent_id : Integer : Parent (comment) id
comment : String : Comment content
user_id : Integer : Comment owner id. The parameter is mandatory in case of comment creation with API Key.
modified_date : Datetime (DATE_ISO8601 - Y-m-d\TH:i:sP) : Modified datetime
permissions : Array : Object user permissions. Used only for user based API list request

Available actions are
list
Request URL:
https://#companyname#.scoro.com/api/v2/comments/list
Description:
Fields "module" and "object_id" are mandatory. Sample list request for module "tasks" with id "123" and filtering by modified date. Including "html" parameter with value 0 to request will strip html tags from comment content.
Example request body:

{
    "user_token": "USER_API_token",
    "lang": "eng",
    "company_account_id": "tutorial",
    "request": {
        "module": "tasks",
        "object_id": "123"
    },
    "filter": {
        "modified_date": {
            "from_date": "2013-02-01",
            "to_date": "2013-02-28"
        }
    }
}

Example response body:

{
    "status": "OK",
    "statusCode": "200",
    "messages": null,
    "data": [
        {
            "comment_id": 301,
            "parent_id": 0,
            "comment": "Example comment",
            "user_id": 1,
            "modified_date": "2020-12-29T09:48:22+02:00",
            "permissions": {
                "view": 1,
                "modify": 1,
                "delete": 1
            }
        },
        {
            "comment_id": 302,
            "parent_id": 0,
            "comment": "Example comment 2",
            "user_id": 1,
            "modified_date": "2020-12-29T09:48:18+02:00",
            "permissions": {
                "view": 1,
                "modify": 1,
                "delete": 1
            }
        }
    ]
}

modify
Request URL:
https://#companyname#.scoro.com/api/v2/comments/modify/(#id)
Description:
Modify existing comments or create a new one with user token. Adding "parent_id" parameter will create a response to the existing comment. Sample add/modify the request for module "tasks" with id "123".
Example request body:

{
    "user_token": "USER_API_token",
    "lang": "eng",
    "company_account_id": "tutorial",
    "request": {
        "module": "tasks",
        "object_id": "123",
        "comment": "Example"
    }
}

Example response body:

{
    "status": "OK",
    "statusCode": "200",
    "messages": null,
    "data": {
        "comment_id": 1,
        "parent_id": 0,
        "comment": "Example",
        "user_id": 1,
        "modified_date": "2020-12-29T11:16:39+02:00",
        "permissions": null,
        "custom_fields": null
    }
}

Description:
Modify existing comments or create a new one with API key. "user_id" parameter is mandatory. Adding "parent_id" parameter will create a response to the existing comment. Sample add/modify the request for module "tasks" with id "123".
Example request body:

{
    "apiKey": "API_hash",
    "lang": "eng",
    "company_account_id": "tutorial",
    "request": {
        "module": "tasks",
        "object_id": "123",
        "user_id": 1,
        "comment": "Example"
    }
}

Example response body:

{
    "status": "OK",
    "statusCode": "200",
    "messages": null,
    "data": {
        "comment_id": 1,
        "parent_id": 0,
        "comment": "Example",
        "user_id": 1,
        "modified_date": "2020-12-29T11:16:39+02:00",
        "permissions": null,
        "custom_fields": null
    }
}



### Project phases
This API endpoint supports requests authenticated by either user_token or apiKey.

Name	Type	Description
id	Integer	Project phase's ID.
project_id	Integer	Project's ID.
type	String	Possible values are "phase" and "milestone".
title	String	Project phase's title.
start_date	Date (YYYY-mm-dd)	Project phase's start date.
end_date	Date (YYYY-mm-dd)	Project phase's end date.
ordering	Integer	Project phase's order in list.
quote_line_id	Integer	Related quote line ID.
Available actions are
list
Request URL:
https://#companyname#.scoro.com/api/v2/projectPhases/list
Description:
Getting list of project phases.
Example request body:

{
    "apiKey": "API_hash",
    "lang": "eng",
    "company_account_id": "tutorial",
    "request": {}
}

Example response body:

{
    "status": "OK",
    "statusCode": 200,
    "messages": null,
    "data": [
        {
            "id": 1,
            "project_id": 3,
            "type": "phase",
            "title": "Analysis",
            "start_date": "2020-03-04",
            "end_date": "2020-03-18",
            "ordering": 0,
            "quote_line_id": 0
        },
        {
            "id": 2,
            "project_id": 3,
            "type": "phase",
            "title": "Development",
            "start_date": "2020-03-19",
            "end_date": "2020-07-22",
            "ordering": 1,
            "quote_line_id": 0
        }
    ]
}

### Time entries
This API endpoint supports requests authenticated by either user_token or apiKey.

Name	Type	Description
time_entry_id	Integer	Time entry ID.
description	String	Description.
title	String	Time Entry title. It will be constructed dynamically based on description and activity id values.
user_id	Integer	Related user ID.
activity_id	Integer	Related activity ID.
billable_time_type	String	Billable time type. Optional.
Possible values: billable, non_billable, custom.
invoice_line_id	Integer	Related invoice line ID.
event_id	Integer	Related event ID.
event_type	String	Event type, task or cal.
calendar_event_id	Integer	Calendar event id for consolidated time entry.
time_entry_type	String	Time entry type, task or cal.
start_datetime	Datetime (DATE_ISO8601 - Y-m-d\TH:i:sP)	Planned start date and time.
end_datetime	Datetime (DATE_ISO8601 - Y-m-d\TH:i:sP)	Planned end date and time.
duration	Time (HH:ii:ss)	Time entry duration. Rounded to the nearest minute.
billable_duration	Time (HH:ii:ss)	Billable duration for time entry. Only used if site has billable hours feature activated. Rounded to the nearest minute.
is_completed	Boolean	Is the time entry completed or not.
is_confirmed	Boolean	Is the time entry confirmed or not.
is_billable	Boolean	Deprecated, use billable_time_type instead.
completed_datetime	Datetime (DATE_ISO8601 - Y-m-d\TH:i:sP)	Date and time when the time entry was completed. Will be set to current time, if time entry is completed and no datetime provided.
is_locked	Boolean	Is the time entry locked or not. The parameter is available only if the "Use time locking" setting is enabled.
permissions	Array	Object user permissions. Used only for user based API
modified_date	Datetime (DATE_ISO8601 - Y-m-d\TH:i:sP)	Date and time when the time entry was modified. If a new time entry is added - it will be set to the current time (created_date).
time_entry_date	Date	Date of the time entry
is_submitted	Boolean	Is the time entry submitted or not.
submitted_date	Datetime (DATE_ISO8601 - Y-m-d\TH:i:sP)	Date and time when the time entry was submitted.
is_deleted	Boolean	Is deleted. Use 'include_deleted = 1' in request object to get deleted objects to response as well.
deleted_date	Datetime (DATE_ISO8601 - Y-m-d\TH:i:sP)	The date when object was deleted.
Available actions are
setDone Version: v2
Request URL:
https://#companyname#.scoro.com/api/v2/timeEntries/setDone/(#id)
Description:
Setting time entry as done.
Example request body:

{
    "lang": "eng",
    "company_account_id": "tutorial",
    "request": {}
}

Example response body:

{
    "status": "OK",
    "statusCode": "200",
    "messages": null
}

modify Version: v2
Request URL:
https://#companyname#.scoro.com/api/v2/timeEntries/modify/(#id)
Description:
Adding new and modifying current time entries. Event ID and user_id (when using apiKey) are mandatory for new time entries. Adding "return_data" parameter will control if object data will be returned with successful request. You can only modify invoice_line_id value on time entries related to calendar events. Use the calendar API to modify the event itself if you need to change anything else.
Example request body:

{
    "lang": "eng",
    "company_account_id": "tutorial",
    "request": {
        "event_id": "1"
    }
}

Example response body:

{
    "status": "OK",
    "statusCode": 200,
    "messages": null,
    "data": {
        "time_entry_id": 1,
        "description": "",
        "title": "",
        "user_id": 1,
        "activity_id": 0,
        "billable_time_type": "billable",
        "invoice_line_id": 0,
        "event_id": 1,
        "event_type": "task",
        "calendar_event_id": 0,
        "time_entry_type": "task",
        "start_datetime": "2016-03-25T15:47:20+02:00",
        "duration": "00:30:00",
        "billable_duration": "00:25:00",
        "is_completed": 1,
        "completed_datetime": "2016-03-25T15:47:20+02:00",
        "is_deleted": 0
    }
}

delete Version: v2
Request URL:
https://#companyname#.scoro.com/api/v2/timeEntries/delete/(#id)
Description:
Deleting time entry.
Example request body:

{
    "lang": "eng",
    "company_account_id": "tutorial",
    "request": {}
}

Example response body:

{
    "status": "OK",
    "statusCode": "200",
    "messages": null
}

list Version: v2
Request URL:
https://#companyname#.scoro.com/api/v2/timeEntries/list
Description:
Listing time entries.
Example request body:

{
    "lang": "eng",
    "company_account_id": "tutorial",
    "request": {}
}

Example response body:

{
    "status": "OK",
    "statusCode": 200,
    "messages": null,
    "data": [
        {
            "time_entry_id": 1,
            "description": "",
            "title": "",
            "user_id": 1,
            "activity_id": 0,
            "invoice_line_id": 0,
            "event_id": 1,
            "event_type": "task",
            "calendar_event_id": 0,
            "time_entry_type": "task",
            "start_datetime": "2017-03-13T18:00:00+02:00",
            "duration": "01:00:00",
            "billable_duration": "00:00:00",
            "is_completed": 0,
            "is_confirmed": 0,
            "is_billable": 0,
            "completed_datetime": null,
            "is_deleted": 0,
            "deleted_date": null
        }
    ]
}

view Version: v2
Request URL:
https://#companyname#.scoro.com/api/v2/timeEntries/view/(#id)
Description:
View time entry.
Example request body:

{
    "lang": "eng",
    "company_account_id": "tutorial",
    "request": {}
}

Example response body:

{
    "status": "OK",
    "statusCode": 200,
    "messages": null,
    "data": {
        "time_entry_id": 1,
        "description": "",
        "title": "",
        "user_id": 3,
        "activity_id": 0,
        "invoice_line_id": 0,
        "event_id": 48,
        "event_type": "task",
        "calendar_event_id": 0,
        "time_entry_type": "task",
        "start_datetime": "2010-03-16T11:00:00+02:00",
        "duration": "01:30:00",
        "billable_duration": "00:00:00",
        "is_completed": 0,
        "is_confirmed": 0,
        "is_billable": 0,
        "completed_datetime": null,
        "is_deleted": 0,
        "deleted_date": null
    }
}

