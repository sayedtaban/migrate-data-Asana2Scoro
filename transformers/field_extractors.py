"""
Field extraction utilities for Asana tasks
"""
from typing import Dict, List, Optional
from utils import logger


def extract_custom_field_value(task: Dict, field_name: str) -> Optional[str]:
    """Extract value from Asana custom fields"""
    custom_fields = task.get('custom_fields', [])
    if not custom_fields:
        return None
    
    for field in custom_fields:
        if isinstance(field, dict):
            field_name_lower = field.get('name', '').lower()
            if field_name.lower() in field_name_lower:
                # Handle different field types
                if 'text_value' in field:
                    value = field.get('text_value')
                    return str(value).strip() if value is not None and str(value).strip() else None
                elif 'enum_value' in field and field['enum_value']:
                    enum_val = field['enum_value']
                    if isinstance(enum_val, dict):
                        return enum_val.get('name')
                    elif hasattr(enum_val, 'name'):
                        return enum_val.name
                    else:
                        return str(enum_val) if enum_val else None
                elif 'number_value' in field:
                    value = field.get('number_value')
                    return str(value) if value is not None else None
                elif 'date_value' in field and field['date_value']:
                    date_val = field['date_value']
                    if isinstance(date_val, dict):
                        return date_val.get('date')
                    elif hasattr(date_val, 'date'):
                        return date_val.date
                    else:
                        return str(date_val) if date_val else None
        elif hasattr(field, 'name') and field_name.lower() in field.name.lower():
            # Handle object with attributes
            if hasattr(field, 'text_value'):
                return field.text_value
            elif hasattr(field, 'enum_value') and field.enum_value:
                return field.enum_value.name if hasattr(field.enum_value, 'name') else str(field.enum_value)
    
    return None


def extract_tags(task: Dict) -> List[str]:
    """Extract tags from Asana task"""
    tags = task.get('tags', [])
    if not tags:
        return []
    
    tag_list = []
    for tag in tags:
        if isinstance(tag, dict):
            tag_name = tag.get('name', '')
            if tag_name:
                tag_list.append(tag_name)
        elif hasattr(tag, 'name'):
            tag_list.append(tag.name)
    
    return tag_list


def extract_priority(task: Dict, title: str) -> str:
    """
    Extract or infer priority from task data
    
    Priority mapping:
    - High: Tasks with "urgent", "asap", "high priority" in title or custom fields
    - Medium: Default for most tasks
    - Low: Tasks with "low priority" or "nice to have" indicators
    """
    # Check custom fields first
    priority_field = extract_custom_field_value(task, 'Priority') or extract_custom_field_value(task, 'priority')
    if priority_field:
        priority_lower = str(priority_field).lower()
        if 'high' in priority_lower or 'urgent' in priority_lower:
            return 'High'
        elif 'low' in priority_lower:
            return 'Low'
        elif 'medium' in priority_lower or 'normal' in priority_lower:
            return 'Medium'
    
    # Infer from title
    title_lower = (title or '').lower()
    if any(word in title_lower for word in ['urgent', 'asap', 'critical', 'important', 'high priority']):
        return 'High'
    elif any(word in title_lower for word in ['low priority', 'nice to have', 'optional', 'backlog']):
        return 'Low'
    
    # Default to Medium
    return 'Medium'


def format_comments_for_description(stories: List[Dict]) -> str:
    """Format task stories/comments into a readable description format"""
    if not stories:
        return ''
    
    comments = []
    for story in stories:
        if isinstance(story, dict):
            story_type = story.get('type', '')
            if story_type == 'comment':
                text = story.get('text', '')
                created_by = story.get('created_by', {})
                if isinstance(created_by, dict):
                    author = created_by.get('name', 'Unknown')
                elif hasattr(created_by, 'name'):
                    author = created_by.name
                else:
                    author = 'Unknown'
                
                created_at = story.get('created_at', '')
                if text:
                    comments.append(f"[{author} - {created_at}]: {text}")
        elif hasattr(story, 'type') and story.type == 'comment':
            text = getattr(story, 'text', '')
            if text:
                comments.append(text)
    
    return '\n\n'.join(comments) if comments else ''

