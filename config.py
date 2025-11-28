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
RATE_LIMIT_DELAY = 0.1  # Delay between API calls in seconds (100ms)
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
#     "1207816263671761",  # Van Zeeland Nursery & Landscape - done1 - 578 tasks
#     "1211389004379875",  # Ethoscapes [VIP] - done1 - 293 tasks
#     "1209371228065321",  # Heritage Landscapes (VIP) - 384 tasks
# ]

# PROJECT_GIDS = [
#     "1207744507032195", # TO BE ASSIGNED PROJECT - 102 tasks
#     "1208790224379335", # Debbie - 1529 tasks
# ]

# PROJECT_GIDS = [
# "1211296592742932", # My Fence - 129 tasks
# ]

# PROJECT_GIDS = [
# "1209757104186341", # Proposals Viewed (That are Previously Signed) - 554 tasks
# "1206396054073419", # Premier Pavers (VIP) - 704 tasks
# "1209660822940485", # Websites in Progress - 575 tasks
# ]

# PROJECT_GIDS = [
# "1202017789763052", # Firesky (VIP) - 1765 tasks
# "1211762627974041", # McKenzie Contracting [VIP] - 279 tasks
# ]

# PROJECT_GIDS = [
#   "1209976010654781", # The Stone Man (VIP+) - 445 tasks
#   "1209101177425265", # 🚨 Oneill Landscape Group (VIP)🚨 - 654 tasks
# ]

# PROJECT_GIDS = [
#   "1201959466824376", # Jan Fence - My Fence (VIP) - 2237 tasks
#   "1202198955540360", # Genesee Valley - 566 tasks
#   "1201997623514342", # Rutland Turf Care (VIP) - 563 tasks
#   "1211103877794723", # Stuarts Landscaping [VIP] - 162 tasks
#   "1206754892659013", # Gardens of the World (VIP) - 523 tasks
# ]

# PROJECT_GIDS = [
#   "1207129822443936", # Carson Outdoor Living (VIP) - 980 tasks
# ]

# PROJECT_GIDS = [
#   "1201721156974866", # Second Nature (VIP) - 890 tasks
#   "1202115152957168", # Niedergeses Landscape [VIP] - 638 tasks
# ]

# PROJECT_GIDS = [
#   "1208236324570171", # Billing Videoshoots - 2 tasks
#   "1207129822443940", # 🚨J&J Landscape Management(VIP+)🚨 - 1094 tasks
# ]

# =================================

# PROJECT_GIDS = [
#   "1207931717530335", # Dani - 1933 tasks
#   "1208021047952985", # Andrea - 1320 tasks
#   "1209226309317546", # Alt's Operation - 361 tasks
#   "1204189444291008", # BUILT. - 201 tasks
#   "1206494161312836", # OKRs - 183 tasks
# ]


# PROJECT_GIDS = [
#   "1207722134870402", # Ellie - 4873 tasks
#   "1210039749266336", # Yardcreations - 163 tasks
#   "1201997748599110", # PurGreen - 146 tasks
#   "1207721928698549", # Task Clarity Training - 157 tasks
#   "1203894445821642", # Cedar Hills Landscaping - 104 tasks
# ]

# PROJECT_GIDS = [
#   "1207931717530407", # Olivia - 1685 tasks
#   "1207448790384675", # Social Posting - 1562 tasks
#   "1206525987654870", # Atlantic Ridge (VIP) - 747 tasks
#   "1210873210287559", # Exscape Group - 184 tasks
#   "1200670717859396", # [H] Billing Master - 70 tasks
#   "1200670785956334", # [H] Department MPP - 183 tasks
# ]

# PROJECT_GIDS = [
# "1209661531978575", # Austin - 3110 tasks
# "1208246397156176", # Client Status - 4158 tasks
#   "1209020347269547", # Lawn & Order - 92 tasks
#   "1209373005483148", # Vision Design Landscaping - 120 tasks
#   "1206124874487664", # Top Rock Design - 69 tasks
#   "1206695579421996", # Reimbursements - 84 tasks
#   "1208771061627949", # George's Paid Trial - 3 tasks
#   "1200856739086838", # Landworx MPP - 24 tasks
# ]

