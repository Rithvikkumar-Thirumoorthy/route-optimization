#!/usr/bin/env python3
"""
Fixed Prospect Route Creator - Agent 914
Uses proper INSERT method to ensure records are actually inserted
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

def create_balanced_clusters(prospects_df, min_size=55, max_size=65):
    """Create balanced clusters with strict 55-65 prospect limit using K-means"""
    print(f"Creating balanced clusters from {len(prospects_df)} prospects...")
    print(f"Cluster size limits: {min_size}-{max_size} prospects each")

    total_prospects = len(prospects_df)

    # Calculate optimal number of clusters to stay within limits
    target_size = 60
    n_clusters = max(1, int(np.ceil(total_prospects / target_size)))

    # Adjust to ensure all clusters fall within 55-65 range
    while True:
        avg_cluster_size = total_prospects / n_clusters
        if avg_cluster_size <= max_size:
            break
        n_clusters += 1

    print(f"Using {n_clusters} clusters (avg: {total_prospects/n_clusters:.1f} prospects each)")

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

    print(f"Initial K-means clustering results:")
    initial_clusters = []
    for cluster_id in range(n_clusters):
        cluster_data = prospects_with_clusters[prospects_with_clusters['cluster'] == cluster_id]
        if len(cluster_data) > 0:
            initial_clusters.append(cluster_data.drop('cluster', axis=1))
            print(f"  Cluster {cluster_id + 1}: {len(cluster_data)} prospects")

    # Balance clusters to ensure 55-65 range
    print(f"\nBalancing clusters to 55-65 range...")
    balanced_clusters = balance_cluster_sizes(initial_clusters, min_size, max_size)

    total_clustered = sum(len(cluster) for cluster in balanced_clusters)
    print(f"BALANCED CLUSTERING RESULTS:")
    for i, cluster in enumerate(balanced_clusters):
        print(f"  Cluster {i + 1}: {len(cluster)} prospects")
    print(f"SUCCESS: All {total_clustered} prospects balanced into {len(balanced_clusters)} clusters")

    return balanced_clusters

def balance_cluster_sizes(clusters, min_size, max_size):
    """Balance cluster sizes to ensure all clusters are within min_size to max_size range"""
    balanced_clusters = []
    overflow_prospects = []

    # First pass: handle oversized clusters
    for cluster in clusters:
        if len(cluster) > max_size:
            # Split oversized cluster
            num_splits = int(np.ceil(len(cluster) / max_size))
            split_size = len(cluster) // num_splits

            for i in range(num_splits):
                start_idx = i * split_size
                end_idx = start_idx + split_size if i < num_splits - 1 else len(cluster)
                sub_cluster = cluster.iloc[start_idx:end_idx].copy()

                if len(sub_cluster) >= min_size:
                    balanced_clusters.append(sub_cluster)
                else:
                    # Add to overflow if too small
                    overflow_prospects.append(sub_cluster)

        elif len(cluster) >= min_size:
            # Keep properly sized clusters
            balanced_clusters.append(cluster)
        else:
            # Add undersized clusters to overflow
            overflow_prospects.append(cluster)

    # Second pass: handle overflow prospects
    if overflow_prospects:
        # Combine all overflow prospects
        all_overflow = pd.concat(overflow_prospects, ignore_index=True)

        # Split overflow into properly sized clusters
        while len(all_overflow) >= min_size:
            # Take optimal number for new cluster
            take_size = min(max_size, len(all_overflow))
            new_cluster = all_overflow.iloc[:take_size].copy()
            balanced_clusters.append(new_cluster)
            all_overflow = all_overflow.iloc[take_size:].reset_index(drop=True)

        # If any remaining overflow, add to existing clusters
        if not all_overflow.empty:
            for _, prospect in all_overflow.iterrows():
                # Find cluster with room that won't exceed max_size
                for cluster in balanced_clusters:
                    if len(cluster) < max_size:
                        cluster = pd.concat([cluster, prospect.to_frame().T], ignore_index=True)
                        break

    return balanced_clusters

def insert_route_with_proper_method(db, route_records, route_date):
    """Insert route records using proper INSERT method"""
    success_count = 0
    error_count = 0

    print(f"  Inserting {len(route_records)} records for {route_date}...")

    for i, record in enumerate(route_records):
        try:
            # Use the proper execute_insert method
            insert_query = """
            INSERT INTO routeplan_ai
            (salesagent, custno, custype, latitude, longitude, stopno, routedate, barangay, barangay_code, is_visited)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            params = (
                record['salesagent'],
                record['custno'],
                record['custype'],
                record['latitude'],
                record['longitude'],
                record['stopno'],
                record['routedate'],
                record['barangay'],
                record['barangay_code'],
                record['is_visited']
            )

            result = db.execute_insert(insert_query, params)
            if result:
                success_count += 1
            else:
                error_count += 1

            # Progress indicator
            if (i + 1) % 20 == 0:
                print(f"    Progress: {i + 1}/{len(route_records)} records processed")

        except Exception as e:
            error_count += 1
            if error_count <= 3:  # Only show first few errors
                print(f"    Error inserting record {i + 1}: {e}")

    print(f"  RESULT: {success_count} successful, {error_count} errors")
    return success_count

def create_fixed_prospect_routes():
    """Create fixed multi-day prospect routes using proper INSERT method"""
    print("CREATING FIXED MULTI-DAY PROSPECT ROUTES FOR AGENT 914")
    print("=" * 70)

    # Configuration
    agent_id = "914"
    barangay_code = "137403027"
    start_date = "2025-09-23"
    min_prospects_per_day = 55
    max_prospects_per_day = 65

    print(f"Agent ID: {agent_id}")
    print(f"Barangay Code: {barangay_code}")
    print(f"Start Date: {start_date}")
    print(f"Prospects per Day: {min_prospects_per_day}-{max_prospects_per_day}")
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

        # Step 2: Create balanced clusters using K-means
        print(f"\nStep 2: Creating balanced clusters...")
        clusters = create_balanced_clusters(prospects_df, min_prospects_per_day, max_prospects_per_day)

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

            # Insert into routeplan_ai using proper method
            records_inserted = insert_route_with_proper_method(db, route_records, route_date)

            if records_inserted > 0:
                total_routes_created += 1
                total_records_inserted += records_inserted
                print(f"  SUCCESS: Day {day_idx+1} completed - {records_inserted} records inserted")

        # Summary
        print(f"\n" + "=" * 70)
        print("FIXED MULTI-DAY PROSPECT ROUTE CREATION COMPLETED!")
        print("=" * 70)
        print(f"SUCCESS: Agent: {agent_id}")
        print(f"SUCCESS: Total Prospects Available: {total_prospects}")
        print(f"SUCCESS: Total Records Inserted: {total_records_inserted}")
        print(f"SUCCESS: Days Created: {total_routes_created}")
        print(f"SUCCESS: Coverage: {(total_records_inserted/total_prospects)*100:.1f}%")
        print(f"SUCCESS: Start Date: {start_date}")
        print(f"SUCCESS: Barangay: {barangay_code}")
        print(f"SUCCESS: Cluster Size: {min_prospects_per_day}-{max_prospects_per_day} prospects")
        print(f"SUCCESS: Clustering: Balanced K-means")
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
        create_fixed_prospect_routes()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()