#!/usr/bin/env python3
"""
Route Optimization Pipeline for Specific Agents
Run TSP optimization for selected agent-date combinations
"""

import sys
import os
import pandas as pd
import numpy as np
from math import radians, cos, sin, asin, sqrt
from datetime import datetime

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

def get_distributor_location(db, distributor_id):
    """Get distributor location"""
    try:
        distributor_query = f"""
        SELECT TOP 1
            distlat as Latitude,
            distlong as Longitude,
            distributorname as Name
        FROM routedata
        WHERE distributorid = '{distributor_id}'
        AND distlat IS NOT NULL
        AND distlong IS NOT NULL
        AND distlat != 0
        AND distlong != 0
        """

        distributor_df = db.execute_query_df(distributor_query)

        if distributor_df is not None and not distributor_df.empty:
            distributor = distributor_df.iloc[0]
            print(f"Distributor: {distributor['Name']}")
            print(f"Location: ({distributor['Latitude']:.6f}, {distributor['Longitude']:.6f})")
            return distributor['Latitude'], distributor['Longitude']
        else:
            print("Using default distributor location")
            return 14.663813, 121.122687  # SKYSCOPE coordinates

    except Exception as e:
        print(f"Error getting distributor location: {e}")
        return 14.663813, 121.122687

def solve_tsp_from_distributor(locations_df, distributor_lat, distributor_lon, agent, date):
    """Solve TSP starting from distributor location"""
    if len(locations_df) <= 1:
        locations_df['optimized_stopno'] = 1
        return locations_df

    print(f"  Starting TSP from distributor ({distributor_lat:.6f}, {distributor_lon:.6f})")

    # Find the customer closest to distributor as first stop
    distances_from_distributor = []
    for _, row in locations_df.iterrows():
        dist = haversine_distance(distributor_lat, distributor_lon, row['latitude'], row['longitude'])
        distances_from_distributor.append(dist)

    # Start from the customer closest to distributor
    first_stop_idx = np.argmin(distances_from_distributor)
    unvisited = locations_df.copy().reset_index(drop=True)
    route = []

    # First stop: closest to distributor
    current_location = unvisited.iloc[first_stop_idx]
    route.append(current_location)
    unvisited = unvisited.drop(first_stop_idx).reset_index(drop=True)

    print(f"  First stop: Customer {current_location['CustNo']} (closest to distributor)")

    # Continue with nearest neighbor from first stop
    while not unvisited.empty:
        current_lat = current_location['latitude']
        current_lon = current_location['longitude']

        # Find nearest unvisited location
        distances = []
        for _, row in unvisited.iterrows():
            dist = haversine_distance(current_lat, current_lon, row['latitude'], row['longitude'])
            distances.append(dist)

        nearest_idx = np.argmin(distances)
        current_location = unvisited.iloc[nearest_idx]
        route.append(current_location)
        unvisited = unvisited.drop(unvisited.index[nearest_idx]).reset_index(drop=True)

    # Create result dataframe with optimized stop numbers
    result_df = pd.DataFrame(route)
    result_df['optimized_stopno'] = range(1, len(result_df) + 1)

    print(f"  TSP completed: {len(result_df)} customers optimized")

    return result_df

