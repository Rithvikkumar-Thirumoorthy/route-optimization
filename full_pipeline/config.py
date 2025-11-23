#!/usr/bin/env python3
"""
Configuration settings for Full Pipeline Route Optimization
"""

import os
from datetime import datetime, timedelta

class PipelineConfig:
    """Main configuration class for the pipeline"""

    # Database Configuration
    DB_CONFIG = {
        'timeout': 300,  # 5 minutes timeout for DB operations
        'retry_count': 3,
        'batch_insert_size': 1000
    }

    # Processing Configuration
    PROCESSING = {
        'default_batch_size': 50,
        'max_workers': 4,
        'timeout_per_agent': 300,  # 5 minutes per agent
        'retry_count': 3,
        'enable_parallel': True,
        'memory_limit_mb': 2048,  # 2GB memory limit
        'max_prospects_per_agent': 60,
        'min_customers_to_process': 5
    }

    # TSP Optimization Settings
    TSP_CONFIG = {
        'algorithm': 'nearest_neighbor',  # or 'genetic', 'simulated_annealing'
        'max_iterations': 1000,
        'improvement_threshold': 0.001,
        'time_limit_seconds': 60,
        'enable_optimization': True
    }

    # Geographic Settings
    GEO_CONFIG = {
        'default_radius_km': 25,
        'max_radius_km': 50,
        'min_distance_between_stops_m': 100,
        'coordinate_precision': 6,  # decimal places
        'enable_coordinate_validation': True
    }

    # Logging Configuration
    LOGGING = {
        'level': 'INFO',  # DEBUG, INFO, WARNING, ERROR
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file_rotation': True,
        'max_file_size_mb': 100,
        'backup_count': 5,
        'console_output': True
    }

    # File Paths
    PATHS = {
        'log_dir': 'full_pipeline/logs',
        'reports_dir': 'full_pipeline/reports',
        'temp_dir': 'full_pipeline/temp',
        'backup_dir': 'full_pipeline/backup'
    }

    # Performance Tuning
    PERFORMANCE = {
        'enable_caching': True,
        'cache_size_mb': 500,
        'enable_memory_monitoring': True,
        'gc_frequency': 100,  # Run garbage collection every N agents
        'enable_progress_bar': True,
        'progress_update_frequency': 10  # Update progress every N agents
    }

    # Data Validation
    VALIDATION = {
        'validate_coordinates': True,
        'validate_customer_data': True,
        'skip_invalid_agents': True,
        'max_coordinate_deviation': 0.1,  # degrees
        'required_fields': ['agent_id', 'route_date', 'customer_count']
    }

    # Error Handling
    ERROR_HANDLING = {
        'continue_on_error': True,
        'max_consecutive_errors': 10,
        'error_notification_threshold': 50,
        'create_error_reports': True,
        'save_failed_agents': True
    }

class DatabaseQueries:
    """Predefined database queries"""

    GET_ALL_AGENTS = """
    SELECT
        Code as agent_id,
        RouteDate as route_date,
        COUNT(DISTINCT CustNo) as customer_count,
        COUNT(*) as total_records,
        MIN(latitude) as min_lat,
        MAX(latitude) as max_lat,
        MIN(longitude) as min_lon,
        MAX(longitude) as max_lon
    FROM routedata
    WHERE Code IS NOT NULL
        AND RouteDate IS NOT NULL
        AND CustNo IS NOT NULL
    GROUP BY Code, RouteDate
    HAVING COUNT(DISTINCT CustNo) >= {min_customers}
    ORDER BY Code, RouteDate DESC
    """

    GET_AGENT_CUSTOMERS = """
    SELECT
        CustNo,
        latitude,
        longitude,
        barangay_code,
        custype,
        Name,
        distributorID,
        address1,
        address2,
        address3
    FROM routedata
    WHERE Code = '{agent_id}' AND RouteDate = '{route_date}'
    AND CustNo IS NOT NULL
    """

    CHECK_PROCESSED_AGENTS = """
    SELECT DISTINCT salesagent, routedate, COUNT(*) as record_count
    FROM routeplan_ai
    GROUP BY salesagent, routedate
    """

    GET_PROSPECTS_BY_BARANGAY = """
    SELECT TOP {limit}
        CustNo,
        Latitude,
        Longitude,
        Barangay,
        barangay_code,
        'prospect' as custype
    FROM prospective
    WHERE barangay_code IN ({barangay_codes})
        AND Latitude IS NOT NULL
        AND Longitude IS NOT NULL
        AND Latitude != 0
        AND Longitude != 0
    ORDER BY NEWID()
    """

    CLEANUP_AGENT_DATA = """
    DELETE FROM routeplan_ai
    WHERE salesagent = '{agent_id}' AND routedate = '{route_date}'
    """

