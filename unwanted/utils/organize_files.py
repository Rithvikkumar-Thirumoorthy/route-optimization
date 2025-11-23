#!/usr/bin/env python3
"""
Organize project files into logical folders
"""

import os
import shutil

def organize_files():
    """Organize files into proper folder structure"""
    print("ORGANIZING PROJECT FILES")
    print("=" * 30)

    # Create folder structure
    folders = {
        'tests': 'Testing and validation files',
        'sql': 'SQL queries and database scripts',
        'core': 'Core pipeline and optimization files',
        'utils': 'Utility and helper scripts',
        'docs': 'Documentation and analysis files'
    }

    # Create folders
    for folder, description in folders.items():
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Created folder: {folder}/ - {description}")

    # File organization mapping
    file_moves = {
        # Testing files
        'tests': [
            'test_performance.py',
            'test_single_agent.py',
            'basic_agent_check.py',
            'check_barangay_code_issue.py',
            'quick_barangay_check.py',
            'find_valid_barangay_codes.py',
            'debug_barangay_matching.py',
            'final_verification_test.py',
            'test_barangay_code_fix.py',
            'analyze_agent_scenarios.py',
            'simple_agent_analysis.py',
            'get_specific_agents.py',
            'detailed_scenario_report.py',
            'clear_and_rerun.py',
            'final_cleanup_and_rerun.py',
            'check_agents_with_prospects.py',
            'analyze_mix_b10_agent.py'
        ],

        # SQL files
        'sql': [
            'scenario_specific_queries.sql',
            'single_comprehensive_query.sql',
            'analysis_queries.sql',
            'find_agents_25_to_59.sql',
            'check_agents_with_prospects.sql',
            'analyze_mix_b10_agent.sql',
            'create_optimized_indexes.sql'
        ],

        # Core pipeline files
        'core': [
            'enhanced_route_optimizer.py',
            'scalable_route_optimizer.py',
            'run_specific_agents.py',
            'run_production_pipeline.py',
            'database.py'
        ],

        # Utility scripts
        'utils': [
            'create_indexes.py',
            'create_package.py',
            'organize_files.py'
        ]
    }

    # Move files
    moved_count = 0
    for folder, files in file_moves.items():
        print(f"\nMoving files to {folder}/:")
        for file in files:
            if os.path.exists(file):
                try:
                    destination = os.path.join(folder, file)
                    shutil.move(file, destination)
                    print(f"  Moved: {file} -> {folder}/")
                    moved_count += 1
                except Exception as e:
                    print(f"  Error moving {file}: {e}")
            else:
                print(f"  Not found: {file}")

    # Keep important files in root
    root_files = [
        '.env',
        'README.md',
        'requirements.txt'
    ]

    print(f"\nFiles remaining in root:")
    for file in root_files:
        if os.path.exists(file):
            print(f"  Kept: {file}")

    # Create folder README files
    readme_contents = {
        'tests': """# Tests Folder

Testing and validation scripts for the route optimization pipeline.

## Key Files:
- test_performance.py - Performance testing
- check_barangay_code_issue.py - Validate barangay code fixes
- final_verification_test.py - End-to-end validation
- Various agent analysis scripts

## Usage:
Run individual test scripts to validate specific functionality.
""",

        'sql': """# SQL Folder

SQL queries for analysis and database operations.

## Key Files:
- scenario_specific_queries.sql - All scenario analysis queries
- single_comprehensive_query.sql - Single comprehensive query
- analysis_queries.sql - Complete query collection
- create_optimized_indexes.sql - Database performance indexes

## Usage:
Execute queries directly in SQL Server Management Studio or through Python scripts.
""",

        'core': """# Core Folder

Core pipeline and optimization files.

## Key Files:
- scalable_route_optimizer.py - Main optimized pipeline for large datasets
- enhanced_route_optimizer.py - Base optimizer with TSP
- run_specific_agents.py - Run pipeline for specific agents
- run_production_pipeline.py - Full production pipeline
- database.py - Database connection module

## Usage:
These are the main files for running the route optimization pipeline.
""",

        'utils': """# Utils Folder

Utility and helper scripts.

## Key Files:
- create_indexes.py - Create database indexes for performance
- create_package.py - Package files for distribution
- organize_files.py - This file organization script

## Usage:
Run these scripts for setup, maintenance, and distribution tasks.
"""
    }

    # Create README files
    for folder, content in readme_contents.items():
        readme_path = os.path.join(folder, 'README.md')
        with open(readme_path, 'w') as f:
            f.write(content)
        print(f"  Created: {folder}/README.md")

    # Create main project README
    main_readme = """# Route Optimization Pipeline

Scalable route optimization for sales agents with prospect matching.

## Project Structure:
- **core/** - Main pipeline and optimization files
- **sql/** - SQL queries and database scripts
- **tests/** - Testing and validation scripts
- **utils/** - Utility and helper scripts

## Quick Start:
1. Set up database connection in `.env`
2. Run `core/create_indexes.py` for performance
3. Use `core/run_specific_agents.py` for targeted processing
4. Use `core/run_production_pipeline.py` for full pipeline

## Key Features:
- Barangay matching: `routedata.barangay_code = prospective.barangay_code`
- TSP route optimization
- Geographic bounding box filtering
- Scalable for 5.8M prospects + 1.8M customers

## Latest Fixes Applied:
- ✅ Barangay_code issue fixed (no more 'nan' values)
- ✅ Agents with >60 customers now saved
- ✅ Unicode character issues resolved
"""

    with open('README.md', 'w') as f:
        f.write(main_readme)
    print(f"Created: README.md")

    print(f"\n" + "="*50)
    print(f"FILE ORGANIZATION COMPLETED!")
    print(f"Total files moved: {moved_count}")
    print(f"Folders created: {len(folders)}")
    print(f"Project is now organized and documented!")
    print(f"="*50)

if __name__ == "__main__":
    organize_files()