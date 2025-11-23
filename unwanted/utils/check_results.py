#!/usr/bin/env python3
"""
Check Results - Verify what was inserted into routeplan_ai
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def check_results():
    """Check what routes were created"""
    db = DatabaseConnection()
    db.connect()

    print("Checking Route Results in routeplan_ai")
    print("=" * 40)

    # Check for our specific agents
    agents_to_check = [
        ("SK-SAT8", "2025-09-04"),
        ("D304", "2025-09-16"),
        ("WesZamVan 3", "2025-09-01"),
        ("TDI-PMS6", "2025-09-24"),
        ("D303", "2025-09-29")
    ]

    total_found = 0

    for agent_id, route_date in agents_to_check:
        print(f"\nChecking Agent: {agent_id}, Date: {route_date}")
        print("-" * 30)

        # Check if records exist
        check_query = f"""
        SELECT
            COUNT(*) as total_records,
            SUM(CASE WHEN custype = 'customer' THEN 1 ELSE 0 END) as customers,
            SUM(CASE WHEN custype = 'prospect' THEN 1 ELSE 0 END) as prospects,
            SUM(CASE WHEN stopno = 100 THEN 1 ELSE 0 END) as stop100_count,
            MIN(stopno) as min_stopno,
            MAX(stopno) as max_stopno
        FROM routeplan_ai
        WHERE salesagent = '{agent_id}' AND routedate = '{route_date}'
        """

        result = db.execute_query_df(check_query)
        if result is not None and not result.empty:
            row = result.iloc[0]
            total_records = row['total_records']

            if total_records > 0:
                print(f"   SUCCESS: Found {total_records} route records")
                print(f"   Customers: {row['customers']}")
                print(f"   Prospects: {row['prospects']}")
                print(f"   Stop100: {row['stop100_count']}")
                print(f"   Stop numbers: {row['min_stopno']} to {row['max_stopno']}")
                total_found += total_records

                # Sample records
                sample_query = f"""
                SELECT TOP 5 custno, custype, stopno, latitude, longitude, barangay_code
                FROM routeplan_ai
                WHERE salesagent = '{agent_id}' AND routedate = '{route_date}'
                ORDER BY stopno
                """

                sample_result = db.execute_query_df(sample_query)
                if sample_result is not None and not sample_result.empty:
                    print(f"   Sample records:")
                    for _, sample_row in sample_result.iterrows():
                        print(f"     Stop {sample_row['stopno']}: {sample_row['custno']} ({sample_row['custype']})")
            else:
                print(f"   No records found")
        else:
            print(f"   Query failed")

    # Overall summary
    print(f"\n" + "=" * 40)
    print(f"SUMMARY")
    print("=" * 40)
    print(f"Total route records created: {total_found}")

    # Recent records in routeplan_ai
    recent_query = """
    SELECT TOP 10
        salesagent,
        routedate,
        COUNT(*) as records,
        SUM(CASE WHEN custype = 'customer' THEN 1 ELSE 0 END) as customers,
        SUM(CASE WHEN custype = 'prospect' THEN 1 ELSE 0 END) as prospects
    FROM routeplan_ai
    GROUP BY salesagent, routedate
    ORDER BY salesagent, routedate DESC
    """

    recent_result = db.execute_query_df(recent_query)
    if recent_result is not None and not recent_result.empty:
        print(f"\nRecent routes in database:")
        for _, row in recent_result.iterrows():
            print(f"   {row['salesagent']} ({row['routedate']}): {row['records']} records")

    db.close()

def main():
    """Main function"""
    try:
        check_results()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()