#!/usr/bin/env python3
"""
Create Multi-Day Prospect Routes with DBSCAN Clustering + TSP - Agent 914
1. Get all 599 prospects from barangay '137403027'
2. Apply DBSCAN clustering to group prospects
3. Create multiple clusters of ~60 prospects each
4. Apply TSP optimization within each cluster
5. Assign each cluster to consecutive days (2025-09-23, 2025-09-24, etc.)
6. Insert optimized routes into routeplan_ai
"""

import sys
import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from math import radians, cos, sin, asin, sqrt
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('route_optimization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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

def apply_dbscan_clustering(prospects_df, target_size=60):
    """Apply optimized DBSCAN clustering to create equally distributed clusters of ~60 prospects each"""
    print(f"Applying optimized DBSCAN clustering to {len(prospects_df)} prospects for equal distribution...")

    # Prepare coordinates for clustering
    coordinates = prospects_df[['Latitude', 'Longitude']].values

    # Standardize coordinates for better clustering
    scaler = StandardScaler()
    coordinates_scaled = scaler.fit_transform(coordinates)

    # Calculate expected number of clusters
    expected_clusters = len(prospects_df) // target_size
    print(f"Target: {expected_clusters} clusters of ~{target_size} prospects each")

    best_clusters = []
    best_score = float('inf')  # Lower is better (variance in cluster sizes)
    best_eps = None

    # Extended eps values for better optimization
    eps_values = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.5]

    for eps in eps_values:
        dbscan = DBSCAN(eps=eps, min_samples=max(3, target_size // 20))  # Adaptive min_samples
        cluster_labels = dbscan.fit_predict(coordinates_scaled)

        # Add cluster labels to dataframe
        prospects_with_clusters = prospects_df.copy()
        prospects_with_clusters['cluster'] = cluster_labels

        # Find clusters (excluding noise points with label -1)
        unique_clusters = [c for c in np.unique(cluster_labels) if c != -1]

        if len(unique_clusters) > 0:
            clusters_list = []
            cluster_sizes = []

            print(f"  eps={eps}: Found {len(unique_clusters)} clusters")

            for cluster_id in unique_clusters:
                cluster_data = prospects_with_clusters[prospects_with_clusters['cluster'] == cluster_id]
                cluster_size = len(cluster_data)
                print(f"    Cluster {cluster_id}: {cluster_size} prospects")

                # Only consider clusters with reasonable size
                if 20 <= cluster_size <= target_size * 2:  # More flexible size range
                    clusters_list.append(cluster_data.drop('cluster', axis=1))
                    cluster_sizes.append(cluster_size)

            # Evaluate clustering quality based on size distribution
            if len(clusters_list) >= 2:
                # Calculate variance in cluster sizes (lower is better)
                mean_size = np.mean(cluster_sizes)
                variance = np.var(cluster_sizes)

                # Preference for clusters closer to target size
                size_penalty = sum(abs(size - target_size) for size in cluster_sizes)

                # Combined score (lower is better)
                score = variance + size_penalty * 0.1

                print(f"    Score: {score:.2f} (variance: {variance:.2f}, size_penalty: {size_penalty})")

                if score < best_score and len(clusters_list) >= 2:
                    best_clusters = clusters_list
                    best_score = score
                    best_eps = eps
                    print(f"    NEW BEST: eps={eps}, {len(clusters_list)} clusters, score={score:.2f}")

    # Post-process clusters to achieve better distribution
    if best_clusters:
        print(f"\nPost-processing clusters for better distribution...")
        optimized_clusters = optimize_cluster_distribution(best_clusters, target_size)

        print(f"OPTIMIZED CLUSTERING RESULTS:")
        print(f"  eps={best_eps}, {len(optimized_clusters)} clusters")
        for i, cluster in enumerate(optimized_clusters):
            print(f"  Cluster {i+1}: {len(cluster)} prospects")

        return optimized_clusters
    else:
        print(f"No suitable DBSCAN clusters found, using K-means alternative...")
        return fallback_kmeans_clustering(prospects_df, target_size)

def optimize_cluster_distribution(clusters, target_size):
    """Optimize cluster distribution by splitting large clusters and merging small ones"""
    optimized_clusters = []

    for cluster in clusters:
        cluster_size = len(cluster)

        if cluster_size > target_size * 1.5:  # Split large clusters
            print(f"  Splitting large cluster ({cluster_size} prospects)...")
            # Split into smaller chunks
            num_splits = int(np.ceil(cluster_size / target_size))
            chunk_size = cluster_size // num_splits

            for i in range(num_splits):
                start_idx = i * chunk_size
                end_idx = start_idx + chunk_size if i < num_splits - 1 else cluster_size
                sub_cluster = cluster.iloc[start_idx:end_idx].copy()
                if len(sub_cluster) >= 20:  # Minimum viable cluster size
                    optimized_clusters.append(sub_cluster)

        elif cluster_size >= 20:  # Keep reasonably sized clusters
            optimized_clusters.append(cluster)

    # Merge very small clusters with nearby ones if needed
    final_clusters = []
    small_clusters = []

    for cluster in optimized_clusters:
        if len(cluster) < 30:
            small_clusters.append(cluster)
        else:
            final_clusters.append(cluster)

    # Merge small clusters
    if small_clusters:
        merged_cluster = pd.concat(small_clusters, ignore_index=True)
        if len(merged_cluster) >= 20:
            final_clusters.append(merged_cluster)

    return final_clusters

def fallback_kmeans_clustering(prospects_df, target_size):
    """Fallback clustering using K-means for equal distribution"""
    print(f"Using K-means clustering as fallback...")

    from sklearn.cluster import KMeans

    # Calculate optimal number of clusters
    n_clusters = max(2, len(prospects_df) // target_size)

    coordinates = prospects_df[['Latitude', 'Longitude']].values
    scaler = StandardScaler()
    coordinates_scaled = scaler.fit_transform(coordinates)

    # Apply K-means
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(coordinates_scaled)

    # Create clusters
    clusters = []
    prospects_with_clusters = prospects_df.copy()
    prospects_with_clusters['cluster'] = cluster_labels

    for cluster_id in range(n_clusters):
        cluster_data = prospects_with_clusters[prospects_with_clusters['cluster'] == cluster_id]
        if len(cluster_data) > 0:
            clusters.append(cluster_data.drop('cluster', axis=1))
            print(f"  K-means Cluster {cluster_id}: {len(cluster_data)} prospects")

    return clusters

def create_prospect_route_dbscan_tsp():
    """Create multi-day prospect routes using DBSCAN clustering + TSP optimization"""
    logger.info("=" * 70)
    logger.info("CREATING MULTI-DAY PROSPECT ROUTES WITH DBSCAN + TSP FOR AGENT 914")
    logger.info("=" * 70)

    # Configuration
    agent_id = "914"
    barangay_code = "137403027"
    start_date = "2025-09-23"
    target_stops_per_day = 60

    logger.info(f"Configuration - Agent ID: {agent_id}")
    logger.info(f"Configuration - Barangay Code: {barangay_code}")
    logger.info(f"Configuration - Start Date: {start_date}")
    logger.info(f"Configuration - Target Stops per Day: {target_stops_per_day}")

    db = None
    pipeline_start_time = datetime.now()

    try:
        # Connect to database
        logger.info("Attempting database connection...")
        db = DatabaseConnection()
        db.connect()
        logger.info("Database connection successful!")

        # Step 1: Get ALL prospects from barangay (599 total)
        logger.info(f"Step 1: Querying prospects from barangay {barangay_code}...")
        query_start_time = datetime.now()

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
        query_duration = (datetime.now() - query_start_time).total_seconds()
        logger.info(f"Query completed in {query_duration:.2f} seconds")

        if prospects_df is None or prospects_df.empty:
            logger.error(f"No prospects found in barangay {barangay_code}")
            return

        total_prospects = len(prospects_df)
        logger.info(f"Successfully retrieved {total_prospects} prospects for clustering")
        logger.debug(f"Prospect data shape: {prospects_df.shape}")

        # Step 2: Apply DBSCAN clustering to create multiple clusters
        logger.info(f"Step 2: Applying DBSCAN clustering for multi-day routes...")
        clustering_start_time = datetime.now()

        clusters = apply_dbscan_clustering(prospects_df, target_stops_per_day)

        clustering_duration = (datetime.now() - clustering_start_time).total_seconds()
        logger.info(f"Clustering completed in {clustering_duration:.2f} seconds")

        if not clusters:
            logger.error("No suitable clusters found after DBSCAN clustering")
            return

        logger.info(f"Successfully created {len(clusters)} clusters")
        for i, cluster in enumerate(clusters):
            logger.info(f"  Cluster {i+1}: {len(cluster)} prospects")

        # Step 3: Process each cluster for different days
        from datetime import timedelta
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")

        total_routes_created = 0
        total_records_inserted = 0

        for day_idx, cluster in enumerate(clusters):
            current_date = start_date_obj + timedelta(days=day_idx)
            route_date = current_date.strftime("%Y-%m-%d")
            day_start_time = datetime.now()

            logger.info(f"Step 3.{day_idx+1}: Processing Day {day_idx+1} ({route_date}) with {len(cluster)} prospects")

            # Apply TSP optimization to this cluster
            logger.info(f"  Applying TSP nearest neighbor optimization...")
            tsp_start_time = datetime.now()

            optimized_route = solve_tsp_nearest_neighbor(cluster)

            tsp_duration = (datetime.now() - tsp_start_time).total_seconds()
            logger.info(f"  TSP optimization completed in {tsp_duration:.2f} seconds")

            # Step 4: Prepare route data for this day
            logger.info(f"  Preparing route data for {route_date}...")

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

            logger.info(f"  Prepared {len(route_records)} route records for {route_date}")

            # Step 5: Insert into routeplan_ai for this day
            logger.info(f"  Inserting route for {route_date} into routeplan_ai...")
            insert_start_time = datetime.now()

            if route_records:
                # Create values for bulk insert
                values_list = []
                for record in route_records:
                    values = f"""('{record['salesagent']}', '{record['custno']}', '{record['custype']}',
                               {record['latitude']}, {record['longitude']}, {record['stopno']}, '{record['routedate']}',
                               '{record['barangay']}', '{record['barangay_code']}', {record['is_visited']})"""
                    values_list.append(values)

                # Split into smaller batches to avoid timeout
                batch_size = 20
                total_inserted = 0

                for i in range(0, len(values_list), batch_size):
                    batch = values_list[i:i+batch_size]
                    insert_query = f"""
                    INSERT INTO routeplan_ai
                    (salesagent, custno, custype, latitude, longitude, stopno, routedate, barangay, barangay_code, is_visited)
                    VALUES {','.join(batch)}
                    """

                    db.execute_query(insert_query)
                    total_inserted += len(batch)
                    logger.debug(f"    Batch {i//batch_size + 1}: Inserted {len(batch)} records")

                insert_duration = (datetime.now() - insert_start_time).total_seconds()
                logger.info(f"  Successfully inserted {total_inserted} records in {insert_duration:.2f} seconds")
                total_records_inserted += total_inserted
                total_routes_created += 1

            day_duration = (datetime.now() - day_start_time).total_seconds()
            logger.info(f"  Day {day_idx+1} processing completed in {day_duration:.2f} seconds")

        # Summary
        pipeline_duration = (datetime.now() - pipeline_start_time).total_seconds()

        logger.info("=" * 70)
        logger.info("MULTI-DAY DBSCAN + TSP PROSPECT ROUTE CREATION COMPLETED!")
        logger.info("=" * 70)
        logger.info(f"Agent: {agent_id}")
        logger.info(f"Total Prospects Processed: {total_prospects}")
        logger.info(f"Total Clusters Created: {len(clusters)}")
        logger.info(f"Days/Routes Created: {total_routes_created}")
        logger.info(f"Total Records Inserted: {total_records_inserted}")
        logger.info(f"Start Date: {start_date}")
        logger.info(f"Barangay: {barangay_code}")
        logger.info(f"DBSCAN Clustering: Applied")
        logger.info(f"TSP Optimized: Yes")
        logger.info(f"Target Table: routeplan_ai")
        logger.info(f"Total Pipeline Duration: {pipeline_duration:.2f} seconds ({pipeline_duration/60:.2f} minutes)")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"Pipeline failed with error: {str(e)}", exc_info=True)
        raise

    finally:
        if db:
            logger.info("Closing database connection...")
            db.close()
            logger.info("Database connection closed")

def main():
    """Main function"""
    try:
        create_prospect_route_dbscan_tsp()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()



 #things to be verified 
 # first the starting location of the salesagent
 # I want to make sure that the starting location is correct
 # checking the barangay code is correct
 #    