# PROJECT_GIDS = [
#   "1206707027635152", # DeBartolo - 134 tasks
#   "1211184926575840", # KELSEY - 31 tasks
#   "1210124803938200", # Integrations - 84 tasks
#   "1209589888865220", # Ryan Lawn & Tree - 96 tasks
#   "1204356110351656", # M.A.B. Landscape Group - 50 tasks
#   "1207413829228228", # Elizabeth - 4177 tasks
#   "1211413968568193", # Delon's Onboarding and Training - 44 tasks
# ]

# PROJECT_GIDS = [
#   "1207931717530371", # Bethany - 2448 tasks
#   "1208531721844593", # Martina - 1395 tasks
#   "1180237628314967", # Platinum - 18 tasks
#   "1199187158790731", # MyFence2Go - SEO - 58 tasks
#   "888334325526069", # LandArt/FireSky- Website - 37 tasks
#   "1210478192678626", # Paramount Outdoor Living - 195 tasks
#   "1209391947899381", # MAB Landscaping - 192 tasks
#   "1206595171320647", # Roche - 6 tasks
#   "1211792420870735", # PM Time Tracking by Client - 4 tasks
#   "1208873745193724", # Hi-Way Concrete - 82 tasks
# ]

# PROJECT_GIDS = [
#   "1201959561838083", # Gary Duff (VIP) - 888 tasks
#   "1204154752021419", # Training - 5 tasks
#   "1211637268379824", # Project Management Tool | Reporting Transition - 22 tasks
#   "1208183190857136", # Jim's Training - 133 tasks
#   "1206396054073411", # Wenzel - 192 tasks
#   "1209773444928037", # Vermont Stone (VS&H Construction) ['25] - 145 tasks
#   "1208236324570171", # Billing Videoshoots - 2 tasks
#   "1153054154859564", # TKC - 257 tasks
#   "1206396054073415", # TKC - 119 tasks
# ]


# PROJECT_GIDS = [
#   "705893338237500", # DNU Halstead Sales & Marketing - 1829 tasks
#   "1202001504658033", # 🚨Town & Country🚨 (VIP) - 773 tasks
#   "1202067237365290", # Platinum (VIP) - 501 tasks
#   "1201944915672225", # Troy Clogg - 779 tasks
#   "1210226294651081", # Christine - 108 tasks
#   "1201759996136469", # Premier Landscaping Inc. - 367 tasks
#   "1209020250329976", # Foremost Fence - 288 tasks
# ]

# ====== New =========

# PROJECT_GIDS = [
# "1207722511334892", # Lauren - 7412 tasks
# "1207931717530299", # Matej - 5681 tasks
#   "1204820764302059", # SEO - 228 tasks
#   "1202598063397832", # Evolve - 140 tasks
# ]

# PROJECT_GIDS = [
#   "1202008550450876", # GLC (VIP) - 697 tasks
#   "1209755485393570", # Review Draft Responses (Mark complete when sent to client and posted on review platform) - 2351 tasks
#   "1201923199778254", # Out of Office Schedule (OOO) - 755 tasks
#   "1202848664849121", # Halstead Sales & Marketing - 2454 tasks
#   "1210146503205032", # Lawn Control Center (VIP+) - 361 tasks
#   "1207469001658854", # Duke's - 473 tasks
#   "1202011327012956", # 🚨 ZLM (VIP)🚨 - 1837 tasks
#   "1201843675611835", # Great Outdoors (VIP) - 800
#   "1210467184621570", # Websites In Progress - 149 tasks
# ]

