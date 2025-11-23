#!/usr/bin/env python3
"""
Clear existing data for our test agents and rerun with fixed barangay_code logic
"""

from database import DatabaseConnection
import subprocess
import sys

def clear_and_rerun():
    """Clear existing data and rerun pipeline"""
    print("CLEARING EXISTING DATA AND RERUNNING PIPELINE")
    print("=" * 50)

    db = None
    try:
        db = DatabaseConnection()
        db.connect()

        # Clear existing data for our test agents
        print("1. Clearing existing data for agents 914 and SK-PMS2...")

        clear_query = """
        DELETE FROM routeplan_ai
        WHERE salesagent IN ('914', 'SK-PMS2')
        """

        db.execute_query(clear_query)
        print("   Existing data cleared")

        # Check what was deleted
        check_query = """
        SELECT COUNT(*) FROM routeplan_ai
        WHERE salesagent IN ('914', 'SK-PMS2')
        """

        result = db.execute_query(check_query)
        remaining_count = result[0][0] if result else 0
        print(f"   Remaining records for these agents: {remaining_count}")

    except Exception as e:
        print(f"Error clearing data: {e}")
        return

    finally:
        if db:
            db.close()

    # Rerun the pipeline
    print("\n2. Rerunning pipeline with fixed barangay_code logic...")
    try:
        result = subprocess.run([sys.executable, "run_specific_agents.py"],
                              capture_output=True, text=True, cwd=".")
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
    except Exception as e:
        print(f"Error running pipeline: {e}")

if __name__ == "__main__":
    clear_and_rerun()