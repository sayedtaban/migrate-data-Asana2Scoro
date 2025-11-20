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