# PROJECT_GIDS = [
#   "1207401689716524", # Lena - 4794 tasks
#   "1207668601734586", # Blogs - 919 tasks
#   "1210990004350835", # All Clients - 402 tasks
#   "1201997748599444", # Red Rock (VIP) - 578 tasks
#   "1201944213595853", # 1st Impressions - 600 tasks
#   "1204845884279023", # Hiner Outdoor Living (VIP) - 917 tasks
#   "1201805737718436", # Teddy's (VIP) - 1045 tasks
#   "1209670241247456", # Polina - 2882 tasks
#   "1207599856837084", # Issue Tracker - 986 tasks
#   "1209331657533757", # Freelancers - 122 tasks
#   "1209205137475783", # Starbucks Landscaping - 199 tasks
# ]

# PROJECT_GIDS = [
#   "706549318301154", # Joe and Tony - 356 tasks
#   "1205366800721766", # Hillman (VIP) - 652 tasks
#   "1208801508897860", # Swimm Pools (VIP) - 436 tasks
#   "1204067243200283", # Hollandia Outdoor Living Concepts (VIP) - 586 tasks
#   "1202198955540360", # Hermes - 566 tasks
#   "1206355124124877", # Flora Landscape Contractors - 497 tasks
#   "1209852258792933", # Giorgi - 536 tasks
# ]



# PROJECT_GIDS = [
#   "1206082775373071", # Apple LandScape Design (VIP) - 402 tasks
#   "1201955186274436", # Albert Pools (VIP) - 883 tasks
#   "1206393501402418", # Creative Hardscapes - 311 tasks
#   "1202103809714710", # Rutland Nurseries (VIP) - 613 tasks
#   "1204250043888413", # Valley Stone Supply - Unilock Dealer - 424 tasks
#   "836807829489875", # Magic Landscaping (VIP) - 1311 tasks
# ]


# PROJECT_GIDS = [
#   "1202103717323633", # Sammarco (VIP) - 691 tasks
#   "1202008494907041", # Fein - 445 tasks
#   "1201994653016894", # Country Lawn Care - 600 tasks
#   "1203644940821003", # 🚨Commonwealth Curb Appeal🚨 (VIP) - 892 tasks
#   "1202664499015949", # Riverside Services - 238 tasks
#   "1202067262153755", # Nature's Accents - 288 tasks
# ]

# PROJECT_GIDS = [
#   "1201997724904303", # CMHA - 458 tasks
#   "1210835404446332", # Brandywine Designs (VIP) - 329 tasks
#   "1210889535977773", # Rising Tide Landscapes (VIP) - 299 tasks
#   "1206394483540315", # Roche Landscaping Services - 631 tasks
#   "1206363754570915", # Project Managers - 473 tasks
#   "1205353734392634", # Pine Ridge Landscaping (VIP) - 636 tasks
#   "1202598063397774", # Legacy Landscape (VIP) - 619 tasks
# ]

# PROJECT_GIDS = [
#   "1203185755588476", # Indresano Corp (VIP) - 588 tasks
#   "1202971583662880", # Hardscape Contractors (VIP+) - 1797 tasks
#   "1208600372368707", # Integrity - 375 tasks
#   "1202473135917638", # GoldGlo (VIP) - 960 tasks
#   "1211117741325774", # Perfect Pavers of SFL (VIP) - 316 tasks
#   "1202067263383878", # Premier Gunite Pools (VIP) - 943 tasks
# ]

# PROJECT_GIDS = [
  # "1207522975026447", # Email Marketing - 505 tasks
#   "1201994636901967", # BTS (VIP) - 1034 tasks
#   "1206355619759195", # Weavers Landscape Company - 474 tasks
# ]

# PROJECT_GIDS = [
#   "1211002007747820", # WTX Outdoor Living (VIP) - 296 tasks
#   "1204320149396735", # Allied Landscape Supply - 377 tasks
#   "1201976495070655", # Unilock - 2333 tasks

#   "1208574178647908", # BayTerra - 431 tasks
# ]

