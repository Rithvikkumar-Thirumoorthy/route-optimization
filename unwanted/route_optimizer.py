import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans
from itertools import permutations
from multiprocessing import Pool, cpu_count
import sys
import warnings
warnings.filterwarnings('ignore')

# Fix for Windows multiprocessing
if sys.platform == 'win32':
    import multiprocessing
    multiprocessing.freeze_support()

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees) in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

def create_distance_matrix(coords):
    """Create distance matrix using vectorized haversine distance"""
    n = len(coords)

    # Convert to radians
    coords_rad = np.radians(coords)

    # Extract lat and lon
    lat = coords_rad[:, 0]
    lon = coords_rad[:, 1]

    # Create meshgrid for vectorized calculation
    lat1 = lat[:, np.newaxis]
    lat2 = lat[np.newaxis, :]
    lon1 = lon[:, np.newaxis]
    lon2 = lon[np.newaxis, :]

    # Vectorized haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371  # Radius of earth in kilometers

    return c * r

def solve_tsp_nearest_neighbor(distance_matrix, start_idx=0):
    """
    Solve TSP using nearest neighbor heuristic.
    Returns the tour (list of indices) and total distance.
    """
    n = len(distance_matrix)
    unvisited = set(range(n))
    current = start_idx
    tour = [current]
    unvisited.remove(current)
    total_distance = 0

    while unvisited:
        nearest = min(unvisited, key=lambda x: distance_matrix[current][x])
        total_distance += distance_matrix[current][nearest]
        current = nearest
        tour.append(current)
        unvisited.remove(current)

    return tour, total_distance

def solve_tsp_2opt_limited(distance_matrix, initial_tour=None, max_iterations=50):
    """
    Improve TSP solution using 2-opt local search with limited iterations for speed.
    """
    n = len(distance_matrix)

    if initial_tour is None:
        tour, _ = solve_tsp_nearest_neighbor(distance_matrix)
    else:
        tour = initial_tour.copy()

    def tour_distance(tour):
        return sum(distance_matrix[tour[i]][tour[i+1]] for i in range(len(tour)-1))

    current_distance = tour_distance(tour)
    iterations = 0
    improved = True

    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        for i in range(1, min(n - 1, 20)):  # Limit inner loop iterations
            for j in range(i + 1, min(n, i + 20)):  # Limit segment size
                # Calculate distance change for 2-opt swap
                # Only swap if it improves the tour
                if j - i == 1 or j + 1 >= n:
                    continue

                # Calculate the change in distance
                current_edges = distance_matrix[tour[i-1]][tour[i]] + distance_matrix[tour[j]][tour[j+1]]
                new_edges = distance_matrix[tour[i-1]][tour[j]] + distance_matrix[tour[i]][tour[j+1]]

                if new_edges < current_edges:
                    # Reverse the segment between i and j
                    tour[i:j+1] = tour[i:j+1][::-1]
                    current_distance = current_distance - current_edges + new_edges
                    improved = True
                    break
            if improved:
                break

    return tour, current_distance

def process_single_cluster(args):
    """
    Process a single cluster - used for parallel processing.
    Returns the processed dataframe for the cluster.
    """
    cluster_id, cluster_df = args
    n_stores = len(cluster_df)

    # Get coordinates
    coords = cluster_df[['Latitude', 'Longitude']].values

    # Create distance matrix
    dist_matrix = create_distance_matrix(coords)

    # Solve TSP - use faster nearest neighbor for large clusters
    if n_stores > 50:
        tour, total_dist = solve_tsp_nearest_neighbor(dist_matrix)
    else:
        tour, total_dist = solve_tsp_2opt_limited(dist_matrix, max_iterations=30)

    # Reorder dataframe according to tour
    cluster_df = cluster_df.iloc[tour].reset_index(drop=True)

    # Calculate distance to next store
    distances_to_next = []
    for i in range(len(cluster_df) - 1):
        lat1 = cluster_df.iloc[i]['Latitude']
        lon1 = cluster_df.iloc[i]['Longitude']
        lat2 = cluster_df.iloc[i + 1]['Latitude']
        lon2 = cluster_df.iloc[i + 1]['Longitude']
        dist = haversine_distance(lat1, lon1, lat2, lon2)
        distances_to_next.append(dist)
    distances_to_next.append(0)  # Last store has 0 distance to next

    # Add sequence and distance columns
    cluster_df['Sequence'] = range(1, len(cluster_df) + 1)
    cluster_df['DistanceToNextStore'] = distances_to_next
    # DayNo will be set later after sorting

    return cluster_id, cluster_df, total_dist

def cluster_stores_exact_size(df, cluster_size=60):
    """
    Create clusters with exactly cluster_size stores each.
    Uses K-means for geographic coherence, then redistributes for exact size.
    Last cluster gets the remainder (can be less than cluster_size).

    Formula: n_clusters = ceil(total_stores / cluster_size)
    Result: First (n-1) clusters have exactly 60 stores, last cluster has remainder
    """
    from scipy.spatial.distance import cdist

    coords = df[['Latitude', 'Longitude']].values
    n_stores = len(coords)

    # Calculate number of clusters
    n_clusters = int(np.ceil(n_stores / cluster_size))
    remainder = n_stores % cluster_size

    print(f"   Total stores: {n_stores}")
    print(f"   Target cluster size: {cluster_size}")
    print(f"   Number of clusters: {n_clusters}")
    if remainder > 0:
        print(f"   First {n_clusters - 1} clusters: {cluster_size} stores each")
        print(f"   Last cluster: {remainder} stores")
    else:
        print(f"   All clusters: {cluster_size} stores each")

    # Initial K-means clustering for geographic coherence
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    initial_labels = kmeans.fit_predict(coords)
    cluster_centers = kmeans.cluster_centers_

    # Calculate distance from each store to each cluster center
    distances = cdist(coords, cluster_centers, metric='euclidean')

    # Redistribute stores to achieve exact size
    labels = np.full(n_stores, -1)  # -1 means unassigned

    for cluster_id in range(n_clusters):
        # Get unassigned stores sorted by distance to this cluster center
        unassigned_indices = [i for i in range(n_stores) if labels[i] == -1]

        if not unassigned_indices:
            break

        store_distances = [
            (idx, distances[idx, cluster_id])
            for idx in unassigned_indices
        ]
        store_distances.sort(key=lambda x: x[1])  # Sort by distance (closest first)

        # Assign exactly cluster_size stores (last cluster gets all remaining)
        if cluster_id == n_clusters - 1:
            # Last cluster: assign all remaining stores
            target_size = len(store_distances)
        else:
            # Regular cluster: exactly cluster_size stores
            target_size = min(cluster_size, len(store_distances))

        for i in range(target_size):
            store_idx = store_distances[i][0]
            labels[store_idx] = cluster_id

    return labels

