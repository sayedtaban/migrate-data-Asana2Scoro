"""
Configuration and constants for Asana to Scoro migration
"""
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Rate limiting configuration
# OPTIMIZATION: Reduce RATE_LIMIT_DELAY if you're not hitting API rate limits
# - 0.1s (100ms) = safe default, ~10 calls/second
# - 0.05s (50ms) = faster, ~20 calls/second (use if API allows)
# - 0.2s (200ms) = slower, ~5 calls/second (use if getting 429 errors)
RATE_LIMIT_DELAY = 0.05  # Delay between API calls in seconds (100ms)
MAX_RETRIES = 3  # Maximum number of retries for failed API calls
RETRY_DELAY = 1  # Initial delay between retries in seconds
RETRY_BACKOFF = 2  # Exponential backoff multiplier

# Batch processing configuration
# OPTIMIZATION: Larger batch sizes can improve throughput, but use more memory
# - 50 = balanced default
# - 100 = faster for large migrations (uses more memory)
# - 25 = safer for limited memory or slower networks
DEFAULT_BATCH_SIZE = 100

# Parallel processing configuration
# OPTIMIZATION: More workers = faster processing, but more API load
# - 5-10 = safe default, respects rate limits
# - 10-20 = faster, use if API allows higher throughput
# - 20+ = aggressive, may hit rate limits (429 errors)
# Set to None to use default (min(32, os.cpu_count() + 4))
MAX_WORKERS = 10  # Number of parallel workers for concurrent API calls

# Test mode configuration - limit number of tasks to migrate (set to None to migrate all tasks)
TEST_MODE_MAX_TASKS = None  # Set to None for PRODUCTION - migrate all tasks

# Logging configuration
# Console log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
CONSOLE_LOG_LEVEL = logging.WARNING  # Log level for console output


# Projects to migrate
# Option 1: Use project GIDs (faster, no search needed)
PROJECT_GIDS = [
    # Add more project GIDs here
    # "1207816263671761",  # Van Zeeland Nursery & Landscape - done1
    # "1209020289079877",  # Exscape (VIP) progress
    # "1201994636901967",  # BTS (VIP) 1034
    "1211389004379875",  # Ethoscapes [VIP] - done1
    # "1209371228065321",  # Heritage Landscapes (VIP)
]

Backup_Scoro_Project_ID = [
  "150"
]

# Option 2: Use project names (will search for projects by name)
PROJECT_NAMES = [
    # "Van Zeeland Nursery & Landscape",  # Example project 1
    # "Another Project Name",  # Example project 2
    # Add more project names here
]

# Workspace GID (required for Asana API)
WORKSPACE_GID = "10447183158961"

# Date cutoff for task filtering
CUTOFF_DATE = datetime(2001, 7, 1)  # Naive datetime for comparison

# Valid Scoro users and user mapping
VALID_SCORO_USERS = {
    'Austin Koziol', 'Bethany Aeckersberg', 'Cait George', 'Tom Sanpakit',
    'Andrea Pejoska', 'Anna Halstead', 'Debbie Hoffman', 'Elizabeth Wasserman',
    'Kelsey Blomquist-Wright', 'Lauren Cullnan', 'Matej Robar', 'Polina Kroytor',
    'Taryn Himmelright', 'Tiffney Ma', 'Tracy Hart',  # <-- Fix here!
    'Christine Holz', 'Corey Halstead', 'Dani Cervantes', 'Devon Stank', 'Elizabeth Wood',
    'Ellie Troughton', 'Giorgi Goguadze', 'Jim McGrorry', 'Katya Pankov',
    'Lena Lebid', 'Lindsey Cartwright', 'Martina Willis', 'Matteo Banfo',
    'Mylessia Tkacs', 'Olivia Mello', 'Sayed Taban', 'Fitore Maxhuni',
    'Jane Numbers', 'John McDunn', 'Kevin Harris'
}

USER_MAPPING = {
    'Matej': 'Matej Robar', 'Ellie': 'Ellie Troughton', 'Tracy': 'Tracy Hart',
    'Austin': 'Austin Koziol', 'Bethany': 'Bethany Aeckersberg',
    'Anna': 'Anna Halstead', 'Debbie': 'Debbie Hoffman', 'Lauren': 'Lauren Cullnan',
    'Andrea': 'Andrea Pejoska', 'Dani': 'Dani Cervantes', 'Lena': 'Lena Lebid',
    'Olivia': 'Olivia Mello', 'Giorgi': 'Giorgi Goguadze', 'Martina': 'Martina Willis',
    'Matteo': 'Matteo Banfo', 'Mylessia': 'Mylessia Tkacs', 'Christine': 'Christine Holz',
    'Kelsey': 'Kelsey Blomquist-Wright', 'Cait': 'Cait George', 'Tom': 'Tom Sanpakit', 
    'Polina': 'Polina Kroytor', 'Taryn': 'Taryn Himmelright', 'Tiffney': 'Tiffney Ma', 
    'Corey': 'Corey Halstead', 'Devon': 'Devon Stank', 'Jim': 'Jim McGrorry', 'Katya': 'Katya Pankov',
    'Lindsey': 'Lindsey Cartwright', 'Sophia': 'Sophia Sanpakit', 'Giuseppe': 'Giuseppe Sanpakit',
    'Marie': 'Marie Sanpakit', 'Rachel': 'Rachel Sanpakit'
}

# Environment variable names
ENV_ASANA_ACCESS_TOKEN = 'ASANA_ACCESS_TOKEN'
ENV_SCORO_API_KEY = 'SCORO_API_KEY'
ENV_SCORO_COMPANY_NAME = 'SCORO_COMPANY_NAME'