# PROJECT_GIDS = [
#   "1202029877560391", # Landscape Architecture - 426 tasks
#   "1207285748194854", # Daybreaker Landscapes - 360 tasks
#   "1202103810014649", # Santucci - 261 tasks
#   "1202067261353489", # Northern Lights - 491 tasks
#   "1209582867880756", # 🚨Riverview Landscapes🚨 (VIP) - 482 tasks
# ]

# PROJECT_GIDS = [
#   "1205797057778863", # King GREEN - 1121 tasks
#   "1159410326686249", # Client Onboarding - 225 tasks
#   "1211118383980197", # test - 289 tasks
#   "1211801318555534", # Duplicate of 2025 Client Template - 295 tasks
#   "1209324707997813", # 2025 Client Template - 345 tasks
# ]
# PROJECT_GIDS = [

#   "1211796317554229", # Tom Test Project for Kelsey - 322 tasks
#   "1207371717043739", # Hively (VIP) - 650 tasks
#   "715809873266920", # Misc for clients - 570 tasks
#   "1211495866167897", # Tom's Test Project - 299 tasks
# ]

# PROJECT_GIDS = [
#   "1204909348975911", # Grandscapes - 272 tasks
#   "1210129565236122", # Artistic Landscaping. Inc. - 319 tasks
#   "1211028564983415", # North East Landscaping Services - 278 tasks
#   "1211489330798377", # Duplicate of 2025 Client Template - 238 tasks
#   "1200858667852392", # [H] Client MPP - 1014 tasks
#   "1202103718886449", # Zacarias - 402 tasks
#   "1209980831176849", # Mylessia Training - 801 tasks
# "1210962441602410", # SEO Dashboard - 482 tasks
# "1209324707998092", # Big Tex Stone - 347 tasks
# "1211067354407900", # Element Outdoor Living (VIP+) - 410 tasks
# "1201769649997354", # Tournoux (VIP) - 657 tasks
# ]


# PROJECT_GIDS = [
#   "1202029935776209", # Local Life - 415 tasks
#   "1204427552401501", # Elizabeth 2023: Interview Asana Project - 211 tasks
#   "1201236676138365", # Content Management - 353 tasks
#   "1201995259444316", # E.P. Jansen - 272 tasks
#   "1209391945032267", # HomeTurf Landscapes (VIP) - 313 tasks
#   "1210941400014664", # TH test project July 2025 - 275 tasks
#   "1206838003174635", # PureModern - 1098 tasks
# ]

# PROJECT_GIDS = [
#   "377184657233986",  # Halstead Content - 264 tasks
#   "1210130088736420", # Southern Classic Landscape Management Inc - 293 tasks
#   "1201994699804530", # Antonucci - 592 tasks
#   "1206594099564496", # Kamin - 230 tasks
#   "1201994599417224", # ARJ - 493 tasks
#   "1205326220124712", # Kennedy Blue Mountain Stone - 219 tasks
# "1209020289079877", # Exscape (VIP) - 554 tasks
# ]

# PROJECT_GIDS = [
#   "1203848708520233", # Birch Hill Landscaping - 253 tasks
#   "1203848537002834", # C&S Landscaping - 299 tasks
#   "1207931717530263", # Alejandra - 1008 tasks
#   "1207743544295787", # Ginny - 647 tasks
#   "1206835287114553", # Earthly Possibilities - 384 tasks
#   "1211028802323242", # Green Impressions [VIP+] - 289 tasks
# ]

# PROJECT_GIDS = [
#   "1203871858478068", # ProScape Lawn & Landscape - 466 tasks
#   "1202067222508732", # Maplehurst - 518 tasks
#   "1203281061714632", # Valley Deck & Patio - 480 tasks
#   "1202017683965876", # JFD - 492 tasks
#   "1201994574141537", # Proscapes - 676 tasks
#   "1202103765718385", # Rine - 722 tasks
# ]


# PROJECT_GIDS = [
# "1201668388055244", # Halstead Media Clients - 50001 tasks
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