class FilterPresets:
    """Predefined filter configurations"""

    # Process only high-volume agents (60+ customers)
    HIGH_VOLUME = {
        'min_customers': 60,
        'max_customers': None,
        'date_range': None,
        'exclude_processed': True
    }

    # Process medium-volume agents (20-59 customers)
    MEDIUM_VOLUME = {
        'min_customers': 20,
        'max_customers': 59,
        'date_range': None,
        'exclude_processed': True
    }

    # Process low-volume agents (5-19 customers)
    LOW_VOLUME = {
        'min_customers': 5,
        'max_customers': 19,
        'date_range': None,
        'exclude_processed': True
    }

    # Process recent data only (last 30 days)
    RECENT_ONLY = {
        'min_customers': 5,
        'max_customers': None,
        'date_range': (datetime.now() - timedelta(days=30), datetime.now()),
        'exclude_processed': True
    }

    # Test mode (first 10 agents)
    TEST_MODE = {
        'min_customers': 5,
        'max_customers': None,
        'date_range': None,
        'exclude_processed': False,
        'limit': 10
    }

def get_environment_config():
    """Get configuration based on environment"""
    env = os.getenv('PIPELINE_ENV', 'production').lower()

    if env == 'development':
        return {
            **PipelineConfig.PROCESSING,
            'default_batch_size': 10,
            'max_workers': 2,
            'enable_parallel': False
        }
    elif env == 'testing':
        return {
            **PipelineConfig.PROCESSING,
            'default_batch_size': 5,
            'max_workers': 1,
            'enable_parallel': False,
            'timeout_per_agent': 60
        }
    else:  # production
        return PipelineConfig.PROCESSING

def validate_config():
    """Validate configuration settings"""
    errors = []

    # Check required directories
    for path_name, path_value in PipelineConfig.PATHS.items():
        if not os.path.exists(path_value):
            try:
                os.makedirs(path_value, exist_ok=True)
            except Exception as e:
                errors.append(f"Could not create {path_name} directory '{path_value}': {e}")

    # Validate numeric ranges
    if PipelineConfig.PROCESSING['default_batch_size'] < 1:
        errors.append("Batch size must be at least 1")

    if PipelineConfig.PROCESSING['max_workers'] < 1:
        errors.append("Max workers must be at least 1")

    if PipelineConfig.PROCESSING['timeout_per_agent'] < 10:
        errors.append("Timeout per agent must be at least 10 seconds")

    return errors

if __name__ == "__main__":
    # Validate configuration
    config_errors = validate_config()

    if config_errors:
        print("Configuration Errors Found:")
        for error in config_errors:
            print(f"  - {error}")
    else:
        print("Configuration validation passed!")

    print(f"\nCurrent Configuration:")
    print(f"  Batch Size: {PipelineConfig.PROCESSING['default_batch_size']}")
    print(f"  Max Workers: {PipelineConfig.PROCESSING['max_workers']}")
    print(f"  Parallel Processing: {PipelineConfig.PROCESSING['enable_parallel']}")
    print(f"  Environment: {os.getenv('PIPELINE_ENV', 'production')}")