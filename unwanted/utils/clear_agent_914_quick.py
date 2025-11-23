#!/usr/bin/env python3
"""
Quick Clear Agent 914 Records
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def clear_agent_914():
    """Quick clear Agent 914 records"""
    print("Clearing Agent 914 records...")

    db = None
    try:
        db = DatabaseConnection()
        db.connect()

        # Delete using execute_insert (which handles commits properly)
        delete_query = "DELETE FROM routeplan_ai WHERE salesagent = ?"
        result = db.execute_insert(delete_query, ("914",))

        if result:
            print("SUCCESS: Agent 914 records cleared")
        else:
            print("ERROR: Failed to clear records")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        if db:
            db.close()

if __name__ == "__main__":
    clear_agent_914()