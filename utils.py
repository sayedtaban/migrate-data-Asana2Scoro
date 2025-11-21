"""
Utility functions for rate limiting, retry logic, and logging
"""
import sys
import os
import logging
import time
from datetime import datetime
from typing import Callable
from functools import wraps

import requests
from asana.rest import ApiException

from config import RATE_LIMIT_DELAY, MAX_RETRIES, RETRY_DELAY, RETRY_BACKOFF

# Configure Windows console for UTF-8 encoding to handle special characters
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

# Create logs directory if it doesn't exist
logs_dir = 'logs'
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Configure logging with UTF-8 encoding to handle special characters
log_filename = os.path.join(logs_dir, f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def rate_limit(func: Callable) -> Callable:
    """Decorator to add rate limiting to API calls"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        time.sleep(RATE_LIMIT_DELAY)
        return func(*args, **kwargs)
    return wrapper


def retry_with_backoff(max_retries: int = MAX_RETRIES, delay: float = RETRY_DELAY, backoff: float = RETRY_BACKOFF):
    """
    Decorator for retrying function calls with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for exponential backoff
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (ApiException, requests.exceptions.RequestException) as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}")
                        raise
                    
                    # Check if error is retryable (5xx errors, rate limits, timeouts)
                    status = getattr(e, 'status', None) if hasattr(e, 'status') else None
                    if hasattr(e, 'response') and e.response is not None:
                        status = e.response.status_code
                    
                    if status and status in [429, 500, 502, 503, 504]:
                        logger.warning(f"Retryable error {status} in {func.__name__}, retrying in {current_delay}s (attempt {retries}/{max_retries})...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        # Non-retryable error, raise immediately
                        raise
                except Exception as e:
                    # Non-API exceptions, don't retry
                    raise
            
        return wrapper
    return decorator


def process_batch(items: list, batch_size: int = 50) -> list:
    """
    Split items into batches for processing
    
    Args:
        items: List of items to batch
        batch_size: Size of each batch
    
    Returns:
        List of batches
    """
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

