#!/usr/bin/env python3
"""
Create Prospect Route - Agent 914
Create new route with 60 prospects from barangay '137403027'
for agent 914, starting from 2025-09-23
"""

import sys
import os
import pandas as pd
from datetime import datetime
from math import radians, cos, sin, asin, sqrt

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on Earth"""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

def solve_tsp_nearest_neighbor(locations_df):
    """Simple TSP using nearest neighbor heuristic"""
    if len(locations_df) <= 1:
        locations_df['stopno'] = 1
        return locations_df

    # Start from first location
    unvisited = locations_df.copy()
    route = []
    current_idx = 0
    current_location = unvisited.iloc[current_idx]
    route.append(current_location)
    unvisited = unvisited.drop(unvisited.index[current_idx])

    # Build route using nearest neighbor
    while not unvisited.empty:
        current_lat = current_location['Latitude']
        current_lon = current_location['Longitude']

        # Find nearest unvisited location
        distances = unvisited.apply(
            lambda row: haversine_distance(
                current_lat, current_lon, row['Latitude'], row['Longitude']
            ), axis=1
        )

        nearest_idx = distances.idxmin()
        current_location = unvisited.loc[nearest_idx]
        route.append(current_location)
        unvisited = unvisited.drop(nearest_idx)

    # Create result dataframe with stop numbers
    result_df = pd.DataFrame(route)
    result_df['stopno'] = range(1, len(result_df) + 1)

    return result_df

def create_prospect_route():
    """Create route with 60 prospects for agent 914"""
    print("CREATING PROSPECT ROUTE FOR AGENT 914")
    print("=" * 50)

    # Configuration
    agent_id = "914"
    barangay_code = "137403027"  
    route_date = "2025-09-23"
    target_stops = 60

    print(f"Agent ID: {agent_id}")
    print(f"Barangay Code: {barangay_code}")
    print(f"Route Date: {route_date}")
    print(f"Target Stops: {target_stops}")
    print()

    db = None

    try:
        # Connect to database
        db = DatabaseConnection()
        db.connect()
        print("Database connection successful!")

        # Step 1: Get prospects from specific barangay
        print(f"\nStep 1: Getting prospects from barangay {barangay_code}...")

        prospects_query = f"""
        SELECT TOP {target_stops}
            CustNo,
            OutletName,
            Latitude,
            Longitude,
            Barangay,
            barangay_code,
            Custype
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
            print(f"ERROR: No prospects found in barangay {barangay_code}")
            return

        actual_stops = len(prospects_df)
        print(f"SUCCESS: Found {actual_stops} prospects in barangay {barangay_code}")

        if actual_stops < target_stops:
            print(f"WARNING: Only {actual_stops} prospects available (target: {target_stops})")

        # Step 2: Optimize route using TSP
        print(f"\nStep 2: Optimizing route with TSP algorithm...")

        # Run TSP optimization directly on prospects
        optimized_route = solve_tsp_nearest_neighbor(prospects_df)
        print(f"SUCCESS: TSP optimization completed for {len(optimized_route)} locations")

        # Step 3: Prepare route data for insertion
        print(f"\nStep 3: Preparing route data for insertion...")

        route_records = []
        for _, prospect in optimized_route.iterrows():
            route_data = {
                'salesagent': agent_id,
                'custno': str(prospect['CustNo']),
                'custype': 'prospect',
                'latitude': float(prospect['Latitude']) if pd.notna(prospect['Latitude']) else None,
                'longitude': float(prospect['Longitude']) if pd.notna(prospect['Longitude']) else None,
                'stopno': int(prospect['stopno']),  # TSP assigns stopno 1,2,3...
                'routedate': route_date,
                'barangay': str(prospect.get('Barangay', '')),
                'barangay_code': str(prospect['barangay_code']),
                'is_visited': 0
            }
            route_records.append(route_data)

        print(f"SUCCESS: Prepared {len(route_records)} route records")

        # Step 4: Insert into routeplan_ai
        print(f"\nStep 4: Inserting route into routeplan_ai...")

        # Build insert query
        if route_records:
            # Create values for bulk insert
            values_list = []
            for record in route_records:
                lat_val = record['latitude'] if record['latitude'] is not None else 'NULL'
                lon_val = record['longitude'] if record['longitude'] is not None else 'NULL'

                values = f"""('{record['salesagent']}', '{record['custno']}', '{record['custype']}',
                           {lat_val}, {lon_val}, {record['stopno']}, '{record['routedate']}',
                           '{record['barangay']}', '{record['barangay_code']}', {record['is_visited']})"""
                values_list.append(values)

            # Execute bulk insert
            insert_query = f"""
            INSERT INTO routeplan_ai
            (salesagent, custno, custype, latitude, longitude, stopno, routedate, barangay, barangay_code, is_visited)
            VALUES {','.join(values_list)}
            """

            db.execute_query(insert_query)
            print(f"SUCCESS: Inserted {len(route_records)} prospect records")

        # Step 5: Verify results
        print(f"\nStep 5: Verifying insertion...")

        verify_query = f"""
        SELECT
            COUNT(*) as total_records,
            MIN(stopno) as min_stop,
            MAX(stopno) as max_stop,
            COUNT(DISTINCT barangay_code) as unique_barangays
        FROM routeplan_ai
        WHERE salesagent = '{agent_id}' AND routedate = '{route_date}'
        """

        verification = db.execute_query_df(verify_query)
        if verification is not None and not verification.empty:
            result = verification.iloc[0]
            print(f"SUCCESS: Verification successful:")
            print(f"  - Total records: {result['total_records']}")
            print(f"  - Stop range: {result['min_stop']} to {result['max_stop']}")
            print(f"  - Unique barangays: {result['unique_barangays']}")

        # Summary
        print(f"\n" + "=" * 50)
        print("PROSPECT ROUTE CREATION COMPLETED!")
        print("=" * 50)
        print(f"SUCCESS: Agent: {agent_id}")
        print(f"SUCCESS: Route Date: {route_date}")
        print(f"SUCCESS: Prospects Added: {len(route_records)}")
        print(f"SUCCESS: Barangay: {barangay_code}")
        print(f"SUCCESS: TSP Optimized: Yes")
        print(f"SUCCESS: Target Table: routeplan_ai")
        print("=" * 50)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

def main():
    """Main function"""
    try:
        create_prospect_route()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()