"""
Scoro API client for interacting with Scoro API
"""
import html
import os
from typing import Dict, List, Optional

import requests

from config import ENV_SCORO_API_KEY, ENV_SCORO_COMPANY_NAME
from utils import logger, retry_with_backoff, rate_limit


class ScoroClient:
    """Handle Scoro API interactions"""
    
    def __init__(self, api_key: Optional[str] = None, company_name: Optional[str] = None):
        """
        Initialize Scoro client
        
        Args:
            api_key: Scoro API key. If None, reads from SCORO_API_KEY env var
            company_name: Scoro company subdomain. If None, reads from SCORO_COMPANY_NAME env var
        """
        self.api_key = api_key or os.getenv(ENV_SCORO_API_KEY)
        self.company_name = company_name or os.getenv(ENV_SCORO_COMPANY_NAME)
        
        if not self.api_key:
            raise ValueError("Scoro API key not provided. Set SCORO_API_KEY env var.")
        if not self.company_name:
            raise ValueError("Scoro company name not provided. Set SCORO_COMPANY_NAME env var.")
        
        # Clean company name - remove protocol, domain, and path if present
        # Should be just the subdomain (e.g., "halsteadmedia8" not "https://halsteadmedia8.scoro.com")
        company_clean = str(self.company_name).strip()
        # Remove https:// or http:// if present
        if company_clean.startswith('https://'):
            company_clean = company_clean[8:]
        elif company_clean.startswith('http://'):
            company_clean = company_clean[7:] 
        # Remove .scoro.com and any path if present
        if '.scoro.com' in company_clean:
            company_clean = company_clean.split('.scoro.com')[0]
        # Remove any trailing slashes or paths
        company_clean = company_clean.split('/')[0]
        
        self.company_name = company_clean
        self.base_url = f"https://{self.company_name}.scoro.com/api/v2/"
        logger.info(f"Scoro base URL: {self.base_url}")
        self.headers = {
            'Content-Type': 'application/json'
        }
        
        # Caching for performance optimization
        self._users_cache = None  # Cache for users list
        self._companies_cache = None  # Cache for companies list
        self._phases_cache = {}  # Cache for phases by project_id: {project_id: [phases]}
        self._user_lookup_cache = {}  # Cache for user lookups by name: {name: user_dict}
        
        logger.info(f"Scoro client initialized for {self.company_name}")
    
    def _build_request_body(self, request_data: Dict) -> Dict:
        """
        Build a Scoro API v2 request body with required fields
        
        Args:
            request_data: The actual request data to wrap
            
        Returns:
            Complete request body with lang, company_account_id, apiKey, and request
        """
        return {
            "lang": "eng",
            "company_account_id": self.company_name,
            "apiKey": self.api_key,
            "request": request_data
        }
    
    def list_projects(self) -> List[Dict]:
        """
        List all existing projects in Scoro
        
        Returns:
            List of project dictionaries
        """
        try:
            # Scoro API v2 requires POST to projects/list with specific request format
            # According to API docs: https://api.scoro.com/api/v2/projects/list
            # Request body must include: lang, company_account_id, apiKey, and request
            endpoint = 'projects/list'
            
            # Base request body format per Scoro API documentation
            base_request = {
                "lang": "eng",
                "company_account_id": self.company_name,
                "apiKey": self.api_key,
                "request": {}
            }
            
            request_formats = [
                # Format 1: Standard format per API documentation (empty request object)
                base_request,
                # Format 2: With basic_data flag
                {**base_request, "basic_data": "1"},
                # Format 3: With filters in request
                {**base_request, "request": {"filters": {}}},
                # Format 4: With detailed_response flag
                {**base_request, "detailed_response": "1"},
            ]
            
            last_error = None
            data = None
            success = False
            
            # Scoro API v2 requires POST requests with a request body
            # Try POST with different request formats
            for request_body in request_formats:
                if success:
                    break
                try:
                    logger.debug(f"Trying POST to endpoint '{endpoint}' with request format")
                    # Remove Authorization header when using apiKey in body
                    headers_without_auth = {
                        'Content-Type': 'application/json'
                    }
                    response = requests.post(
                        f'{self.base_url}{endpoint}',
                        headers=headers_without_auth,
                        json=request_body
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    # Check if we got an error response
                    if isinstance(data, dict) and data.get('status') == 'ERROR':
                        error_msg = data.get('messages', {}).get('error', ['Unknown error'])
                        last_error = f"Scoro API error: {error_msg}"
                        logger.debug(f"Format failed with error: {error_msg}, trying next format...")
                        data = None  # Reset data so we try next format
                        continue
                    
                    # If we got here, the request was successful
                    success = True
                    break
                except requests.exceptions.HTTPError as e:
                    if e.response is not None:
                        try:
                            error_data = e.response.json()
                            if isinstance(error_data, dict) and error_data.get('status') == 'ERROR':
                                error_msg = error_data.get('messages', {}).get('error', ['Unknown error'])
                                last_error = f"Scoro API error: {error_msg}"
                                logger.debug(f"Format failed with HTTP error: {error_msg}, trying next format...")
                                # Log the response body for debugging
                                logger.debug(f"Response body: {e.response.text}")
                                continue
                            else:
                                # Non-error response, might be valid
                                data = error_data
                                success = True
                                break
                        except Exception as parse_error:
                            logger.debug(f"Could not parse error response: {parse_error}, response text: {e.response.text}")
                    last_error = str(e)
                    logger.debug(f"Format failed with exception: {e}, trying next format...")
                    continue
            
            if data is None:
                # All formats failed - provide detailed error message
                error_details = f"All request formats failed. Last error: {last_error}"
                logger.error(error_details)
                logger.error("Tried the following combinations:")
                logger.error("  - POST requests to: projects/list")
                logger.error("  - POST requests with apiKey authentication in request body")
                logger.error("  - Various request body formats (with/without basic_data, detailed_response, filters)")
                logger.error("")
                logger.error("Possible issues:")
                logger.error("  1. The Scoro API v2 endpoint or format may be different")
                logger.error("  2. The API key may not have permissions to list projects")
                logger.error("  3. Check Scoro API documentation for the correct endpoint format")
                if last_error:
                    raise ValueError(last_error)
                else:
                    raise ValueError("All request formats failed. Please check Scoro API documentation.")
            
            # Handle different response structures
            if isinstance(data, list):
                # Direct list response
                projects = data
            elif isinstance(data, dict):
                # Check if it's an error response
                if 'status' in data and data.get('status') == 'ERROR':
                    error_msg = data.get('messages', {}).get('error', ['Unknown error'])
                    logger.error(f"Scoro API error: {error_msg}")
                    raise ValueError(f"Scoro API error: {error_msg}")
                # Check if projects are in a 'data' key
                elif 'data' in data and isinstance(data['data'], list):
                    projects = data['data']
                # Check if projects are in a 'projects' key
                elif 'projects' in data and isinstance(data['projects'], list):
                    projects = data['projects']
                # Check if there's a nested 'request' or 'result' structure
                elif 'request' in data and isinstance(data.get('request'), dict):
                    # Try to find projects in nested structure
                    request_data = data.get('request', {})
                    if 'data' in request_data and isinstance(request_data['data'], list):
                        projects = request_data['data']
                    elif 'projects' in request_data and isinstance(request_data['projects'], list):
                        projects = request_data['projects']
                    else:
                        logger.warning(f"Unexpected nested response structure from Scoro API: {data}")
                        projects = []
                else:
                    # Unknown structure, log and return empty list
                    logger.warning(f"Unexpected response structure from Scoro API: {data}")
                    projects = []
            else:
                logger.warning(f"Unexpected response type from Scoro API: {type(data)}")
                projects = []
            
            logger.info(f"Retrieved {len(projects)} projects from Scoro")
            return projects
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing Scoro projects: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
    
    @retry_with_backoff()
    @rate_limit
    def create_project(self, project_data: Dict, project_id: Optional[int] = None) -> Dict:
        """
        Create or modify a project in Scoro
        
        Args:
            project_data: Project data dictionary (must include 'project_name' at minimum)
            project_id: Optional project ID for updating existing project
        
        Returns:
            Created or updated project dictionary
        """
        try:
            # Build request body per Scoro API v2 format
            request_body = self._build_request_body(project_data)
            
            # Use modify endpoint - with ID for updates, without for creates
            if project_id:
                endpoint = f'projects/modify/{project_id}'
            else:
                endpoint = 'projects/modify'
            
            response = requests.post(
                f'{self.base_url}{endpoint}',
                headers=self.headers,
                json=request_body
            )
            response.raise_for_status()
            result = response.json()
            
            # Handle response structure
            if isinstance(result, dict):
                if result.get('status') == 'ERROR':
                    error_msg = result.get('messages', {}).get('error', ['Unknown error'])
                    raise ValueError(f"Scoro API error: {error_msg}")
                # Response may have data key or be the project directly
                project = result.get('data', result)
            else:
                project = result
            
            project_name = project.get('project_name') or project.get('name', 'Unknown')
            logger.info(f"Created/updated Scoro project: {project_name}")
            return project
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating/updating Scoro project: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
    
    @retry_with_backoff()
    @rate_limit
    def get_project(self, project_id: int) -> Optional[Dict]:
        """
        Get a project by ID from Scoro
        
        Args:
            project_id: Project ID
        
        Returns:
            Project dictionary if found, None otherwise
        """
        try:
            endpoint = f'projects/view/{project_id}'
            request_body = self._build_request_body({})
            
            response = requests.post(
                f'{self.base_url}{endpoint}',
                headers=self.headers,
                json=request_body
            )
            response.raise_for_status()
            result = response.json()
            
            # Handle response structure
            if isinstance(result, dict):
                if result.get('status') == 'ERROR':
                    error_msg = result.get('messages', {}).get('error', ['Unknown error'])
                    logger.warning(f"Error getting project {project_id}: {error_msg}")
                    return None
                # Response may have data key or be the project directly
                project = result.get('data', result)
            else:
                project = result
            
            return project
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error getting Scoro project {project_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.debug(f"Response: {e.response.text}")
            return None
    
    @retry_with_backoff()
    @rate_limit
    def add_phase_to_project(self, project_id: int, phase_name: str, 
                             phase_type: str = "phase", 
                             start_date: Optional[str] = None, 
                             end_date: Optional[str] = None) -> Dict:
        """
        Add a phase to a Scoro project
        
        According to Scoro API, phases are added by modifying the project with a phases array.
        This method preserves existing phases and adds the new one.
        
        Args:
            project_id: Project ID
            phase_name: Name/title of the phase
            phase_type: Type of phase - "phase" or "milestone" (default: "phase")
            start_date: Optional start date in YYYY-mm-dd format
            end_date: Optional end date in YYYY-mm-dd format
        
        Returns:
            Updated project dictionary
        """
        try:
            # Get existing project to preserve existing phases
            project = self.get_project(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Get existing phases from the project
            existing_phases = project.get('phases', [])
            if not isinstance(existing_phases, list):
                existing_phases = []
            
            # Check if phase with same name already exists
            phase_name_lower = phase_name.lower().strip()
            for existing_phase in existing_phases:
                existing_title = existing_phase.get('title', '') or existing_phase.get('name', '')
                if existing_title.lower().strip() == phase_name_lower:
                    logger.info(f"Phase '{phase_name}' already exists in project {project_id}")
                    return project
            
            # Create new phase object
            new_phase = {
                "type": phase_type,
                "title": phase_name
            }
            
            if start_date:
                new_phase["start_date"] = start_date
            if end_date:
                new_phase["end_date"] = end_date
            
            # Add new phase to existing phases
            updated_phases = existing_phases + [new_phase]
            
            # Prepare project update data with phases
            project_data = {
                "phases": updated_phases
            }
            
            # Update the project with all phases
            updated_project = self.create_project(project_data, project_id=project_id)
            
            logger.info(f"Added phase '{phase_name}' to project {project_id}")
            return updated_project
        except requests.exceptions.RequestException as e:
            logger.error(f"Error adding phase to project {project_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
    
    @retry_with_backoff()
    @rate_limit
    def create_task(self, task_data: Dict, task_id: Optional[int] = None) -> Dict:
        """
        Create or modify a task in Scoro
        
        Args:
            task_data: Task data dictionary (must include 'event_name' at minimum)
            task_id: Optional task ID for updating existing task
        
        Returns:
            Created or updated task dictionary
        """
        try:
            # Build request body per Scoro API v2 format
            request_body = self._build_request_body(task_data)
            
            # Use modify endpoint - with ID for updates, without for creates
            if task_id:
                endpoint = f'tasks/modify/{task_id}'
            else:
                endpoint = 'tasks/modify'
            
            response = requests.post(
                f'{self.base_url}{endpoint}',
                headers=self.headers,
                json=request_body
            )
            response.raise_for_status()
            result = response.json()
            
            # Handle response structure
            if isinstance(result, dict):
                if result.get('status') == 'ERROR':
                    error_msg = result.get('messages', {}).get('error', ['Unknown error'])
                    raise ValueError(f"Scoro API error: {error_msg}")
                # Response may have data key or be the task directly
                task = result.get('data', result)
            else:
                task = result
            
            # Scoro API may return 'event_name', 'title', or 'name' field
            task_name = task.get('event_name') or task.get('title') or task.get('name', 'Unknown')
            logger.info(f"Created/updated Scoro task: {task_name}")
            return task
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating/updating Scoro task: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
    
    @retry_with_backoff()
    @rate_limit
    def create_milestone(self, milestone_data: Dict, milestone_id: Optional[int] = None) -> Dict:
        """
        Create or modify a milestone (project phase) in Scoro
        
        According to Scoro API, milestones are project phases with type="milestone"
        
        Args:
            milestone_data: Milestone data dictionary (must include 'title', 'project_id', 'type': 'milestone')
            milestone_id: Optional milestone ID for updating existing milestone
        
        Returns:
            Created or updated milestone dictionary
        """
        try:
            # Ensure type is set to milestone if not already set
            if 'type' not in milestone_data:
                milestone_data['type'] = 'milestone'
            
            # Build request body per Scoro API v2 format
            request_body = self._build_request_body(milestone_data)
            
            # Use projectPhases/modify endpoint
            if milestone_id:
                endpoint = f'projectPhases/modify/{milestone_id}'
            else:
                endpoint = 'projectPhases/modify'
            
            response = requests.post(
                f'{self.base_url}{endpoint}',
                headers=self.headers,
                json=request_body
            )
            response.raise_for_status()
            result = response.json()
            
            # Handle response structure
            if isinstance(result, dict):
                if result.get('status') == 'ERROR':
                    error_msg = result.get('messages', {}).get('error', ['Unknown error'])
                    raise ValueError(f"Scoro API error: {error_msg}")
                # Response may have data key or be the milestone directly
                milestone = result.get('data', result)
            else:
                milestone = result
            
            milestone_name = milestone.get('title') or milestone.get('name', 'Unknown')
            logger.info(f"Created/updated Scoro milestone: {milestone_name}")
            return milestone
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating/updating Scoro milestone: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
    
    @retry_with_backoff()
    @rate_limit
    def list_companies(self) -> List[Dict]:
        """
        List all companies in Scoro
        Automatically handles pagination to fetch all companies.
        
        Returns:
            List of company dictionaries
        """
        try:
            endpoint = 'companies/list'
            all_companies = []
            page = 1
            max_pages = 1000  # Safety limit to prevent infinite loops
            
            # Base request body format per Scoro API documentation
            base_request = {
                "lang": "eng",
                "company_account_id": self.company_name,
                "apiKey": self.api_key,
                "request": {}
            }
            
            request_formats = [
                # Format 1: Standard format per API documentation (empty request object)
                base_request,
                # Format 2: With basic_data flag
                {**base_request, "basic_data": "1"},
                # Format 3: With filters in request
                {**base_request, "request": {"filters": {}}},
            ]
            
            # Try to fetch all pages
            while page <= max_pages:
                last_error = None
                data = None
                success = False
                bookmark_id = None
                
                # Try POST with different request formats
                for request_body in request_formats:
                    if success:
                        break
                    
                    # Add pagination if we're on page > 1
                    if page > 1:
                        # Try with bookmark if we have one
                        if bookmark_id:
                            request_body = {**request_body, "bookmark": {"bookmark_id": str(bookmark_id)}}
                        # Or try with page/per_page parameters
                        else:
                            request_body = {**request_body, "page": str(page), "per_page": "100"}
                    
                    try:
                        logger.debug(f"Trying POST to endpoint '{endpoint}' page {page}")
                        headers_without_auth = {
                            'Content-Type': 'application/json'
                        }
                        response = requests.post(
                            f'{self.base_url}{endpoint}',
                            headers=headers_without_auth,
                            json=request_body
                        )
                        response.raise_for_status()
                        data = response.json()
                        
                        # Check if we got an error response
                        if isinstance(data, dict) and data.get('status') == 'ERROR':
                            error_msg = data.get('messages', {}).get('error', ['Unknown error'])
                            # If it's a pagination error (no more pages), break
                            if 'bookmark' in str(error_msg).lower() or 'page' in str(error_msg).lower():
                                logger.debug(f"No more pages available (page {page})")
                                break
                            last_error = f"Scoro API error: {error_msg}"
                            logger.debug(f"Format failed with error: {error_msg}, trying next format...")
                            continue
                        
                        # If we got here, the request was successful
                        success = True
                        break
                    except requests.exceptions.HTTPError as e:
                        if e.response is not None:
                            try:
                                error_data = e.response.json()
                                if isinstance(error_data, dict) and error_data.get('status') == 'ERROR':
                                    error_msg = error_data.get('messages', {}).get('error', ['Unknown error'])
                                    # If it's a pagination error, break
                                    if 'bookmark' in str(error_msg).lower() or 'page' in str(error_msg).lower() or page > 1:
                                        logger.debug(f"No more pages available (page {page})")
                                        break
                                    last_error = f"Scoro API error: {error_msg}"
                                    logger.debug(f"Format failed with HTTP error: {error_msg}, trying next format...")
                                    continue
                                else:
                                    # Non-error response, might be valid
                                    data = error_data
                                    success = True
                                    break
                            except Exception:
                                pass
                        last_error = str(e)
                        logger.debug(f"Format failed with exception: {e}, trying next format...")
                        continue
                
                if data is None:
                    if page == 1:
                        logger.warning("Could not list companies from Scoro API")
                        return []
                    else:
                        # No more pages
                        break
                
                # Handle different response structures
                page_companies = []
                if isinstance(data, list):
                    page_companies = data
                elif isinstance(data, dict):
                    if 'data' in data and isinstance(data['data'], list):
                        page_companies = data['data']
                    elif 'companies' in data and isinstance(data['companies'], list):
                        page_companies = data['companies']
                    # Check for bookmark for next page
                    bookmark = data.get('bookmark') or data.get('request', {}).get('bookmark')
                    if bookmark:
                        if isinstance(bookmark, dict):
                            bookmark_id = bookmark.get('bookmark_id')
                        elif isinstance(bookmark, str):
                            bookmark_id = bookmark
                
                if not page_companies:
                    # No more companies
                    break
                
                all_companies.extend(page_companies)
                logger.debug(f"Retrieved {len(page_companies)} companies from page {page} (total: {len(all_companies)})")
                
                # If we got fewer than 100 companies, we've likely reached the end
                if len(page_companies) < 100:
                    break
                
                # If no bookmark and we're on page 1, try to continue with page numbers
                if not bookmark_id and page == 1:
                    page += 1
                    continue
                elif bookmark_id:
                    # Use bookmark for next page
                    page += 1
                    continue
                else:
                    # No more pages
                    break
            
            logger.info(f"Retrieved {len(all_companies)} total companies from Scoro (across {page} page(s))")
            return all_companies
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error listing Scoro companies: {e}")
            return []
    
    def _get_cached_companies(self) -> List[Dict]:
        """
        Get companies list, using cache if available
        
        Returns:
            List of company dictionaries
        """
        if self._companies_cache is None:
            self._companies_cache = self.list_companies()
        return self._companies_cache
    
    def preload_companies_cache(self) -> None:
        """
        Pre-load companies cache to avoid repeated API calls during migration.
        Call this at the start of migration for better performance.
        """
        if self._companies_cache is None:
            logger.info("Pre-loading companies cache...")
            self._companies_cache = self.list_companies()
            logger.info(f"✓ Cached {len(self._companies_cache)} companies")
    
    @retry_with_backoff()
    @rate_limit
    def find_company_by_name(self, company_name: str) -> Optional[Dict]:
        """
        Find a company by name in Scoro
        First tries to find it as a client (contact with is_client=True), then tries companies endpoint.
        Uses improved pagination and name matching.
        Uses cached companies list to avoid repeated API calls.
        
        Args:
            company_name: Name of the company to find
        
        Returns:
            Company dictionary if found, None otherwise
        """
        if not company_name or not company_name.strip():
            return None
        
        try:
            # First, try to find it as a client (contact with is_client=True)
            # This is important because many companies are stored as contacts/clients
            logger.debug(f"Searching for company '{company_name}' as a client first...")
            client = self.find_client_by_name(company_name)
            if client:
                # Found as a client/contact, return it
                client_id = client.get('id') or client.get('contact_id')
                name = client.get('name', '') or client.get('search_name', '')
                logger.info(f"Found existing company as client: {name} (ID: {client_id})")
                return client
            
            # If not found as a client, try the companies endpoint (using cache)
            logger.debug(f"Company '{company_name}' not found as client, trying companies endpoint...")
            companies = self._get_cached_companies()
            
            if not companies:
                logger.debug(f"No companies found in Scoro")
                return None
            
            # Normalize name for comparison (same logic as find_client_by_name)
            def normalize_name(s):
                """Normalize a name for comparison"""
                if not s:
                    return ""
                return ' '.join(s.lower().strip().split())
            
            company_name_normalized = normalize_name(company_name)
            
            # Search through companies with improved matching
            for company in companies:
                name = company.get('name', '') or company.get('company_name', '')
                name_normalized = normalize_name(name)
                
                # Try exact match
                if name_normalized == company_name_normalized:
                    company_id = company.get('id') or company.get('company_id') or company.get('client_id') or company.get('contact_id')
                    logger.info(f"Found existing company: {name} (ID: {company_id})")
                    return company
                
                # Try partial match (if names are long enough)
                if name_normalized and len(company_name_normalized) >= 3 and len(name_normalized) >= 3:
                    if company_name_normalized in name_normalized or name_normalized in company_name_normalized:
                        company_id = company.get('id') or company.get('company_id') or company.get('client_id') or company.get('contact_id')
                        logger.info(f"Found existing company by partial match: {name} (ID: {company_id})")
                        return company
            
            logger.debug(f"Company not found: {company_name}")
            return None
        except Exception as e:
            logger.warning(f"Error finding company '{company_name}': {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    @retry_with_backoff()
    @rate_limit
    def create_company(self, company_data: Dict, company_id: Optional[int] = None) -> Dict:
        """
        Create or modify a company in Scoro
        
        Args:
            company_data: Company data dictionary (must include 'name' at minimum)
            company_id: Optional company ID for updating existing company
        
        Returns:
            Created or updated company dictionary
        """
        try:
            # Ensure name is provided
            if not company_data.get('name'):
                raise ValueError("Company name is required")
            
            # Build request body per Scoro API v2 format
            request_body = self._build_request_body(company_data)
            
            # Use modify endpoint - with ID for updates, without for creates
            if company_id:
                endpoint = f'companies/modify/{company_id}'
            else:
                endpoint = 'companies/modify'
            
            response = requests.post(
                f'{self.base_url}{endpoint}',
                headers=self.headers,
                json=request_body
            )
            response.raise_for_status()
            result = response.json()
            
            # Handle response structure
            if isinstance(result, dict):
                if result.get('status') == 'ERROR':
                    error_msg = result.get('messages', {}).get('error', ['Unknown error'])
                    raise ValueError(f"Scoro API error: {error_msg}")
                # Response may have data key or be the company directly
                company = result.get('data', result)
            else:
                company = result
            
            company_name = company.get('name', 'Unknown')
            company_id = company.get('id') or company.get('company_id') or company.get('client_id') or company.get('contact_id')
            logger.info(f"Created/updated Scoro company: {company_name} (ID: {company_id})")
            return company
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating/updating Scoro company: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
    
    @retry_with_backoff()
    @rate_limit
    def get_or_create_company(self, company_name: str, additional_data: Optional[Dict] = None) -> Dict:
        """
        Get an existing company by name or create a new one if it doesn't exist
        
        Args:
            company_name: Name of the company
            additional_data: Optional additional company data to use when creating
        
        Returns:
            Company dictionary (existing or newly created)
        """
        if not company_name or not company_name.strip():
            raise ValueError("Company name is required")
        
        # Try to find existing company
        existing_company = self.find_company_by_name(company_name)
        if existing_company:
            return existing_company
        
        # Create new company
        logger.info(f"Company '{company_name}' not found, creating new company...")
        company_data = {
            'name': company_name.strip()
        }
        
        if additional_data:
            company_data.update(additional_data)
        
        return self.create_company(company_data)
    
    @retry_with_backoff()
    @rate_limit
    def list_users(self) -> List[Dict]:
        """
        List all users in Scoro
        
        Returns:
            List of user dictionaries
        """
        try:
            # Scoro API v2 requires POST to users/list with specific request format
            # Similar to companies/list and projects/list endpoints
            endpoint = 'users/list'
            
            # Base request body format per Scoro API documentation
            # Note: API docs show user_token for users/list, but we'll try apiKey first (consistent with other endpoints)
            base_request = {
                "lang": "eng",
                "company_account_id": self.company_name,
                "apiKey": self.api_key,
                "request": {}
            }
            
            request_formats = [
                # Format 1: Standard format per API documentation (empty request object) with apiKey
                base_request,
                # Format 2: With basic_data flag
                {**base_request, "basic_data": "1"},
                # Format 3: With filters in request
                {**base_request, "request": {"filters": {}}},
                # Format 4: Try with user_token instead of apiKey (API docs show user_token for users/list)
                {
                    "lang": "eng",
                    "company_account_id": self.company_name,
                    "user_token": self.api_key,
                    "request": {}
                },
            ]
            
            last_error = None
            data = None
            success = False
            
            # Scoro API v2 requires POST requests with a request body
            # Try POST with different request formats
            for request_body in request_formats:
                if success:
                    break
                try:
                    logger.debug(f"Trying POST to endpoint '{endpoint}'")
                    # Remove Authorization header when using apiKey in body
                    headers_without_auth = {
                        'Content-Type': 'application/json'
                    }
                    response = requests.post(
                        f'{self.base_url}{endpoint}',
                        headers=headers_without_auth,
                        json=request_body
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    # Check if we got an error response
                    if isinstance(data, dict) and data.get('status') == 'ERROR':
                        error_msg = data.get('messages', {}).get('error', ['Unknown error'])
                        last_error = f"Scoro API error: {error_msg}"
                        logger.debug(f"Format failed with error: {error_msg}, trying next format...")
                        continue
                    
                    # If we got here, the request was successful
                    success = True
                    break
                except requests.exceptions.HTTPError as e:
                    if e.response is not None:
                        try:
                            error_data = e.response.json()
                            if isinstance(error_data, dict) and error_data.get('status') == 'ERROR':
                                error_msg = error_data.get('messages', {}).get('error', ['Unknown error'])
                                last_error = f"Scoro API error: {error_msg}"
                                logger.debug(f"Format failed with HTTP error: {error_msg}, trying next format...")
                                continue
                            else:
                                # Non-error response, might be valid
                                data = error_data
                                success = True
                                break
                        except Exception:
                            pass
                    last_error = str(e)
                    logger.debug(f"Format failed with exception: {e}, trying next format...")
                    continue
            
            if data is None:
                logger.warning("Could not list users from Scoro API")
                return []
            
            # Handle different response structures
            if isinstance(data, list):
                users = data
            elif isinstance(data, dict):
                if 'data' in data and isinstance(data['data'], list):
                    users = data['data']
                elif 'users' in data and isinstance(data['users'], list):
                    users = data['users']
                else:
                    users = []
            else:
                users = []
            
            logger.info(f"Retrieved {len(users)} users from Scoro")
            return users
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error listing Scoro users: {e}")
            return []
    
    @retry_with_backoff()
    @rate_limit
    def list_activities(self) -> List[Dict]:
        """
        List all activities from Scoro
        
        Returns:
            List of activity dictionaries
        """
        try:
            # Scoro API v2 requires POST to activities/list with specific request format
            endpoint = 'activities/list'
            
            # Build request body per Scoro API v2 format
            request_body = self._build_request_body({})
            
            logger.debug(f"Trying POST to endpoint '{endpoint}'")
            
            response = requests.post(
                f'{self.base_url}{endpoint}',
                headers=self.headers,
                json=request_body
            )
            response.raise_for_status()
            result = response.json()
            
            # Handle different response structures
            if isinstance(result, list):
                activities = result
            elif isinstance(result, dict):
                # Check if activities are in a 'data' key
                if 'data' in result and isinstance(result['data'], list):
                    activities = result['data']
                else:
                    logger.warning(f"Unexpected response structure from Scoro API: {result}")
                    activities = []
            else:
                logger.warning(f"Unexpected response type from Scoro API: {type(result)}")
                activities = []
            
            logger.info(f"Retrieved {len(activities)} activities from Scoro")
            return activities
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing Scoro activities: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return []
    
    def find_activity_by_name(self, activity_name: str) -> Optional[Dict]:
        """
        Find an activity by name in Scoro
        
        Args:
            activity_name: Activity name to search for
        
        Returns:
            Activity dictionary if found, None otherwise
        """
        if not activity_name or not str(activity_name).strip():
            return None
        
        activity_name = str(activity_name).strip()
        
        # Get all activities
        activities = self.list_activities()
        if not activities:
            logger.warning("No activities found in Scoro")
            return None
        
        # Try exact match first
        for activity in activities:
            name = activity.get('name') or activity.get('activity_name') or activity.get('title', '')
            if name.strip() == activity_name:
                logger.debug(f"Found activity by exact match: {name} (ID: {activity.get('id')})")
                return activity
        
        # Try case-insensitive match
        activity_name_lower = activity_name.lower()
        for activity in activities:
            name = activity.get('name') or activity.get('activity_name') or activity.get('title', '')
            if name.strip().lower() == activity_name_lower:
                logger.debug(f"Found activity by case-insensitive match: {name} (ID: {activity.get('id')})")
                return activity
        
        logger.warning(f"Activity '{activity_name}' not found in Scoro")
        return None
    
    @retry_with_backoff()
    @rate_limit
    def create_comment(self, module: str, object_id: int, comment_text: str, user_id: Optional[int] = None, parent_id: Optional[int] = None, comment_id: Optional[int] = None) -> Dict:
        """
        Create or modify a comment in Scoro
        
        Args:
            module: Module name (e.g., "tasks", "projects")
            object_id: ID of the object to comment on (e.g., task ID)
            comment_text: Comment content
            user_id: User ID of the comment owner (mandatory when using apiKey)
            parent_id: Optional parent comment ID for replies
            comment_id: Optional comment ID for updating existing comment
        
        Returns:
            Created or updated comment dictionary
        """
        try:
            # Build request data per Scoro Comments API format
            request_data = {
                'module': module,
                'object_id': str(object_id),  # API expects string for object_id
                'comment': comment_text
            }
            
            # user_id is mandatory when using apiKey
            if user_id is None:
                raise ValueError("user_id is mandatory when using apiKey authentication")
            request_data['user_id'] = user_id
            
            # Add parent_id for replies
            if parent_id:
                request_data['parent_id'] = parent_id
            
            # Build request body per Scoro API v2 format
            request_body = self._build_request_body(request_data)
            
            # Use modify endpoint - with ID for updates, without for creates
            if comment_id:
                endpoint = f'comments/modify/{comment_id}'
            else:
                endpoint = 'comments/modify'
            
            response = requests.post(
                f'{self.base_url}{endpoint}',
                headers=self.headers,
                json=request_body
            )
            response.raise_for_status()
            result = response.json()
            
            # Handle response structure
            if isinstance(result, dict):
                if result.get('status') == 'ERROR':
                    error_msg = result.get('messages', {}).get('error', ['Unknown error'])
                    raise ValueError(f"Scoro API error: {error_msg}")
                # Response may have data key or be the comment directly
                comment = result.get('data', result)
            else:
                comment = result
            
            comment_id_returned = comment.get('comment_id') or comment.get('id')
            logger.debug(f"Created/updated Scoro comment (ID: {comment_id_returned}) on {module} {object_id}")
            return comment
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating/updating Scoro comment: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
    
    @retry_with_backoff()
    @rate_limit
    def create_time_entry(self, time_entry_data: Dict, time_entry_id: Optional[int] = None) -> Dict:
        """
        Create or modify a time entry in Scoro
        
        Args:
            time_entry_data: Time entry data dictionary (must include 'event_id' and 'user_id' at minimum)
            time_entry_id: Optional time entry ID for updating existing time entry
        
        Returns:
            Created or updated time entry dictionary
        """
        try:
            # Validate required fields
            if 'event_id' not in time_entry_data:
                raise ValueError("event_id is required for time entry")
            if 'user_id' not in time_entry_data:
                raise ValueError("user_id is required for time entry when using apiKey")
            
            # Build request body per Scoro API v2 format
            request_body = self._build_request_body(time_entry_data)
            
            # Use modify endpoint - with ID for updates, without for creates
            if time_entry_id:
                endpoint = f'timeEntries/modify/{time_entry_id}'
            else:
                endpoint = 'timeEntries/modify'
            
            response = requests.post(
                f'{self.base_url}{endpoint}',
                headers=self.headers,
                json=request_body
            )
            response.raise_for_status()
            result = response.json()
            
            # Handle response structure
            if isinstance(result, dict):
                if result.get('status') == 'ERROR':
                    error_msg = result.get('messages', {}).get('error', ['Unknown error'])
                    raise ValueError(f"Scoro API error: {error_msg}")
                # Response may have data key or be the time entry directly
                time_entry = result.get('data', result)
            else:
                time_entry = result
            
            time_entry_id_returned = time_entry.get('time_entry_id') or time_entry.get('id')
            duration = time_entry.get('duration', 'Unknown')
            logger.debug(f"Created/updated Scoro time entry (ID: {time_entry_id_returned}, Duration: {duration})")
            return time_entry
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating/updating Scoro time entry: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
    
    def _get_cached_users(self) -> List[Dict]:
        """
        Get users list, using cache if available
        
        Returns:
            List of user dictionaries
        """
        if self._users_cache is None:
            self._users_cache = self.list_users()
        return self._users_cache
    
    def preload_users_cache(self) -> None:
        """
        Pre-load users cache to avoid repeated API calls during migration.
        Call this at the start of migration for better performance.
        """
        if self._users_cache is None:
            logger.info("Pre-loading users cache...")
            self._users_cache = self.list_users()
            logger.info(f"✓ Cached {len(self._users_cache)} users")
    
    @retry_with_backoff()
    @rate_limit
    def find_user_by_name(self, user_name: str) -> Optional[Dict]:
        """
        Find a user by name in Scoro
        
        Uses cached users list to avoid repeated API calls.
        
        Args:
            user_name: Name of the user to find (can be full_name, firstname + lastname, or email)
        
        Returns:
            User dictionary if found, None otherwise
        """
        try:
            # Check lookup cache first
            user_name_lower = user_name.lower().strip()
            if user_name_lower in self._user_lookup_cache:
                cached_user = self._user_lookup_cache[user_name_lower]
                logger.debug(f"Found user in lookup cache: {user_name}")
                return cached_user
            
            # Get users from cache (or fetch if not cached)
            users = self._get_cached_users()
            if not users:
                logger.debug(f"No users available to search for: {user_name}")
                return None
            
            # Try multiple matching strategies
            for user in users:
                # Try full_name first
                full_name = user.get('full_name', '')
                if full_name and full_name.lower().strip() == user_name_lower:
                    user_id = user.get('id')
                    logger.debug(f"Found user by full_name: {full_name} (ID: {user_id})")
                    # Cache the result
                    self._user_lookup_cache[user_name_lower] = user
                    return user
                
                # Try firstname + lastname
                firstname = user.get('firstname', '')
                lastname = user.get('lastname', '')
                if firstname and lastname:
                    combined_name = f"{firstname} {lastname}".lower().strip()
                    if combined_name == user_name_lower:
                        user_id = user.get('id')
                        logger.debug(f"Found user by firstname+lastname: {combined_name} (ID: {user_id})")
                        # Cache the result
                        self._user_lookup_cache[user_name_lower] = user
                        return user
                
                # Try email
                email = user.get('email', '')
                if email and email.lower().strip() == user_name_lower:
                    user_id = user.get('id')
                    logger.debug(f"Found user by email: {email} (ID: {user_id})")
                    # Cache the result
                    self._user_lookup_cache[user_name_lower] = user
                    return user
                
                # Try partial match on full_name (in case of slight variations)
                if full_name:
                    # Check if the provided name is contained in full_name or vice versa
                    full_name_lower = full_name.lower().strip()
                    if user_name_lower in full_name_lower or full_name_lower in user_name_lower:
                        # Only match if it's a reasonable match (not too short)
                        if len(user_name_lower) >= 3 and len(full_name_lower) >= 3:
                            user_id = user.get('id')
                            logger.debug(f"Found user by partial match: {full_name} (ID: {user_id})")
                            # Cache the result
                            self._user_lookup_cache[user_name_lower] = user
                            return user
            
            # Cache None result to avoid repeated lookups for non-existent users
            self._user_lookup_cache[user_name_lower] = None
            logger.debug(f"User not found: {user_name}")
            return None
        except Exception as e:
            logger.warning(f"Error finding user '{user_name}': {e}")
            return None
    
    @retry_with_backoff()
    @rate_limit
    def list_project_phases(self, project_id: Optional[int] = None) -> List[Dict]:
        """
        List all project phases in Scoro
        
        Args:
            project_id: Optional project ID to filter phases for a specific project
        
        Returns:
            List of phase dictionaries
        """
        try:
            # Scoro API v2 endpoint for project phases
            endpoint = 'projectPhases/list'
            
            # Base request body format per Scoro API documentation
            base_request = {
                "lang": "eng",
                "company_account_id": self.company_name,
                "apiKey": self.api_key,
                "request": {}
            }
            
            # Add project_id filter if provided
            if project_id:
                base_request["request"]["filters"] = {"project_id": project_id}
            
            request_formats = [
                # Format 1: Standard format
                base_request,
                # Format 2: With basic_data flag
                {**base_request, "basic_data": "1"},
            ]
            
            last_error = None
            data = None
            success = False
            
            # Try POST with different request formats
            for request_body in request_formats:
                if success:
                    break
                try:
                    logger.debug(f"Trying POST to endpoint '{endpoint}'")
                    headers_without_auth = {
                        'Content-Type': 'application/json'
                    }
                    response = requests.post(
                        f'{self.base_url}{endpoint}',
                        headers=headers_without_auth,
                        json=request_body
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    # Check if we got an error response
                    if isinstance(data, dict) and data.get('status') == 'ERROR':
                        error_msg = data.get('messages', {}).get('error', ['Unknown error'])
                        last_error = f"Scoro API error: {error_msg}"
                        logger.debug(f"Format failed with error: {error_msg}, trying next format...")
                        continue
                    
                    # If we got here, the request was successful
                    success = True
                    break
                except requests.exceptions.HTTPError as e:
                    if e.response is not None:
                        try:
                            error_data = e.response.json()
                            if isinstance(error_data, dict) and error_data.get('status') == 'ERROR':
                                error_msg = error_data.get('messages', {}).get('error', ['Unknown error'])
                                last_error = f"Scoro API error: {error_msg}"
                                logger.debug(f"Format failed with HTTP error: {error_msg}, trying next format...")
                                continue
                            else:
                                # Non-error response, might be valid
                                data = error_data
                                success = True
                                break
                        except Exception:
                            pass
                    last_error = str(e)
                    logger.debug(f"Format failed with exception: {e}, trying next format...")
                    continue
            
            if data is None:
                logger.warning("Could not list project phases from Scoro API")
                return []
            
            # Handle different response structures
            if isinstance(data, list):
                phases = data
            elif isinstance(data, dict):
                if 'data' in data and isinstance(data['data'], list):
                    phases = data['data']
                elif 'phases' in data and isinstance(data['phases'], list):
                    phases = data['phases']
                else:
                    phases = []
            else:
                phases = []
            
            logger.debug(f"Retrieved {len(phases)} project phases from Scoro")
            # logger.debug(f"Phases: {phases}")
            return phases
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error listing Scoro project phases: {e}")
            return []
    
    def _get_cached_phases(self, project_id: Optional[int] = None) -> List[Dict]:
        """
        Get project phases list, using cache if available
        
        When project_id is provided, uses get_project() to get phases directly from the project,
        which is more reliable than filtering the phases list endpoint.
        
        Args:
            project_id: Optional project ID to filter phases
        
        Returns:
            List of phase dictionaries
        """
        cache_key = project_id if project_id else 'all'
        if cache_key not in self._phases_cache:
            if project_id:
                # For specific project, get phases directly from project view (more reliable)
                project = self.get_project(project_id)
                if project and 'phases' in project:
                    phases = project['phases']
                    if isinstance(phases, list):
                        # Ensure each phase has project_id set
                        for phase in phases:
                            if 'project_id' not in phase:
                                phase['project_id'] = project_id
                        self._phases_cache[cache_key] = phases
                        logger.debug(f"Retrieved {len(phases)} phases from project {project_id} view")
                    else:
                        self._phases_cache[cache_key] = []
                else:
                    self._phases_cache[cache_key] = []
            else:
                # For all phases, use the list endpoint
                self._phases_cache[cache_key] = self.list_project_phases(project_id=project_id)
        return self._phases_cache[cache_key]
    
    @retry_with_backoff()
    @rate_limit
    def find_phase_by_name(self, phase_name: str, project_id: Optional[int] = None) -> Optional[Dict]:
        """
        Find a project phase by name in Scoro
        Uses cached phases list to avoid repeated API calls.
        
        Uses strict matching: prefers exact matches (case-sensitive) first,
        then falls back to case-insensitive matches. This prevents matching
        the wrong phase when multiple phases have similar names.
        
        Args:
            phase_name: Name (title) of the phase to find
            project_id: Optional project ID to limit search to a specific project
        
        Returns:
            Phase dictionary if found, None otherwise
        """
        try:
            phases = self._get_cached_phases(project_id=project_id)
            if not phases:
                logger.debug(f"No phases available to search for: '{phase_name}' in project {project_id if project_id else 'any'}")
                return None
            
            # When project_id is provided, phases are already filtered to that project (from get_project)
            # But we keep this as a safety check in case we're using the list endpoint
            if project_id is not None:
                # Double-check that all phases belong to this project (safety check)
                phases = [p for p in phases if p.get('project_id') == project_id]
                if not phases:
                    logger.debug(f"No phases found for project ID {project_id} after filtering")
                    return None
                logger.debug(f"Searching {len(phases)} phases for project ID {project_id} to find phase: '{phase_name}'")
            
            # Normalize phase name by decoding HTML entities (e.g., &amp; -> &)
            # Scoro API may return phase names with HTML entities encoded
            phase_name_stripped = html.unescape(phase_name.strip())
            phase_name_lower = phase_name_stripped.lower()
            
            # First pass: Try exact match (case-sensitive) - this is the most reliable
            for phase in phases:
                # Try title field (most common)
                title = phase.get('title', '')
                if title:
                    # Decode HTML entities in phase title before comparison
                    title_normalized = html.unescape(title.strip())
                    if title_normalized == phase_name_stripped:
                        phase_id = phase.get('id') or phase.get('phase_id')
                        phase_project_id = phase.get('project_id')
                        logger.info(f"Found phase by exact title match: '{title}' (ID: {phase_id}, Project ID: {phase_project_id}) for search: '{phase_name}'")
                        return phase
                
                # Try name field as fallback
                name = phase.get('name', '')
                if name:
                    # Decode HTML entities in phase name before comparison
                    name_normalized = html.unescape(name.strip())
                    if name_normalized == phase_name_stripped:
                        phase_id = phase.get('id') or phase.get('phase_id')
                        phase_project_id = phase.get('project_id')
                        logger.info(f"Found phase by exact name match: '{name}' (ID: {phase_id}, Project ID: {phase_project_id}) for search: '{phase_name}'")
                        return phase
            
            # Second pass: Try case-insensitive match (fallback)
            # Log all potential matches for debugging
            potential_matches = []
            for phase in phases:
                title = phase.get('title', '')
                name = phase.get('name', '')
                if title:
                    # Decode HTML entities in phase title before comparison
                    title_normalized = html.unescape(title.strip())
                    if title_normalized.lower() == phase_name_lower:
                        potential_matches.append(('title', title, phase))
                elif name:
                    # Decode HTML entities in phase name before comparison
                    name_normalized = html.unescape(name.strip())
                    if name_normalized.lower() == phase_name_lower:
                        potential_matches.append(('name', name, phase))
            
            if potential_matches:
                # If multiple matches, log warning and use first one
                if len(potential_matches) > 1:
                    logger.warning(f"Multiple case-insensitive matches found for phase '{phase_name}' in project {project_id}: {[m[1] for m in potential_matches]}")
                    logger.warning(f"Using first match: '{potential_matches[0][1]}' (this may be incorrect if phase names are similar)")
                
                match_type, match_name, phase = potential_matches[0]
                phase_id = phase.get('id') or phase.get('phase_id')
                phase_project_id = phase.get('project_id')
                logger.info(f"Found phase by case-insensitive {match_type} match: '{match_name}' (ID: {phase_id}, Project ID: {phase_project_id}) for search: '{phase_name}'")
                return phase
            
            # No match found - log available phases for debugging
            # Decode HTML entities in phase names for clearer logging
            available_phases = [html.unescape(p.get('title') or p.get('name', 'Unknown')) for p in phases]
            logger.warning(f"Phase '{phase_name}' not found in project {project_id if project_id else 'any'}")
            logger.debug(f"Available phases in project {project_id}: {available_phases}")
            return None
        except Exception as e:
            logger.warning(f"Error finding phase '{phase_name}': {e}")
            return None
    
    @retry_with_backoff()
    @rate_limit
    def list_contacts(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        List contacts from Scoro with optional filtering
        Automatically handles pagination to fetch all contacts.
        
        Args:
            filters: Optional dictionary of filters to apply (e.g., {'is_client': True, 'name': 'Company Name'})
        
        Returns:
            List of contact dictionaries
        """
        try:
            endpoint = 'contacts/list'
            all_contacts = []
            page = 1
            max_pages = 1000  # Safety limit to prevent infinite loops
            
            # Base request body format per Scoro API documentation
            base_request = {
                "lang": "eng",
                "company_account_id": self.company_name,
                "apiKey": self.api_key,
                "request": {}
            }
            
            # Add filters to request if provided
            if filters:
                base_request["request"]["filters"] = filters
            
            request_formats = [
                # Format 1: Standard format per API documentation
                base_request,
                # Format 2: With basic_data flag
                {**base_request, "basic_data": "1"},
                # Format 3: With detailed_response flag
                {**base_request, "detailed_response": "1"},
            ]
            
            # Try to fetch all pages
            while page <= max_pages:
                last_error = None
                data = None
                success = False
                bookmark_id = None
                
                # Try POST with different request formats
                for request_body in request_formats:
                    if success:
                        break
                    
                    # Add pagination if we're on page > 1
                    if page > 1:
                        # Try with bookmark if we have one
                        if bookmark_id:
                            request_body = {**request_body, "bookmark": {"bookmark_id": str(bookmark_id)}}
                        # Or try with page/per_page parameters
                        else:
                            request_body = {**request_body, "page": str(page), "per_page": "100"}
                    
                    try:
                        logger.debug(f"Trying POST to endpoint '{endpoint}' page {page} with filters: {filters}")
                        headers_without_auth = {
                            'Content-Type': 'application/json'
                        }
                        response = requests.post(
                            f'{self.base_url}{endpoint}',
                            headers=headers_without_auth,
                            json=request_body
                        )
                        response.raise_for_status()
                        data = response.json()
                        
                        # Check if we got an error response
                        if isinstance(data, dict) and data.get('status') == 'ERROR':
                            error_msg = data.get('messages', {}).get('error', ['Unknown error'])
                            # If it's a pagination error (no more pages), break
                            if 'bookmark' in str(error_msg).lower() or 'page' in str(error_msg).lower():
                                logger.debug(f"No more pages available (page {page})")
                                break
                            last_error = f"Scoro API error: {error_msg}"
                            logger.debug(f"Format failed with error: {error_msg}, trying next format...")
                            continue
                        
                        # If we got here, the request was successful
                        success = True
                        break
                    except requests.exceptions.HTTPError as e:
                        if e.response is not None:
                            try:
                                error_data = e.response.json()
                                if isinstance(error_data, dict) and error_data.get('status') == 'ERROR':
                                    error_msg = error_data.get('messages', {}).get('error', ['Unknown error'])
                                    # If it's a pagination error, break
                                    if 'bookmark' in str(error_msg).lower() or 'page' in str(error_msg).lower() or page > 1:
                                        logger.debug(f"No more pages available (page {page})")
                                        break
                                    last_error = f"Scoro API error: {error_msg}"
                                    logger.debug(f"Format failed with HTTP error: {error_msg}, trying next format...")
                                    continue
                                else:
                                    # Non-error response, might be valid
                                    data = error_data
                                    success = True
                                    break
                            except Exception:
                                pass
                        last_error = str(e)
                        logger.debug(f"Format failed with exception: {e}, trying next format...")
                        continue
                
                if data is None:
                    if page == 1:
                        logger.warning("Could not list contacts from Scoro API")
                        return []
                    else:
                        # No more pages
                        break
                
                # Handle different response structures
                page_contacts = []
                if isinstance(data, list):
                    page_contacts = data
                elif isinstance(data, dict):
                    if 'data' in data and isinstance(data['data'], list):
                        page_contacts = data['data']
                    elif 'contacts' in data and isinstance(data['contacts'], list):
                        page_contacts = data['contacts']
                    # Check for pagination - look for bookmark or pagination info
                    elif 'request' in data and isinstance(data.get('request'), dict):
                        request_data = data.get('request', {})
                        if 'data' in request_data and isinstance(request_data['data'], list):
                            page_contacts = request_data['data']
                        elif 'contacts' in request_data and isinstance(request_data['contacts'], list):
                            page_contacts = request_data['contacts']
                    
                    # Check for bookmark for next page
                    bookmark = data.get('bookmark') or data.get('request', {}).get('bookmark')
                    if bookmark:
                        if isinstance(bookmark, dict):
                            bookmark_id = bookmark.get('bookmark_id')
                        elif isinstance(bookmark, str):
                            bookmark_id = bookmark
                
                if not page_contacts:
                    # No more contacts
                    break
                
                all_contacts.extend(page_contacts)
                logger.debug(f"Retrieved {len(page_contacts)} contacts from page {page} (total: {len(all_contacts)})")
                
                # If we got fewer than 100 contacts, we've likely reached the end
                if len(page_contacts) < 100:
                    break
                
                # If no bookmark and we're on page 1, try to continue with page numbers
                if not bookmark_id and page == 1:
                    page += 1
                    continue
                elif bookmark_id:
                    # Use bookmark for next page
                    page += 1
                    continue
                else:
                    # No more pages
                    break
            
            logger.info(f"Retrieved {len(all_contacts)} total contacts from Scoro (across {page} page(s))")
            return all_contacts
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error listing Scoro contacts: {e}")
            return []
    
    @retry_with_backoff()
    @rate_limit
    def find_client_by_name(self, client_name: str) -> Optional[Dict]:
        """
        Find a client (contact with is_client=True) by name in Scoro
        
        Args:
            client_name: Name of the client to find
        
        Returns:
            Contact dictionary if found, None otherwise
        """
        try:
            if not client_name or not client_name.strip():
                return None
            
            client_name_clean = client_name.strip()
            client_name_lower = client_name_clean.lower()
            
            # Note: Scoro API filter for is_client might not work as expected
            # So we'll get all contacts and filter client-side
            # Also, companies might be in the companies endpoint, not contacts
            # Let's try both approaches
            
            # First, try to get contacts without filter (API filter might not work)
            contacts = self.list_contacts(filters=None)
            
            if not contacts:
                logger.debug(f"No contacts found in Scoro")
                return None
            
            logger.debug(f"Searching through {len(contacts)} contacts for client: {client_name}")
            
            # Normalize names for comparison (handle special characters, whitespace)
            def normalize_name(s):
                """Normalize a name for comparison"""
                if not s:
                    return ""
                # Convert to lowercase, strip whitespace, normalize whitespace
                normalized = ' '.join(s.lower().strip().split())
                return normalized
            
            client_name_normalized = normalize_name(client_name_clean)
            
            # Filter by name (case-insensitive) and check is_client flag
            matching_contacts = []
            for contact in contacts:
                # Check if it's a client (is_client should be True or 1)
                is_client = contact.get('is_client', False)
                # Handle both boolean and integer values
                if is_client not in (True, 1, '1', 'true'):
                    continue
                
                # Check name field (for companies)
                name = contact.get('name', '')
                search_name = contact.get('search_name', '')
                
                # Debug: log first few contacts to see structure
                if len(matching_contacts) == 0 and name:
                    logger.debug(f"Sample contact - name: '{name}', search_name: '{search_name}', is_client: {is_client}, contact_type: {contact.get('contact_type', 'N/A')}")
                
                # Normalize names for comparison
                name_normalized = normalize_name(name)
                search_name_normalized = normalize_name(search_name)
                
                # Try exact match on name
                if name_normalized == client_name_normalized:
                    matching_contacts.append(contact)
                    continue
                
                # Try exact match on search_name
                if search_name_normalized == client_name_normalized:
                    matching_contacts.append(contact)
                    continue
                
                # Try partial match for name (if names are long enough)
                if name_normalized and len(client_name_normalized) >= 3 and len(name_normalized) >= 3:
                    if client_name_normalized in name_normalized or name_normalized in client_name_normalized:
                        matching_contacts.append(contact)
            
            if matching_contacts:
                # Return the first match (or could return all matches)
                contact = matching_contacts[0]
                contact_id = contact.get('id') or contact.get('contact_id')
                name = contact.get('name', '') or contact.get('search_name', '')
                logger.info(f"Found {len(matching_contacts)} client(s) matching '{client_name}': {name} (ID: {contact_id})")
                return contact
            
            # If not found in contacts, try companies endpoint
            logger.debug(f"Client not found in contacts, trying companies endpoint...")
            companies = self.list_companies()
            
            if companies:
                logger.debug(f"Searching through {len(companies)} companies for: {client_name}")
                # Normalize function (reuse from above)
                def normalize_name(s):
                    if not s:
                        return ""
                    return ' '.join(s.lower().strip().split())
                
                client_name_normalized = normalize_name(client_name_clean)
                
                for company in companies:
                    name = company.get('name', '') or company.get('company_name', '')
                    name_normalized = normalize_name(name)
                    
                    if name_normalized == client_name_normalized:
                        company_id = company.get('id') or company.get('company_id') or company.get('contact_id')
                        logger.info(f"Found company by name: {name} (ID: {company_id})")
                        return company
            
            logger.debug(f"Client not found: {client_name}")
            return None
        except Exception as e:
            logger.warning(f"Error finding client '{client_name}': {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def client_exists(self, client_name: str) -> bool:
        """
        Check if a client exists in Scoro by name
        
        Args:
            client_name: Name of the client to check
        
        Returns:
            True if client exists, False otherwise
        """
        client = self.find_client_by_name(client_name)
        return client is not None
    
    @retry_with_backoff()
    @rate_limit
    def find_all_clients_by_name(self, client_name: str) -> List[Dict]:
        """
        Find ALL clients (contacts with is_client=True) matching the given name in Scoro
        
        Args:
            client_name: Name of the client to find
        
        Returns:
            List of contact dictionaries matching the name
        """
        try:
            if not client_name or not client_name.strip():
                return []
            
            client_name_clean = client_name.strip()
            
            # Get all contacts
            contacts = self.list_contacts(filters=None)
            
            if not contacts:
                logger.debug(f"No contacts found in Scoro")
                return []
            
            logger.debug(f"Searching through {len(contacts)} contacts for all clients matching: {client_name}")
            
            # Normalize names for comparison
            def normalize_name(s):
                """Normalize a name for comparison"""
                if not s:
                    return ""
                return ' '.join(s.lower().strip().split())
            
            client_name_normalized = normalize_name(client_name_clean)
            
            # Filter by name (case-insensitive) and check is_client flag
            matching_contacts = []
            for contact in contacts:
                # Check if it's a client (is_client should be True or 1)
                is_client = contact.get('is_client', False)
                # Handle both boolean and integer values
                if is_client not in (True, 1, '1', 'true'):
                    continue
                
                # Check name field (for companies)
                name = contact.get('name', '')
                search_name = contact.get('search_name', '')
                
                # Normalize names for comparison
                name_normalized = normalize_name(name)
                search_name_normalized = normalize_name(search_name)
                
                # Try exact match on name
                if name_normalized == client_name_normalized:
                    matching_contacts.append(contact)
                    continue
                
                # Try exact match on search_name
                if search_name_normalized == client_name_normalized:
                    matching_contacts.append(contact)
                    continue
                
                # Try partial match for name (if names are long enough)
                if name_normalized and len(client_name_normalized) >= 3 and len(name_normalized) >= 3:
                    if client_name_normalized in name_normalized or name_normalized in client_name_normalized:
                        matching_contacts.append(contact)
            
            logger.info(f"Found {len(matching_contacts)} client(s) matching '{client_name}'")
            return matching_contacts
        except Exception as e:
            logger.warning(f"Error finding all clients '{client_name}': {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    @retry_with_backoff()
    @rate_limit
    def delete_contact(self, contact_id: int) -> bool:
        """
        Delete a contact in Scoro
        
        First tries the delete endpoint if available, otherwise uses modify to set deleted_date
        
        Args:
            contact_id: ID of the contact to delete
        
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # First, try the delete endpoint (similar to timeEntries/delete)
            endpoint = f'contacts/delete/{contact_id}'
            
            request_body = self._build_request_body({})
            
            try:
                response = requests.post(
                    f'{self.base_url}{endpoint}',
                    headers=self.headers,
                    json=request_body
                )
                response.raise_for_status()
                result = response.json()
                
                # Check if it was successful
                if isinstance(result, dict):
                    if result.get('status') == 'OK':
                        logger.info(f"Successfully deleted contact {contact_id} via delete endpoint")
                        return True
                    elif result.get('status') == 'ERROR':
                        # Delete endpoint might not exist, try modify approach
                        logger.debug(f"Delete endpoint returned error, trying modify approach...")
                    else:
                        logger.info(f"Successfully deleted contact {contact_id}")
                        return True
            except requests.exceptions.HTTPError as e:
                # If delete endpoint doesn't exist (404), try modify approach
                if e.response and e.response.status_code == 404:
                    logger.debug(f"Delete endpoint not found (404), trying modify approach...")
                else:
                    raise
            
            # Fallback: Use modify endpoint to set deleted_date
            from datetime import datetime, timezone
            endpoint = f'contacts/modify/{contact_id}'
            
            # Build request body to mark contact as deleted
            # Set deleted_date to current timestamp in ISO8601 format (Y-m-d\TH:i:sP)
            # Format: YYYY-mm-ddTHH:ii:ss+00:00 (ISO8601 with timezone)
            now = datetime.now(timezone.utc)
            # Format as ISO8601: YYYY-mm-ddTHH:MM:SS+00:00
            deleted_date = now.strftime('%Y-%m-%dT%H:%M:%S+00:00')
            
            request_data = {
                'deleted_date': deleted_date
            }
            
            request_body = self._build_request_body(request_data)
            
            response = requests.post(
                f'{self.base_url}{endpoint}',
                headers=self.headers,
                json=request_body
            )
            response.raise_for_status()
            result = response.json()
            
            # Handle response structure
            if isinstance(result, dict):
                if result.get('status') == 'ERROR':
                    error_msg = result.get('messages', {}).get('error', ['Unknown error'])
                    logger.error(f"Failed to delete contact {contact_id}: {error_msg}")
                    return False
                logger.info(f"Successfully deleted contact {contact_id} via modify endpoint")
                return True
            else:
                logger.info(f"Successfully deleted contact {contact_id}")
                return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error deleting contact {contact_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return False
    
    @retry_with_backoff()
    @rate_limit
    def list_tasks(self, project_id: Optional[int] = None, filters: Optional[Dict] = None) -> List[Dict]:
        """
        List all tasks in Scoro with optional filtering
        
        Args:
            project_id: Optional project ID to filter tasks by project
            filters: Optional dictionary of additional filters to apply
        
        Returns:
            List of task dictionaries
        """
        try:
            endpoint = 'tasks/list'
            all_tasks = []
            page = 1
            max_pages = 1000  # Safety limit to prevent infinite loops
            
            # Base request body format per Scoro API documentation
            base_request = {
                "lang": "eng",
                "company_account_id": self.company_name,
                "apiKey": self.api_key,
                "request": {}
            }
            
            # Add filters to request if provided
            request_filters = {}
            if project_id is not None:
                request_filters["project_id"] = project_id
            if filters:
                request_filters.update(filters)
            
            if request_filters:
                base_request["request"]["filters"] = request_filters
            
            request_formats = [
                # Format 1: Standard format per API documentation
                base_request,
                # Format 2: With basic_data flag
                {**base_request, "basic_data": "1"},
                # Format 3: With detailed_response flag
                {**base_request, "detailed_response": "1"},
            ]
            
            # Try to fetch all pages
            while page <= max_pages:
                last_error = None
                data = None
                success = False
                bookmark_id = None
                
                # Try POST with different request formats
                for request_body in request_formats:
                    if success:
                        break
                    
                    # Add pagination if we're on page > 1
                    if page > 1:
                        # Try with bookmark if we have one
                        if bookmark_id:
                            request_body = {**request_body, "bookmark": {"bookmark_id": str(bookmark_id)}}
                        # Or try with page/per_page parameters
                        else:
                            request_body = {**request_body, "page": str(page), "per_page": "100"}
                    
                    try:
                        logger.debug(f"Trying POST to endpoint '{endpoint}' page {page} with filters: {request_filters}")
                        headers_without_auth = {
                            'Content-Type': 'application/json'
                        }
                        response = requests.post(
                            f'{self.base_url}{endpoint}',
                            headers=headers_without_auth,
                            json=request_body
                        )
                        response.raise_for_status()
                        data = response.json()
                        
                        # Check if we got an error response
                        if isinstance(data, dict) and data.get('status') == 'ERROR':
                            error_msg = data.get('messages', {}).get('error', ['Unknown error'])
                            # If it's a pagination error (no more pages), break
                            if 'bookmark' in str(error_msg).lower() or 'page' in str(error_msg).lower():
                                logger.debug(f"No more pages available (page {page})")
                                break
                            last_error = f"Scoro API error: {error_msg}"
                            logger.debug(f"Format failed with error: {error_msg}, trying next format...")
                            continue
                        
                        # If we got here, the request was successful
                        success = True
                        break
                    except requests.exceptions.HTTPError as e:
                        if e.response is not None:
                            try:
                                error_data = e.response.json()
                                if isinstance(error_data, dict) and error_data.get('status') == 'ERROR':
                                    error_msg = error_data.get('messages', {}).get('error', ['Unknown error'])
                                    # If it's a pagination error, break
                                    if 'bookmark' in str(error_msg).lower() or 'page' in str(error_msg).lower() or page > 1:
                                        logger.debug(f"No more pages available (page {page})")
                                        break
                                    last_error = f"Scoro API error: {error_msg}"
                                    logger.debug(f"Format failed with HTTP error: {error_msg}, trying next format...")
                                    continue
                                else:
                                    # Non-error response, might be valid
                                    data = error_data
                                    success = True
                                    break
                            except Exception:
                                pass
                        last_error = str(e)
                        logger.debug(f"Format failed with exception: {e}, trying next format...")
                        continue
                
                if data is None:
                    if page == 1:
                        logger.warning("Could not list tasks from Scoro API")
                        return []
                    else:
                        # No more pages - API returned no data for this page
                        logger.debug(f"No data returned for page {page}, stopping pagination")
                        break
                
                # Handle different response structures
                page_tasks = []
                if isinstance(data, list):
                    page_tasks = data
                elif isinstance(data, dict):
                    if 'data' in data and isinstance(data['data'], list):
                        page_tasks = data['data']
                    elif 'tasks' in data and isinstance(data['tasks'], list):
                        page_tasks = data['tasks']
                    # Check for bookmark for next page
                    bookmark = data.get('bookmark') or data.get('request', {}).get('bookmark')
                    if bookmark:
                        if isinstance(bookmark, dict):
                            bookmark_id = bookmark.get('bookmark_id')
                        elif isinstance(bookmark, str):
                            bookmark_id = bookmark
                
                if not page_tasks:
                    # No more tasks
                    break
                
                all_tasks.extend(page_tasks)
                logger.debug(f"Retrieved {len(page_tasks)} tasks from page {page} (total: {len(all_tasks)})")
                
                # If we got fewer than 100 tasks, we've likely reached the end
                if len(page_tasks) < 100:
                    break
                
                # Continue to next page
                # Prefer bookmark if available, otherwise use page numbers
                if bookmark_id:
                    # Use bookmark for next page
                    page += 1
                    continue
                else:
                    # No bookmark, but continue with page numbers
                    # This ensures we fetch all pages even if API doesn't provide bookmarks
                    page += 1
                    continue
            
            logger.info(f"Retrieved {len(all_tasks)} total tasks from Scoro (across {page} page(s))")
            return all_tasks
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error listing Scoro tasks: {e}")
            return []
    
    @retry_with_backoff()
    @rate_limit
    def delete_task(self, task_id: int) -> bool:
        """
        Delete a task in Scoro
        
        Args:
            task_id: ID of the task to delete
        
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Try the delete endpoint (similar to timeEntries/delete)
            endpoint = f'tasks/delete/{task_id}'
            
            request_body = self._build_request_body({})
            
            try:
                response = requests.post(
                    f'{self.base_url}{endpoint}',
                    headers=self.headers,
                    json=request_body
                )
                response.raise_for_status()
                result = response.json()
                
                # Check if it was successful
                if isinstance(result, dict):
                    if result.get('status') == 'OK':
                        logger.info(f"Successfully deleted task {task_id} via delete endpoint")
                        return True
                    elif result.get('status') == 'ERROR':
                        # Delete endpoint might not exist, try modify approach
                        logger.debug(f"Delete endpoint returned error, trying modify approach...")
                    else:
                        logger.info(f"Successfully deleted task {task_id}")
                        return True
            except requests.exceptions.HTTPError as e:
                # If delete endpoint doesn't exist (404), try modify approach
                if e.response and e.response.status_code == 404:
                    logger.debug(f"Delete endpoint not found (404), trying modify approach...")
                else:
                    raise
            
            # Fallback: Use modify endpoint to set deleted_date
            from datetime import datetime, timezone
            endpoint = f'tasks/modify/{task_id}'
            
            # Build request body to mark task as deleted
            now = datetime.now(timezone.utc)
            deleted_date = now.strftime('%Y-%m-%dT%H:%M:%S+00:00')
            
            request_data = {
                'deleted_date': deleted_date
            }
            
            request_body = self._build_request_body(request_data)
            
            response = requests.post(
                f'{self.base_url}{endpoint}',
                headers=self.headers,
                json=request_body
            )
            response.raise_for_status()
            result = response.json()
            
            # Handle response structure
            if isinstance(result, dict):
                if result.get('status') == 'ERROR':
                    error_msg = result.get('messages', {}).get('error', ['Unknown error'])
                    logger.error(f"Failed to delete task {task_id}: {error_msg}")
                    return False
                logger.info(f"Successfully deleted task {task_id} via modify endpoint")
                return True
            else:
                logger.info(f"Successfully deleted task {task_id}")
                return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return False
    
    @retry_with_backoff()
    @rate_limit
    def delete_project(self, project_id: int) -> bool:
        """
        Delete a project in Scoro
        
        Args:
            project_id: ID of the project to delete
        
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Use the delete endpoint per Scoro API documentation
            endpoint = f'projects/delete/{project_id}'
            
            request_body = self._build_request_body({})
            
            response = requests.post(
                f'{self.base_url}{endpoint}',
                headers=self.headers,
                json=request_body
            )
            response.raise_for_status()
            result = response.json()
            
            # Handle response structure
            if isinstance(result, dict):
                if result.get('status') == 'OK':
                    logger.info(f"Successfully deleted project {project_id}")
                    return True
                elif result.get('status') == 'ERROR':
                    error_msg = result.get('messages', {}).get('error', ['Unknown error'])
                    logger.error(f"Failed to delete project {project_id}: {error_msg}")
                    return False
                else:
                    logger.info(f"Successfully deleted project {project_id}")
                    return True
            else:
                logger.info(f"Successfully deleted project {project_id}")
                return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error deleting project {project_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return False

