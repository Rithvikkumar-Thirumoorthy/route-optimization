#!/usr/bin/env python3
"""
Check Database Table - Verify routeplan_ai table structure and all records
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def check_database_table():
    """Check the routeplan_ai table structure and contents"""
    print("CHECKING DATABASE TABLE: routeplan_ai")
    print("=" * 50)

    db = None

    try:
        # Connect to database
        db = DatabaseConnection()
        db.connect()
        print("Database connection successful!")

        # Check table structure
        print(f"\nChecking table structure...")
        structure_query = """
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'routeplan_ai'
        ORDER BY ORDINAL_POSITION
        """

        structure_result = db.execute_query_df(structure_query)
        if structure_result is not None and not structure_result.empty:
            print("Table structure:")
            for _, row in structure_result.iterrows():
                print(f"  {row['COLUMN_NAME']}: {row['DATA_TYPE']} ({row['IS_NULLABLE']})")
        else:
            print("Could not retrieve table structure!")

        # Check total records in table
        print(f"\nChecking total records in routeplan_ai...")
        total_query = """
        SELECT COUNT(*) as total_records
        FROM routeplan_ai
        """

        total_result = db.execute_query_df(total_query)
        if total_result is not None and not total_result.empty:
            total_records = total_result.iloc[0]['total_records']
            print(f"Total records in table: {total_records}")
        else:
            print("Could not count records!")

        if total_records > 0:
            # Check recent records
            print(f"\nChecking recent records...")
            recent_query = """
            SELECT TOP 10
                salesagent,
                custno,
                custype,
                routedate,
                stopno,
                barangay_code
            FROM routeplan_ai
            ORDER BY routedate DESC, stopno
            """

            recent_result = db.execute_query_df(recent_query)
            if recent_result is not None and not recent_result.empty:
                print("Recent records:")
                for _, row in recent_result.iterrows():
                    print(f"  Agent: {row['salesagent']}, Date: {row['routedate']}, Stop: {row['stopno']}, Customer: {row['custno']}")

            # Check by agent
            print(f"\nChecking records by agent...")
            agent_query = """
            SELECT
                salesagent,
                COUNT(*) as count,
                MIN(routedate) as first_date,
                MAX(routedate) as last_date
            FROM routeplan_ai
            GROUP BY salesagent
            ORDER BY salesagent
            """

            agent_result = db.execute_query_df(agent_query)
            if agent_result is not None and not agent_result.empty:
                print("Records by agent:")
                for _, row in agent_result.iterrows():
                    print(f"  Agent {row['salesagent']}: {row['count']} records ({row['first_date']} to {row['last_date']})")

        print(f"\n" + "=" * 50)
        print("DATABASE CHECK COMPLETED!")
        print("=" * 50)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    check_database_table()