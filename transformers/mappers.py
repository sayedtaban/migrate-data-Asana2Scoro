"""
Mapping functions for transforming Asana fields to Scoro fields
"""
from typing import Optional
from config import VALID_SCORO_USERS, USER_MAPPING

# Category mapping from Asana to Scoro Activity Types
CATEGORY_MAPPING = {
    'Account Management': 'Project Management',
    'Blogs': 'SEO',
    'Brand Package': 'Branding',
    'Brochure': 'Brochure',
    'Client Management': 'Project Management',
    'Content & Creative': 'Graphic Design Support',
    'Contractor/Homeowner Brochure': 'Brochure',
    'Copywriter': 'Website - New',
    'CrewRecruiter': 'CrewRecruiter',
    'Dealer Brochure': 'Brochure',
    'Design - New Website': 'Website - New',
    'Email': 'Email',
    'Facebook Ads': 'Facebook Ads',
    'Google Ads': 'Google Ads',
    'Halstead': 'Halstead Marketing',
    'Internal Operations': 'Administrative - Internal',
    'Lead Magnet': 'Lead Magnet',
    'LinkedIn Ads': 'Linkedin Ads',
    'Marketing Collateral Package': 'Branding',
    'Meetings': 'Project Management',
    'Microsoft Ads': 'Microsoft Ads',
    'Offboarding, Pausing, & Ending Projects': 'Project Management',
    'OKRs': 'Administrative - Internal',
    'Onboarding': 'Onboarding',
    'Onboarding | Access': 'Onboarding',
    'Onboarding | After Client Kick Off Call': 'Onboarding',
    'Onboarding | Before Client Kick Off Call': 'Onboarding',
    'Onboarding | During Client Kick Off Call': 'Onboarding',
    'Onboarding | Lead Tracking & Review Building': 'Onboarding',
    'Other': 'Other',
    'Paid Advertising': 'Google Ads',
    'PM Status Update': 'Project Management',
    'SEO': 'SEO',
    'SEO Services': 'SEO',
    'Social Media': 'Social Posting',
    'Social Posting': 'Social Posting',
    'Special Projects': 'Other',
    'Videography': 'Videography',
    'Website - One Week Before Go Live': 'Website - New',
    'Website Core Pages': 'Website - New',
    'Website Design': 'Website - New',
    'Website Development': 'Website - New',
    'Website Final Approval': 'Website - New',
    'Website Full Build': 'Website - New',
    'Website Go Live': 'Website - New',
    'Website Homepage in Squarespace': 'Website - New',
    'Website Homepage Mockup': 'Website - New',
    'Website Strategy': 'Website - New',
    'Website Updates': 'Website - SEO',
}


def improve_misc_tracking(title: str) -> str:
    """Improve Misc tracking based on title analysis"""
    if not title:
        return 'Misc'
    
    title_lower = title.lower()
    
    if 'seo' in title_lower or 'keyword' in title_lower:
        if 'keyword' in title_lower or 'research' in title_lower:
            return 'SEO - Keyword Research'
        elif 'gmb' in title_lower or 'google my business' in title_lower:
            return 'SEO - Google My Business (GMB)'
        elif 'blog' in title_lower:
            return 'SEO - Blog Writing' if 'writ' in title_lower else 'SEO - Blogs Publishing'
        elif 'monthly' in title_lower:
            return 'SEO - Monthly'
        else:
            return 'SEO - General'
    elif 'meeting' in title_lower or 'call' in title_lower or 'kickoff' in title_lower:
        return 'Meetings'
    elif 'email' in title_lower:
        return 'Writing - Email'
    elif 'social' in title_lower:
        if 'schedul' in title_lower or 'post' in title_lower:
            return 'Social Scheduling'
        else:
            return 'Graphic Design - Social'
    elif 'facebook ad' in title_lower or 'fb ad' in title_lower:
        if 'boost' in title_lower:
            return 'Facebook Ads - Boosting'
        else:
            return 'Facebook Ads - Management'
    elif 'google ad' in title_lower or 'ppc' in title_lower:
        return 'Google Ads - Management'
    elif 'design' in title_lower or 'mockup' in title_lower:
        if 'homepage' in title_lower:
            return 'Design - Homepage Mockup'
        elif 'core page' in title_lower:
            return 'Design - Core Pages'
        elif 'full' in title_lower or 'build' in title_lower:
            return 'Design - Build Out Site'
        else:
            return 'Design - New Website'
    elif 'squarespace' in title_lower or ('homepage' in title_lower and 'design' not in title_lower):
        return 'Design - Homepage in Squarespace'
    elif 'go live' in title_lower or 'launch' in title_lower or 'domain' in title_lower:
        return 'Design - Domain/Go Live'
    elif 'writ' in title_lower or 'copy' in title_lower or 'content' in title_lower:
        if 'core page' in title_lower:
            return 'Writing - Core Pages'
        elif 'homepage' in title_lower:
            return 'Writing - New Site Homepage Copy'
        elif 'full' in title_lower:
            return 'Writing - New Site Full Copy'
        elif 'email' in title_lower:
            return 'Writing - Email'
        elif 'social' in title_lower:
            return 'Writing - Social'
        elif 'seo' in title_lower or 'blog' in title_lower:
            return 'Writing - SEO'
        else:
            return 'Writing - Misc'
    elif 'edit' in title_lower:
        if 'core page' in title_lower:
            return 'Editing - Core Pages'
        elif 'homepage' in title_lower:
            return 'Editing - Homepage Client Revisions'
        elif 'full' in title_lower:
            return 'Editing - Full Site Client Revisions'
        elif 'blog' in title_lower:
            return 'Editing - Blog Posts'
        else:
            return 'Editing - Misc'
    elif 'video' in title_lower:
        if 'edit' in title_lower:
            return 'Video Editing - Social Posting'
        else:
            return 'Editing - Video'
    elif 'report' in title_lower or 'reporting' in title_lower:
        return 'Reporting'
    elif 'status' in title_lower or 'follow up' in title_lower or 'check in' in title_lower or 'update' in title_lower or 'confirm' in title_lower:
        return 'Writing - Client Communications (Slack, Calls, Meetings)'
    elif 'brochure' in title_lower:
        return 'Graphic Design - Brochure'
    elif 'lead magnet' in title_lower:
        return 'Lead Magnet'
    elif 'training' in title_lower or 'onboard' in title_lower:
        return 'Training'
    elif 'integrat' in title_lower or 'setup' in title_lower or 'install' in title_lower or 'access via' in title_lower:
        return 'Integrations'
    elif 'compile' in title_lower:
        if 'full site' in title_lower:
            return 'Editing - Full Site Client Revisions'
        elif 'core page' in title_lower:
            return 'Editing - Core Pages'
        else:
            return 'Editing - Misc'
    
    return 'Misc'


