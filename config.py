"""
Configuration and constants for Asana to Scoro migration
"""
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Rate limiting configuration
RATE_LIMIT_DELAY = 0.1  # Delay between API calls in seconds (100ms)
MAX_RETRIES = 3  # Maximum number of retries for failed API calls
RETRY_DELAY = 1  # Initial delay between retries in seconds
RETRY_BACKOFF = 2  # Exponential backoff multiplier

# Batch processing configuration
DEFAULT_BATCH_SIZE = 50

# Test mode configuration - limit number of tasks to migrate (set to None to migrate all tasks)
TEST_MODE_MAX_TASKS = 13  # Set to None for PRODUCTION - migrate all tasks

# Date cutoff for task filtering
CUTOFF_DATE = datetime(2025, 7, 1)  # Naive datetime for comparison

# Valid Scoro users and user mapping
VALID_SCORO_USERS = {
    'Austin Koziol', 'Bethany Aeckersberg', 'Cait George', 'Tom Sanpakit',
    'Andrea Pejoska', 'Anna Halstead', 'Debbie Hoffman', 'Elizabeth Wasserman',
    'Kelsey Blomquist-Wright', 'Lauren Cullnan', 'Matej Robar', 'Polina Kroyter',
    'Taryn Himmelright', 'Tiffney Ma', 'Tracy Hart', 'Christine Holz',
    'Corey Halstead', 'Dani Cervantes', 'Devon Stank', 'Elizabeth Wood',
    'Ellie Troughton', 'Giorgi Goguadze', 'Jim McGorry', 'Katya Pankov',
    'Lena Lebid', 'Lindsey Cartwright', 'Martina Willis', 'Matteo Banfo',
    'Mylessia Tkacs', 'Olivia Mello'
}

USER_MAPPING = {
    'Matej': 'Matej Robar', 'Ellie': 'Ellie Troughton', 'Tracy': 'Tracy Sanpakit',
    'Austin': 'Austin Koziol', 'Sophia': 'Sophia Sanpakit', 'Giuseppe': 'Giuseppe Sanpakit',
    'Marie': 'Marie Sanpakit', 'Rachel': 'Rachel Sanpakit', 'Bethany': 'Bethany Aeckersberg',
    'Anna': 'Anna Halstead', 'Debbie': 'Debbie Hoffman', 'Lauren': 'Lauren Cullnan',
    'Andrea': 'Andrea Pejoska', 'Dani': 'Dani Cervantes', 'Lena': 'Lena Lebid',
    'Olivia': 'Olivia Mello', 'Giorgi': 'Giorgi Goguadze', 'Martina': 'Martina Willis',
    'Matteo': 'Matteo Banfo', 'Mylessia': 'Mylessia Tkacs', 'Christine': 'Christine Holz',
    'Kelsey': 'Kelsey Blomquist-Wright', 'Cait': 'Cait George', 'Tom': 'Tom Sanpakit'
}

# Environment variable names
ENV_ASANA_ACCESS_TOKEN = 'ASANA_ACCESS_TOKEN'
ENV_SCORO_API_KEY = 'SCORO_API_KEY'
ENV_SCORO_COMPANY_NAME = 'SCORO_COMPANY_NAME'

# Projects to migrate
# Option 1: Use project GIDs (faster, no search needed)
PROJECT_GIDS = [
    "1207816263671761",  # Example project 1
    # Add more project GIDs here
]

# Option 2: Use project names (will search for projects by name)
PROJECT_NAMES = [
    # "Van Zeeland Nursery & Landscape",  # Example project 1
    # "Another Project Name",  # Example project 2
    # Add more project names here
]

# Workspace GID (required for Asana API)
WORKSPACE_GID = "10447183158961"

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
  }
]