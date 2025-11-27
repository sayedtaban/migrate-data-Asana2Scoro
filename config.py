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
# PROJECT_GIDS = [
#     "1207816263671761",  # Van Zeeland Nursery & Landscape - done1
#     "1211389004379875",  # Ethoscapes [VIP] - done1
#     "1209371228065321",  # Heritage Landscapes (VIP)
# ]





# PROJECT_GIDS = [
#     "1207744507032195", # TO BE ASSIGNED PROJECT
#     "1208790224379335", # Debbie
#     "1207931717530407", # Olivia
#     "1207722134870402", # Ellie
#     "1209755485393570", # Review Draft Responses (Mark complete when sent to client and posted on review platform)
# ]

# PROJECT_GIDS = [
# "1207722511334892", # Lauren
# "1206835287114553", # Earthly Possibilities
# "1209020289079877", # Exscape (VIP)
# "1208246397156176", # Client Status
# "1211028802323242", # Green Impressions [VIP+]
# ]

# PROJECT_GIDS = [
# "1211296592742932", # My Fence
# "1207931717530299", # Matej
# "1204820764302059", # SEO
# "1209980831176849", # Mylessia Training
# "1210962441602410", # SEO Dashboard
# ]

# PROJECT_GIDS = [
# "1207413829228228", # Elizabeth
# "1209661531978575", # Austin
# "1209324707998092", # Big Tex Stone
# "1211067354407900", # Element Outdoor Living (VIP+)
# "1201769649997354", # Tournoux (VIP)
# "1208021047952985", # Andrea
# ]

# PROJECT_GIDS = [
# "1209757104186341", # Proposals Viewed (That are Previously Signed)
# "1206396054073419", # Premier Pavers (VIP)
# "1209660822940485", # Websites in Progress
# "1202011327012956", # 🚨 ZLM (VIP)🚨
# "1202011327012956", # Great Outdoors (VIP)
# ]

# PROJECT_GIDS = [
# "1202017789763052", # Firesky (VIP)
# "1211762627974041", # McKenzie Contracting [VIP]
# "1202848664849121", # Halstead Sales & Marketing
# "1210146503205032", # Lawn Control Center (VIP+)
# "1207469001658854", # Duke's
# ]

# PROJECT_GIDS = [
# "1208143258940139", # Blue Ribbon Outdoor (VIP)
# "1201668388055244", # Halstead Media Clients
# "377184657233986", # Halstead Content
# "1207668601734586", # Blogs
# "1210990004350835", # All Clients
# ]

# PROJECT_GIDS = [
#   "1209976010654781", # The Stone Man (VIP+)
#   "1209101177425265", # 🚨 Oneill Landscape Group (VIP)🚨
#   "1207931717530371", # Bethany
#   "1209331657533757", # Freelancers
#   "1208531721844593", # Martina
# ]



# PROJECT_GIDS = [
#   "1201959466824376", # Jan Fence - My Fence (VIP)
#   "1202198955540360", # Genesee Valley
#   "1201997623514342", # Rutland Turf Care (VIP)
#   "1211103877794723", # Stuarts Landscaping [VIP]
#   "1206754892659013", # Gardens of the World (VIP)
# ]

# PROJECT_GIDS = [
#   "1207129822443936", # Carson Outdoor Living (VIP)
#   "1207522975026447", # Email Marketing
#   "1207448790384675", # Social Posting
#   "1206525987654870", # Atlantic Ridge (VIP)
#   "1202008550450876", # GLC (VIP)
# ]





# PROJECT_GIDS = [
#   "1201721156974866", # Second Nature (VIP)
#   "1202115152957168", # Niedergeses Landscape [VIP]
#   "1201923199778254", # Out of Office Schedule (OOO)
#   "1200670717859396", # [H] Billing Master
#   "1200670785956334", # [H] Department MPP
# ]

# PROJECT_GIDS = [

# ]



PROJECT_GIDS = [
  "1209226309317546", # Alt's Operation
  "1201997748599444", # Red Rock (VIP)
  "1201944213595853", # 1st Impressions
  "1204845884279023", # Hiner Outdoor Living (VIP)
  "1210130088736420", # Southern Classic Landscape Management Inc
  "1201805737718436", # Teddy's (VIP)
  "1209670241247456", # Polina
  "1207401689716524", # Lena
  "1207599856837084", # Issue Tracker

]

# PROJECT_GIDS = [
#   "706549318301154", # Joe and Tony
#   "1205366800721766", # Hillman (VIP)
#   "1208801508897860", # Swimm Pools (VIP)
#   "1204067243200283", # Hollandia Outdoor Living Concepts (VIP)
#   "1202198955540360", # Hermes
#   "1206355124124877", # Flora Landscape Contractors
#   "1209852258792933", # Giorgi
# ]

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