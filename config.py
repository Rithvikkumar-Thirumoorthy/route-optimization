"""
Configuration module for Hierarchical Route Pipeline

This module contains all configurable parameters for the pipeline.
Modify these values to adjust pipeline behavior without changing code.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DB_CONFIG = {
    'server': os.getenv('DB_SERVER'),
    'database': os.getenv('DB_DATABASE'),
    'username': os.getenv('DB_USERNAME'),
    'password': os.getenv('DB_PASSWORD'),
    'use_windows_auth': os.getenv('DB_USE_WINDOWS_AUTH', 'False') == 'True',
}

# ============================================================================
# PIPELINE PROCESSING PARAMETERS
# ============================================================================

# Batch processing
BATCH_SIZE = 50  # Number of routes to process in a batch
MAX_WORKERS = 4  # Maximum number of parallel workers (use 1 for sequential)

# Progress reporting
PROGRESS_INTERVAL = 10  # Report progress every N combinations processed

# ============================================================================
# ROUTE OPTIMIZATION PARAMETERS
# ============================================================================

# TSP (Traveling Salesman Problem) configuration
# NOTE: Starting location priority order:
#   1. CLI arguments (--start-lat/--start-lon) - overrides everything
#   2. Distributor table - fetched per distributor from database
#   3. These config defaults - fallback if distributor location not in DB
TSP_CONFIG = {
    'algorithm': 'nearest_neighbor',  # Algorithm to use for TSP
    'start_lat': 14.663813,  # Default starting latitude (fallback only)
    'start_lon': 121.122687,  # Default starting longitude (fallback only)
}

# Stop number assignments
STOPNO_NO_COORDS = 100  # StopNo assigned to customers without coordinates

# ============================================================================
# PROSPECT SEARCH PARAMETERS
# ============================================================================

# Prospect addition thresholds
MIN_ROUTE_SIZE = 60  # Minimum route size before adding prospects
MAX_DISTANCE_KM = 5.0  # Maximum search radius for prospects (kilometers)
TARGET_PROSPECTS_PER_ROUTE = 5  # Target number of prospects to add per route

# Prospect search configuration
PROSPECT_SEARCH = {
    'enabled': True,  # Enable/disable prospect addition
    'barangay_matching': True,  # Match prospects by barangay
    'exclude_visited': True,  # Exclude already-visited prospects
    'randomize_selection': True,  # Randomize prospect selection (ORDER BY NEWID())
}

# ============================================================================
# FILTERING PARAMETERS
# ============================================================================

# Optional filters (None = process all)
DISTRIBUTOR_ID_FILTER = None  # Filter by specific distributor ID
AGENT_ID_FILTER = None  # Filter by specific agent ID
DATE_FILTER = None  # Filter by specific date (format: 'YYYY-MM-DD')

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOGGING_CONFIG = {
    'level': 'INFO',  # Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'log_to_file': True,  # Save logs to file
    'log_to_console': True,  # Print logs to console
    'log_directory': 'logs',  # Directory for log files
}

# ============================================================================
# COLUMN MAPPINGS
# ============================================================================

# Table and column mappings (useful if schema changes)
TABLE_NAMES = {
    'monthly_plan': 'MonthlyRoutePlan_temp',
    'customer': 'customer',
    'prospective': 'prospective',
    'custvisit': 'custvisit',
}

# Column mappings for prospective table (updated schema)
PROSPECTIVE_COLUMNS = {
    'id': 'tdlinx',  # Prospect ID column
    'latitude': 'latitude',
    'longitude': 'longitude',
    'barangay': 'barangay',  # Barangay column
    'name': 'store_name_nielsen',  # Name column
}

# Column mappings for customer table
CUSTOMER_COLUMNS = {
    'id': 'CustNo',
    'latitude': 'latitude',
    'longitude': 'longitude',
    'barangay': 'address3',  # Barangay code in customer table
}

# ============================================================================
# VALIDATION PARAMETERS
# ============================================================================

# Data validation thresholds
VALIDATION = {
    'min_latitude': -90.0,
    'max_latitude': 90.0,
    'min_longitude': -180.0,
    'max_longitude': 180.0,
    'allow_null_coordinates': True,  # Allow customers without coordinates
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_config():
    """
    Validate configuration settings.
    Raises ValueError if configuration is invalid.
    """
    # Check database configuration
    if not all([DB_CONFIG['server'], DB_CONFIG['database']]):
        raise ValueError("Database server and database name must be configured")

    if not DB_CONFIG['use_windows_auth']:
        if not all([DB_CONFIG['username'], DB_CONFIG['password']]):
            raise ValueError("Database username and password required when not using Windows auth")

    # Check numeric parameters
    if BATCH_SIZE < 1:
        raise ValueError("BATCH_SIZE must be at least 1")

    if MAX_WORKERS < 1:
        raise ValueError("MAX_WORKERS must be at least 1")

    if MAX_DISTANCE_KM <= 0:
        raise ValueError("MAX_DISTANCE_KM must be positive")

    if MIN_ROUTE_SIZE < 0:
        raise ValueError("MIN_ROUTE_SIZE must be non-negative")

    print("✓ Configuration validation passed")

def print_config():
    """Print current configuration (for debugging)"""
    print("=" * 80)
    print("CURRENT CONFIGURATION")
    print("=" * 80)
    print(f"Database: {DB_CONFIG['database']} @ {DB_CONFIG['server']}")
    print(f"Batch Size: {BATCH_SIZE}")
    print(f"Max Workers: {MAX_WORKERS}")
    print(f"Min Route Size: {MIN_ROUTE_SIZE}")
    print(f"Max Distance: {MAX_DISTANCE_KM} km")
    print(f"Target Prospects: {TARGET_PROSPECTS_PER_ROUTE}")
    print(f"Distributor Filter: {DISTRIBUTOR_ID_FILTER or 'None (all)'}")
    print(f"Agent Filter: {AGENT_ID_FILTER or 'None (all)'}")
    print(f"Date Filter: {DATE_FILTER or 'None (all)'}")
    print("=" * 80)

if __name__ == "__main__":
    # Test configuration
    try:
        validate_config()
        print_config()
    except Exception as e:
        print(f"Configuration error: {e}")
