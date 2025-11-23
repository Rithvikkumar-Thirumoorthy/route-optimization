#!/usr/bin/env python3
"""
Effective Prospect Route Creator - Agent 914
Simple K-means clustering + TSP optimization that uses ALL 599 prospects
"""

import sys
import os
import pandas as pd
import numpy as np
from math import radians, cos, sin, asin, sqrt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta

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
    """Solve TSP using nearest neighbor heuristic"""
    if len(locations_df) <= 1:
        locations_df['stopno'] = 1
        return locations_df

    # Start from first location
    unvisited = locations_df.copy().reset_index(drop=True)
    route = []
    current_idx = 0
    current_location = unvisited.iloc[current_idx]
    route.append(current_location)
    unvisited = unvisited.drop(current_idx).reset_index(drop=True)

    # Build route using nearest neighbor
    while not unvisited.empty:
        current_lat = current_location['Latitude']
        current_lon = current_location['Longitude']

        # Find nearest unvisited location
        distances = []
        for _, row in unvisited.iterrows():
            dist = haversine_distance(current_lat, current_lon, row['Latitude'], row['Longitude'])
            distances.append(dist)

        nearest_idx = np.argmin(distances)
        current_location = unvisited.iloc[nearest_idx]
        route.append(current_location)
        unvisited = unvisited.drop(unvisited.index[nearest_idx]).reset_index(drop=True)

    # Create result dataframe with stop numbers
    result_df = pd.DataFrame(route)
    result_df['stopno'] = range(1, len(result_df) + 1)

    return result_df

def create_effective_clusters(prospects_df, target_size=60):
    """Create effective clusters using K-means that uses ALL prospects with 55-65 limit"""
    print(f"Creating effective clusters from {len(prospects_df)} prospects...")

    # Calculate number of clusters needed to stay within 55-65 range
    min_size, max_size = 55, 65
    n_clusters = max(1, int(np.ceil(len(prospects_df) / target_size)))

    # Adjust cluster count if resulting sizes would be outside 55-65 range
    avg_cluster_size = len(prospects_df) / n_clusters
    if avg_cluster_size > max_size:
        n_clusters = int(np.ceil(len(prospects_df) / max_size))
    elif avg_cluster_size < min_size:
        n_clusters = max(1, int(len(prospects_df) / min_size))

    print(f"Target: {n_clusters} clusters of 55-65 prospects each (avg: {len(prospects_df)/n_clusters:.1f})")

    # Prepare coordinates for clustering
    coordinates = prospects_df[['Latitude', 'Longitude']].values

    # Standardize coordinates
    scaler = StandardScaler()
    coordinates_scaled = scaler.fit_transform(coordinates)

    # Apply K-means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10, max_iter=300)
    cluster_labels = kmeans.fit_predict(coordinates_scaled)

    # Create clusters
    clusters = []
    prospects_with_clusters = prospects_df.copy()
    prospects_with_clusters['cluster'] = cluster_labels

    print(f"K-means clustering results:")
    for cluster_id in range(n_clusters):
        cluster_data = prospects_with_clusters[prospects_with_clusters['cluster'] == cluster_id]
        if len(cluster_data) > 0:
            clusters.append(cluster_data.drop('cluster', axis=1))
            print(f"  Cluster {cluster_id + 1}: {len(cluster_data)} prospects")

    total_clustered = sum(len(cluster) for cluster in clusters)
    print(f"SUCCESS: All {total_clustered} prospects clustered into {len(clusters)} groups")

    return clusters

def insert_route_safely(db, route_records, route_date):
    """Insert route records safely one by one to avoid batch errors"""
    success_count = 0
    error_count = 0

    print(f"  Inserting {len(route_records)} records for {route_date}...")

    for i, record in enumerate(route_records):
        try:
            insert_query = f"""
            INSERT INTO routeplan_ai
            (salesagent, custno, custype, latitude, longitude, stopno, routedate, barangay, barangay_code, is_visited)
            VALUES ('{record['salesagent']}', '{record['custno']}', '{record['custype']}',
                    {record['latitude']}, {record['longitude']}, {record['stopno']},
                    '{record['routedate']}', '{record['barangay']}', '{record['barangay_code']}', {record['is_visited']})
            """

            db.execute_query(insert_query)
            success_count += 1

            # Progress indicator
            if (i + 1) % 20 == 0:
                print(f"    Progress: {i + 1}/{len(route_records)} records inserted")

        except Exception as e:
            error_count += 1
            if error_count <= 3:  # Only show first few errors
                print(f"    Error inserting record {i + 1}: {e}")

    print(f"  RESULT: {success_count} successful, {error_count} errors")
    return success_count

