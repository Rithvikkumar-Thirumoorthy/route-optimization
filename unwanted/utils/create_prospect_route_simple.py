#!/usr/bin/env python3
"""
Simple Prospect Route Creator - Agent 914
Create route with prospects from barangay 137403027
"""

import sys
import os
import pandas as pd

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def create_simple_prospect_route():
    """Create simple prospect route without TSP"""
    print("CREATING SIMPLE PROSPECT ROUTE FOR AGENT 914")
    print("=" * 50)

    # Configuration
    agent_id = "914"
    barangay_code = "137403027"
    route_date = "2025-09-23"
    target_stops = 60

    print(f"Agent: {agent_id}")
    print(f"Barangay: {barangay_code}")
    print(f"Date: {route_date}")
    print(f"Target: {target_stops} stops")

    db = None
    try:
        # Connect to database
        db = DatabaseConnection()
        db.connect()
        print("Database connected!")

        # Get prospects
        print(f"\nGetting prospects from barangay {barangay_code}...")
        prospects_query = f"""
        SELECT TOP {target_stops}
            CustNo,
            OutletName,
            Latitude,
            Longitude,
            Barangay,
            barangay_code
        FROM prospective
        WHERE barangay_code = '{barangay_code}'
        AND Latitude IS NOT NULL
        AND Longitude IS NOT NULL
        AND Latitude != 0
        AND Longitude != 0
        ORDER BY CustNo
        """

        prospects_df = db.execute_query_df(prospects_query)

        if prospects_df is None or prospects_df.empty:
            print("No prospects found!")
            return

        actual_count = len(prospects_df)
        print(f"Found {actual_count} prospects")

        # Insert records one by one
        print(f"\nInserting {actual_count} records...")
        success_count = 0

        for i, (_, prospect) in enumerate(prospects_df.iterrows(), 1):
            try:
                insert_query = f"""
                INSERT INTO routeplan_ai
                (salesagent, custno, custype, latitude, longitude, stopno, routedate, barangay, barangay_code, is_visited)
                VALUES ('{agent_id}', '{prospect['CustNo']}', 'prospect',
                        {prospect['Latitude']}, {prospect['Longitude']}, {i},
                        '{route_date}', '{prospect.get('Barangay', '')}', '{prospect['barangay_code']}', 0)
                """

                db.execute_query(insert_query)
                success_count += 1

                if i % 10 == 0:
                    print(f"  Inserted {i}/{actual_count} records...")

            except Exception as e:
                print(f"  Error inserting record {i}: {e}")

        print(f"\nSUCCESS: Inserted {success_count}/{actual_count} records")

        # Verify
        print(f"\nVerifying results...")
        verify_query = f"""
        SELECT COUNT(*) as total, MIN(stopno) as min_stop, MAX(stopno) as max_stop
        FROM routeplan_ai
        WHERE salesagent = '{agent_id}' AND routedate = '{route_date}'
        """

        result = db.execute_query_df(verify_query)
        if result is not None and not result.empty:
            row = result.iloc[0]
            print(f"Verification: {row['total']} records, stops {row['min_stop']}-{row['max_stop']}")

        print(f"\n" + "=" * 50)
        print("PROSPECT ROUTE CREATION COMPLETED!")
        print(f"Agent 914 now has {success_count} prospect stops on {route_date}")
        print("=" * 50)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    create_simple_prospect_route()