
# Configuration settings for the scraper
SCRAPER_CONFIG = {
    'max_bids': 300,
    'delay_min': 3,
    'delay_max': 5,
    'headless': False,
    'federal_org_code': None,  # Set to None to skip, or provide code like "247 - 400 YEARS..."
    'notice_types': None,  # Set to None to skip, or provide list like ["Special Notice", "Presolicitation"]
    'set_aside_types': None,  # Set to None to skip, or provide list
    'date_range': "today",  # "today", "custom", or None
    'output_file': 'sam_gov_bids.csv'
}

# Configuration settings for septa
SEPTA_CONFIG = {
    'max_bids': 300,
    'delay_min': 3,
    'delay_max': 5,
    'headless': False,
    'federal_org_code': None,  # Set to None to skip, or provide code like "247 - 400 YEARS..."
    'notice_types': None,  # Set to None to skip, or provide list like ["Special Notice", "Presolicitation"]
    'set_aside_types': None,  # Set to None to skip, or provide list
    'date_range': "today",  # "today", "custom", or None
    'output_file': 'septa.csv'
}

# configurations settings for unison
UNISON_CONFIG = {
    'max_bids': 300,
    'delay_min': 3,
    'delay_max': 5,
    'headless': False,
    'federal_org_code': None,  # Set to None to skip, or provide code like "247 - 400 YEARS..."
    'notice_types': None,  # Set to None to skip, or provide list like ["Special Notice", "Presolicitation"]
    'set_aside_types': None,  # Set to None to skip, or provide list
    'date_range': "today",  # "today", "custom", or None
    'output_file': 'unison.csv'
}
