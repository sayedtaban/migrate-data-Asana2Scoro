"""
Scoro API client for interacting with Scoro API
"""
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
        
        Returns:
            List of company dictionaries
        """
        try:
            # Scoro API v2 requires POST to companies/list with specific request format
            # Similar to projects/list endpoint
            endpoint = 'companies/list'
            
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
                logger.warning("Could not list companies from Scoro API")
                return []
            
            # Handle different response structures
            if isinstance(data, list):
                companies = data
            elif isinstance(data, dict):
                if 'data' in data and isinstance(data['data'], list):
                    companies = data['data']
                elif 'companies' in data and isinstance(data['companies'], list):
                    companies = data['companies']
                else:
                    companies = []
            else:
                companies = []
            
            logger.info(f"Retrieved {len(companies)} companies from Scoro")
            return companies
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error listing Scoro companies: {e}")
            return []
    
    @retry_with_backoff()
    @rate_limit
    def find_company_by_name(self, company_name: str) -> Optional[Dict]:
        """
        Find a company by name in Scoro
        
        Args:
            company_name: Name of the company to find
        
        Returns:
            Company dictionary if found, None otherwise
        """
        try:
            companies = self.list_companies()
            company_name_lower = company_name.lower().strip()
            
            for company in companies:
                name = company.get('name', '') or company.get('company_name', '')
                if name and name.lower().strip() == company_name_lower:
                    company_id = company.get('id') or company.get('company_id') or company.get('client_id') or company.get('contact_id')
                    logger.info(f"Found existing company: {name} (ID: {company_id})")
                    return company
            
            logger.debug(f"Company not found: {company_name}")
            return None
        except Exception as e:
            logger.warning(f"Error finding company '{company_name}': {e}")
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

