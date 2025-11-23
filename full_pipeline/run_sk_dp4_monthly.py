#!/usr/bin/env python3
"""
Run prospect-only routes for SK-DP4 agent for entire month
Starting location: 14.663813, 121.122687 (near Binangonan area)
"""

import subprocess
import sys
from datetime import datetime

def run_sk_dp4_monthly():
    """Run prospect routes for SK-DP4 for entire month"""

    # Configuration
    distributor_id = "11814"
    agent_id = "SK-DP4"
    start_date = "2025-01-01"  # Change this to your desired start date
    num_days = 30  # Full month
    prospects_per_day = 60

    # Starting location (Binangonan area)
    start_lat = 14.663813
    start_lon = 121.122687

    # Barangay codes near starting location - UPDATE THESE WITH ACTUAL NEARBY BARANGAYS
    # You can specify multiple barangays comma-separated
    # Example barangays (these are examples - replace with actual nearby barangay codes)
    barangays = "137403027,137403028,137403029"  # UPDATE WITH ACTUAL BARANGAY CODES

    print("=" * 80)
    print("SK-DP4 MONTHLY PROSPECT ROUTE CREATION")
    print("=" * 80)
    print(f"Agent: {agent_id}")
    print(f"Distributor: {distributor_id}")
    print(f"Start Date: {start_date}")
    print(f"Number of Days: {num_days}")
    print(f"Prospects per Day: {prospects_per_day}")
    print(f"Starting Location: ({start_lat}, {start_lon})")
    print(f"Barangays: {barangays}")
    print("=" * 80)
    print("\nWARNING: This will create routes for the ENTIRE MONTH")
    print("Prospects will be EXCLUDED if they are already in:")
    print("  - MonthlyRoutePlan_temp")
    print("  - custvist")
    print("=" * 80)

    # Confirm before proceeding
    response = input("\nDo you want to run in TEST MODE first? (yes/no): ")
    test_mode = response.lower() == 'yes'

    # Build command
    cmd = [
        "python",
        "run_prospect_only_routes.py",
        "--distributor", distributor_id,
        "--agent", agent_id,
        "--start-date", start_date,
        "--num-days", str(num_days),
        "--prospects-per-day", str(prospects_per_day),
        "--barangays", barangays,
        "--start-lat", str(start_lat),
        "--start-lon", str(start_lon)
    ]

    if test_mode:
        cmd.append("--test")
        print("\n*** RUNNING IN TEST MODE - NO DATABASE CHANGES ***\n")
    else:
        print("\n*** RUNNING IN LIVE MODE - WILL MODIFY DATABASE ***\n")
        confirm = input("Type 'CONFIRM' to proceed: ")
        if confirm != 'CONFIRM':
            print("Cancelled.")
            return

    # Run the command
    print(f"\nExecuting: {' '.join(cmd)}\n")
    subprocess.run(cmd)

if __name__ == "__main__":
    run_sk_dp4_monthly()
