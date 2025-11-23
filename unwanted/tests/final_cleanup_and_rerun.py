#!/usr/bin/env python3
"""
Final cleanup - remove all duplicates and rerun cleanly
"""

from database import DatabaseConnection
import subprocess
import sys

def final_cleanup_and_rerun():
    """Remove all data for test agents and rerun cleanly"""
    print("FINAL CLEANUP AND CLEAN RERUN")
    print("=" * 35)

    db = None
    try:
        db = DatabaseConnection()
        db.connect()

        # Remove ALL data for our test agents
        print("1. Removing ALL existing data for agents 914, 10551, and SK-PMS2...")

        clear_query = """
        DELETE FROM routeplan_ai
        WHERE salesagent IN ('914', '10551', 'SK-PMS2')
        """

        db.execute_query(clear_query)
        print("   All existing data cleared")

        # Verify cleanup
        check_query = """
        SELECT COUNT(*) FROM routeplan_ai
        WHERE salesagent IN ('914', '10551', 'SK-PMS2')
        """

        result = db.execute_query(check_query)
        remaining_count = result[0][0] if result else 0
        print(f"   Remaining records: {remaining_count}")

    except Exception as e:
        print(f"Error during cleanup: {e}")
        return

    finally:
        if db:
            db.close()

    # Clean rerun
    print("\n2. Running clean pipeline with fixed barangay_code logic...")
    try:
        result = subprocess.run([sys.executable, "run_specific_agents.py"],
                              capture_output=True, text=True, cwd=".")
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
    except Exception as e:
        print(f"Error running pipeline: {e}")

    # Final verification
    print("\n3. Final verification of barangay_code values...")
    try:
        result = subprocess.run([sys.executable, "check_barangay_code_issue.py"],
                              capture_output=True, text=True, cwd=".")
        # Only show the prospect entries part
        lines = result.stdout.split('\n')
        in_prospect_section = False
        for line in lines:
            if "Checking prospect entries specifically:" in line:
                in_prospect_section = True
            elif "Checking source prospect data:" in line:
                in_prospect_section = False

            if in_prospect_section:
                print(line)

    except Exception as e:
        print(f"Error during verification: {e}")

if __name__ == "__main__":
    final_cleanup_and_rerun()