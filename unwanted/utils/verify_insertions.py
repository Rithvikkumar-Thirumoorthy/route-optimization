#!/usr/bin/env python3
"""
Verify Route Insertions - Check if records were actually inserted
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def verify_route_insertions():
    """Verify if route records were actually inserted into routeplan_ai"""
    print("VERIFYING ROUTE INSERTIONS FOR AGENT 914")
    print("=" * 50)

    agent_id = "914"
    barangay_code = "137403027"
    start_date = "2025-09-23"

    db = None

    try:
        # Connect to database
        db = DatabaseConnection()
        db.connect()
        print("Database connection successful!")

        # Check total records for agent 914
        print(f"\nChecking records for Agent {agent_id}...")

        total_query = f"""
        SELECT COUNT(*) as total_records
        FROM routeplan_ai
        WHERE salesagent = '{agent_id}'
        AND routedate >= '{start_date}'
        """

        total_result = db.execute_query_df(total_query)
        if total_result is not None and not total_result.empty:
            total_records = total_result.iloc[0]['total_records']
            print(f"Total records found: {total_records}")
        else:
            print("No records found!")
            return

        # Check records by date
        print(f"\nBreakdown by date:")

        date_query = f"""
        SELECT
            routedate,
            COUNT(*) as count,
            MIN(stopno) as min_stop,
            MAX(stopno) as max_stop,
            COUNT(DISTINCT barangay_code) as unique_barangays
        FROM routeplan_ai
        WHERE salesagent = '{agent_id}'
        AND routedate >= '{start_date}'
        GROUP BY routedate
        ORDER BY routedate
        """

        date_results = db.execute_query_df(date_query)
        if date_results is not None and not date_results.empty:
            total_verified = 0
            for _, row in date_results.iterrows():
                print(f"  {row['routedate']}: {row['count']} records (stops {row['min_stop']}-{row['max_stop']})")
                total_verified += row['count']

            print(f"\nTotal verified records: {total_verified}")

        # Check barangay distribution
        print(f"\nBarangay distribution:")

        barangay_query = f"""
        SELECT
            barangay_code,
            COUNT(*) as count
        FROM routeplan_ai
        WHERE salesagent = '{agent_id}'
        AND routedate >= '{start_date}'
        GROUP BY barangay_code
        ORDER BY count DESC
        """

        barangay_results = db.execute_query_df(barangay_query)
        if barangay_results is not None and not barangay_results.empty:
            for _, row in barangay_results.iterrows():
                print(f"  Barangay {row['barangay_code']}: {row['count']} records")

        # Check prospect types
        print(f"\nCustomer types:")

        type_query = f"""
        SELECT
            custype,
            COUNT(*) as count
        FROM routeplan_ai
        WHERE salesagent = '{agent_id}'
        AND routedate >= '{start_date}'
        GROUP BY custype
        """

        type_results = db.execute_query_df(type_query)
        if type_results is not None and not type_results.empty:
            for _, row in type_results.iterrows():
                print(f"  {row['custype']}: {row['count']} records")

        print(f"\n" + "=" * 50)
        print("VERIFICATION COMPLETED!")
        print("=" * 50)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    verify_route_insertions()