def main():
    print("=" * 70)
    print("ROUTE OPTIMIZATION SYSTEM")
    print("=" * 70)

    # 1. Load the data
    print("\n[1/5] Loading data...")
    file_path = ('C:/Simplr projects/Route-optimization/full_pipeline/calumpang_df_clustered.csv')
    # Load with latin-1 encoding
    print(f"   Loading with latin-1 encoding...", end='', flush=True)
    df_barangay = pd.read_csv(file_path, encoding='latin-1', low_memory=False)
    print(f" [OK]")
    print(f"   Total stores loaded: {len(df_barangay):,}")

    # 2. Remove rows with missing coordinates
    df_barangay = df_barangay.dropna(subset=['Latitude', 'Longitude'])
    print(f"   Stores with valid coordinates: {len(df_barangay):,}")

    # 2. Create clusters with exactly 60 stores each
    print("\n[2/5] Creating clusters with exactly 60 stores each...")
    print("   Formula: n_clusters = ceil(total_stores / 60)")

    # Create new clusters
    labels = cluster_stores_exact_size(df_barangay, cluster_size=60)
    df_barangay['Cluster'] = labels

    # Show cluster distribution
    cluster_counts = df_barangay['Cluster'].value_counts().sort_index()
    print(f"\n   Successfully created {len(cluster_counts)} clusters")
    print("\n   Cluster distribution:")
    for cluster_id, count in cluster_counts.items():
        print(f"   Day {cluster_id + 1}: {count} stores")

    # 3. Solve TSP for each cluster using parallel processing
    print("\n[3/5] Optimizing routes for each cluster...")
    num_cores = cpu_count()
    print(f"   Using {num_cores} CPU cores for parallel processing", flush=True)

    # Prepare cluster data for parallel processing
    cluster_data = []
    for cluster_id in sorted(df_barangay['Cluster'].unique()):
        cluster_df = df_barangay[df_barangay['Cluster'] == cluster_id].copy()
        cluster_data.append((cluster_id, cluster_df))

    print(f"   Processing {len(cluster_data)} clusters...", flush=True)

    # Process clusters in parallel
    with Pool(processes=num_cores) as pool:
        pool_results = pool.map(process_single_cluster, cluster_data)

    # Print results and organize
    results = []
    for cluster_id, cluster_df, total_dist in pool_results:
        n_stores = len(cluster_df)
        print(f"   Cluster {cluster_id}: {n_stores} stores, {total_dist:.2f} km")
        results.append((cluster_id, cluster_df))

    # Sort results by cluster_id to maintain order
    results.sort(key=lambda x: x[0])

    # Renumber days sequentially from 1
    renumbered_results = []
    for day_num, (cluster_id, cluster_df) in enumerate(results, start=1):
        cluster_df['DayNo'] = day_num
        renumbered_results.append(cluster_df)

    results = renumbered_results

    # 4. Combine all results
    print("\n[4/5] Generating final output...")
    final_df = pd.concat(results, ignore_index=True)

    # Select and rename columns for output
    output_df = final_df[[
        'TDLinx',
        'Latitude',
        'Longitude',
        'DayNo',
        'Sequence',
        'DistanceToNextStore'
    ]].copy()

    output_df.columns = [
        'store',
        'latitude',
        'longitude',
        'dayno',
        'sequence',
        'distancetonextstore'
    ]

    # Round numeric values
    output_df['latitude'] = output_df['latitude'].round(8)
    output_df['longitude'] = output_df['longitude'].round(8)
    output_df['distancetonextstore'] = output_df['distancetonextstore'].round(3)

    # Save to CSV
    output_file = '' \
    '' \
    '.csv'
    output_df.to_csv(output_file, index=False)

    print(f"\n   Output saved to: {output_file}")
    print(f"   Total stores in output: {len(output_df):,}")

    # Summary statistics
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Barangay: Calumpang,126303033")
    print(f"Total stores: {len(output_df):,}")
    print(f"Total days: {output_df['dayno'].nunique()}")
    print(f"Total distance: {output_df['distancetonextstore'].sum():.2f} km")
    print(f"Average distance per day: {output_df.groupby('dayno')['distancetonextstore'].sum().mean():.2f} km")

    print("\nStores per day:")
    for day in sorted(output_df['dayno'].unique()):
        day_stores = len(output_df[output_df['dayno'] == day])
        day_distance = output_df[output_df['dayno'] == day]['distancetonextstore'].sum()
        print(f"  Day {day}: {day_stores} stores, {day_distance:.2f} km")

    print("\n" + "=" * 70)
    print("Process completed successfully!")
    print("=" * 70)

if __name__ == "__main__":
    main()
