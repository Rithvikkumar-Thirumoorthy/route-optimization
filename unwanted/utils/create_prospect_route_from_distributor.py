#!/usr/bin/env python3
"""
Prospect Route Creator from Distributor - Agent 914
TSP optimization starting from distributor location but only visiting prospects
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

def solve_tsp_from_distributor(locations_df, distributor_lat, distributor_lon):
    """Solve TSP starting from distributor location but only visiting prospect locations"""
    if len(locations_df) <= 1:
        locations_df['stopno'] = 1
        return locations_df

    print(f"  Starting TSP from distributor ({distributor_lat}, {distributor_lon})")

    # Find the prospect closest to distributor as first stop
    distances_from_distributor = []
    for _, row in locations_df.iterrows():
        dist = haversine_distance(distributor_lat, distributor_lon, row['Latitude'], row['Longitude'])
        distances_from_distributor.append(dist)

    # Start from the prospect closest to distributor
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

    print(f"  TSP completed: {len(result_df)} prospects optimized from distributor location")

    return result_df

def get_distributor_location(db, agent_id):
    """Get distributor location for the agent from distributors table"""
    try:
        distributor_query = f"""
        SELECT TOP 1
            Latitude,
            Longitude,
            Name,
            Address
        FROM distributors
        WHERE AgentID = '{agent_id}'
        AND Latitude IS NOT NULL
        AND Longitude IS NOT NULL
        AND Latitude != 0
        AND Longitude != 0
        """

        distributor_df = db.execute_query_df(distributor_query)

        if distributor_df is not None and not distributor_df.empty:
            distributor = distributor_df.iloc[0]
            print(f"Found distributor: {distributor['Name']}")
            print(f"Location: ({distributor['Latitude']}, {distributor['Longitude']})")
            print(f"Address: {distributor['Address']}")
            return distributor['Latitude'], distributor['Longitude']
        else:
            print("No distributor found for agent, using default location")
            # Default location if no distributor found
            return 14.5995, 120.9842  # Manila coordinates as fallback

    except Exception as e:
        print(f"Error getting distributor location: {e}")
        print("Using default location")
        return 14.5995, 120.9842  # Manila coordinates as fallback

def create_balanced_clusters(prospects_df, min_size=50, max_size=70):
    """Create balanced clusters that include ALL prospects with 50+ per cluster using K-means"""
    print(f"Creating balanced clusters from {len(prospects_df)} prospects...")
    print(f"Cluster size limits: {min_size}-{max_size} prospects each (ensuring ALL prospects included)")

    total_prospects = len(prospects_df)

    # Calculate optimal number of clusters to stay within limits
    target_size = 60  # Aim for 60 per cluster
    n_clusters = max(1, int(np.ceil(total_prospects / target_size)))

    # Adjust if clusters would be too small
    while total_prospects / n_clusters < min_size and n_clusters > 1:
        n_clusters -= 1

    # Adjust if clusters would be too large
    while total_prospects / n_clusters > max_size:
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

    # Balance clusters to ensure all prospects included
    print(f"\nBalancing clusters to include ALL prospects...")
    balanced_clusters = balance_cluster_sizes_complete(initial_clusters, min_size, max_size)

    total_clustered = sum(len(cluster) for cluster in balanced_clusters)
    print(f"BALANCED CLUSTERING RESULTS:")
    for i, cluster in enumerate(balanced_clusters):
        print(f"  Cluster {i + 1}: {len(cluster)} prospects")
    print(f"SUCCESS: All {total_clustered} prospects balanced into {len(balanced_clusters)} clusters")

    return balanced_clusters

def balance_cluster_sizes_complete(clusters, min_size, max_size):
    """Balance cluster sizes to include ALL prospects with min_size+ per cluster"""
    all_prospects = []

    # Collect all prospects from all clusters
    for cluster in clusters:
        all_prospects.append(cluster)

    # Combine all prospects into single dataframe
    combined_prospects = pd.concat(all_prospects, ignore_index=True)
    total_prospects = len(combined_prospects)

    print(f"  Redistributing {total_prospects} prospects to ensure ALL are included...")

    # Calculate optimal number of clusters to include all prospects
    target_size = 60  # Aim for 60 per cluster
    n_clusters = max(1, int(np.ceil(total_prospects / target_size)))

    # Adjust if clusters would be too small
    while total_prospects / n_clusters < min_size and n_clusters > 1:
        n_clusters -= 1

    # Adjust if clusters would be too large
    while total_prospects / n_clusters > max_size:
        n_clusters += 1

    print(f"  Creating {n_clusters} clusters to include all {total_prospects} prospects")

    # Split prospects evenly across clusters
    prospects_per_cluster = total_prospects // n_clusters
    remainder = total_prospects % n_clusters

    balanced_clusters = []
    start_idx = 0
    for i in range(n_clusters):
        # Add one extra prospect to first 'remainder' clusters
        cluster_size = prospects_per_cluster + (1 if i < remainder else 0)
        end_idx = start_idx + cluster_size

        cluster = combined_prospects.iloc[start_idx:end_idx].copy()
        balanced_clusters.append(cluster)

        start_idx = end_idx

    # Verify all prospects are included
    total_included = sum(len(cluster) for cluster in balanced_clusters)
    print(f"  Verification: {total_included} prospects distributed across {len(balanced_clusters)} clusters")

    return balanced_clusters

def insert_route_safely(db, route_records, route_date):
    """Insert route records safely using proper INSERT method"""
    success_count = 0
    error_count = 0

    print(f"  Inserting {len(route_records)} records for {route_date}...")

    for i, record in enumerate(route_records):
        try:
            # Use parameterized query with execute_insert method
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

            # Use the proper execute_insert method instead of execute_query
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

def create_prospect_routes_from_distributor():
    """Create prospect routes starting from distributor location using TSP"""
    print("CREATING PROSPECT ROUTES FROM DISTRIBUTOR FOR AGENT 914")
    print("=" * 70)

    # Configuration
    agent_id = "914"
    barangay_code = "137403027"
    start_date = "2025-09-23"
    min_prospects_per_day = 50
    max_prospects_per_day = 70

    print(f"Agent ID: {agent_id}")
    print(f"Barangay Code: {barangay_code}")
    print(f"Start Date: {start_date}")
    print(f"Prospects per Day: {min_prospects_per_day}-{max_prospects_per_day}")
    print(f"TSP Starting Point: Distributor location (not included as stop)")
    print()

    db = None

    try:
        # Connect to database
        db = DatabaseConnection()
        db.connect()
        print("Database connection successful!")

        # Step 1: Get distributor location
        print(f"\nStep 1: Getting distributor location for Agent {agent_id}...")
        distributor_lat, distributor_lon = get_distributor_location(db, agent_id)

        # Step 2: Get ALL prospects from barangay
        print(f"\nStep 2: Getting ALL prospects from barangay {barangay_code}...")

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

        # Step 3: Create balanced clusters using K-means
        print(f"\nStep 3: Creating balanced clusters...")
        clusters = create_balanced_clusters(prospects_df, min_prospects_per_day, max_prospects_per_day)

        if not clusters:
            print("ERROR: No clusters created")
            return

        # Step 4: Process each cluster for different days with distributor-based TSP
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        total_routes_created = 0
        total_records_inserted = 0

        for day_idx, cluster in enumerate(clusters):
            current_date = start_date_obj + timedelta(days=day_idx)
            route_date = current_date.strftime("%Y-%m-%d")

            print(f"\nStep 4.{day_idx+1}: Processing Day {day_idx+1} ({route_date}) - {len(cluster)} prospects")

            # Apply TSP optimization starting from distributor location
            print(f"  Applying TSP optimization from distributor...")
            optimized_route = solve_tsp_from_distributor(cluster, distributor_lat, distributor_lon)
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
            records_inserted = insert_route_safely(db, route_records, route_date)

            if records_inserted > 0:
                total_routes_created += 1
                total_records_inserted += records_inserted
                print(f"  SUCCESS: Day {day_idx+1} completed - {records_inserted} records inserted")

        # Summary
        print(f"\n" + "=" * 70)
        print("DISTRIBUTOR-BASED PROSPECT ROUTE CREATION COMPLETED!")
        print("=" * 70)
        print(f"SUCCESS: Agent: {agent_id}")
        print(f"SUCCESS: Distributor Location: ({distributor_lat:.4f}, {distributor_lon:.4f})")
        print(f"SUCCESS: Total Prospects Available: {total_prospects}")
        print(f"SUCCESS: Total Records Inserted: {total_records_inserted}")
        print(f"SUCCESS: Days Created: {total_routes_created}")
        print(f"SUCCESS: Coverage: {(total_records_inserted/total_prospects)*100:.1f}%")
        print(f"SUCCESS: Start Date: {start_date}")
        print(f"SUCCESS: Barangay: {barangay_code}")
        print(f"SUCCESS: Cluster Size: {min_prospects_per_day}-{max_prospects_per_day} prospects")
        print(f"SUCCESS: Clustering: Balanced K-means")
        print(f"SUCCESS: TSP Optimized: Yes (from distributor)")
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
        create_prospect_routes_from_distributor()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()