def smart_map_phase(title: str, activity_type: Optional[str], current_section: Optional[str]) -> str:
    """Map task to project phase based on title, activity, and section"""
    if current_section and current_section.strip():
        return current_section.strip()
    
    title_lower = (title or '').lower()
    activity_lower = (activity_type or '').lower()
    
    if 'seo' in title_lower or 'seo' in activity_lower:
        return 'SEO'
    elif 'email' in title_lower or 'email' in activity_lower:
        return 'Email'
    elif 'facebook' in title_lower or 'facebook' in activity_lower:
        return 'Facebook Ads'
    elif 'google ad' in title_lower or 'google ads' in activity_lower:
        return 'Google Ads'
    elif 'video' in title_lower or 'videography' in activity_lower:
        return 'Videography'
    elif 'design' in title_lower or 'mockup' in title_lower:
        return 'Website Design'
    elif 'homepage' in title_lower or 'homepage' in activity_lower:
        return 'Website Homepage'
    elif 'go live' in title_lower or 'launch' in title_lower or 'go live' in activity_lower:
        return 'Website Go Live'
    elif 'update' in title_lower or 'updates' in activity_lower:
        return 'Website Updates'
    elif 'account management' in title_lower or 'account management' in activity_lower:
        return 'Account Management'
    elif 'status' in title_lower or 'follow up' in title_lower:
        return 'Client Status'
    
    return 'Account Management'


def smart_map_activity_and_tracking(title: str, current_activity: Optional[str], section: Optional[str]) -> str:
    """
    Map task to activity type (category) using the category mapping.
    
    If category (current_activity) is blank, always map to 'Other'.
    Do NOT attempt to infer category from title, section, or assignee.
    
    Note: Time Task Tracking field has been eliminated - only Activity Types are used.
    """
    # Normalize the category value
    activity = current_activity.strip() if current_activity and current_activity.strip() else None
    
    # If category is blank, always map to 'Other' - do not infer from title or section
    if not activity:
        return 'Other'
    
    # Map the category using the mapping dictionary
    # Use exact match first, then case-insensitive match
    if activity in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[activity]
    
    # Try case-insensitive match
    activity_lower = activity.lower()
    for asana_category, scoro_activity in CATEGORY_MAPPING.items():
        if asana_category.lower() == activity_lower:
            return scoro_activity
    
    # If no mapping found, return 'Other'
    return 'Other'


def validate_user(user_name: Optional[str], default_to_tom: bool = False) -> str:
    """Validate and map user name to valid Scoro user"""
    if not user_name or user_name.strip() == '':
        return 'Tom Sanpakit' if default_to_tom else ''
    
    user_name = user_name.strip()
    
    # Check for short name mapping
    for short, full in USER_MAPPING.items():
        if short in user_name:
            user_name = full
            break
    
    if user_name in VALID_SCORO_USERS:
        return user_name
    else:
        return 'Tom Sanpakit' if default_to_tom else ''