# Migration mode: use 'gids' to migrate by GID list, 'names' to migrate by name list
MIGRATION_MODE = 'gids'  # Options: 'gids' or 'names'

PROFILE_USERNAME_MAPPING = [
  {
    "name": "Anna Halstead",
    "asana_url": "https://app.asana.com/0/profile/10447184036603"
  },
  {
    "name": "Andrea Pejoska",
    "asana_url": "https://app.asana.com/0/profile/1206867781400650"
  },
  {
    "name": "Steven Johnson",
    "asana_url": "https://app.asana.com/0/profile/1207635308997107"
  },
  {
    "name": "Polina Kroytor",
    "asana_url": "https://app.asana.com/0/profile/1209094057469108"
  },
  {
    "name": "ol@halsteadmedia.com",
    "asana_url": "https://app.asana.com/0/profile/1211806426074842"
  },
  {
    "name": "Olivia Mello",
    "asana_url": "https://app.asana.com/0/profile/1202721628575576"
  },
  {
    "name": "Matteo Banfo",
    "asana_url": "https://app.asana.com/0/profile/1208917064861757"
  },
  {
    "name": "Martina Willis",
    "asana_url": "https://app.asana.com/0/profile/1208531756730727"
  },
  {
    "name": "Mylessia Tkacs",
    "asana_url": "https://app.asana.com/0/profile/1207404021328999"
  },
  {
    "name": "Matej",
    "asana_url": "https://app.asana.com/0/profile/541101205537979"
  },
  {
    "name": "Lena Lebid",
    "asana_url": "https://app.asana.com/0/profile/1206488509834213"
  },
  {
    "name": "Kelsey Blomquist-Wright",
    "asana_url": "https://app.asana.com/0/profile/1205368383443301"
  },
  {
    "name": "Katya Pankov",
    "asana_url": "https://app.asana.com/0/profile/1210679736012806"
  },
  {
    "name": "",
    "asana_url": "https://app.asana.com/0/profile/1210188488437299"
  },
  {
    "name": "Giorgi Goguadze",
    "asana_url": "https://app.asana.com/0/profile/1207470101295118"
  },
  {
    "name": "Elizabeth Wood",
    "asana_url": "https://app.asana.com/0/profile/1210678634682814"
  },
  {
    "name": "Ellie Troughton",
    "asana_url": "https://app.asana.com/0/profile/1206729612623556"
  },
  {
    "name": "Elizabeth Wasserman",
    "asana_url": "https://app.asana.com/0/profile/1205788360495774"
  },
  {
    "name": "Debbie Hoffman",
    "asana_url": "https://app.asana.com/0/profile/1208799271721028"
  },
  {
    "name": "Dani Cervantes",
    "asana_url": "https://app.asana.com/0/profile/1205507145644227"
  },
  {
    "name": "Devon Stank",
    "asana_url": "https://app.asana.com/0/profile/1209775398366541"
  },
  {
    "name": "Christine Holz",
    "asana_url": "https://app.asana.com/0/profile/1210225450436990"
  },
  {
    "name": "Cait George",
    "asana_url": "https://app.asana.com/0/profile/1211664775676977"
  },
  {
    "name": "Corey",
    "asana_url": "https://app.asana.com/0/profile/10447183158962"
  },
  {
    "name": "Bethany Aeckersberg",
    "asana_url": "https://app.asana.com/0/profile/1205337487077774"
  },
  {
    "name": "Austin Koziol",
    "asana_url": "https://app.asana.com/0/profile/1208915300929869"
  },
  {
    "name": "Tisha Tolar",
    "asana_url": "https://app.asana.com/0/profile/1211970711109258"
  },
  {
    "name": "Tom Sanpakit",
    "asana_url": "https://app.asana.com/0/profile/1211495860411951"
  },
  {
    "name": "Tracy Hart",
    "asana_url": "https://app.asana.com/0/profile/1198747167491633"
  },
  {
    "name": "Tiffney Ma",
    "asana_url": "https://app.asana.com/0/profile/1209546983786365"
  },
  {
    "name": "Taryn Himmelright",
    "asana_url": "https://app.asana.com/0/profile/1210804863139837"
  },
  {
    "name": "Lauren Cullnan",
    "asana_url": "https://app.asana.com/0/profile/1202400906089987"
  },
  {
    "name": "Matteo Banfo",
    "asana_url": "https://app.asana.com/0/profile/1163326161975925"
  },
  {
    "name": "Shane",
    "asana_url": "https://app.asana.com/0/profile/1201319977684086"
  },
  {
    "name": "Hannah",
    "asana_url": "https://app.asana.com/0/profile/1207659194399796"
  },
  {
    "name": "Alejandra",
    "asana_url": "https://app.asana.com/0/profile/1207665658939814"
  },
  {
    "name": "Rachel Sanpakit",
    "asana_url": "https://app.asana.com/0/profile/1207826681290603"
  },
  {
    "name": "George ",
    "asana_url": "https://app.asana.com/0/profile/1208771038183777"
  },
  {
    "name": "Tena",
    "asana_url": "https://app.asana.com/0/profile/1209264874946823"
  },
  {
    "name": "Jeffrey",
    "asana_url": "https://app.asana.com/0/profile/1209276867222044"
  },
  {
    "name": "Timofei",
    "asana_url": "https://app.asana.com/0/profile/1209489338708948"
  },
  {
    "name": "Kia",
    "asana_url": "https://app.asana.com/0/profile/1209589451922990"
  },
  {
    "name": "Jim McGrorry",
    "asana_url": "https://app.asana.com/0/profile/1210209261925896"
  },
  {
    "name": "Delon",
    "asana_url": "https://app.asana.com/0/profile/1211419910114508"
  }
]