def insert_optimized_route(db, route_df, agent, date):
    """Insert optimized route into routeplan_ai table"""
    success_count = 0
    error_count = 0

    print(f"  Inserting {len(route_df)} optimized records...")

    for _, row in route_df.iterrows():
        try:
            # Handle null/invalid coordinates
            lat = row['latitude']
            lon = row['longitude']

            # Convert to float if valid, otherwise use None
            try:
                lat_val = float(lat) if pd.notna(lat) and lat != 0 else None
                lon_val = float(lon) if pd.notna(lon) and lon != 0 else None
            except (ValueError, TypeError):
                lat_val = None
                lon_val = None

            # Insert into routeplan_ai table using its column structure
            insert_query = """
            INSERT INTO routeplan_ai
            (salesagent, custno, custype, latitude, longitude, stopno, routedate, barangay, barangay_code, is_visited)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            params = (
                agent,                                      # salesagent
                str(row['CustNo']),                        # custno
                str(row.get('custype', 'customer')),       # custype
                lat_val,                                   # latitude
                lon_val,                                   # longitude
                int(row['optimized_stopno']),              # stopno
                date,                                      # routedate
                str(row.get('barangay', '')),              # barangay
                str(row.get('barangay_code', '')),         # barangay_code
                0                                          # is_visited (default to 0)
            )

            result = db.execute_insert(insert_query, params)
            if result:
                success_count += 1
            else:
                error_count += 1

            if (success_count + error_count) % 20 == 0:
                print(f"    Progress: {success_count + error_count}/{len(route_df)} records processed")

        except Exception as e:
            error_count += 1
            if error_count <= 3:
                print(f"    Error inserting record: {e}")

    print(f"  RESULT: {success_count} successful, {error_count} errors")
    return success_count

def process_agent_route(db, agent, date, distributor_id):
    """Process route optimization for a specific agent and date"""
    print(f"\n{'='*60}")
    print(f"PROCESSING: Agent {agent} on {date}")
    print(f"{'='*60}")

    try:
        # Get ALL route data for this agent and date (including invalid coordinates)
        all_route_query = f"""
        SELECT
            Code as agent,
            CustNo,
            RouteDate as routedate,
            latitude,
            longitude,
            barangay_code,
            custype
        FROM routedata
        WHERE distributorid = '{distributor_id}'
        AND Code = '{agent}'
        AND RouteDate = '{date}'
        ORDER BY CustNo
        """

        all_route_df = db.execute_query_df(all_route_query)

        if all_route_df is None or all_route_df.empty:
            print(f"ERROR: No route data found for {agent} on {date}")
            return False

        # Separate valid and invalid coordinate records
        valid_coords = all_route_df[
            (all_route_df['latitude'].notna()) &
            (all_route_df['longitude'].notna()) &
            (all_route_df['latitude'] != 0) &
            (all_route_df['longitude'] != 0)
        ]

        invalid_coords = all_route_df[
            (all_route_df['latitude'].isna()) |
            (all_route_df['longitude'].isna()) |
            (all_route_df['latitude'] == 0) |
            (all_route_df['longitude'] == 0)
        ]

        total_customers = len(all_route_df)
        valid_count = len(valid_coords)
        invalid_count = len(invalid_coords)

        print(f"SUCCESS: Found {total_customers} total customers")
        print(f"  - {valid_count} customers with valid coordinates")
        print(f"  - {invalid_count} customers with invalid coordinates")

        # Process records based on coordinate validity
        final_route = pd.DataFrame()

        if valid_count > 0:
            # Get distributor location
            distributor_lat, distributor_lon = get_distributor_location(db, distributor_id)

            # Apply TSP optimization to valid coordinates
            print(f"Applying TSP optimization to {valid_count} customers with valid coordinates...")
            optimized_valid = solve_tsp_from_distributor(valid_coords, distributor_lat, distributor_lon, agent, date)

            # Calculate route improvement metrics
            total_optimized_distance = 0
            prev_lat, prev_lon = distributor_lat, distributor_lon
            for _, row in optimized_valid.iterrows():
                dist = haversine_distance(prev_lat, prev_lon, row['latitude'], row['longitude'])
                total_optimized_distance += dist
                prev_lat, prev_lon = row['latitude'], row['longitude']

            print(f"  Optimized route distance: {total_optimized_distance:.2f} km")
            final_route = optimized_valid

        # Handle invalid coordinates - assign stop number 100
        if invalid_count > 0:
            print(f"Assigning stop number 100 to {invalid_count} customers with invalid coordinates...")
            invalid_coords_copy = invalid_coords.copy()
            invalid_coords_copy['optimized_stopno'] = 100

            # Combine valid optimized route with invalid coordinate records
            if not final_route.empty:
                final_route = pd.concat([final_route, invalid_coords_copy], ignore_index=True)
            else:
                final_route = invalid_coords_copy

        # Insert ALL records (100% upload)
        print(f"Uploading 100% of records ({len(final_route)} total customers)...")
        records_inserted = insert_optimized_route(db, final_route, agent, date)

        if records_inserted == total_customers:
            print(f"SUCCESS: {agent} on {date} - {records_inserted}/{total_customers} records (100%) uploaded")
            return True
        else:
            print(f"WARNING: {agent} on {date} - Only {records_inserted}/{total_customers} records uploaded")
            return records_inserted > 0

    except Exception as e:
        print(f"ERROR processing {agent} on {date}: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_agent_pipeline():
    """Run route optimization pipeline for specific agents"""
    print("ROUTE OPTIMIZATION PIPELINE FOR SPECIFIC AGENTS")
    print("=" * 70)

    # Target agents and dates
    agent_dates = [
        ("SK-SAT5", "2025-09-03"),
        ("SK-SAT4", "2025-09-11"),
        ("PVM-PRE01", "2025-09-08"),
        ("SK-SAT4", "2025-09-27"),
        ("PVM-PRE02", "2025-09-25")
    ]

    distributor_id = "11814"

    print(f"Distributor ID: {distributor_id}")
    print(f"Target Agents: {len(agent_dates)} agent-date combinations")
    for agent, date in agent_dates:
        print(f"  - {agent} on {date}")
    print()

    db = None
    successful_optimizations = 0

    try:
        # Connect to database
        db = DatabaseConnection()
        db.connect()
        print("Database connection successful!")

        # Using existing routeplan_ai table
        print("Using existing routeplan_ai table for optimized routes")

        # Process each agent-date combination
        for agent, date in agent_dates:
            success = process_agent_route(db, agent, date, distributor_id)
            if success:
                successful_optimizations += 1

        # Final summary
        print(f"\n" + "=" * 70)
        print("ROUTE OPTIMIZATION PIPELINE COMPLETED!")
        print("=" * 70)
        print(f"SUCCESS: Processed {len(agent_dates)} agent-date combinations")
        print(f"SUCCESS: {successful_optimizations} successful optimizations")
        print(f"SUCCESS: Results stored in routeplan_ai table")

        if successful_optimizations < len(agent_dates):
            failed = len(agent_dates) - successful_optimizations
            print(f"WARNING: {failed} optimizations failed")

        # Show summary of optimized routes
        summary_query = """
        SELECT salesagent as agent, routedate, COUNT(*) as customers,
               CASE WHEN stopno = 100 THEN 'No_coordinates_stop_100' ELSE 'TSP_from_distributor' END as optimization_method
        FROM routeplan_ai
        WHERE salesagent IN ('SK-SAT5', 'SK-SAT4', 'PVM-PRE01', 'PVM-PRE02')
        AND routedate IN ('2025-09-03', '2025-09-11', '2025-09-08', '2025-09-27', '2025-09-25')
        GROUP BY salesagent, routedate, CASE WHEN stopno = 100 THEN 'No_coordinates_stop_100' ELSE 'TSP_from_distributor' END
        ORDER BY salesagent, routedate
        """

        summary_df = db.execute_query_df(summary_query)
        if summary_df is not None and not summary_df.empty:
            print(f"\nOptimized Routes Summary:")
            print(summary_df.to_string(index=False))

        print("=" * 70)

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
        run_agent_pipeline()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()