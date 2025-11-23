#!/usr/bin/env python3
"""
Create a package of all important files for download
"""

import os
import shutil
import zipfile

def create_package():
    """Create a zip package of all important files"""

    package_dir = "route_optimization_package"

    # Create package directory
    if os.path.exists(package_dir):
        shutil.rmtree(package_dir)
    os.makedirs(package_dir)

    # List of important files to include
    important_files = [
        "run_specific_agents.py",
        "scalable_route_optimizer.py",
        "enhanced_route_optimizer.py",
        "database.py",
        "scenario_specific_queries.sql",
        "single_comprehensive_query.sql",
        "analysis_queries.sql",
        "find_agents_25_to_59.sql",
        "check_agents_with_prospects.sql",
        "analyze_mix_b10_agent.sql",
        "create_indexes.py",
        "create_optimized_indexes.sql",
        "run_production_pipeline.py",
        "test_performance.py"
    ]

    # Copy files that exist
    copied_files = []
    for file in important_files:
        if os.path.exists(file):
            shutil.copy2(file, package_dir)
            copied_files.append(file)
            print(f"COPIED: {file}")
        else:
            print(f"NOT FOUND: {file}")

    # Create README for the package
    readme_content = """# Route Optimization Package

## Files Included:

### Core Pipeline Files:
- run_specific_agents.py - Main script to run pipeline for specific agents
- scalable_route_optimizer.py - Optimized for large datasets (5.8M prospects)
- enhanced_route_optimizer.py - Base route optimizer with TSP
- database.py - Database connection module

### SQL Queries:
- scenario_specific_queries.sql - All analysis queries by scenario
- single_comprehensive_query.sql - Single query for complex analysis
- analysis_queries.sql - Complete query collection
- find_agents_25_to_59.sql - Find agents with 25-59 customers
- check_agents_with_prospects.sql - Check prospect availability

### Performance & Setup:
- create_indexes.py - Create database performance indexes
- create_optimized_indexes.sql - Index creation SQL
- run_production_pipeline.py - Full production pipeline
- test_performance.py - Performance testing

## Key Matching Logic:
routedata.barangay_code = prospective.barangay_code

## Usage:
1. Set up database connection in .env file
2. Run create_indexes.py for performance
3. Use run_specific_agents.py for targeted processing
4. Use scenario queries for analysis

## Barangay Code Fix Applied:
- Customers: Use barangay_code from routedata
- Prospects: Use Barangay_code from prospective table
"""

    with open(os.path.join(package_dir, "README.md"), 'w') as f:
        f.write(readme_content)

    # Create zip file
    zip_filename = "route_optimization_package.zip"
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, package_dir)
                zipf.write(file_path, arcname)

    print(f"\nPackage created: {zip_filename}")
    print(f"Contains {len(copied_files)} files")
    print(f"Ready for download!")

    # Clean up temp directory
    shutil.rmtree(package_dir)

if __name__ == "__main__":
    create_package()