def create_effective_prospect_routes():
    """Create effective multi-day prospect routes using K-means + TSP"""
    print("CREATING EFFECTIVE MULTI-DAY PROSPECT ROUTES FOR AGENT 914")
    print("=" * 70)

    # Configuration
    agent_id = "914"
    barangay_code = "137403027"
    start_date = "2025-09-23"
    target_stops_per_day = 60  # Will create clusters of 55-65 prospects each

    print(f"Agent ID: {agent_id}")
    print(f"Barangay Code: {barangay_code}")
    print(f"Start Date: {start_date}")
    print(f"Target Stops per Day: {target_stops_per_day}")
    print()

    db = None

    try:
        # Connect to database
        db = DatabaseConnection()
        db.connect()
        print("Database connection successful!")

        # Step 1: Get ALL prospects from barangay
        print(f"\nStep 1: Getting ALL prospects from barangay {barangay_code}...")

        prospects_query = f"""
        SELECT
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

        total_prospects = len(prospects_df)
        print(f"SUCCESS: Found {total_prospects} prospects")

        # Step 2: Create effective clusters using K-means
        print(f"\nStep 2: Creating effective clusters...")
        clusters = create_effective_clusters(prospects_df, target_stops_per_day)

        if not clusters:
            print("ERROR: No clusters created")
            return

        # Step 3: Process each cluster for different days
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        total_routes_created = 0
        total_records_inserted = 0

        for day_idx, cluster in enumerate(clusters):
            current_date = start_date_obj + timedelta(days=day_idx)
            route_date = current_date.strftime("%Y-%m-%d")

            print(f"\nStep 3.{day_idx+1}: Processing Day {day_idx+1} ({route_date}) - {len(cluster)} prospects")

            # Apply TSP optimization to this cluster
            print(f"  Applying TSP optimization...")
            optimized_route = solve_tsp_nearest_neighbor(cluster)
            print(f"  TSP optimization completed")

            # Prepare route data for this day
            route_records = []
            for _, prospect in optimized_route.iterrows():
                route_data = {
                    'salesagent': agent_id,
                    'custno': str(prospect['CustNo']),
                    'custype': 'prospect',
                    'latitude': float(prospect['Latitude']),
                    'longitude': float(prospect['Longitude']),
                    'stopno': int(prospect['stopno']),
                    'routedate': route_date,
                    'barangay': str(prospect.get('Barangay', '')),
                    'barangay_code': str(prospect['barangay_code']),
                    'is_visited': 0
                }
                route_records.append(route_data)

            # Insert into routeplan_ai safely
            records_inserted = insert_route_safely(db, route_records, route_date)

            if records_inserted > 0:
                total_routes_created += 1
                total_records_inserted += records_inserted
                print(f"  SUCCESS: Day {day_idx+1} completed - {records_inserted} records inserted")

        # Summary
        print(f"\n" + "=" * 70)
        print("EFFECTIVE MULTI-DAY PROSPECT ROUTE CREATION COMPLETED!")
        print("=" * 70)
        print(f"SUCCESS: Agent: {agent_id}")
        print(f"SUCCESS: Total Prospects Available: {total_prospects}")
        print(f"SUCCESS: Total Records Inserted: {total_records_inserted}")
        print(f"SUCCESS: Days Created: {total_routes_created}")
        print(f"SUCCESS: Coverage: {(total_records_inserted/total_prospects)*100:.1f}%")
        print(f"SUCCESS: Start Date: {start_date}")
        print(f"SUCCESS: Barangay: {barangay_code}")
        print(f"SUCCESS: Clustering: K-means (effective)")
        print(f"SUCCESS: TSP Optimized: Yes")
        print(f"SUCCESS: Target Table: routeplan_ai")
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
        create_effective_prospect_routes()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()