#!/usr/bin/env python3
"""
Test script to transform raw comment dataset with URL transformation algorithm
"""
import sys
import os
import html
import re
from typing import Dict, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from url_name_transformation_dataset import raw_dataset

# Mock ScoroClient for testing
class MockScoroClient:
    """Mock ScoroClient that simulates user lookup"""
    
    # Mock user database - mapping names to user objects
    # Based on common names from the config
    MOCK_USERS = {
        'Ellie Troughton': {'id': 21, 'firstname': 'Ellie', 'lastname': 'Troughton', 'full_name': 'Ellie Troughton'},
        'Tom Sanpakit': {'id': 1, 'firstname': 'Tom', 'lastname': 'Sanpakit', 'full_name': 'Tom Sanpakit'},
        'Andrea Pejoska': {'id': 2, 'firstname': 'Andrea', 'lastname': 'Pejoska', 'full_name': 'Andrea Pejoska'},
        'Dani Cervantes': {'id': 3, 'firstname': 'Dani', 'lastname': 'Cervantes', 'full_name': 'Dani Cervantes'},
        'Tena': {'id': 4, 'firstname': 'Tena', 'lastname': '', 'full_name': 'Tena'},
        # Add more as needed - these are examples
    }
    
    def find_user_by_name(self, user_name: str) -> Optional[Dict]:
        """Mock find_user_by_name - tries exact match and partial match"""
        user_name_lower = user_name.lower().strip()
        
        # Try exact match first
        for name, user in self.MOCK_USERS.items():
            if name.lower() == user_name_lower:
                return user
        
        # Try partial match
        for name, user in self.MOCK_USERS.items():
            if user_name_lower in name.lower() or name.lower() in user_name_lower:
                return user
        
        return None


def replace_asana_profile_urls_with_scoro_mentions(
    comment_text: str,
    scoro_client,
    asana_data: Optional[Dict] = None
) -> str:
    """
    Replace Asana profile URLs in comment text with Scoro user mention HTML.
    (Copy of the actual function for testing)
    """
    if not comment_text:
        return comment_text
    
    # Pattern to match Asana profile URLs: https://app.asana.com/0/profile/{GID}
    asana_profile_pattern = r'https://app\.asana\.com/0/profile/(\d+)'
    
    # Check if there are any URLs to replace
    urls_found = re.findall(asana_profile_pattern, comment_text)
    if not urls_found:
        return comment_text
    
    def replace_url(match):
        """Replace a single Asana profile URL with Scoro user mention"""
        gid = match.group(1)
        url = match.group(0)
        
        # Try to get user name from asana_data users map
        user_name = None
        if asana_data:
            users_map = asana_data.get('users', {})
            
            # Try to find user by GID (try both string and as-is)
            user_details = None
            if gid in users_map:
                user_details = users_map[gid]
            else:
                # GID might be stored with a different type, try to find by value
                for key, value in users_map.items():
                    if str(key) == str(gid):
                        user_details = value
                        break
            
            if user_details:
                user_name = user_details.get('name', '')
        
        # If we don't have a user name, we can't create a proper mention
        if not user_name:
            return url
        
        # Find the Scoro user by name
        scoro_user = scoro_client.find_user_by_name(user_name)
        if not scoro_user:
            return url
        
        user_id = scoro_user.get('id')
        if not user_id:
            return url
        
        # Get first and last name from Scoro user
        firstname = scoro_user.get('firstname', '').strip()
        lastname = scoro_user.get('lastname', '').strip()
        full_name = scoro_user.get('full_name', '').strip() or f"{firstname} {lastname}".strip()
        
        # If we don't have first/last name, try to split full_name
        if not firstname or not lastname:
            name_parts = full_name.split(maxsplit=1)
            if len(name_parts) >= 2:
                firstname = name_parts[0]
                lastname = name_parts[1]
            elif len(name_parts) == 1:
                firstname = name_parts[0]
                lastname = ''
            else:
                firstname = full_name
                lastname = ''
        
        # Build Scoro user mention HTML
        full_name_escaped = html.escape(full_name)
        firstname_escaped = html.escape(firstname)
        lastname_escaped = html.escape(lastname) if lastname else ''
        
        mention_html = (
            f'<span title="{full_name_escaped}" class="mceNonEditable js-tinymce-user tinymce-user user-{user_id}">'
            f'@<span class="mceNonEditable">{firstname_escaped}</span>'
        )
        if lastname:
            mention_html += f' <span class="mceNonEditable">{lastname_escaped}</span>'
        mention_html += '</span>'
        
        return mention_html
    
    # Replace all Asana profile URLs in the comment text
    result = re.sub(asana_profile_pattern, replace_url, comment_text)
    
    # Wrap the comment in <p> tags if it's not already wrapped
    result = result.strip()
    if result:
        if not (result.startswith('<p>') and result.endswith('</p>')):
            result = f'<p>{result}</p>'
    
    return result


def main():
    """Main test function"""
    # Create mock asana_data with users map
    # GID -> user details mapping
    # Note: These are example mappings - in real scenario, these would come from Asana export
    asana_data = {
        'users': {
            '1205507145644227': {'name': 'Ellie Troughton', 'email': 'ellie@example.com'},
            '1208799271721028': {'name': 'Tom Sanpakit', 'email': 'tom@example.com'},
            '1206729612623556': {'name': 'Ellie Troughton', 'email': 'ellie@example.com'},
            '1208531756730727': {'name': 'Andrea Pejoska', 'email': 'andrea@example.com'},
            '1209264874946823': {'name': 'Dani Cervantes', 'email': 'dani@example.com'},
            '1205337487077774': {'name': 'Tena', 'email': 'tena@example.com'},
        }
    }
    
    # Create mock Scoro client
    scoro_client = MockScoroClient()
    
    print("=" * 80)
    print("URL TRANSFORMATION TEST RESULTS")
    print("=" * 80)
    print()
    
    for i, raw_comment in enumerate(raw_dataset, 1):
        print(f"Test Case {i}:")
        print("-" * 80)
        print("ORIGINAL:")
        try:
            print(raw_comment)
        except UnicodeEncodeError:
            # Handle Unicode encoding issues
            print(raw_comment.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
        print()
        
        # Transform the comment
        transformed = replace_asana_profile_urls_with_scoro_mentions(
            raw_comment,
            scoro_client,
            asana_data
        )
        
        print("TRANSFORMED:")
        try:
            print(transformed)
        except UnicodeEncodeError:
            print(transformed.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
        print()
        
        # Show visible text (what user would see)
        visible_text = re.sub(r'<[^>]+>', '', transformed)
        print("VISIBLE TEXT (HTML stripped):")
        try:
            print(visible_text)
        except UnicodeEncodeError:
            print(visible_text.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
        print()
        print("=" * 80)
        print()


if __name__ == "__main__":
    main()

