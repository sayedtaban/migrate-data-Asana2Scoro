"""
Task deduplication logic for handling tasks across multiple projects
"""
from typing import Dict, Any
from config import VALID_SCORO_USERS

# Global task tracker for deduplication across multiple projects
# Key: task_gid, Value: {'project_name': str, 'is_client_project': bool}
_seen_tasks: Dict[str, Dict[str, Any]] = {}


def is_client_project(project_name: str) -> bool:
    """
    Determine if a project is a client project or a team member project.
    
    Client projects are typically named after clients/companies.
    Team member projects are typically named after individuals (e.g., "Lena's project", "Austin's tasks").
    
    Args:
        project_name: Name of the project
        
    Returns:
        True if it appears to be a client project, False if it appears to be a team member project
    """
    if not project_name:
        return False
    
    project_name_lower = project_name.lower().strip()
    
    # Common patterns for team member projects
    team_member_indicators = [
        "'s project",
        "'s tasks",
        "'s workspace",
        " personal",
        " individual",
        " my ",
    ]
    
    # Check if project name contains team member indicators
    for indicator in team_member_indicators:
        if indicator in project_name_lower:
            return False
    
    # Check if project name matches known team member names (from VALID_SCORO_USERS)
    # If the project name is just a person's name, it's likely a team member project
    for user_name in VALID_SCORO_USERS:
        user_name_lower = user_name.lower()
        # Exact match or name with possessive
        if project_name_lower == user_name_lower or project_name_lower == f"{user_name_lower}'s":
            return False
        # Check if project name starts with a person's first name
        first_name = user_name.split()[0].lower() if ' ' in user_name else user_name.lower()
        if project_name_lower.startswith(first_name) and ("'s" in project_name_lower or " project" in project_name_lower):
            return False
    
    # Default to client project if no team member indicators found
    # Client projects are typically company names, client names, or other non-personal project names
    return True


def reset_task_tracker():
    """Reset the global task tracker. Call this at the start of a new migration batch."""
    global _seen_tasks
    _seen_tasks = {}


def get_deduplication_stats() -> Dict[str, Any]:
    """
    Get statistics about task deduplication.
    
    Returns:
        Dictionary with deduplication statistics:
        - total_tasks_seen: Total number of unique tasks seen
        - client_project_tasks: Number of tasks from client projects
        - team_member_project_tasks: Number of tasks from team member projects
        - tasks_by_project: Dictionary mapping project names to task counts
    """
    global _seen_tasks
    
    stats = {
        'total_tasks_seen': len(_seen_tasks),
        'client_project_tasks': 0,
        'team_member_project_tasks': 0,
        'tasks_by_project': {}
    }
    
    for task_gid, task_info in _seen_tasks.items():
        project_name = task_info.get('project_name', 'Unknown')
        is_client = task_info.get('is_client_project', False)
        
        if is_client:
            stats['client_project_tasks'] += 1
        else:
            stats['team_member_project_tasks'] += 1
        
        if project_name not in stats['tasks_by_project']:
            stats['tasks_by_project'][project_name] = 0
        stats['tasks_by_project'][project_name] += 1
    
    return stats


def get_seen_tasks() -> Dict[str, Dict[str, Any]]:
    """
    Get the current seen tasks tracker.
    
    Returns:
        Dictionary mapping task GIDs to task info
    """
    return _seen_tasks


def set_seen_tasks(tracker: Dict[str, Dict[str, Any]]):
    """
    Set the seen tasks tracker (for testing or custom tracking).
    
    Args:
        tracker: Dictionary mapping task GIDs to task info
    """
    global _seen_tasks
    _seen_tasks = tracker

