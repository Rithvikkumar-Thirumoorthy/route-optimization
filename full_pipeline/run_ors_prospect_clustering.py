#!/usr/bin/env python3
"""
ORS-Based Prospect Route Clustering Pipeline

This pipeline creates prospect routes FOR ONE MONTH ONLY using:
1. Sales agents with access = 15 (filtered by distributor via nodetree)
2. Calculate monthly route capacity: N agents × actual working days in month
   - Counts real working days (Mon-Sat, excluding Sundays only)
   - Adapts to each month's calendar (e.g., Dec 2025 = 26 days)
3. Get distributor-specific barangays from nodetree
4. Count and sort barangays by store count (HIGHEST FIRST)
   - Ensures large barangays (>60 stores) are clustered first
   - Prevents large barangays from being split poorly
5. Process barangays in order until monthly capacity is reached
   - Uses CONSTRAINED K-MEANS clustering (NOT DBSCAN)
   - Guarantees balanced clusters with max 60 stores per cluster
   - PARTIAL SELECTION: Takes only needed clusters to fill capacity
   - STOPS when capacity limit hit
   - Remaining barangays/clusters saved for future months
6. Post-processing:
   - Merge small clusters (<20 stores) into nearby clusters
   - Rebalance nearby clusters for equal distribution
7. Agent assignment per cluster (one cluster per agent per day)
8. Date assignment starting from first Monday of month
9. Working days: Monday-Saturday (6 days/week, Sunday is holiday)

CLUSTERING METHOD:
- Uses Constrained K-Means (k_means_constrained library)
- Direct control over cluster sizes (min=1, max=60)
- Deterministic and predictable results
- No noise points (all stores assigned)

MONTHLY CAPACITY LIMITATION:
- Route capacity: N agents × actual working days in month
- Example: 5 agents × 26 days (Dec 2025) = 130 routes
- Example: 5 agents × 24 days (Feb 2025) = 120 routes
- Processing STOPS when capacity reached (100% utilization)
- Unprocessed barangays remain for next month's run

Processing order: Barangays sorted by store count descending (highest first)
This ensures optimal clustering for large barangays before handling smaller ones.

Uses OpenRouteService (ORS) API for accurate road-based distance calculations.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import calendar
import logging
import argparse
import requests
import json
import hashlib
import random
from collections import defaultdict
from math import radians, cos, sin, asin, sqrt

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

# Import ORS config from hierarchical pipeline
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'hierarchical-route-pipeline'))
try:
    import config as ors_config
except ImportError:
    # Fallback: define ORS config locally
    class ors_config:
        ORS_CONFIG = {
            'enabled': True,
            'matrix_endpoint': 'http://localhost:8080/ors/v2/matrix/driving-car',
            'timeout': 30,
            'use_cache': True,
            'fallback_to_haversine': True,
        }


class ORSProspectClusteringPipeline:
    def __init__(self, test_mode=False, max_stores_per_cluster=60, min_stores_threshold=20, ors_api_key=None):
        """Initialize ORS-based prospect clustering pipeline

        Args:
            test_mode: If True, runs without updating database (dry-run)
            max_stores_per_cluster: Maximum stores per cluster (default: 60)
            min_stores_threshold: Minimum stores for standalone cluster (default: 20)
            ors_api_key: Optional ORS API key for authenticated requests
        """
        self.test_mode = test_mode
        self.max_stores_per_cluster = max_stores_per_cluster
        self.min_stores_threshold = min_stores_threshold
        self.ors_api_key = ors_api_key
        self.start_time = None
        self.all_test_records = []  # Store all records in test mode

        # ORS caching
        self._ors_matrix_cache = {}

        # Setup logging
        self.setup_logging()

    def setup_logging(self):
        """Setup logging configuration"""
        log_filename = f"ors_prospect_clustering_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_path = os.path.join(os.path.dirname(__file__), 'logs', log_filename)

        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    # ========================================================================
    # ORS API METHODS
    # ========================================================================

    def get_ors_distance_matrix(self, locations):
        """
        Get distance matrix from ORS API for multiple locations

        Args:
            locations: List of [longitude, latitude] pairs (ORS uses lon,lat order!)

        Returns:
            2D numpy array of distances in kilometers, or None if API call fails
        """
        try:
            # Create cache key from locations
            cache_key = hashlib.md5(json.dumps(locations, sort_keys=True).encode()).hexdigest()

            # Check cache first
            if ors_config.ORS_CONFIG['use_cache'] and cache_key in self._ors_matrix_cache:
                self.logger.debug(f"ORS Matrix cache hit for {len(locations)} locations")
                return self._ors_matrix_cache[cache_key]

            # Prepare ORS Matrix API request
            request_body = {
                "locations": locations,
                "metrics": ["distance"],
                "units": "km"
            }

            self.logger.info(f"Calling ORS Matrix API for {len(locations)} locations...")

            # Prepare headers
            headers = {'Content-Type': 'application/json'}
            if self.ors_api_key:
                headers['Authorization'] = self.ors_api_key
                self.logger.debug("Using ORS API key for authentication")

            # Make API request
            response = requests.post(
                ors_config.ORS_CONFIG['matrix_endpoint'],
                json=request_body,
                headers=headers,
                timeout=ors_config.ORS_CONFIG['timeout']
            )

            # Check response
            if response.status_code == 200:
                result = response.json()

                if 'distances' in result:
                    distance_matrix = np.array(result['distances'])

                    # Cache the result
                    if ors_config.ORS_CONFIG['use_cache']:
                        self._ors_matrix_cache[cache_key] = distance_matrix

                    self.logger.info(f"ORS Matrix API success: {distance_matrix.shape} matrix retrieved")
                    return distance_matrix
                else:
                    self.logger.error(f"ORS API response missing 'distances' field")
                    return None
            else:
                self.logger.error(f"ORS API error: HTTP {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            self.logger.error(f"ORS API timeout after {ors_config.ORS_CONFIG['timeout']}s")
            return None
        except requests.exceptions.ConnectionError:
            self.logger.error(f"ORS API connection error - is the service running at {ors_config.ORS_CONFIG['matrix_endpoint']}?")
            return None
        except Exception as e:
            self.logger.error(f"Error calling ORS Matrix API: {e}")
            return None

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate the great circle distance between two points on Earth (in km)"""
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Radius of earth in kilometers
        return c * r

    def haversine_distance_matrix_fast(self, locations):
        """
        OPTIMIZED: Calculate distance matrix for multiple locations using vectorization
        10-100x faster than nested loops!

        Args:
            locations: List of [lon, lat] pairs
        Returns:
            numpy array of pairwise distances (km)
        """
        # Convert to numpy arrays
        locs = np.array(locations)
        lats = np.radians(locs[:, 1])
        lons = np.radians(locs[:, 0])

        # Vectorized calculation using broadcasting
        n = len(locations)
        distance_matrix = np.zeros((n, n))

        for i in range(n):
            dlat = lats - lats[i]
            dlon = lons - lons[i]
            a = np.sin(dlat/2)**2 + np.cos(lats[i]) * np.cos(lats) * np.sin(dlon/2)**2
            c = 2 * np.arcsin(np.sqrt(a))
            distance_matrix[i] = c * 6371  # Earth radius in km

        return distance_matrix

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate distance between two points using Haversine (FAST MODE)
        ORS API calls disabled for performance
        """
        # PERFORMANCE MODE: Use Haversine only (skip ORS API calls)
        return self.haversine_distance(lat1, lon1, lat2, lon2)

    # ========================================================================
    # STEP 1: GET SALES AGENTS WITH ACCESS = 15
    # ========================================================================

    def get_sales_agents_with_access_15(self, db, distributor_id=None):
        """Get sales agents with access = 15, optionally filtered by distributor

        Args:
            db: Database connection
            distributor_id: Optional distributor ID to filter agents
        """
        try:
            if distributor_id:
                # Filter agents by distributor using nodetree table
                # salesagent.nodetreevalue -> nodetree.salesmanterritory -> nodetree.DistributorID
                query = f"""
                SELECT
                    sa.Code as AgentID,
                    sa.nodetreevalue as SalesManTerritory,
                    sa.Name as AgentName
                FROM salesagent sa
                INNER JOIN nodetree nt ON sa.nodetreevalue = nt.salesmanterritory
                WHERE sa.access = 15
                    AND nt.DistributorID = '{distributor_id}'
                """
                self.logger.info(f"Getting sales agents with access = 15 for distributor {distributor_id}")
            else:
                # Get all agents with access = 15 (original behavior)
                query = """
                SELECT
                    Code as AgentID,
                    nodetreevalue as SalesManTerritory,
                    Name as AgentName
                FROM salesagent
                WHERE access = 15
                """
                self.logger.info("Getting all sales agents with access = 15")

            agents_df = db.execute_query_df(query)

            if agents_df is not None and not agents_df.empty:
                self.logger.info(f"Found {len(agents_df)} sales agents with access = 15")
                return agents_df
            else:
                self.logger.warning("No sales agents found with access = 15")
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error getting sales agents: {e}")
            return pd.DataFrame()

    # ========================================================================
    # STEP 2: GET DISTRIBUTOR BARANGAYS (Optimized - Direct Match)
    # ========================================================================

    def get_distributor_barangays(self, db, distributor_id):
        """
        Get barangays for a specific distributor (OPTIMIZED VERSION)

        Strategy: Instead of complex joins, use distributor name directly
        1. Get DistributorName from distributor table
        2. Match with RD column in prospective table
        3. Get unique barangays from matching prospects

        This is MUCH faster than joining through nodetree → salesagent → customer
        """
        try:
            # Step 1: Get Distributor Name
            distributor_query = f"""
            SELECT DistributorName
            FROM Distributor
            WHERE DistributorID = '{distributor_id}'
            """

            distributor_df = db.execute_query_df(distributor_query)

            if distributor_df is None or distributor_df.empty:
                self.logger.error(f"Distributor {distributor_id} not found in Distributor table")
                return pd.DataFrame()

            distributor_name = distributor_df.iloc[0]['DistributorName']
            self.logger.info(f"Distributor {distributor_id}: {distributor_name}")

            # Step 2: Get barangays from prospective table where RD matches distributor name
            barangays_query = f"""
            SELECT DISTINCT
                '{distributor_id}' as DistributorID,
                p.barangay_code AS BarangayCode,
                b.BarangayName
            FROM prospective p
            LEFT JOIN Barangay b ON b.Code = p.barangay_code
            WHERE p.RD = '{distributor_name}'
                AND p.barangay_code IS NOT NULL
                AND p.barangay_code != ''
            ORDER BY b.BarangayName
            """

            barangays_df = db.execute_query_df(barangays_query)

            if barangays_df is not None and not barangays_df.empty:
                self.logger.info(f"Found {len(barangays_df)} barangays for distributor {distributor_id} ({distributor_name})")
                return barangays_df
            else:
                self.logger.warning(f"No barangays found for distributor {distributor_id}")
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error getting distributor barangays: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    # ========================================================================
    # STEP 3: GET PROSPECTS PER BARANGAY AND CLUSTER
    # ========================================================================

    def count_stores_per_barangay(self, db, barangays_df, excluded_ids=None):
        """
        Count available stores per barangay (after exclusions)
        Returns barangays_df with added 'StoreCount' column, sorted by count descending

        Args:
            db: Database connection
            barangays_df: DataFrame with barangay codes
            excluded_ids: Set of excluded customer IDs

        Returns:
            DataFrame with StoreCount column, sorted highest to lowest
        """
        try:
            self.logger.info("\nCounting stores per barangay...")

            barangay_counts = []

            for _, row in barangays_df.iterrows():
                barangay_code = row['BarangayCode']

                # Count prospects for this barangay
                query = f"""
                SELECT COUNT(*) as store_count
                FROM prospective p
                WHERE p.barangay_code = '{barangay_code}'
                    AND p.latitude IS NOT NULL
                    AND p.longitude IS NOT NULL
                    AND p.latitude != 0
                    AND p.longitude != 0
                """

                count_df = db.execute_query_df(query)
                total_count = count_df.iloc[0]['store_count'] if count_df is not None and not count_df.empty else 0

                # If we have excluded_ids, we need to fetch and filter
                if excluded_ids and len(excluded_ids) > 0 and total_count > 0:
                    prospects_df = self.get_prospects_by_barangay(db, barangay_code, excluded_ids=None)
                    if not prospects_df.empty:
                        prospects_df = prospects_df[~prospects_df['CustNo'].isin(excluded_ids)]
                        available_count = len(prospects_df)
                    else:
                        available_count = 0
                else:
                    available_count = total_count

                barangay_counts.append({
                    'BarangayCode': barangay_code,
                    'BarangayName': row['BarangayName'],
                    'DistributorID': row['DistributorID'],
                    'TotalStores': total_count,
                    'AvailableStores': available_count
                })

                self.logger.info(f"  {row['BarangayName']} ({barangay_code}): {available_count} stores available (total: {total_count})")

            # Create DataFrame and sort by available stores descending
            result_df = pd.DataFrame(barangay_counts)
            result_df = result_df.sort_values('AvailableStores', ascending=False).reset_index(drop=True)

            self.logger.info(f"\nBarangays sorted by store count (highest first):")
            for idx, row in result_df.head(10).iterrows():
                self.logger.info(f"  {idx+1}. {row['BarangayName']}: {row['AvailableStores']} stores")

            if len(result_df) > 10:
                self.logger.info(f"  ... and {len(result_df) - 10} more barangays")

            return result_df

        except Exception as e:
            self.logger.error(f"Error counting stores per barangay: {e}")
            import traceback
            traceback.print_exc()
            return barangays_df

    def get_prospects_by_barangay(self, db, barangay_code, excluded_ids=None):
        """
        Get prospects for a specific barangay
        Excludes:
        - Stores already in MonthlyRoutePlan_temp (latest month)
        - Stores with history in custvisit table

        Args:
            db: Database connection
            barangay_code: Barangay code to filter
            excluded_ids: Pre-fetched set of excluded customer IDs (optional)
        """
        try:
            # Fetch all prospects for barangay (no exclusions in SQL - much faster!)
            query = f"""
            SELECT
                p.tdlinx as CustNo,
                p.latitude,
                p.longitude,
                p.barangay_code,
                p.store_name_nielsen as Name
            FROM prospective p
            WHERE p.barangay_code = '{barangay_code}'
                AND p.latitude IS NOT NULL
                AND p.longitude IS NOT NULL
                AND p.latitude != 0
                AND p.longitude != 0
            """

            prospects_df = db.execute_query_df(query)

            if prospects_df is None or prospects_df.empty:
                return pd.DataFrame()

            # Filter out excluded IDs in pandas (very fast) if provided
            if excluded_ids is not None and len(excluded_ids) > 0:
                before_count = len(prospects_df)
                prospects_df = prospects_df[~prospects_df['CustNo'].isin(excluded_ids)]
                after_count = len(prospects_df)
                if before_count != after_count:
                    self.logger.info(f"    Barangay {barangay_code}: {before_count} prospects → {after_count} after exclusions")
                else:
                    self.logger.info(f"    Barangay {barangay_code}: {after_count} prospects")
            else:
                self.logger.info(f"    Barangay {barangay_code}: {len(prospects_df)} prospects")

            return prospects_df

        except Exception as e:
            self.logger.error(f"Error getting prospects for barangay {barangay_code}: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def fetch_excluded_ids(self, db, exclude_latest_month=True):
        """
        Fetch excluded customer IDs once for all barangays
        Much faster than querying for each barangay
        """
        try:
            excluded_ids = set()

            if exclude_latest_month:
                # Get IDs from MonthlyRoutePlan_temp (latest month)
                self.logger.info(f"  Fetching excluded IDs from MonthlyRoutePlan_temp...")
                mrp_query = """
                SELECT DISTINCT CustNo
                FROM MonthlyRoutePlan_temp
                WHERE RouteDate >= DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()), 0)
                """
                mrp_df = db.execute_query_df(mrp_query)
                if mrp_df is not None and not mrp_df.empty:
                    excluded_ids.update(mrp_df['CustNo'].tolist())
                    self.logger.info(f"  Excluded {len(mrp_df)} IDs from MonthlyRoutePlan_temp")

            # Get IDs from custvisit
            self.logger.info(f"  Fetching excluded IDs from custvisit...")
            cv_query = """
            SELECT DISTINCT CustID
            FROM custvisit
            """
            cv_df = db.execute_query_df(cv_query)
            if cv_df is not None and not cv_df.empty:
                excluded_ids.update(cv_df['CustID'].tolist())
                self.logger.info(f"  Excluded {len(cv_df)} IDs from custvisit")

            self.logger.info(f"  Total excluded IDs: {len(excluded_ids)}")
            return excluded_ids

        except Exception as e:
            self.logger.error(f"Error fetching excluded IDs: {e}")
            import traceback
            traceback.print_exc()
            return set()

    def cluster_prospects_with_ors(self, prospects_df, max_per_cluster=60):
        """
        Cluster prospects using Constrained K-Means
        Guarantees balanced clusters with size constraints (max 60 stores per cluster)

        Args:
            prospects_df: DataFrame with prospect data (must have latitude, longitude)
            max_per_cluster: Maximum stores per cluster

        Returns:
            DataFrame with added 'cluster_id' column
        """
        try:
            if len(prospects_df) == 0:
                return prospects_df

            # If prospects <= max_per_cluster, all in one cluster
            if len(prospects_df) <= max_per_cluster:
                prospects_df['cluster_id'] = 0
                self.logger.info(f"    Single cluster: {len(prospects_df)} prospects")
                return prospects_df

            # Calculate optimal number of clusters
            num_prospects = len(prospects_df)
            num_clusters = int(np.ceil(num_prospects / max_per_cluster))

            self.logger.info(f"    Clustering {num_prospects} prospects into {num_clusters} clusters (max {max_per_cluster} per cluster)...")

            # Extract features: use coordinates directly
            features = prospects_df[['latitude', 'longitude']].values

            # Use Constrained K-Means to ensure balanced clusters
            from k_means_constrained import KMeansConstrained

            # Each cluster must have between 1 and max_per_cluster stores
            clf = KMeansConstrained(
                n_clusters=num_clusters,
                size_min=1,
                size_max=max_per_cluster,
                random_state=42
            )

            cluster_labels = clf.fit_predict(features)

            # Assign cluster IDs to dataframe
            prospects_df['cluster_id'] = cluster_labels

            # Show cluster distribution
            cluster_sizes = prospects_df.groupby('cluster_id').size()
            self.logger.info(f"    Created {num_clusters} clusters")
            self.logger.info(f"    Cluster sizes: min={cluster_sizes.min()}, max={cluster_sizes.max()}, mean={cluster_sizes.mean():.1f}")

            # Validation: ensure no cluster exceeds max_per_cluster
            oversized = cluster_sizes[cluster_sizes > max_per_cluster]
            if len(oversized) > 0:
                self.logger.error(f"    ERROR: {len(oversized)} clusters exceed {max_per_cluster} stores!")
                for cluster_id, size in oversized.items():
                    self.logger.error(f"      Cluster {cluster_id}: {size} stores")

            return prospects_df

        except Exception as e:
            self.logger.error(f"Error clustering prospects: {e}")
            import traceback
            traceback.print_exc()
            # Fallback: assign all to one cluster
            prospects_df['cluster_id'] = 0
            return prospects_df

    # ========================================================================
    # STEP 4: POST-PROCESSING FOR SMALL BARANGAYS
    # ========================================================================

    def merge_small_clusters(self, all_clusters_df, min_size=20, max_size=60):
        """
        Merge clusters with < min_size stores into nearby clusters
        IMPORTANT: Enforces max_size limit - will NOT merge if result exceeds max_size

        Args:
            all_clusters_df: DataFrame with all prospects and cluster_id
            min_size: Minimum cluster size threshold
            max_size: Maximum cluster size (default: 60)

        Returns:
            DataFrame with updated cluster_id
        """
        try:
            self.logger.info(f"\nPost-processing: Merging clusters with < {min_size} stores (max size: {max_size})...")

            # Identify small clusters
            cluster_sizes = all_clusters_df.groupby('cluster_id').size()
            small_clusters = cluster_sizes[cluster_sizes < min_size].index.tolist()

            if not small_clusters:
                self.logger.info("  No small clusters to merge")
                return all_clusters_df

            self.logger.info(f"  Found {len(small_clusters)} small clusters to merge")

            merged_count = 0
            skipped_count = 0

            # For each small cluster, find nearest cluster that can accept it
            for small_cluster_id in small_clusters:
                small_cluster_df = all_clusters_df[all_clusters_df['cluster_id'] == small_cluster_id]
                small_cluster_size = len(small_cluster_df)

                if small_cluster_size == 0:
                    continue

                # Calculate center of small cluster
                center_lat = small_cluster_df['latitude'].mean()
                center_lon = small_cluster_df['longitude'].mean()

                # Find all other clusters (refresh cluster_sizes each iteration)
                current_cluster_sizes = all_clusters_df.groupby('cluster_id').size()
                other_clusters = all_clusters_df[all_clusters_df['cluster_id'] != small_cluster_id]

                if other_clusters.empty:
                    self.logger.warning(f"  No other clusters available to merge cluster {small_cluster_id}")
                    skipped_count += 1
                    continue

                # Find nearest cluster that can accept this small cluster without exceeding max_size
                other_cluster_ids = other_clusters['cluster_id'].unique()
                min_distance = float('inf')
                best_cluster_id = None

                for candidate_id in other_cluster_ids:
                    candidate_size = current_cluster_sizes[candidate_id]

                    # CHECK: Would merging exceed max_size?
                    if candidate_size + small_cluster_size > max_size:
                        continue  # Skip this candidate, would exceed limit

                    candidate_df = all_clusters_df[all_clusters_df['cluster_id'] == candidate_id]
                    candidate_lat = candidate_df['latitude'].mean()
                    candidate_lon = candidate_df['longitude'].mean()

                    distance = self.calculate_distance(center_lat, center_lon, candidate_lat, candidate_lon)

                    if distance is None:
                        continue

                    if distance < min_distance:
                        min_distance = distance
                        best_cluster_id = candidate_id

                if best_cluster_id is not None:
                    target_size = current_cluster_sizes[best_cluster_id]
                    new_size = target_size + small_cluster_size
                    self.logger.info(f"  Merging cluster {small_cluster_id} ({small_cluster_size} stores) into cluster {best_cluster_id} ({target_size} → {new_size} stores, distance: {min_distance:.2f}km)")
                    all_clusters_df.loc[all_clusters_df['cluster_id'] == small_cluster_id, 'cluster_id'] = best_cluster_id
                    merged_count += 1
                else:
                    self.logger.warning(f"  Cannot merge cluster {small_cluster_id} ({small_cluster_size} stores) - would exceed {max_size} store limit")
                    skipped_count += 1

            self.logger.info(f"  Merged {merged_count} small clusters, skipped {skipped_count}")

            # Recalculate cluster sizes after merging
            final_cluster_sizes = all_clusters_df.groupby('cluster_id').size()
            self.logger.info(f"\nFinal cluster distribution:")
            self.logger.info(f"  Total clusters: {len(final_cluster_sizes)}")
            self.logger.info(f"  Cluster sizes: min={final_cluster_sizes.min()}, max={final_cluster_sizes.max()}, mean={final_cluster_sizes.mean():.1f}")

            # VALIDATION: Check no cluster exceeds max_size
            oversized = final_cluster_sizes[final_cluster_sizes > max_size]
            if len(oversized) > 0:
                self.logger.error(f"  ERROR: {len(oversized)} clusters exceed {max_size} stores!")
                for cluster_id, size in oversized.items():
                    self.logger.error(f"    Cluster {cluster_id}: {size} stores")

            return all_clusters_df

        except Exception as e:
            self.logger.error(f"Error merging small clusters: {e}")
            import traceback
            traceback.print_exc()
            return all_clusters_df

    # ========================================================================
    # STEP 4.5: REBALANCE NEARBY CLUSTERS
    # ========================================================================

    def rebalance_nearby_clusters(self, all_clusters_df, min_size=40, max_size=60):
        """
        Rebalance stores across nearby clusters (same barangay) to equalize distribution
        Example: Clusters [30, 45, 59, 60, 60, 40] → balance to [49, 49, 49, 49, 49, 49]

        Args:
            all_clusters_df: DataFrame with all prospects and cluster_id
            min_size: Target minimum cluster size (default: 40)
            max_size: Maximum cluster size (default: 60)

        Returns:
            DataFrame with rebalanced cluster_id assignments
        """
        try:
            self.logger.info(f"\nPost-processing: Rebalancing nearby clusters (target: {min_size}-{max_size} stores)...")

            # Group by barangay (clusters in same barangay are spatially nearby)
            barangays = all_clusters_df['barangay_code'].unique()

            rebalanced_count = 0
            for barangay_code in barangays:
                barangay_df = all_clusters_df[all_clusters_df['barangay_code'] == barangay_code].copy()

                # Get cluster sizes in this barangay
                cluster_sizes = barangay_df.groupby('cluster_id').size()

                # Skip if only one cluster
                if len(cluster_sizes) <= 1:
                    continue

                # Calculate statistics
                mean_size = cluster_sizes.mean()
                min_cluster_size = cluster_sizes.min()
                max_cluster_size = cluster_sizes.max()
                variance = cluster_sizes.std()

                # Only rebalance if there's significant imbalance (std dev > 10)
                if variance < 10:
                    continue

                self.logger.info(f"  Barangay {barangay_code}: {len(cluster_sizes)} clusters, sizes {min_cluster_size}-{max_cluster_size}, mean={mean_size:.1f}, std={variance:.1f}")

                # Check if rebalancing would help
                # We can rebalance if: total stores / num clusters fits within limits
                total_stores = len(barangay_df)
                num_clusters = len(cluster_sizes)
                ideal_size = total_stores // num_clusters

                if ideal_size < min_size or ideal_size > max_size:
                    self.logger.info(f"    Cannot rebalance: ideal size {ideal_size} outside {min_size}-{max_size} range")
                    continue

                # Rebalance: redistribute stores evenly
                self.logger.info(f"    Rebalancing to ~{ideal_size} stores per cluster...")

                # Sort stores by cluster_id to maintain some spatial grouping
                barangay_df_sorted = barangay_df.sort_values(['cluster_id', 'latitude', 'longitude']).reset_index(drop=True)

                # Get cluster IDs in this barangay
                cluster_ids = sorted(cluster_sizes.index.tolist())

                # Reassign stores round-robin style to balance
                new_cluster_assignments = []
                cluster_index = 0

                for idx, row in barangay_df_sorted.iterrows():
                    # Assign to current cluster
                    new_cluster_id = cluster_ids[cluster_index]
                    new_cluster_assignments.append((row.name, new_cluster_id))

                    # Move to next cluster in round-robin fashion
                    # But ensure no cluster exceeds max_size
                    current_count = sum(1 for _, cid in new_cluster_assignments if cid == new_cluster_id)
                    if current_count >= ideal_size + 1:  # Allow +1 for rounding
                        cluster_index = (cluster_index + 1) % num_clusters

                # Apply new assignments
                for orig_idx, new_cluster_id in new_cluster_assignments:
                    all_clusters_df.loc[orig_idx, 'cluster_id'] = new_cluster_id

                # Log results
                new_cluster_sizes = all_clusters_df[all_clusters_df['barangay_code'] == barangay_code].groupby('cluster_id').size()
                self.logger.info(f"    ✓ Rebalanced: sizes now {new_cluster_sizes.min()}-{new_cluster_sizes.max()}, mean={new_cluster_sizes.mean():.1f}")
                rebalanced_count += 1

            if rebalanced_count > 0:
                self.logger.info(f"  Rebalanced {rebalanced_count} barangays")
            else:
                self.logger.info(f"  No barangays needed rebalancing")

            return all_clusters_df

        except Exception as e:
            self.logger.error(f"Error rebalancing clusters: {e}")
            import traceback
            traceback.print_exc()
            return all_clusters_df

    # ========================================================================
    # HELPER: CALCULATE WORKING DAYS
    # ========================================================================

    def calculate_working_days_in_month(self, year, month):
        """
        Calculate working days in a month (Monday-Saturday, exclude Sundays only)

        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            Number of working days in the month
        """
        # Get number of days in month
        num_days = calendar.monthrange(year, month)[1]

        working_days = 0
        for day in range(1, num_days + 1):
            date = datetime(year, month, day)
            # 0=Monday, 6=Sunday
            if date.weekday() != 6:  # Exclude Sunday only
                working_days += 1

        return working_days

    # ========================================================================
    # STEP 5: ASSIGN AGENTS AND DATES
    # ========================================================================

    def assign_agents_and_dates_to_clusters(self, clustered_df, agents_df, start_date):
        """
        Assign sales agents and dates to each cluster
        IMPORTANT: Each (agent, date) combination gets ONLY ONE cluster
        Ensures no agent has more than one cluster per day

        Working days: Monday-Saturday (6 days per week, Sunday is holiday)
        For N agents × 6 days/week × 4 weeks = N × 24 routes per month

        Args:
            clustered_df: DataFrame with prospects and cluster_id
            agents_df: DataFrame with available sales agents
            start_date: Starting date (YYYY-MM-DD string or datetime)

        Returns:
            DataFrame with added AgentID, RouteDate, WD columns
        """
        try:
            self.logger.info("\nAssigning agents and dates to clusters...")

            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d')

            # Find the first Monday of the month
            # Move to first day of month, then find first Monday
            first_day_of_month = start_date.replace(day=1)
            days_until_monday = (7 - first_day_of_month.weekday()) % 7
            if first_day_of_month.weekday() != 0:  # If not already Monday
                start_date = first_day_of_month + timedelta(days=days_until_monday)
            else:
                start_date = first_day_of_month

            self.logger.info(f"  Start date (First Monday of month): {start_date.strftime('%Y-%m-%d')}")
            self.logger.info(f"  Working days: Monday-Saturday (6 days per week, Sunday is holiday)")

            # Get unique cluster IDs
            cluster_ids = clustered_df['cluster_id'].unique()
            cluster_ids = [cid for cid in cluster_ids if cid != -1]  # Exclude noise

            num_agents = len(agents_df)
            num_clusters = len(cluster_ids)
            routes_per_week = num_agents * 6  # 6 working days per week
            routes_per_4weeks = routes_per_week * 4  # Approximately 1 month

            self.logger.info(f"  Number of agents: {num_agents}")
            self.logger.info(f"  Number of clusters to assign: {num_clusters}")
            self.logger.info(f"  Monthly capacity: {routes_per_4weeks} routes ({num_agents} agents × 6 days × 4 weeks)")

            # This should never happen since we now limit clusters during processing
            if num_clusters > routes_per_4weeks:
                self.logger.error(f"  ERROR: {num_clusters} clusters exceeds {routes_per_4weeks} monthly capacity!")
                self.logger.error(f"  This should not happen - capacity check failed in processing step!")
                # Truncate to capacity
                self.logger.warning(f"  Truncating to first {routes_per_4weeks} clusters...")
                cluster_ids = cluster_ids[:routes_per_4weeks]
                num_clusters = len(cluster_ids)

            self.logger.info(f"  Assigning {num_clusters} clusters to {num_agents} agents...")

            # Create (agent, date) combinations systematically
            # Each combination gets EXACTLY ONE cluster
            agent_ids = agents_df['AgentID'].tolist()
            current_date = start_date
            weekday = 1  # Monday
            agent_index = 0

            assignments = []
            used_combinations = set()  # Track (agent, date) to ensure uniqueness

            for i, cluster_id in enumerate(cluster_ids):
                # Cycle through agents for current date
                agent_id = agent_ids[agent_index]
                agent_row = agents_df[agents_df['AgentID'] == agent_id].iloc[0]

                # Ensure this (agent, date) combination is unique
                combination_key = (agent_id, current_date.strftime('%Y-%m-%d'))
                if combination_key in used_combinations:
                    self.logger.error(f"  ERROR: Duplicate (agent, date) detected: {combination_key}")
                used_combinations.add(combination_key)

                # Assign this cluster
                assignment = {
                    'cluster_id': cluster_id,
                    'AgentID': agent_id,
                    'SalesManTerritory': agent_row['SalesManTerritory'],
                    'RouteDate': current_date.strftime('%Y-%m-%d'),
                    'WD': weekday
                }
                assignments.append(assignment)

                self.logger.info(f"  Cluster {cluster_id}: Agent {agent_id}, Date {current_date.strftime('%Y-%m-%d')} (WD={weekday})")

                # Move to next agent
                agent_index += 1

                # If all agents assigned for this date, move to next date
                if agent_index >= len(agent_ids):
                    agent_index = 0
                    current_date += timedelta(days=1)
                    weekday += 1

                    # Skip Sunday only (working days: Mon-Sat = WD 1-6)
                    if weekday > 6:  # After Saturday
                        # Skip Sunday, move to Monday
                        current_date += timedelta(days=1)
                        weekday = 1

            # Merge assignments into clustered_df
            assignments_df = pd.DataFrame(assignments)

            # Ensure RouteDate is string type in assignments_df
            if 'RouteDate' in assignments_df.columns:
                assignments_df['RouteDate'] = assignments_df['RouteDate'].astype(str)

            result_df = clustered_df.merge(assignments_df, on='cluster_id', how='left')

            # Verify RouteDate is string after merge
            if 'RouteDate' in result_df.columns:
                result_df['RouteDate'] = result_df['RouteDate'].astype(str)

            # Check for unassigned clusters (NaN in RouteDate)
            unassigned = result_df[result_df['RouteDate'].isna()]
            if len(unassigned) > 0:
                self.logger.error(f"  ERROR: {len(unassigned)} prospects have no RouteDate assigned!")
                self.logger.error(f"  Cluster IDs with issues: {unassigned['cluster_id'].unique()}")

            self.logger.info(f"  Assigned {len(assignments)} clusters to {len(used_combinations)} unique (agent, date) combinations")
            if len(assignments) != len(used_combinations):
                self.logger.warning(f"  WARNING: Duplicate combinations detected!")

            return result_df

        except Exception as e:
            self.logger.error(f"Error assigning agents and dates: {e}")
            import traceback
            traceback.print_exc()
            return clustered_df

    # ========================================================================
    # STEP 6: TSP OPTIMIZATION AND INSERT
    # ========================================================================

    def optimize_cluster_route_with_ors(self, cluster_df, distributor_lat=None, distributor_lon=None):
        """
        Optimize route within a cluster using Haversine-based TSP (FAST MODE)

        Args:
            cluster_df: DataFrame with cluster prospects
            distributor_lat: Starting latitude (optional)
            distributor_lon: Starting longitude (optional)

        Returns:
            DataFrame with added StopNo column
        """
        try:
            if len(cluster_df) <= 1:
                cluster_df = cluster_df.copy()
                cluster_df['StopNo'] = 1
                return cluster_df

            # Build location list for distance matrix
            locations = []
            location_mapping = []

            # Add starting location if provided (distributor)
            has_start_location = distributor_lat is not None and distributor_lon is not None
            if has_start_location:
                locations.append([distributor_lon, distributor_lat])
                location_mapping.append({'type': 'start', 'index': None})

            # Add all prospect locations
            for idx, row in cluster_df.iterrows():
                locations.append([row['longitude'], row['latitude']])
                location_mapping.append({'type': 'prospect', 'index': idx})

            # PERFORMANCE OPTIMIZED: Use vectorized Haversine distance matrix (10-100x faster!)
            distance_matrix = self.haversine_distance_matrix_fast(locations)

            # Nearest neighbor TSP
            unvisited_indices = list(range(len(locations)))
            route_indices = []

            # Start from distributor or first prospect
            if has_start_location:
                current_idx = 0
                unvisited_indices.remove(0)
            else:
                current_idx = 0
                unvisited_indices.remove(0)
                route_indices.append(current_idx)

            # Build route
            while unvisited_indices:
                # Find nearest unvisited location
                nearest_idx = None
                nearest_dist = float('inf')

                for idx in unvisited_indices:
                    dist = distance_matrix[current_idx][idx]
                    if dist < nearest_dist:
                        nearest_dist = dist
                        nearest_idx = idx

                route_indices.append(nearest_idx)
                unvisited_indices.remove(nearest_idx)
                current_idx = nearest_idx

            # Map back to dataframe indices and assign stop numbers
            route_df_indices = []
            for route_idx in route_indices:
                mapping = location_mapping[route_idx]
                if mapping['type'] == 'prospect':
                    route_df_indices.append(mapping['index'])

            # Create result with stop numbers
            result_rows = []
            for stop_no, df_idx in enumerate(route_df_indices, start=1):
                row = cluster_df.loc[df_idx].copy()
                row['StopNo'] = stop_no
                result_rows.append(row)

            result_df = pd.DataFrame(result_rows)

            return result_df

        except Exception as e:
            self.logger.error(f"Error optimizing route: {e}")
            import traceback
            traceback.print_exc()
            cluster_df['StopNo'] = range(1, len(cluster_df) + 1)
            return cluster_df

    def prepare_monthly_route_records(self, optimized_df, distributor_id):
        """
        Prepare records for insertion into MonthlyRoutePlan_temp

        Args:
            optimized_df: DataFrame with optimized routes (must have StopNo, AgentID, RouteDate, etc.)
            distributor_id: Distributor ID

        Returns:
            List of dicts ready for insertion
        """
        try:
            records = []

            for _, row in optimized_df.iterrows():
                # Handle RouteDate - ensure it's a string
                route_date = row['RouteDate']
                if pd.isna(route_date):
                    self.logger.error(f"Skipping record with missing RouteDate: {row.get('CustNo', 'Unknown')}")
                    continue

                # Convert to string if it's not already
                if not isinstance(route_date, str):
                    if isinstance(route_date, pd.Timestamp):
                        route_date_str = route_date.strftime('%Y-%m-%d')
                    else:
                        route_date_str = str(route_date)
                else:
                    route_date_str = route_date

                # Calculate week number
                try:
                    route_date_obj = datetime.strptime(route_date_str, '%Y-%m-%d')
                    week_number = route_date_obj.isocalendar()[1]
                except ValueError as e:
                    self.logger.error(f"Invalid date format for {route_date_str}: {e}")
                    continue

                # Generate RouteCode: Territory_WeekNo_WD
                territory = row.get('SalesManTerritory', '')
                wd = row.get('WD', 1)
                if territory:
                    route_code = f"{territory}_W{week_number:02d}_D{wd}"
                else:
                    route_code = f"W{week_number:02d}_D{wd}"

                record = {
                    'CustNo': str(row['CustNo']),
                    'RouteDate': route_date_str,
                    'Name': str(row.get('Name', '')),
                    'WD': int(row.get('WD', 1)),
                    'SalesManTerritory': str(row.get('SalesManTerritory', '')),
                    'AgentID': str(row.get('AgentID', '')),
                    'RouteName': f"Prospect Route {row.get('AgentID', '')} {route_date_str}",
                    'DistributorID': str(distributor_id),
                    'RouteCode': route_code,
                    'SalesOfficeID': '',
                    'StopNo': int(row['StopNo'])
                }
                records.append(record)

            return records

        except Exception as e:
            self.logger.error(f"Error preparing records: {e}")
            import traceback
            traceback.print_exc()
            return []

    def insert_into_monthlyrouteplan(self, db, records):
        """Insert records into MonthlyRoutePlan_temp"""
        try:
            if not records:
                self.logger.warning("No records to insert")
                return 0

            if self.test_mode:
                # Store records for CSV export
                self.all_test_records.extend(records)

                self.logger.info("=" * 60)
                self.logger.info("TEST MODE - NO DATABASE CHANGES")
                self.logger.info("=" * 60)
                self.logger.info(f"WOULD INSERT: {len(records)} records")
                self.logger.info("\nSample Records (first 5):")
                for i, rec in enumerate(records[:5]):
                    self.logger.info(f"  {i+1}. CustNo={rec['CustNo']}, Agent={rec['AgentID']}, Date={rec['RouteDate']}, StopNo={rec['StopNo']}")
                self.logger.info("=" * 60)
                return len(records)
            else:
                # Real insertion
                connection = db.connection
                cursor = connection.cursor()

                insert_query = """
                INSERT INTO MonthlyRoutePlan_temp
                (CustNo, RouteDate, Name, WD, SalesManTerritory, AgentID, RouteName, DistributorID, RouteCode, SalesOfficeID, StopNo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                insert_params = [
                    (
                        rec['CustNo'],
                        rec['RouteDate'],
                        rec['Name'],
                        rec['WD'],
                        rec['SalesManTerritory'],
                        rec['AgentID'],
                        rec['RouteName'],
                        rec['DistributorID'],
                        rec['RouteCode'],
                        rec['SalesOfficeID'],
                        rec['StopNo']
                    )
                    for rec in records
                ]

                cursor.executemany(insert_query, insert_params)
                connection.commit()
                cursor.close()

                self.logger.info(f"Successfully inserted {len(insert_params)} records")
                return len(insert_params)

        except Exception as e:
            self.logger.error(f"Error inserting records: {e}")
            import traceback
            traceback.print_exc()
            if not self.test_mode:
                connection.rollback()
            return 0

    # ========================================================================
    # MAIN PIPELINE
    # ========================================================================

    def run_pipeline(self, distributor_id, start_date, distributor_lat=None, distributor_lon=None, barangay_code_filter=None):
        """
        Run the complete ORS-based prospect clustering pipeline

        Args:
            distributor_id: Distributor ID
            start_date: Starting date (YYYY-MM-DD)
            distributor_lat: Starting latitude for routes (optional)
            distributor_lon: Starting longitude for routes (optional)
            barangay_code_filter: Test with single barangay only (optional)

        Returns:
            Number of records inserted/exported
        """
        self.start_time = datetime.now()

        self.logger.info("=" * 80)
        if self.test_mode:
            self.logger.info("TEST MODE - ORS PROSPECT CLUSTERING (DRY RUN)")
            self.logger.info("NO DATABASE CHANGES WILL BE MADE")
        else:
            self.logger.info("ORS PROSPECT CLUSTERING PIPELINE")
        self.logger.info("=" * 80)
        self.logger.info(f"Distributor ID: {distributor_id}")
        self.logger.info(f"Start Date: {start_date} (will adjust to first Monday of month)")
        self.logger.info(f"Working Days: Monday-Saturday (6 days/week, Sunday is holiday)")
        self.logger.info(f"Max Stores per Cluster: {self.max_stores_per_cluster}")
        self.logger.info(f"Min Stores Threshold: {self.min_stores_threshold}")
        if distributor_lat and distributor_lon:
            self.logger.info(f"Distributor Location: ({distributor_lat}, {distributor_lon})")
        self.logger.info("=" * 80)

        db = None
        try:
            db = DatabaseConnection()
            db.connect()

            # STEP 1: Get sales agents with access = 15 for this distributor
            self.logger.info("\n" + "=" * 80)
            self.logger.info(f"STEP 1: Getting sales agents with access = 15 for distributor {distributor_id}")
            self.logger.info("=" * 80)
            agents_df = self.get_sales_agents_with_access_15(db, distributor_id)

            if agents_df.empty:
                self.logger.error("No sales agents found. Cannot proceed.")
                return 0

            # STEP 2: Get distributor barangays
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 2: Getting distributor barangays")
            self.logger.info("=" * 80)
            barangays_df = self.get_distributor_barangays(db, distributor_id)

            if barangays_df.empty:
                self.logger.error("No barangays found for distributor. Cannot proceed.")
                return 0

            # STEP 2.5: Calculate monthly route capacity (actual working days in month)
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 2.5: Calculating monthly route capacity")
            self.logger.info("=" * 80)

            # Parse start_date to get year and month
            if isinstance(start_date, str):
                date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            else:
                date_obj = start_date

            target_year = date_obj.year
            target_month = date_obj.month

            # Calculate actual working days in this specific month
            working_days_in_month = self.calculate_working_days_in_month(target_year, target_month)

            num_agents = len(agents_df)
            monthly_route_capacity = num_agents * working_days_in_month

            self.logger.info(f"Target month: {calendar.month_name[target_month]} {target_year}")
            self.logger.info(f"Number of agents: {num_agents}")
            self.logger.info(f"Working days in month: {working_days_in_month} (Mon-Sat, excluding Sundays only)")
            self.logger.info(f"MONTHLY ROUTE CAPACITY: {monthly_route_capacity} routes ({num_agents} agents × {working_days_in_month} days)")
            self.logger.info(f"Max stores per route: {self.max_stores_per_cluster}")
            self.logger.info(f"Theoretical max stores per month: {monthly_route_capacity * self.max_stores_per_cluster}")
            self.logger.info("=" * 80)

            # STEP 2.6: Count and sort barangays by store count (highest first)
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 2.6: Counting stores per barangay and sorting")
            self.logger.info("=" * 80)

            # OPTIMIZATION: Fetch excluded IDs once for all barangays (much faster!)
            excluded_ids = self.fetch_excluded_ids(db, exclude_latest_month=True)

            # Count stores and sort barangays (highest store count first)
            barangays_df = self.count_stores_per_barangay(db, barangays_df, excluded_ids)

            # Filter to single barangay if specified (for testing)
            if barangay_code_filter:
                barangays_df = barangays_df[barangays_df['BarangayCode'] == barangay_code_filter]
                if barangays_df.empty:
                    self.logger.error(f"Barangay {barangay_code_filter} not found for this distributor")
                    return 0
                self.logger.info(f"Testing with single barangay: {barangay_code_filter}")

            # STEP 3: Process each barangay and cluster (in order of store count)
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 3: Processing barangays and clustering prospects")
            self.logger.info("Processing order: HIGHEST store count first")
            self.logger.info(f"Monthly capacity: {monthly_route_capacity} routes (will stop when reached)")
            self.logger.info("=" * 80)

            all_clustered_prospects = []
            total_clusters_created = 0  # Track number of clusters (routes) created
            total_stores_assigned = 0  # Track total stores assigned

            global_cluster_id_offset = 0  # Track offset for making cluster_ids globally unique

            for idx, barangay_row in barangays_df.iterrows():
                # Check if we've reached monthly capacity
                if total_clusters_created >= monthly_route_capacity:
                    remaining_barangays = len(barangays_df) - idx
                    self.logger.info("\n" + "=" * 80)
                    self.logger.info(f"✓ MONTHLY CAPACITY REACHED: {total_clusters_created}/{monthly_route_capacity} routes")
                    self.logger.info(f"✓ Total stores assigned: {total_stores_assigned}")
                    self.logger.info(f"  Skipping remaining {remaining_barangays} barangays for this month")
                    self.logger.info(f"  These will be processed in future months")
                    self.logger.info("=" * 80)
                    break

                barangay_code = barangay_row['BarangayCode']
                barangay_name = barangay_row['BarangayName']
                available_stores = barangay_row.get('AvailableStores', '?')

                # Calculate expected clusters for informational purposes
                if isinstance(available_stores, int) and available_stores > 0:
                    expected_clusters = int(np.ceil(available_stores / self.max_stores_per_cluster))
                    self.logger.info(f"\n[{idx+1}/{len(barangays_df)}] Processing: {barangay_name} ({barangay_code})")
                    self.logger.info(f"  Stores: {available_stores}, Expected clusters: {expected_clusters}")
                else:
                    self.logger.info(f"\n[{idx+1}/{len(barangays_df)}] Processing: {barangay_name} ({barangay_code}) - {available_stores} stores")

                self.logger.info(f"  Progress: {total_clusters_created}/{monthly_route_capacity} routes used, {total_stores_assigned} stores assigned")

                # Get prospects for this barangay (passing pre-fetched excluded_ids)
                prospects_df = self.get_prospects_by_barangay(db, barangay_code, excluded_ids=excluded_ids)

                if prospects_df.empty:
                    self.logger.info(f"  No prospects found, skipping")
                    continue

                # Cluster prospects
                clustered_df = self.cluster_prospects_with_ors(prospects_df, self.max_stores_per_cluster)

                # Count how many clusters (routes) this barangay created
                if 'cluster_id' in clustered_df.columns:
                    num_clusters_this_barangay = len(clustered_df[clustered_df['cluster_id'] != -1]['cluster_id'].unique())
                    cluster_ids_this_barangay = sorted(clustered_df[clustered_df['cluster_id'] != -1]['cluster_id'].unique())
                else:
                    num_clusters_this_barangay = 0
                    cluster_ids_this_barangay = []

                # Check if adding this barangay would exceed capacity
                if total_clusters_created + num_clusters_this_barangay > monthly_route_capacity:
                    remaining_capacity = monthly_route_capacity - total_clusters_created

                    if remaining_capacity > 0:
                        # PARTIAL SELECTION: Take only what we need to fill capacity
                        self.logger.warning(f"  ⚠ Adding all {num_clusters_this_barangay} clusters would exceed capacity")
                        self.logger.warning(f"  Current: {total_clusters_created}, Would become: {total_clusters_created + num_clusters_this_barangay}, Limit: {monthly_route_capacity}")
                        self.logger.info(f"  ✓ PARTIAL SELECTION: Taking first {remaining_capacity} clusters, saving {num_clusters_this_barangay - remaining_capacity} for next month")

                        # Select only the first N clusters to fill capacity
                        clusters_to_take = cluster_ids_this_barangay[:remaining_capacity]
                        clustered_df = clustered_df[clustered_df['cluster_id'].isin(clusters_to_take)]
                        num_clusters_this_barangay = remaining_capacity

                        self.logger.info(f"  Selected clusters: {clusters_to_take}")
                    else:
                        # No capacity left at all
                        self.logger.warning(f"  ⚠ Monthly capacity fully utilized: {total_clusters_created}/{monthly_route_capacity}")
                        self.logger.warning(f"  Skipping this and remaining barangays for this month")
                        break

                # CRITICAL FIX: Make cluster_id globally unique across all barangays
                # Without this, each barangay creates clusters with IDs 0,1,2... causing
                # multiple clusters to share the same ID and get assigned to same (agent, date)
                if 'cluster_id' in clustered_df.columns:
                    valid_cluster_ids = clustered_df[clustered_df['cluster_id'] != -1]['cluster_id']
                    if not valid_cluster_ids.empty:
                        # Add offset to make IDs globally unique
                        clustered_df.loc[clustered_df['cluster_id'] != -1, 'cluster_id'] += global_cluster_id_offset
                        # Update offset for next barangay
                        global_cluster_id_offset = clustered_df['cluster_id'].max() + 1

                clustered_df['barangay_code'] = barangay_code
                clustered_df['barangay_name'] = barangay_name

                all_clustered_prospects.append(clustered_df)

                # Update counters
                total_clusters_created += num_clusters_this_barangay
                total_stores_assigned += len(clustered_df[clustered_df['cluster_id'] != -1])

                self.logger.info(f"  ✓ Created {num_clusters_this_barangay} clusters from this barangay")
                self.logger.info(f"  ✓ Running total: {total_clusters_created}/{monthly_route_capacity} routes, {total_stores_assigned} stores")

                # Check if we've reached exact capacity
                if total_clusters_created >= monthly_route_capacity:
                    remaining_barangays = len(barangays_df) - (idx + 1)
                    self.logger.info("\n" + "=" * 80)
                    self.logger.info(f"✓ MONTHLY CAPACITY REACHED: {total_clusters_created}/{monthly_route_capacity} routes")
                    self.logger.info(f"✓ Total stores assigned: {total_stores_assigned}")
                    if remaining_barangays > 0:
                        self.logger.info(f"  Skipping remaining {remaining_barangays} barangays for this month")
                        self.logger.info(f"  These will be processed in future months")
                    self.logger.info("=" * 80)
                    break

            if not all_clustered_prospects:
                self.logger.error("No prospects found across all barangays. Cannot proceed.")
                return 0

            # Combine all clusters
            all_clusters_df = pd.concat(all_clustered_prospects, ignore_index=True)
            self.logger.info(f"\nTotal prospects clustered: {len(all_clusters_df)}")

            # STEP 4: Merge small clusters
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 4: Post-processing - Merging small clusters")
            self.logger.info("=" * 80)
            all_clusters_df = self.merge_small_clusters(all_clusters_df, self.min_stores_threshold, self.max_stores_per_cluster)

            # STEP 4.5: Rebalance nearby clusters for equal distribution
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 4.5: Post-processing - Rebalancing nearby clusters")
            self.logger.info("=" * 80)
            all_clusters_df = self.rebalance_nearby_clusters(all_clusters_df, min_size=40, max_size=self.max_stores_per_cluster)

            # STEP 5: Assign agents and dates
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 5: Assigning agents and dates to clusters")
            self.logger.info("=" * 80)
            assigned_df = self.assign_agents_and_dates_to_clusters(all_clusters_df, agents_df, start_date)

            # STEP 6: Optimize routes and insert
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 6: Optimizing routes and preparing for insertion")
            self.logger.info("=" * 80)

            all_optimized_routes = []
            unique_clusters = assigned_df['cluster_id'].unique()
            unique_clusters = [c for c in unique_clusters if c != -1]

            for cluster_id in unique_clusters:
                cluster_df = assigned_df[assigned_df['cluster_id'] == cluster_id].copy()

                self.logger.info(f"\nOptimizing Cluster {cluster_id}: {len(cluster_df)} prospects")

                # Optimize route with ORS
                optimized_df = self.optimize_cluster_route_with_ors(
                    cluster_df,
                    distributor_lat,
                    distributor_lon
                )

                all_optimized_routes.append(optimized_df)

            # Combine all optimized routes
            final_routes_df = pd.concat(all_optimized_routes, ignore_index=True)

            # Prepare records for insertion
            records = self.prepare_monthly_route_records(final_routes_df, distributor_id)

            # Insert into database
            total_inserted = self.insert_into_monthlyrouteplan(db, records)

            # Summary
            duration = (datetime.now() - self.start_time).total_seconds()
            self.logger.info("\n" + "=" * 80)
            if self.test_mode:
                self.logger.info("TEST MODE COMPLETED - NO CHANGES MADE TO DATABASE")

                # Export to CSV
                if self.all_test_records:
                    csv_filename = f"ors_prospect_routes_{distributor_id}_{start_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    csv_path = os.path.join(os.path.dirname(__file__), 'output', csv_filename)
                    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

                    df = pd.DataFrame(self.all_test_records)
                    df.to_csv(csv_path, index=False)

                    self.logger.info(f"CSV EXPORTED: {csv_path}")
                    self.logger.info(f"Total records in CSV: {len(self.all_test_records)}")
                    print(f"\n>>> CSV file saved: {csv_path}")
            else:
                self.logger.info("PIPELINE COMPLETED!")

            self.logger.info(f"Total records processed: {total_inserted}")
            self.logger.info(f"Total clusters created: {len(unique_clusters)}")
            self.logger.info(f"Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
            self.logger.info("=" * 80)

            return total_inserted

        except Exception as e:
            self.logger.error(f"Pipeline error: {e}")
            import traceback
            traceback.print_exc()
            return 0

        finally:
            if db:
                db.close()


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="ORS-Based Prospect Clustering Pipeline")
    parser.add_argument("--test", "--dry-run", action="store_true",
                        help="Test mode - run without making database changes")
    parser.add_argument("--distributor", "-d", type=str, required=True,
                        help="DistributorID (e.g., 11814)")
    parser.add_argument("--start-date", type=str, required=True,
                        help="Start date - will be adjusted to first Monday of the month (YYYY-MM-DD)")
    parser.add_argument("--max-cluster-size", type=int, default=60,
                        help="Maximum stores per cluster (default: 60)")
    parser.add_argument("--min-cluster-size", type=int, default=20,
                        help="Minimum stores for standalone cluster (default: 20)")
    parser.add_argument("--distributor-lat", type=float, default=None,
                        help="Distributor starting latitude for routes (optional)")
    parser.add_argument("--distributor-lon", type=float, default=None,
                        help="Distributor starting longitude for routes (optional)")
    parser.add_argument("--barangay-code", type=str, default=None,
                        help="Test with single barangay code only (e.g., 137401001)")
    parser.add_argument("--ors-api-key", type=str, default=None,
                        help="ORS API key for authenticated requests (optional)")

    args = parser.parse_args()

    print("=" * 80)
    if args.test:
        print("TEST MODE - ORS PROSPECT CLUSTERING")
        print("DRY RUN - NO DATABASE CHANGES WILL BE MADE")
    else:
        print("ORS PROSPECT CLUSTERING PIPELINE")
        print("WARNING: THIS WILL MODIFY THE DATABASE")
    print("=" * 80)
    print(f"Distributor: {args.distributor}")
    print(f"Start Date: {args.start_date} (will adjust to first Monday of month)")
    print(f"Working Days: Monday-Saturday (6 days/week, Sunday is holiday)")
    print(f"Max Cluster Size: {args.max_cluster_size} stores")
    print(f"Min Cluster Size: {args.min_cluster_size} stores")
    if args.distributor_lat and args.distributor_lon:
        print(f"Distributor Location: ({args.distributor_lat}, {args.distributor_lon})")
    if args.ors_api_key:
        print(f"ORS API Key: {'*' * 20} (provided)")
    else:
        print(f"ORS API Key: None (using public endpoint)")
    print("=" * 80)

    if not args.test:
        confirm = input("\nContinue with database modifications? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled by user")
            return

    try:
        # Determine ORS API key: command line > .env file
        ors_api_key = args.ors_api_key
        if not ors_api_key and hasattr(ors_config, 'ORS_CONFIG'):
            ors_api_key = ors_config.ORS_CONFIG.get('api_key')

        # Run pipeline
        pipeline = ORSProspectClusteringPipeline(
            test_mode=args.test,
            max_stores_per_cluster=args.max_cluster_size,
            min_stores_threshold=args.min_cluster_size,
            ors_api_key=ors_api_key
        )

        pipeline.run_pipeline(
            distributor_id=args.distributor,
            start_date=args.start_date,
            distributor_lat=args.distributor_lat,
            distributor_lon=args.distributor_lon,
            barangay_code_filter=args.barangay_code
        )

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
