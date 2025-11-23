#!/usr/bin/env python3
"""
Clear Agent 914 Records - Remove existing records for fresh insertion
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def clear_agent_914_records():
    """Clear all existing records for Agent 914"""
    print("CLEARING EXISTING RECORDS FOR AGENT 914")
    print("=" * 50)

    agent_id = "914"

    db = None

    try:
        # Connect to database
        db = DatabaseConnection()
        db.connect()
        print("Database connection successful!")

        # Check existing records
        print(f"\nChecking existing records for Agent {agent_id}...")
        count_query = f"""
        SELECT COUNT(*) as count
        FROM routeplan_ai
        WHERE salesagent = '{agent_id}'
        """

        count_result = db.execute_query_df(count_query)
        if count_result is not None and not count_result.empty:
            existing_count = count_result.iloc[0]['count']
            print(f"Found {existing_count} existing records for Agent {agent_id}")

            if existing_count > 0:
                # Delete existing records
                print(f"Deleting existing records...")
                delete_query = f"""
                DELETE FROM routeplan_ai
                WHERE salesagent = '{agent_id}'
                """

                # Use execute_query for DELETE operation
                db.execute_query(delete_query)
                print(f"SUCCESS: Deleted {existing_count} records for Agent {agent_id}")

                # Verify deletion
                verify_result = db.execute_query_df(count_query)
                if verify_result is not None and not verify_result.empty:
                    remaining_count = verify_result.iloc[0]['count']
                    print(f"Verification: {remaining_count} records remaining for Agent {agent_id}")
            else:
                print(f"No existing records found for Agent {agent_id}")

        print(f"\n" + "=" * 50)
        print("AGENT 914 RECORDS CLEARED!")
        print("=" * 50)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    clear_agent_914_records()