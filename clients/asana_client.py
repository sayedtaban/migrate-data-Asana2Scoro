"""
Asana API client for interacting with Asana API
"""
import os
from typing import Dict, List, Optional

import asana
from asana.rest import ApiException

from config import ENV_ASANA_ACCESS_TOKEN
from utils import logger, retry_with_backoff, rate_limit


class AsanaClient:
    """Handle Asana API interactions"""
    
    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize Asana client
        
        Args:
            access_token: Asana personal access token. If None, reads from ASANA_ACCESS_TOKEN env var
        """
        self.access_token = access_token or os.getenv(ENV_ASANA_ACCESS_TOKEN)
        if not self.access_token:
            raise ValueError("Asana access token not provided. Set ASANA_ACCESS_TOKEN env var.")
        
        # Validate token format (basic check - should not be empty or just whitespace)
        if not self.access_token.strip():
            raise ValueError("Asana access token is empty. Please set a valid ASANA_ACCESS_TOKEN in .env file.")
        
        # Log token status (without exposing the actual token)
        token_preview = f"{self.access_token[:4]}...{self.access_token[-4:]}" if len(self.access_token) > 8 else "***"
        logger.info(f"Loading Asana token: {token_preview} (length: {len(self.access_token)})")
        
        # Initialize Asana API client using Configuration and ApiClient
        self.configuration = asana.Configuration()
        self.configuration.access_token = self.access_token
        self.api_client = asana.ApiClient(self.configuration)
        
        # Initialize API instances
        self.projects_api = asana.ProjectsApi(self.api_client)
        self.tasks_api = asana.TasksApi(self.api_client)
        self.sections_api = asana.SectionsApi(self.api_client)
        
        logger.info("Asana client initialized")
    
    def test_connection(self) -> bool:
        """
        Test the Asana API connection by making a simple API call
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to get workspaces as a simple test
            workspaces_api = asana.WorkspacesApi(self.api_client)
            opts = {
                'opt_fields': 'gid,name'
            }
            workspaces = workspaces_api.get_workspaces(opts)
            workspaces_list = list(workspaces) if hasattr(workspaces, '__iter__') else workspaces
            logger.info(f"Connection test successful. Found {len(workspaces_list)} workspace(s).")
            return True
        except ApiException as e:
            status = e.status if hasattr(e, 'status') else 'Unknown'
            if status == 401:
                logger.error("Connection test failed: Authentication error (401)")
                return False
            else:
                logger.warning(f"Connection test returned status {status}: {e}")
                return False
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_project_by_name(self, project_name: str, workspace_gid: Optional[str] = None) -> Optional[Dict]:
        """
        Find a project by name in Asana
        
        Args:
            project_name: Name of the project to find
            workspace_gid: Optional workspace GID to limit search (can be string or int)
        
        Returns:
            Project dictionary if found, None otherwise
        """
        try:
            # Convert workspace_gid to string if provided as int
            if workspace_gid is not None:
                workspace_gid = str(workspace_gid)
            
            if not workspace_gid:
                # If no workspace specified, we need to get all workspaces first
                # For now, we'll search all projects (this might be slow for large workspaces)
                logger.warning("No workspace_gid provided. Searching all projects may be slow.")
            
            opts = {
                'limit': 100,
                'archived': False,
                'opt_fields': 'gid,name,created_at,modified_at,notes,public,default_view'
            }
            
            if workspace_gid:
                logger.info(f"Searching for project in workspace: {workspace_gid}")
                projects = self.projects_api.get_projects_for_workspace(workspace_gid, opts)
                logger.debug(f"projects: {projects}")
                logger.info(f"Retrieved {len(list(projects)) if hasattr(projects, '__iter__') else 'unknown'} projects from workspace")
            else:
                # Get all projects (requires iterating through workspaces)
                # For simplicity, we'll try to get projects from the first workspace
                # In production, you might want to specify workspace_gid
                workspaces_api = asana.WorkspacesApi(self.api_client)
                opts = {
                    'opt_fields': 'gid,name'
                }
                workspaces = workspaces_api.get_workspaces(opts)
                workspaces_list = list(workspaces) if hasattr(workspaces, '__iter__') else workspaces
                if not workspaces_list:
                    logger.error("No workspaces found")
                    return None
                
                # Search in all workspaces
                for workspace in workspaces_list:
                    try:
                        workspace_dict = workspace.to_dict() if hasattr(workspace, 'to_dict') else dict(workspace)
                        workspace_gid = workspace_dict.get('gid')
                        if not workspace_gid:
                            continue
                        
                        projects = self.projects_api.get_projects_for_workspace(workspace_gid, opts)
                        for project in projects:
                            project_dict = project.to_dict() if hasattr(project, 'to_dict') else dict(project)
                            if project_dict.get('name') == project_name:
                                logger.info(f"Found Asana project: {project_name} (GID: {project_dict['gid']})")
                                return project_dict
                    except ApiException:
                        continue
                
                logger.warning(f"Project '{project_name}' not found in Asana")
                return None
            
            # Search in the specified workspace
            logger.info(f"Searching through projects for: '{project_name}'...")
            project_count = 0
            for project in projects:
                project_count += 1
                project_dict = project.to_dict() if hasattr(project, 'to_dict') else dict(project)
                logger.debug(f"  Checking project {project_count}: {project_dict.get('name', 'Unknown')}")
                if project_dict.get('name') == project_name:
                    logger.info(f"✓ Found Asana project: {project_name} (GID: {project_dict['gid']})")
                    return project_dict
            logger.info(f"Searched through {project_count} projects, project '{project_name}' not found")
            
            logger.warning(f"Project '{project_name}' not found in Asana")
            return None
            
        except ApiException as e:
            # Provide cleaner error messages
            status = e.status if hasattr(e, 'status') else 'Unknown'
            error_body = e.body if hasattr(e, 'body') else str(e)
            
            if status == 401:
                error_msg = ("Authentication failed (401 Unauthorized). "
                           "Please verify your ASANA_ACCESS_TOKEN is valid and not expired. "
                           "You can create a new token at: https://app.asana.com/0/developer-console")
                logger.error(error_msg)
                logger.error(f"API Error Details: Status {status}")
                raise ValueError(error_msg) from e
            else:
                error_msg = f"API error searching for Asana project (Status {status}): {error_body}"
                logger.error(error_msg)
                raise
        except Exception as e:
            logger.error(f"Error searching for Asana project: {e}")
            raise
    
    def get_project_details(self, project_gid: str) -> Dict:
        """
        Get detailed information about a project
        
        Args:
            project_gid: Project GID
        
        Returns:
            Detailed project information
        """
        try:
            opts = {
                'opt_fields': 'gid,name,created_at,modified_at,notes,public,default_view,archived,color,completed,completed_at,due_date,due_on,start_on,current_status,custom_fields,members,owner,team,workspace'
            }
            project = self.projects_api.get_project(project_gid, opts)
            project_dict = project.to_dict() if hasattr(project, 'to_dict') else dict(project)
            logger.info(f"Retrieved details for project: {project_dict.get('name', 'Unknown')}")
            return project_dict
        except ApiException as e:
            status = e.status if hasattr(e, 'status') else 'Unknown'
            if status == 401:
                error_msg = "Authentication failed. Please check your ASANA_ACCESS_TOKEN."
                logger.error(error_msg)
                raise ValueError(error_msg) from e
            logger.error(f"API error retrieving project details (Status {status}): {e}")
            raise
        except Exception as e:
            logger.error(f"Error retrieving project details: {e}")
            raise
    
    @retry_with_backoff()
    @rate_limit
    def get_project_tasks(self, project_gid: str, include_subtasks: bool = True) -> List[Dict]:
        """
        Get all tasks for a project with comprehensive field extraction
        
        Args:
            project_gid: Project GID
            include_subtasks: Whether to include subtasks
        
        Returns:
            List of task dictionaries
        """
        try:
            # Enhanced field list to get all available task data
            opt_fields = [
                'gid', 'name', 'notes', 'html_notes', 'due_on', 'due_at', 'start_on', 'start_at',
                'assignee', 'assignee_status', 'completed', 'completed_at', 'created_at', 'modified_at',
                'custom_fields', 'parent', 'memberships', 'tags', 'followers', 'dependencies',
                'dependents', 'num_subtasks', 'num_likes', 'liked', 'resource_subtype',
                'workspace', 'projects', 'permalink_url'
            ]
            
            opts = {
                'limit': 100,
                'opt_fields': ','.join(opt_fields)
            }
            tasks = self.tasks_api.get_tasks_for_project(project_gid, opts)
            task_list = []
            for task in tasks:
                task_dict = task.to_dict() if hasattr(task, 'to_dict') else dict(task)
                task_list.append(task_dict)
            logger.info(f"Retrieved {len(task_list)} tasks for project {project_gid}")
            return task_list
        except ApiException as e:
            status = e.status if hasattr(e, 'status') else 'Unknown'
            if status == 401:
                error_msg = "Authentication failed. Please check your ASANA_ACCESS_TOKEN."
                logger.error(error_msg)
                raise ValueError(error_msg) from e
            logger.error(f"API error retrieving project tasks (Status {status}): {e}")
            raise
        except Exception as e:
            logger.error(f"Error retrieving project tasks: {e}")
            raise
    
    @retry_with_backoff()
    @rate_limit
    def get_task_details(self, task_gid: str) -> Dict:
        """
        Get detailed information about a task including subtasks, dependencies, attachments, and comments
        
        Args:
            task_gid: Task GID
        
        Returns:
            Detailed task information
        """
        try:
            # Comprehensive field list for detailed task information
            opt_fields = [
                'gid', 'name', 'notes', 'html_notes', 'due_on', 'due_at', 'start_on', 'start_at',
                'assignee', 'assignee_status', 'completed', 'completed_at', 'created_at', 'modified_at',
                'custom_fields', 'parent', 'memberships', 'tags', 'followers', 'dependencies',
                'dependents', 'num_subtasks', 'num_likes', 'liked', 'resource_subtype',
                'attachments', 'stories', 'subtasks', 'workspace', 'projects', 'permalink_url'
            ]
            
            opts = {
                'opt_fields': ','.join(opt_fields)
            }
            task = self.tasks_api.get_task(task_gid, opts)
            task_dict = task.to_dict() if hasattr(task, 'to_dict') else dict(task)
            return task_dict
        except ApiException as e:
            status = e.status if hasattr(e, 'status') else 'Unknown'
            if status == 401:
                error_msg = "Authentication failed. Please check your ASANA_ACCESS_TOKEN."
                logger.error(error_msg)
                raise ValueError(error_msg) from e
            logger.error(f"API error retrieving task details (Status {status}): {e}")
            raise
        except Exception as e:
            logger.error(f"Error retrieving task details: {e}")
            raise
    
    @retry_with_backoff()
    @rate_limit
    def get_subtasks(self, task_gid: str) -> List[Dict]:
        """
        Get all subtasks for a parent task
        
        Args:
            task_gid: Parent task GID
        
        Returns:
            List of subtask dictionaries
        """
        try:
            opts = {
                'limit': 100,
                'opt_fields': 'gid,name,notes,due_on,due_at,assignee,completed,created_at,modified_at,custom_fields,parent'
            }
            subtasks = self.tasks_api.get_subtasks_for_task(task_gid, opts)
            subtask_list = []
            for subtask in subtasks:
                subtask_dict = subtask.to_dict() if hasattr(subtask, 'to_dict') else dict(subtask)
                subtask_list.append(subtask_dict)
            logger.debug(f"Retrieved {len(subtask_list)} subtasks for task {task_gid}")
            return subtask_list
        except ApiException as e:
            status = e.status if hasattr(e, 'status') else 'Unknown'
            if status == 401:
                error_msg = "Authentication failed. Please check your ASANA_ACCESS_TOKEN."
                logger.error(error_msg)
                raise ValueError(error_msg) from e
            logger.warning(f"Could not retrieve subtasks for task {task_gid} (Status {status}): {e}")
            return []
        except Exception as e:
            logger.warning(f"Error retrieving subtasks for task {task_gid}: {e}")
            return []
    
    @retry_with_backoff()
    @rate_limit
    def get_task_stories(self, task_gid: str) -> List[Dict]:
        """
        Get all stories (comments) for a task
        
        Args:
            task_gid: Task GID
        
        Returns:
            List of story/comment dictionaries
        """
        try:
            stories_api = asana.StoriesApi(self.api_client)
            opts = {
                'limit': 100,
                'opt_fields': 'gid,created_at,created_by,text,type,resource_subtype'
            }
            stories = stories_api.get_stories_for_task(task_gid, opts)
            story_list = []
            for story in stories:
                story_dict = story.to_dict() if hasattr(story, 'to_dict') else dict(story)
                story_list.append(story_dict)
            logger.debug(f"Retrieved {len(story_list)} stories for task {task_gid}")
            return story_list
        except ApiException as e:
            status = e.status if hasattr(e, 'status') else 'Unknown'
            if status == 401:
                error_msg = "Authentication failed. Please check your ASANA_ACCESS_TOKEN."
                logger.error(error_msg)
                raise ValueError(error_msg) from e
            logger.warning(f"Could not retrieve stories for task {task_gid} (Status {status}): {e}")
            return []
        except Exception as e:
            logger.warning(f"Error retrieving stories for task {task_gid}: {e}")
            return []
    
    @retry_with_backoff()
    @rate_limit
    def get_task_attachments(self, task_gid: str) -> List[Dict]:
        """
        Get all attachments for a task
        
        Args:
            task_gid: Task GID
        
        Returns:
            List of attachment dictionaries
        """
        try:
            attachments_api = asana.AttachmentsApi(self.api_client)
            opts = {
                'limit': 100,
                'opt_fields': 'gid,name,created_at,download_url,host,parent,view_url,size'
            }
            attachments = attachments_api.get_attachments_for_object(task_gid, opts)
            attachment_list = []
            for attachment in attachments:
                attachment_dict = attachment.to_dict() if hasattr(attachment, 'to_dict') else dict(attachment)
                attachment_list.append(attachment_dict)
            logger.debug(f"Retrieved {len(attachment_list)} attachments for task {task_gid}")
            return attachment_list
        except ApiException as e:
            status = e.status if hasattr(e, 'status') else 'Unknown'
            if status == 401:
                error_msg = "Authentication failed. Please check your ASANA_ACCESS_TOKEN."
                logger.error(error_msg)
                raise ValueError(error_msg) from e
            logger.warning(f"Could not retrieve attachments for task {task_gid} (Status {status}): {e}")
            return []
        except Exception as e:
            logger.warning(f"Error retrieving attachments for task {task_gid}: {e}")
            return []
    
    @retry_with_backoff()
    @rate_limit
    def get_project_sections(self, project_gid: str) -> List[Dict]:
        """
        Get all sections (columns) for a project
        
        Args:
            project_gid: Project GID
        
        Returns:
            List of section dictionaries
        """
        try:
            opts = {
                'limit': 100,
                'opt_fields': 'gid,name,created_at'
            }
            sections = self.sections_api.get_sections_for_project(project_gid, opts)
            section_list = []
            for section in sections:
                section_dict = section.to_dict() if hasattr(section, 'to_dict') else dict(section)
                section_list.append(section_dict)
            logger.info(f"Retrieved {len(section_list)} sections for project {project_gid}")
            return section_list
        except ApiException as e:
            status = e.status if hasattr(e, 'status') else 'Unknown'
            if status == 401:
                error_msg = "Authentication failed. Please check your ASANA_ACCESS_TOKEN."
                logger.error(error_msg)
                raise ValueError(error_msg) from e
            logger.error(f"API error retrieving project sections (Status {status}): {e}")
            raise
        except Exception as e:
            logger.error(f"Error retrieving project sections: {e}")
            raise
    
    @retry_with_backoff()
    @rate_limit
    def get_project_milestones(self, project_gid: str) -> List[Dict]:
        """
        Get all milestones for a project
        
        Args:
            project_gid: Project GID
        
        Returns:
            List of milestone dictionaries
        """
        try:
            # Milestones in Asana are tasks with resource_subtype = 'milestone'
            # We'll filter tasks to find milestones
            opts = {
                'limit': 100,
                'opt_fields': 'gid,name,notes,due_on,due_at,completed,created_at,modified_at,resource_subtype'
            }
            tasks = self.tasks_api.get_tasks_for_project(project_gid, opts)
            milestones = []
            for task in tasks:
                task_dict = task.to_dict() if hasattr(task, 'to_dict') else dict(task)
                # Check if this is a milestone
                resource_subtype = task_dict.get('resource_subtype', '')
                if resource_subtype == 'milestone':
                    milestones.append(task_dict)
            logger.info(f"Retrieved {len(milestones)} milestones for project {project_gid}")
            return milestones
        except ApiException as e:
            status = e.status if hasattr(e, 'status') else 'Unknown'
            if status == 401:
                error_msg = "Authentication failed. Please check your ASANA_ACCESS_TOKEN."
                logger.error(error_msg)
                raise ValueError(error_msg) from e
            logger.warning(f"Could not retrieve milestones for project {project_gid} (Status {status}): {e}")
            return []
        except Exception as e:
            logger.warning(f"Error retrieving milestones for project {project_gid}: {e}")
            return []

