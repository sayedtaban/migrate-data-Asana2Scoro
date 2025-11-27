#!/usr/bin/env python3
"""
Script to check current Scoro API rate limit status
Displays remaining requests, limits, and reset times
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional

import requests

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, will use system environment variables
    pass

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ENV_SCORO_API_KEY, ENV_SCORO_COMPANY_NAME


def format_time_remaining(seconds: Optional[int]) -> str:
    """Format seconds into a human-readable time string"""
    if seconds is None:
        return "N/A"
    
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def get_rate_limit_status() -> Dict:
    """
    Make a simple API call to Scoro and extract rate limit headers
    
    Returns:
        Dictionary containing rate limit information
    """
    api_key = os.getenv(ENV_SCORO_API_KEY)
    company_name = os.getenv(ENV_SCORO_COMPANY_NAME)
    
    if not api_key:
        raise ValueError("Scoro API key not provided. Set SCORO_API_KEY env var.")
    if not company_name:
        raise ValueError("Scoro company name not provided. Set SCORO_COMPANY_NAME env var.")
    
    # Clean company name
    company_clean = str(company_name).strip()
    if company_clean.startswith('https://'):
        company_clean = company_clean[8:]
    elif company_clean.startswith('http://'):
        company_clean = company_clean[7:]
    if '.scoro.com' in company_clean:
        company_clean = company_clean.split('.scoro.com')[0]
    company_clean = company_clean.split('/')[0]
    
    base_url = f"https://{company_clean}.scoro.com/api/v2/"
    endpoint = 'projects/list'
    
    # Build request body
    request_body = {
        "lang": "eng",
        "company_account_id": company_clean,
        "apiKey": api_key,
        "request": {},
        "basic_data": "1"  # Use basic_data to minimize response size
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        print(f"Making API call to {base_url}{endpoint}...")
        response = requests.post(
            f'{base_url}{endpoint}',
            headers=headers,
            json=request_body
        )
        
        # Extract rate limit headers
        rate_limit_info = {
            'status_code': response.status_code,
            '2_second_window': {
                'limit': response.headers.get('x-ratelimit-limit'),
                'remaining': response.headers.get('x-ratelimit-remaining'),
                'reset_in_seconds': response.headers.get('x-ratelimit-reset'),
            },
            'daily_limit': {
                'limit': response.headers.get('x-daily-requests-limit'),
                'remaining': response.headers.get('x-daily-requests-remaining'),
                'reset_in_seconds': response.headers.get('x-daily-requests-reset'),
            },
            'all_headers': dict(response.headers)  # Store all headers for debugging
        }
        
        # Try to parse response if it's an error
        if response.status_code == 429:
            try:
                error_data = response.json()
                rate_limit_info['error'] = error_data
            except:
                rate_limit_info['error'] = "Could not parse error response"
        
        return rate_limit_info
        
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        raise


def display_rate_limit_status(info: Dict):
    """Display rate limit information in a readable format"""
    print("\n" + "="*70)
    print("SCORO API RATE LIMIT STATUS")
    print("="*70)
    
    # Status code
    status_code = info.get('status_code')
    if status_code == 429:
        print(f"\n⚠️  STATUS: HTTP {status_code} - TOO MANY REQUESTS (Rate Limited)")
        if 'error' in info:
            print(f"   Error: {info['error']}")
    elif status_code == 200:
        print(f"\n✅ STATUS: HTTP {status_code} - OK")
    else:
        print(f"\n⚠️  STATUS: HTTP {status_code}")
    
    # 2-second window limits
    print("\n" + "-"*70)
    print("2-SECOND WINDOW LIMITS")
    print("-"*70)
    window = info.get('2_second_window', {})
    limit = window.get('limit')
    remaining = window.get('remaining')
    reset = window.get('reset_in_seconds')
    
    if limit and remaining:
        limit = int(limit)
        remaining = int(remaining)
        used = limit - remaining
        percentage = (remaining / limit * 100) if limit > 0 else 0
        
        print(f"  Limit:        {limit} requests per 2 seconds")
        print(f"  Remaining:    {remaining} requests")
        print(f"  Used:         {used} requests ({100 - percentage:.1f}%)")
        
        if reset:
            reset_seconds = int(reset)
            print(f"  Reset in:     {format_time_remaining(reset_seconds)}")
            
            # Calculate reset time
            reset_time = datetime.now() + timedelta(seconds=reset_seconds)
            print(f"  Reset at:     {reset_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Warning if low
        if remaining < limit * 0.1:  # Less than 10% remaining
            print(f"  ⚠️  WARNING: Low remaining requests! ({remaining}/{limit})")
        elif remaining == 0:
            print(f"  🚨 CRITICAL: No requests remaining! Rate limited!")
    else:
        print("  ⚠️  Rate limit headers not found in response")
        if limit:
            print(f"  Limit: {limit}")
        if remaining:
            print(f"  Remaining: {remaining}")
        if reset:
            print(f"  Reset in: {format_time_remaining(int(reset))}")
    
    # Daily limits
    print("\n" + "-"*70)
    print("DAILY LIMITS")
    print("-"*70)
    daily = info.get('daily_limit', {})
    daily_limit = daily.get('limit')
    daily_remaining = daily.get('remaining')
    daily_reset = daily.get('reset_in_seconds')
    
    if daily_limit and daily_remaining:
        daily_limit = int(daily_limit)
        daily_remaining = int(daily_remaining)
        daily_used = daily_limit - daily_remaining
        daily_percentage = (daily_remaining / daily_limit * 100) if daily_limit > 0 else 0
        
        print(f"  Limit:        {daily_limit:,} requests per day")
        print(f"  Remaining:    {daily_remaining:,} requests")
        print(f"  Used:         {daily_used:,} requests ({100 - daily_percentage:.1f}%)")
        
        if daily_reset:
            daily_reset_seconds = int(daily_reset)
            print(f"  Reset in:     {format_time_remaining(daily_reset_seconds)}")
            
            # Calculate reset time (midnight UTC)
            reset_time = datetime.now() + timedelta(seconds=daily_reset_seconds)
            print(f"  Reset at:     {reset_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        # Warning if low
        if daily_remaining < daily_limit * 0.1:  # Less than 10% remaining
            print(f"  ⚠️  WARNING: Low daily requests remaining! ({daily_remaining:,}/{daily_limit:,})")
        elif daily_remaining == 0:
            print(f"  🚨 CRITICAL: No daily requests remaining! Rate limited!")
    else:
        print("  ⚠️  Daily limit headers not found in response")
        if daily_limit:
            print(f"  Limit: {daily_limit:,}")
        if daily_remaining:
            print(f"  Remaining: {daily_remaining:,}")
        if daily_reset:
            print(f"  Reset in: {format_time_remaining(int(daily_reset))}")
    
    print("\n" + "="*70)
    print(f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")


def main():
    """Main function"""
    try:
        print("Checking Scoro API rate limit status...")
        rate_limit_info = get_rate_limit_status()
        display_rate_limit_status(rate_limit_info)
        
        # Exit with error code if rate limited
        if rate_limit_info.get('status_code') == 429:
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
