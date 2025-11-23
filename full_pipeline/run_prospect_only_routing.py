#!/usr/bin/env python3
"""
Prospect-Only Route Clustering Pipeline

This pipeline creates prospect routes using distributor name (RD) as input:
1. Get stores from prospective table by RD column
2. Get all barangay codes for the RD
3. Constraint k-means clustering within each barangay (max 60 stores per cluster)
4. Exclude stores that exist in custvisit table
5. Post-processing: merge small clusters with nearby clusters based on coordinates
6. TSP optimization starting from distributor location
7. Assign salesagents based on distributor → nodetree → salesagent relationship
8. Random agent/date assignment
9. Output in MonthlyRoutePlan_temp format

A cluster = one day's route for one salesagent
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import calendar
import logging
import argparse
import json
import hashlib
import random
from collections import defaultdict
from math import radians, cos, sin, asin, sqrt

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection


class ProspectOnlyRoutingPipeline:
    def __init__(self, test_mode=False, max_stores_per_cluster=60, min_stores_threshold=20):
        """Initialize prospect-only routing pipeline

        Args:
            test_mode: If True, runs without updating database (dry-run)
            max_stores_per_cluster: Maximum stores per cluster (default: 60)
            min_stores_threshold: Minimum stores for standalone cluster (default: 20)
        """
        self.test_mode = test_mode
        self.max_stores_per_cluster = max_stores_per_cluster
        self.min_stores_threshold = min_stores_threshold
        self.start_time = None
        self.all_test_records = []  # Store all records in test mode

        # Setup logging
        self.setup_logging()

    def setup_logging(self):
        """Setup logging configuration"""
        log_filename = f"prospect_only_routing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
    # DISTANCE CALCULATION
    # ========================================================================

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

    # ========================================================================
    # STEP 1: GET DISTRIBUTOR INFO BY NAME (RD)
    # ========================================================================

    def get_distributor_by_name(self, db, distributor_name):
        """Get distributor information by name (RD)

        Args:
            db: Database connection
            distributor_name: Distributor name (RD from prospective table)

        Returns:
            Dictionary with distributor info (ID, name, lat, lon)
        """
        try:
            query = f"""
            SELECT
                DistributorID,
                DistributorName,
                Latitude,
                Longitude
            FROM Distributor
            WHERE DistributorName = '{distributor_name}'
            """

            result_df = db.execute_query_df(query)

            if result_df is None or result_df.empty:
                self.logger.error(f"Distributor '{distributor_name}' not found in Distributor table")
                return None

            dist_info = {
                'DistributorID': result_df.iloc[0]['DistributorID'],
                'DistributorName': result_df.iloc[0]['DistributorName'],
                'Latitude': result_df.iloc[0]['Latitude'],
                'Longitude': result_df.iloc[0]['Longitude']
            }

            self.logger.info(f"Found distributor: {dist_info['DistributorName']} (ID: {dist_info['DistributorID']})")
            self.logger.info(f"  Location: ({dist_info['Latitude']}, {dist_info['Longitude']})")

            return dist_info

        except Exception as e:
            self.logger.error(f"Error getting distributor by name: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ========================================================================
    # STEP 2: GET BARANGAYS FOR RD
    # ========================================================================

    def get_barangays_for_rd(self, db, distributor_name):
        """Get all barangay codes for a distributor (RD)

        Args:
            db: Database connection
            distributor_name: Distributor name (RD)

        Returns:
            DataFrame with barangay codes and names
        """
        try:
            query = f"""
            SELECT DISTINCT
                p.barangay_code AS BarangayCode,
                b.BarangayName
            FROM prospective p
            LEFT JOIN Barangay b ON b.Code = p.barangay_code
            WHERE p.RD = '{distributor_name}'
                AND p.barangay_code IS NOT NULL
                AND p.barangay_code != ''
            ORDER BY b.BarangayName
            """

            barangays_df = db.execute_query_df(query)

            if barangays_df is not None and not barangays_df.empty:
                self.logger.info(f"Found {len(barangays_df)} barangays for RD '{distributor_name}'")
                return barangays_df
            else:
                self.logger.warning(f"No barangays found for RD '{distributor_name}'")
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error getting barangays for RD: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    # ========================================================================
    # STEP 3: GET PROSPECTS AND EXCLUDE CUSTVISIT
    # ========================================================================

    def fetch_excluded_ids_from_custvisit(self, db):
        """Fetch store IDs that exist in custvisit table (to exclude)"""
        try:
            self.logger.info("Fetching excluded IDs from custvisit...")
            query = """
            SELECT DISTINCT CustID
            FROM custvisit
            """
            cv_df = db.execute_query_df(query)

            if cv_df is not None and not cv_df.empty:
                excluded_ids = set(cv_df['CustID'].tolist())
                self.logger.info(f"  Excluded {len(excluded_ids)} store IDs from custvisit")
                return excluded_ids
            else:
                self.logger.info("  No exclusions from custvisit")
                return set()

        except Exception as e:
            self.logger.error(f"Error fetching excluded IDs: {e}")
            import traceback
            traceback.print_exc()
            return set()

    def get_prospects_by_barangay(self, db, barangay_code, rd_name, excluded_ids=None):
        """Get prospects for a specific barangay and RD

        Args:
            db: Database connection
            barangay_code: Barangay code to filter
            rd_name: RD (distributor name) to filter
            excluded_ids: Set of excluded store IDs from custvisit

        Returns:
            DataFrame with prospect data
        """
        try:
            query = f"""
            SELECT
                p.tdlinx as CustNo,
                p.latitude,
                p.longitude,
                p.barangay_code,
                p.store_name_nielsen as Name,
                p.RD
            FROM prospective p
            WHERE p.barangay_code = '{barangay_code}'
                AND p.RD = '{rd_name}'
                AND p.latitude IS NOT NULL
                AND p.longitude IS NOT NULL
                AND p.latitude != 0
                AND p.longitude != 0
            """

            prospects_df = db.execute_query_df(query)

            if prospects_df is None or prospects_df.empty:
                return pd.DataFrame()

            # Filter out excluded IDs (from custvisit)
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

    def count_stores_per_barangay(self, db, barangays_df, rd_name, excluded_ids=None):
        """Count available stores per barangay

        Returns barangays_df with added 'StoreCount' column, sorted by count descending
        """
        try:
            self.logger.info("\nCounting stores per barangay...")

            barangay_counts = []

            for _, row in barangays_df.iterrows():
                barangay_code = row['BarangayCode']

                # Get prospects for this barangay
                prospects_df = self.get_prospects_by_barangay(db, barangay_code, rd_name, excluded_ids)
                available_count = len(prospects_df)

                barangay_counts.append({
                    'BarangayCode': barangay_code,
                    'BarangayName': row['BarangayName'],
                    'AvailableStores': available_count
                })

                self.logger.info(f"  {row['BarangayName']} ({barangay_code}): {available_count} stores available")

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

    # ========================================================================
    # STEP 4: CLUSTERING
    # ========================================================================

    def cluster_prospects_constrained_kmeans(self, prospects_df, max_per_cluster=60):
        """Cluster prospects using Constrained K-Means

        Args:
            prospects_df: DataFrame with prospect data
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

            return prospects_df

        except Exception as e:
            self.logger.error(f"Error clustering prospects: {e}")
            import traceback
            traceback.print_exc()
            # Fallback: assign all to one cluster
            prospects_df['cluster_id'] = 0
            return prospects_df

    # ========================================================================
    # STEP 5: POST-PROCESSING - MERGE SMALL CLUSTERS
    # ========================================================================

    def merge_small_clusters_by_proximity(self, all_clusters_df, min_size=20, max_size=60):
        """Merge clusters with < min_size stores into nearby clusters based on coordinates
        Can merge across barangays if stores are geographically close

        Args:
            all_clusters_df: DataFrame with all prospects and cluster_id
            min_size: Minimum cluster size threshold
            max_size: Maximum cluster size

        Returns:
            DataFrame with updated cluster_id
        """
        try:
            self.logger.info(f"\nPost-processing: Merging clusters with < {min_size} stores...")

            # Identify small clusters
            cluster_sizes = all_clusters_df.groupby('cluster_id').size()
            small_clusters = cluster_sizes[cluster_sizes < min_size].index.tolist()

            if not small_clusters:
                self.logger.info("  No small clusters to merge")
                return all_clusters_df

            self.logger.info(f"  Found {len(small_clusters)} small clusters to merge")

            merged_count = 0
            skipped_count = 0

            # For each small cluster, find nearest cluster based on coordinates
            for small_cluster_id in small_clusters:
                small_cluster_df = all_clusters_df[all_clusters_df['cluster_id'] == small_cluster_id]
                small_cluster_size = len(small_cluster_df)

                if small_cluster_size == 0:
                    continue

                # Calculate center of small cluster
                center_lat = small_cluster_df['latitude'].mean()
                center_lon = small_cluster_df['longitude'].mean()

                # Find all other clusters
                current_cluster_sizes = all_clusters_df.groupby('cluster_id').size()
                other_clusters = all_clusters_df[all_clusters_df['cluster_id'] != small_cluster_id]

                if other_clusters.empty:
                    self.logger.warning(f"  No other clusters available to merge cluster {small_cluster_id}")
                    skipped_count += 1
                    continue

                # Find nearest cluster by geographic distance (can be different barangay)
                other_cluster_ids = other_clusters['cluster_id'].unique()
                min_distance = float('inf')
                best_cluster_id = None

                for candidate_id in other_cluster_ids:
                    candidate_size = current_cluster_sizes[candidate_id]

                    # Check if merging would exceed max_size
                    if candidate_size + small_cluster_size > max_size:
                        continue

                    candidate_df = all_clusters_df[all_clusters_df['cluster_id'] == candidate_id]
                    candidate_lat = candidate_df['latitude'].mean()
                    candidate_lon = candidate_df['longitude'].mean()

                    distance = self.haversine_distance(center_lat, center_lon, candidate_lat, candidate_lon)

                    if distance < min_distance:
                        min_distance = distance
                        best_cluster_id = candidate_id

                if best_cluster_id is not None:
                    target_size = current_cluster_sizes[best_cluster_id]
                    new_size = target_size + small_cluster_size

                    # Get barangay info for logging
                    small_barangay = small_cluster_df['barangay_code'].iloc[0]
                    target_barangay = all_clusters_df[all_clusters_df['cluster_id'] == best_cluster_id]['barangay_code'].iloc[0]
                    cross_barangay = " (cross-barangay)" if small_barangay != target_barangay else ""

                    self.logger.info(f"  Merging cluster {small_cluster_id} ({small_cluster_size} stores) into cluster {best_cluster_id} ({target_size} → {new_size} stores, distance: {min_distance:.2f}km){cross_barangay}")
                    all_clusters_df.loc[all_clusters_df['cluster_id'] == small_cluster_id, 'cluster_id'] = best_cluster_id
                    merged_count += 1
                else:
                    self.logger.warning(f"  Cannot merge cluster {small_cluster_id} ({small_cluster_size} stores) - would exceed {max_size} store limit")
                    skipped_count += 1

            self.logger.info(f"  Merged {merged_count} small clusters, skipped {skipped_count}")

            # Final statistics
            final_cluster_sizes = all_clusters_df.groupby('cluster_id').size()
            self.logger.info(f"\nFinal cluster distribution:")
            self.logger.info(f"  Total clusters: {len(final_cluster_sizes)}")
            self.logger.info(f"  Cluster sizes: min={final_cluster_sizes.min()}, max={final_cluster_sizes.max()}, mean={final_cluster_sizes.mean():.1f}")

            return all_clusters_df

        except Exception as e:
            self.logger.error(f"Error merging small clusters: {e}")
            import traceback
            traceback.print_exc()
            return all_clusters_df

    # ========================================================================
    # STEP 6: GET SALESAGENTS FOR DISTRIBUTOR
    # ========================================================================

    def get_salesagents_for_distributor(self, db, distributor_id):
        """Get salesagents assigned to a distributor

        Logic:
        1. Get salesagents where access = 15
        2. Match salesagent.nodetreevalue to nodetree.salesmanterritory
        3. Filter by nodetree.DistributorID

        Args:
            db: Database connection
            distributor_id: Distributor ID

        Returns:
            DataFrame with salesagent info
        """
        try:
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

            agents_df = db.execute_query_df(query)

            if agents_df is not None and not agents_df.empty:
                self.logger.info(f"Found {len(agents_df)} salesagents for distributor {distributor_id}")
                for _, agent in agents_df.iterrows():
                    self.logger.info(f"  Agent: {agent['AgentName']} (ID: {agent['AgentID']}, Territory: {agent['SalesManTerritory']})")
                return agents_df
            else:
                self.logger.warning(f"No salesagents found for distributor {distributor_id}")
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error getting salesagents: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    # ========================================================================
    # STEP 7: ASSIGN AGENTS AND DATES RANDOMLY
    # ========================================================================

    def assign_agents_and_dates_randomly(self, clustered_df, agents_df, start_date):
        """Randomly assign sales agents and dates to each cluster

        Args:
            clustered_df: DataFrame with prospects and cluster_id
            agents_df: DataFrame with available sales agents
            start_date: Starting date (YYYY-MM-DD string or datetime)

        Returns:
            DataFrame with added AgentID, RouteDate, WD columns
        """
        try:
            self.logger.info("\nRandomly assigning agents and dates to clusters...")

            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d')

            # Get unique cluster IDs
            cluster_ids = clustered_df['cluster_id'].unique()
            cluster_ids = [cid for cid in cluster_ids if cid != -1]

            num_agents = len(agents_df)
            num_clusters = len(cluster_ids)

            self.logger.info(f"  Number of agents: {num_agents}")
            self.logger.info(f"  Number of clusters: {num_clusters}")

            # Generate random agent/date assignments
            agent_ids = agents_df['AgentID'].tolist()
            assignments = []

            # Generate date range (e.g., 30 days from start_date)
            date_range = []
            current_date = start_date
            for _ in range(30):  # 30 working days
                # Skip Sundays
                if current_date.weekday() != 6:
                    date_range.append(current_date)
                current_date += timedelta(days=1)

            for cluster_id in cluster_ids:
                # Randomly select agent
                agent_id = random.choice(agent_ids)
                agent_row = agents_df[agents_df['AgentID'] == agent_id].iloc[0]

                # Randomly select date
                route_date = random.choice(date_range)
                weekday = route_date.weekday() + 1  # 1=Monday, 6=Saturday

                assignment = {
                    'cluster_id': cluster_id,
                    'AgentID': agent_id,
                    'SalesManTerritory': agent_row['SalesManTerritory'],
                    'RouteDate': route_date.strftime('%Y-%m-%d'),
                    'WD': weekday if weekday <= 6 else 1  # Ensure WD is 1-6
                }
                assignments.append(assignment)

                self.logger.info(f"  Cluster {cluster_id}: Agent {agent_id}, Date {route_date.strftime('%Y-%m-%d')} (WD={assignment['WD']})")

            # Merge assignments into clustered_df
            assignments_df = pd.DataFrame(assignments)

            # Ensure RouteDate is string type
            if 'RouteDate' in assignments_df.columns:
                assignments_df['RouteDate'] = assignments_df['RouteDate'].astype(str)

            result_df = clustered_df.merge(assignments_df, on='cluster_id', how='left')

            # Verify RouteDate is string after merge
            if 'RouteDate' in result_df.columns:
                result_df['RouteDate'] = result_df['RouteDate'].astype(str)

            self.logger.info(f"  Assigned {len(assignments)} clusters")

            return result_df

        except Exception as e:
            self.logger.error(f"Error assigning agents and dates: {e}")
            import traceback
            traceback.print_exc()
            return clustered_df

    # ========================================================================
    # STEP 8: TSP OPTIMIZATION
    # ========================================================================

    def optimize_cluster_route_tsp(self, cluster_df, distributor_lat, distributor_lon):
        """Optimize route within a cluster using TSP starting from distributor location

        Args:
            cluster_df: DataFrame with cluster prospects
            distributor_lat: Distributor latitude (starting point)
            distributor_lon: Distributor longitude (starting point)

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

            # Add starting location (distributor)
            if distributor_lat is not None and distributor_lon is not None:
                locations.append([distributor_lon, distributor_lat])
                location_mapping.append({'type': 'start', 'index': None})
                has_start = True
            else:
                has_start = False

            # Add all prospect locations
            for idx, row in cluster_df.iterrows():
                locations.append([row['longitude'], row['latitude']])
                location_mapping.append({'type': 'prospect', 'index': idx})

            # Calculate distance matrix
            distance_matrix = self.haversine_distance_matrix_fast(locations)

            # Nearest neighbor TSP
            unvisited_indices = list(range(len(locations)))
            route_indices = []

            # Start from distributor or first prospect
            if has_start:
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

    # ========================================================================
    # STEP 9: PREPARE RECORDS FOR MONTHLYROUTEPLAN
    # ========================================================================

    def prepare_monthly_route_records(self, optimized_df, distributor_id):
        """Prepare records for insertion into MonthlyRoutePlan_temp

        Args:
            optimized_df: DataFrame with optimized routes
            distributor_id: Distributor ID

        Returns:
            List of dicts ready for insertion
        """
        try:
            records = []

            for _, row in optimized_df.iterrows():
                # Handle RouteDate
                route_date = row['RouteDate']
                if pd.isna(route_date):
                    self.logger.error(f"Skipping record with missing RouteDate: {row.get('CustNo', 'Unknown')}")
                    continue

                # Convert to string if needed
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

    def run_pipeline(self, distributor_name, start_date):
        """Run the complete prospect-only routing pipeline

        Args:
            distributor_name: Distributor name (RD from prospective table)
            start_date: Starting date (YYYY-MM-DD)

        Returns:
            Number of records inserted/exported
        """
        self.start_time = datetime.now()

        self.logger.info("=" * 80)
        if self.test_mode:
            self.logger.info("TEST MODE - PROSPECT-ONLY ROUTING (DRY RUN)")
            self.logger.info("NO DATABASE CHANGES WILL BE MADE")
        else:
            self.logger.info("PROSPECT-ONLY ROUTING PIPELINE")
        self.logger.info("=" * 80)
        self.logger.info(f"Distributor (RD): {distributor_name}")
        self.logger.info(f"Start Date: {start_date}")
        self.logger.info(f"Max Stores per Cluster: {self.max_stores_per_cluster}")
        self.logger.info(f"Min Stores Threshold: {self.min_stores_threshold}")
        self.logger.info("=" * 80)

        db = None
        try:
            db = DatabaseConnection()
            db.connect()

            # STEP 1: Get distributor info by name
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 1: Getting distributor info by name (RD)")
            self.logger.info("=" * 80)
            dist_info = self.get_distributor_by_name(db, distributor_name)

            if dist_info is None:
                self.logger.error("Cannot proceed without distributor info")
                return 0

            distributor_id = dist_info['DistributorID']
            distributor_lat = dist_info['Latitude']
            distributor_lon = dist_info['Longitude']

            # STEP 2: Get barangays for this RD
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 2: Getting barangays for RD")
            self.logger.info("=" * 80)
            barangays_df = self.get_barangays_for_rd(db, distributor_name)

            if barangays_df.empty:
                self.logger.error("No barangays found. Cannot proceed.")
                return 0

            # STEP 3: Fetch excluded IDs from custvisit
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 3: Fetching excluded store IDs from custvisit")
            self.logger.info("=" * 80)
            excluded_ids = self.fetch_excluded_ids_from_custvisit(db)

            # STEP 4: Count stores per barangay
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 4: Counting stores per barangay")
            self.logger.info("=" * 80)
            barangays_df = self.count_stores_per_barangay(db, barangays_df, distributor_name, excluded_ids)

            # STEP 5: Process each barangay and cluster
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 5: Processing barangays and clustering prospects")
            self.logger.info("=" * 80)

            all_clustered_prospects = []
            global_cluster_id_offset = 0

            for idx, barangay_row in barangays_df.iterrows():
                barangay_code = barangay_row['BarangayCode']
                barangay_name = barangay_row['BarangayName']
                available_stores = barangay_row.get('AvailableStores', 0)

                if available_stores == 0:
                    self.logger.info(f"\n[{idx+1}/{len(barangays_df)}] Skipping {barangay_name} - no stores")
                    continue

                self.logger.info(f"\n[{idx+1}/{len(barangays_df)}] Processing: {barangay_name} ({barangay_code}) - {available_stores} stores")

                # Get prospects
                prospects_df = self.get_prospects_by_barangay(db, barangay_code, distributor_name, excluded_ids)

                if prospects_df.empty:
                    continue

                # Cluster prospects
                clustered_df = self.cluster_prospects_constrained_kmeans(prospects_df, self.max_stores_per_cluster)

                # Make cluster IDs globally unique
                if 'cluster_id' in clustered_df.columns:
                    valid_cluster_ids = clustered_df[clustered_df['cluster_id'] != -1]['cluster_id']
                    if not valid_cluster_ids.empty:
                        clustered_df.loc[clustered_df['cluster_id'] != -1, 'cluster_id'] += global_cluster_id_offset
                        global_cluster_id_offset = clustered_df['cluster_id'].max() + 1

                clustered_df['barangay_code'] = barangay_code
                clustered_df['barangay_name'] = barangay_name

                all_clustered_prospects.append(clustered_df)

            if not all_clustered_prospects:
                self.logger.error("No prospects found. Cannot proceed.")
                return 0

            # Combine all clusters
            all_clusters_df = pd.concat(all_clustered_prospects, ignore_index=True)
            self.logger.info(f"\nTotal prospects clustered: {len(all_clusters_df)}")

            # STEP 6: Merge small clusters based on proximity
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 6: Post-processing - Merging small clusters by proximity")
            self.logger.info("=" * 80)
            all_clusters_df = self.merge_small_clusters_by_proximity(
                all_clusters_df,
                self.min_stores_threshold,
                self.max_stores_per_cluster
            )

            # STEP 7: Get salesagents for distributor
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 7: Getting salesagents for distributor")
            self.logger.info("=" * 80)
            agents_df = self.get_salesagents_for_distributor(db, distributor_id)

            if agents_df.empty:
                self.logger.error("No salesagents found. Cannot proceed.")
                return 0

            # STEP 8: Randomly assign agents and dates
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 8: Randomly assigning agents and dates to clusters")
            self.logger.info("=" * 80)
            assigned_df = self.assign_agents_and_dates_randomly(all_clusters_df, agents_df, start_date)

            # STEP 9: Optimize routes with TSP
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 9: Optimizing routes with TSP")
            self.logger.info("=" * 80)

            all_optimized_routes = []
            unique_clusters = assigned_df['cluster_id'].unique()
            unique_clusters = [c for c in unique_clusters if c != -1]

            for cluster_id in unique_clusters:
                cluster_df = assigned_df[assigned_df['cluster_id'] == cluster_id].copy()

                self.logger.info(f"\nOptimizing Cluster {cluster_id}: {len(cluster_df)} prospects")

                optimized_df = self.optimize_cluster_route_tsp(
                    cluster_df,
                    distributor_lat,
                    distributor_lon
                )

                all_optimized_routes.append(optimized_df)

            # Combine all optimized routes
            final_routes_df = pd.concat(all_optimized_routes, ignore_index=True)

            # STEP 10: Prepare and insert records
            self.logger.info("\n" + "=" * 80)
            self.logger.info("STEP 10: Preparing records for MonthlyRoutePlan_temp")
            self.logger.info("=" * 80)

            records = self.prepare_monthly_route_records(final_routes_df, distributor_id)
            total_inserted = self.insert_into_monthlyrouteplan(db, records)

            # Summary
            duration = (datetime.now() - self.start_time).total_seconds()
            self.logger.info("\n" + "=" * 80)
            if self.test_mode:
                self.logger.info("TEST MODE COMPLETED - NO CHANGES MADE TO DATABASE")

                # Export to CSV
                if self.all_test_records:
                    csv_filename = f"prospect_only_routes_{distributor_name}_{start_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
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
    parser = argparse.ArgumentParser(description="Prospect-Only Routing Pipeline")
    parser.add_argument("--test", "--dry-run", action="store_true",
                        help="Test mode - run without making database changes")
    parser.add_argument("--distributor-name", "-d", type=str, required=True,
                        help="Distributor name (RD from prospective table, e.g., 'PEPSI-COLA PRODUCTS PHILIPPINES, INC. - MANDAUE')")
    parser.add_argument("--start-date", type=str, required=True,
                        help="Start date (YYYY-MM-DD)")
    parser.add_argument("--max-cluster-size", type=int, default=60,
                        help="Maximum stores per cluster (default: 60)")
    parser.add_argument("--min-cluster-size", type=int, default=20,
                        help="Minimum stores for standalone cluster (default: 20)")

    args = parser.parse_args()

    print("=" * 80)
    if args.test:
        print("TEST MODE - PROSPECT-ONLY ROUTING")
        print("DRY RUN - NO DATABASE CHANGES WILL BE MADE")
    else:
        print("PROSPECT-ONLY ROUTING PIPELINE")
        print("WARNING: THIS WILL MODIFY THE DATABASE")
    print("=" * 80)
    print(f"Distributor (RD): {args.distributor_name}")
    print(f"Start Date: {args.start_date}")
    print(f"Max Cluster Size: {args.max_cluster_size} stores")
    print(f"Min Cluster Size: {args.min_cluster_size} stores")
    print("=" * 80)

    if not args.test:
        confirm = input("\nContinue with database modifications? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled by user")
            return

    try:
        # Run pipeline
        pipeline = ProspectOnlyRoutingPipeline(
            test_mode=args.test,
            max_stores_per_cluster=args.max_cluster_size,
            min_stores_threshold=args.min_cluster_size
        )

        pipeline.run_pipeline(
            distributor_name=args.distributor_name,
            start_date=args.start_date
        )

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
