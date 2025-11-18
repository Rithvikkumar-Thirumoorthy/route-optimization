#!/usr/bin/env python3
"""
Monthly Route Plan Pipeline - Hierarchical Flow
Process MonthlyRoutePlan_temp with hierarchical structure:
1. DistributorID (top level)
2. SalesAgent (within each distributor)
3. Date (ordered chronologically)
4. Run scenario conditions for each combination
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import time
from math import radians, cos, sin, asin, sqrt
import threading

# Import database module from local src directory
try:
    from database import DatabaseConnection
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running from the project root directory")
    sys.exit(1)

class HierarchicalMonthlyRoutePipelineProcessor:
    def __init__(self, batch_size=50, max_workers=4, start_lat=None, start_lon=None, distributor_id=None):
        """Initialize hierarchical monthly route pipeline processor

        Args:
            batch_size: Batch size for processing
            max_workers: Maximum worker threads
            start_lat: Starting latitude for TSP optimization (optional)
            start_lon: Starting longitude for TSP optimization (optional)
            distributor_id: Filter by specific distributor ID (optional)
        """
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.processed_count = 0
        self.error_count = 0
        self.start_time = None
        self.start_lat = start_lat
        self.start_lon = start_lon
        self.distributor_id = distributor_id

        # Performance optimization: Add caching
        self._customer_coords_cache = {}  # Cache customer coordinates
        self._barangay_cache = {}  # Cache barangay lookups
        self._prospect_cache = {}  # Cache prospect queries
        self._distributor_location_cache = {}  # Cache distributor locations

        # Track if user explicitly set start coordinates via CLI
        self._user_set_coordinates = start_lat is not None and start_lon is not None

        # Thread safety for parallel processing
        self._progress_lock = threading.Lock()
        self._cache_lock = threading.Lock()

        # Setup logging
        self.setup_logging()

    def setup_logging(self):
        """Setup logging configuration"""
        log_filename = f"hierarchical_monthly_route_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_path = os.path.join(os.path.dirname(__file__), 'logs', log_filename)

        # Create logs directory if it doesn't exist
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

    def get_customer_coordinates_batch(self, db, customer_nos_list):
        """
        Performance optimization: Batch fetch customer coordinates with caching

        Args:
            db: Database connection
            customer_nos_list: List of customer numbers

        Returns:
            DataFrame with customer coordinates
        """
        try:
            # Check cache first (thread-safe)
            uncached_custnos = []
            cached_data = []

            with self._cache_lock:
                for custno in customer_nos_list:
                    if custno in self._customer_coords_cache:
                        cached_data.append(self._customer_coords_cache[custno])
                    else:
                        uncached_custnos.append(custno)

            # Fetch uncached data from database
            if uncached_custnos:
                customer_nos = "', '".join([str(c) for c in uncached_custnos])
                customer_query = f"""
                SELECT
                    CustNo, latitude, longitude, address3 as barangay_code
                FROM customer
                WHERE CustNo IN ('{customer_nos}')
                AND latitude IS NOT NULL
                AND longitude IS NOT NULL
                AND latitude != 0.0
                AND longitude != 0.0
                AND ABS(latitude) > 0.000001
                AND ABS(longitude) > 0.000001
                """
                customer_coords_df = db.execute_query_df(customer_query)

                if customer_coords_df is not None and not customer_coords_df.empty:
                    # Cache the results (thread-safe)
                    with self._cache_lock:
                        for _, row in customer_coords_df.iterrows():
                            self._customer_coords_cache[row['CustNo']] = row.to_dict()
                            cached_data.append(row.to_dict())

            # Convert cached data to DataFrame
            if cached_data:
                return pd.DataFrame(cached_data)
            else:
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error in batch coordinate fetch: {e}")
            return pd.DataFrame()

    def get_distributor_location(self, db, distributor_id):
        """
        Get distributor location from distributors table with caching and fallback

        Priority order:
        1. User-specified coordinates (CLI arguments) - highest priority
        2. Distributor table location - from database
        3. Config default values - fallback

        Args:
            db: Database connection
            distributor_id: Distributor ID to fetch location for

        Returns:
            Tuple of (latitude, longitude)
        """
        try:
            # Priority 1: If user explicitly set coordinates via CLI, always use those
            if self._user_set_coordinates:
                self.logger.info(f"Using user-specified coordinates: ({self.start_lat}, {self.start_lon})")
                return self.start_lat, self.start_lon

            # Check cache first (thread-safe)
            with self._cache_lock:
                if distributor_id in self._distributor_location_cache:
                    cached_location = self._distributor_location_cache[distributor_id]
                    self.logger.debug(f"Using cached location for distributor {distributor_id}")
                    return cached_location['Latitude'], cached_location['Longitude']

            # Priority 2: Fetch from distributors table
            distributor_query = f"""
            SELECT TOP 1
                Latitude,
                Longitude,
                Name,
                Address
            FROM distributors
            WHERE DistributorID = '{distributor_id}'
            AND Latitude IS NOT NULL
            AND Longitude IS NOT NULL
            AND Latitude != 0
            AND Longitude != 0
            AND ABS(Latitude) > 0.000001
            AND ABS(Longitude) > 0.000001
            """

            distributor_df = db.execute_query_df(distributor_query)

            if distributor_df is not None and not distributor_df.empty:
                distributor = distributor_df.iloc[0]
                location_data = {
                    'Latitude': distributor['Latitude'],
                    'Longitude': distributor['Longitude'],
                    'Name': distributor.get('Name', 'Unknown'),
                    'Address': distributor.get('Address', 'Unknown')
                }

                # Cache the result (thread-safe)
                with self._cache_lock:
                    self._distributor_location_cache[distributor_id] = location_data

                self.logger.info(f"Distributor {distributor_id} ({location_data['Name']}): "
                               f"({location_data['Latitude']:.6f}, {location_data['Longitude']:.6f})")

                return location_data['Latitude'], location_data['Longitude']
            else:
                # Priority 3: Fallback to config defaults
                self.logger.warning(f"No location found for distributor {distributor_id}, using config defaults")
                if self.start_lat and self.start_lon:
                    return self.start_lat, self.start_lon
                else:
                    # Ultimate fallback - Manila coordinates
                    self.logger.warning("No start coordinates configured, using Manila default")
                    return 14.5995, 120.9842

        except Exception as e:
            self.logger.error(f"Error fetching distributor location: {e}")
            # Fallback on error
            if self.start_lat and self.start_lon:
                return self.start_lat, self.start_lon
            else:
                self.logger.warning("Using Manila default coordinates due to error")
                return 14.5995, 120.9842

    def get_distributors_hierarchy(self, db):
        """Get hierarchical structure: DistributorID -> SalesAgent -> Date

        OPTIMIZED: Single query instead of nested loops
        """
        try:
            self.logger.info("Building hierarchical processing structure...")

            # OPTIMIZED: Single query to get entire hierarchy
            distributor_filter = ""
            if self.distributor_id:
                distributor_filter = f"AND DistributorID = '{self.distributor_id}'"
                self.logger.info(f"Filtering for DistributorID: {self.distributor_id}")

            # Single query gets all distributors, agents, dates, and stats
            hierarchy_query = f"""
            SELECT
                DistributorID,
                AgentID,
                RouteDate,
                COUNT(DISTINCT CustNo) as customer_count,
                COUNT(*) as total_records
            FROM MonthlyRoutePlan_temp
            WHERE DistributorID IS NOT NULL
                AND AgentID IS NOT NULL
                AND RouteDate IS NOT NULL
                AND CustNo IS NOT NULL
                {distributor_filter}
            GROUP BY DistributorID, AgentID, RouteDate
            ORDER BY DistributorID, AgentID, RouteDate ASC
            """

            hierarchy_df = db.execute_query_df(hierarchy_query)

            if hierarchy_df is None or hierarchy_df.empty:
                self.logger.error("No data found in MonthlyRoutePlan_temp")
                return {}

            # Build hierarchy dictionary from query results
            hierarchy = {}
            for _, row in hierarchy_df.iterrows():
                distributor_id = row['DistributorID']
                agent_id = row['AgentID']

                if distributor_id not in hierarchy:
                    hierarchy[distributor_id] = {}

                if agent_id not in hierarchy[distributor_id]:
                    hierarchy[distributor_id][agent_id] = []

                hierarchy[distributor_id][agent_id].append({
                    'RouteDate': row['RouteDate'],
                    'customer_count': row['customer_count'],
                    'total_records': row['total_records']
                })

            # Log summary
            for distributor_id, agents in hierarchy.items():
                total_agents = len(agents)
                total_combinations = sum(len(dates) for dates in agents.values())
                self.logger.info(f"DistributorID {distributor_id}: {total_agents} agents, {total_combinations} date combinations")

            total_distributors = len(hierarchy)
            total_agents = sum(len(agents) for agents in hierarchy.values())
            total_combinations = sum(sum(len(dates) for dates in agents.values()) for agents in hierarchy.values())
            self.logger.info(f"Total: {total_distributors} distributors, {total_agents} agents, {total_combinations} combinations")

            return hierarchy

        except Exception as e:
            self.logger.error(f"Error building hierarchy: {e}")
            return {}

    def process_agent_parallel_wrapper(self, distributor_id, agent_id, dates_list):
        """
        Wrapper for parallel agent processing - creates its own DB connection
        Each thread needs its own database connection to avoid conflicts

        Args:
            distributor_id: Distributor ID
            agent_id: Agent ID
            dates_list: List of date dictionaries

        Returns:
            List of result dictionaries
        """
        db = None
        try:
            # Create dedicated database connection for this thread
            db = DatabaseConnection(pool_size=2, max_overflow=5)
            db.connect(enable_pooling=True)

            # Process the agent using the dedicated connection
            results = self.process_agent_with_sequential_stopno(
                db, distributor_id, agent_id, dates_list
            )

            return results

        except Exception as e:
            self.logger.error(f"Error in parallel agent processing {agent_id}: {e}")
            return [{
                "status": "error",
                "distributor": distributor_id,
                "agent": agent_id,
                "error": str(e)
            }]
        finally:
            if db:
                db.close()

    def process_agent_with_sequential_stopno(self, db, distributor_id, agent_id, dates_list):
        """Process all dates for a single agent with sequential StopNo across all dates"""
        try:
            self.logger.info(f"Processing Agent {agent_id} with {len(dates_list)} dates - Sequential StopNo Assignment")

            # Get distributor-specific starting location
            dist_start_lat, dist_start_lon = self.get_distributor_location(db, distributor_id)
            self.logger.info(f"Using starting location for TSP: ({dist_start_lat:.6f}, {dist_start_lon:.6f})")

            # Sort dates chronologically
            sorted_dates = sorted(dates_list, key=lambda x: x['RouteDate'])

            # Collect all data across all dates for sequential numbering
            all_optimized_data = []
            all_no_coord_data = []
            results = []
            current_stopno = 1

            # Process each date and collect optimized data
            for date_info in sorted_dates:
                route_date = date_info['RouteDate']
                customer_count = date_info['customer_count']

                self.logger.info(f"Processing Date: {route_date} ({customer_count} customers)")

                # Check scenario conditions
                should_process, scenario_info = self.check_scenario_conditions(distributor_id, agent_id, route_date, customer_count)

                if not should_process:
                    self.logger.info(f"Skipping {route_date} based on scenario conditions: {scenario_info.get('scenario', 'unknown')}")
                    results.append({
                        "status": "skipped",
                        "distributor": distributor_id,
                        "agent": agent_id,
                        "date": route_date,
                        "reason": "scenario_conditions",
                        "scenario": scenario_info
                    })
                    continue

                # Get and enrich data for this date
                all_data_for_tsp, customers_without_coords = self.enrich_monthly_plan_data(db, distributor_id, agent_id, route_date)

                if not all_data_for_tsp.empty:
                    # Apply TSP optimization using distributor-specific starting location
                    self.logger.info(f"Applying TSP optimization to {len(all_data_for_tsp)} locations for {route_date}")
                    optimized_data = self.solve_tsp_nearest_neighbor(all_data_for_tsp, dist_start_lat, dist_start_lon)

                    # Keep track of the original route date
                    optimized_data['RouteDate'] = route_date
                    all_optimized_data.append(optimized_data)

                if not customers_without_coords.empty:
                    # Keep customers without coordinates separate
                    customers_without_coords['RouteDate'] = route_date
                    all_no_coord_data.append(customers_without_coords)

            # Now assign FRESH sequential StopNo across all dates (ignoring any existing StopNo)
            total_updates = 0

            # Combine all data from all dates into one big list for sequential numbering
            all_customers_for_sequential_assignment = []

            # Process each date separately with per-date StopNo assignment (1-N per date)
            for date_info in sorted_dates:
                route_date = date_info['RouteDate']

                # Find optimized data for this date
                optimized_for_this_date = None
                for optimized_data in all_optimized_data:
                    if optimized_data['RouteDate'].iloc[0] == route_date:
                        optimized_for_this_date = optimized_data
                        break

                # Find no-coordinate data for this date
                no_coord_for_this_date = None
                for no_coord_data in all_no_coord_data:
                    if no_coord_data['RouteDate'].iloc[0] == route_date:
                        no_coord_for_this_date = no_coord_data
                        break

                # For each date, start StopNo from 1 for customers with coordinates
                date_stopno = 1

                # Add optimized customers first (StopNo 1, 2, 3, ... N)
                if optimized_for_this_date is not None:
                    for _, row in optimized_for_this_date.iterrows():
                        all_customers_for_sequential_assignment.append({
                            'CustNo': row['CustNo'],
                            'RouteDate': row['RouteDate'],
                            'new_stopno': date_stopno,
                            'type': 'optimized'
                        })
                        date_stopno += 1

                # Add customers without coordinates (StopNo = 100)
                if no_coord_for_this_date is not None:
                    for _, row in no_coord_for_this_date.iterrows():
                        all_customers_for_sequential_assignment.append({
                            'CustNo': row['CustNo'],
                            'RouteDate': row['RouteDate'],
                            'new_stopno': 100,
                            'type': 'no_coordinates'
                        })

            # Now update existing customers and insert prospects with their new StopNo assignments
            updates_by_date = {}
            inserts_by_date = {}

            self.logger.info(f"Processing {len(all_customers_for_sequential_assignment)} records (updates + inserts)")

            # Use direct database connection for more reliable operations
            connection = db.connection
            cursor = connection.cursor()

            try:
                # Separate existing customers (for UPDATE) from prospects (for INSERT)
                update_params = []
                insert_params = []

                for customer in all_customers_for_sequential_assignment:
                    if customer['type'] == 'optimized':
                        # Check if this is an existing customer or a prospect
                        # Find the original record in optimized data
                        is_prospect = False
                        for optimized_data in all_optimized_data:
                            matching_rows = optimized_data[
                                (optimized_data['CustNo'] == customer['CustNo']) &
                                (optimized_data['RouteDate'] == customer['RouteDate'])
                            ]
                            if not matching_rows.empty and 'custype' in matching_rows.columns:
                                is_prospect = (matching_rows.iloc[0]['custype'] == 'prospect')
                                break

                        if is_prospect:
                            # INSERT prospect into monthlyrouteplan_temp
                            # Get prospect details from optimized_data
                            for optimized_data in all_optimized_data:
                                matching_rows = optimized_data[
                                    (optimized_data['CustNo'] == customer['CustNo']) &
                                    (optimized_data['RouteDate'] == customer['RouteDate'])
                                ]
                                if not matching_rows.empty:
                                    prospect_row = matching_rows.iloc[0]

                                    # Convert numpy types to native Python types
                                    wd_value = prospect_row.get('WD', 1)
                                    if pd.notna(wd_value):
                                        wd_value = int(wd_value)
                                    else:
                                        wd_value = 1

                                    # Truncate Name to avoid SQL truncation error
                                    # Name column appears to be VARCHAR(15) based on SQL errors
                                    name_value = str(prospect_row.get('Name', ''))[:15]  # Truncate to 15 chars

                                    insert_params.append((
                                        str(distributor_id)[:30],  # Truncate all fields for safety
                                        str(agent_id)[:30],
                                        str(customer['RouteDate']),
                                        str(customer['CustNo'])[:30],
                                        int(customer['new_stopno']),
                                        name_value,
                                        wd_value,
                                        str(prospect_row.get('SalesManTerritory', ''))[:30],
                                        str(prospect_row.get('RouteName', ''))[:30],
                                        str(prospect_row.get('RouteCode', ''))[:30],
                                        str(prospect_row.get('SalesOfficeID', ''))[:30]
                                    ))

                                    # Track inserts by date
                                    date_key = customer['RouteDate']
                                    if date_key not in inserts_by_date:
                                        inserts_by_date[date_key] = 0
                                    inserts_by_date[date_key] += 1
                                    break
                        else:
                            # UPDATE existing customer
                            update_params.append((
                                customer['new_stopno'],
                                distributor_id,
                                agent_id,
                                customer['RouteDate'],
                                customer['CustNo']
                            ))

                            # Track updates by date
                            date_key = customer['RouteDate']
                            if date_key not in updates_by_date:
                                updates_by_date[date_key] = 0
                            updates_by_date[date_key] += 1
                    else:
                        # No coordinates - UPDATE existing customer
                        update_params.append((
                            customer['new_stopno'],
                            distributor_id,
                            agent_id,
                            customer['RouteDate'],
                            customer['CustNo']
                        ))

                        # Track updates by date
                        date_key = customer['RouteDate']
                        if date_key not in updates_by_date:
                            updates_by_date[date_key] = 0
                        updates_by_date[date_key] += 1

                # Execute batch update for existing customers
                if update_params:
                    update_query = """
                    UPDATE MonthlyRoutePlan_temp
                    SET StopNo = ?
                    WHERE DistributorID = ? AND AgentID = ? AND RouteDate = ? AND CustNo = ?
                    """
                    cursor.executemany(update_query, update_params)
                    self.logger.info(f"Successfully updated {len(update_params)} existing customer records")

                # Execute batch insert for prospects
                if insert_params:
                    insert_query = """
                    INSERT INTO MonthlyRoutePlan_temp
                    (DistributorID, AgentID, RouteDate, CustNo, StopNo, Name, WD, SalesManTerritory, RouteName, RouteCode, SalesOfficeID)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    cursor.executemany(insert_query, insert_params)
                    self.logger.info(f"Successfully inserted {len(insert_params)} prospect records")

                connection.commit()

                total_updates = len(update_params)
                total_inserts = len(insert_params)
                self.logger.info(f"Total operations: {total_updates} updates + {total_inserts} inserts = {total_updates + total_inserts} records")

            except Exception as e:
                self.logger.error(f"Error in batch update/insert: {e}")
                connection.rollback()
                raise e
            finally:
                cursor.close()

            # Create results for each date
            all_dates = set(list(updates_by_date.keys()) + list(inserts_by_date.keys()))
            for route_date in all_dates:
                update_count = updates_by_date.get(route_date, 0)
                insert_count = inserts_by_date.get(route_date, 0)
                total_count = update_count + insert_count

                results.append({
                    "status": "success",
                    "distributor": distributor_id,
                    "agent": agent_id,
                    "date": route_date,
                    "records_updated": update_count,
                    "records_inserted": insert_count,
                    "total_records": total_count
                })

                self.logger.info(f"Completed {route_date}: {update_count} updates + {insert_count} inserts = {total_count} total")

            self.logger.info(f"Agent {agent_id} completed: {total_updates} updates + {total_inserts} inserts = {total_updates + total_inserts} total records")
            return results

        except Exception as e:
            self.logger.error(f"Error processing agent {agent_id}: {e}")
            return [{
                "status": "error",
                "distributor": distributor_id,
                "agent": agent_id,
                "error": str(e)
            }]

    def check_scenario_conditions(self, distributor_id, agent_id, route_date, customer_count):
        """
        Check scenario conditions for processing
        Returns: (should_process: bool, scenario_info: dict)
        """
        try:
            # Define scenario conditions based on your requirements
            scenario_info = {
                'distributor_id': distributor_id,
                'agent_id': agent_id,
                'route_date': route_date,
                'customer_count': customer_count,
                'scenario': None,
                'should_process': False
            }

            # Scenario 1: High volume routes (25+ customers)
            if customer_count >= 25:
                scenario_info['scenario'] = 'high_volume'
                scenario_info['should_process'] = True
                self.logger.info(f"  Scenario: High Volume (25+ customers)")
                return True, scenario_info

            # Scenario 2: Medium volume routes (10-24 customers)
            elif customer_count >= 10:
                scenario_info['scenario'] = 'medium_volume'
                scenario_info['should_process'] = True
                self.logger.info(f"  Scenario: Medium Volume (10-24 customers)")
                return True, scenario_info

            # Scenario 3: Low volume routes (5-9 customers)
            elif customer_count >= 5:
                scenario_info['scenario'] = 'low_volume'
                scenario_info['should_process'] = True
                self.logger.info(f"  Scenario: Low Volume (5-9 customers)")
                return True, scenario_info

            # Scenario 4: Very small routes (1-4 customers)
            else:
                scenario_info['scenario'] = 'very_small'
                scenario_info['should_process'] = True
                self.logger.info(f"  Scenario: Very Small (< 5 customers)")
                return True, scenario_info

        except Exception as e:
            self.logger.error(f"Error checking scenario conditions: {e}")
            return False, {'error': str(e)}

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate the great circle distance between two points on Earth (in km)"""
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Radius of earth in kilometers
        return c * r

    def find_nearby_prospects_by_location(self, db, distributor_id, agent_id, route_date, customers_with_coords, needed_prospects, max_distance_km=5.0, exclude_custnos=None):
        """
        Find nearby prospects based on customer locations using geospatial distance

        Args:
            db: Database connection
            distributor_id: Distributor ID
            agent_id: Agent ID
            route_date: Route date
            customers_with_coords: DataFrame of customers with valid coordinates
            needed_prospects: Number of prospects needed
            max_distance_km: Maximum distance in kilometers to search (default: 5km)
            exclude_custnos: List of CustNo to exclude (optional, for avoiding duplicates)

        Returns:
            DataFrame of nearby prospects
        """
        try:
            if customers_with_coords.empty:
                self.logger.warning("No customers with coordinates to use for location-based prospect search")
                return pd.DataFrame()

            # Calculate center point (average location of all customers)
            center_lat = customers_with_coords['latitude'].mean()
            center_lon = customers_with_coords['longitude'].mean()

            self.logger.info(f"Searching for prospects near center point: ({center_lat:.6f}, {center_lon:.6f})")
            self.logger.info(f"Search radius: {max_distance_km} km")

            # Build exclusion clause if needed
            exclusion_clause = ""
            if exclude_custnos is not None and len(exclude_custnos) > 0:
                exclude_list = "', '".join([str(cust) for cust in exclude_custnos])
                exclusion_clause = f"AND tdlinx NOT IN ('{exclude_list}')"
                self.logger.info(f"Excluding {len(exclude_custnos)} already-found prospects from search")

            # Get all prospects from prospective table with coordinates
            # We'll filter by distance in Python since SQL Server spatial queries can be complex
            prospect_query = f"""
            SELECT
                tdlinx as CustNo, latitude, longitude,
                barangay_code, store_name_nielsen as Name
            FROM prospective
            WHERE latitude IS NOT NULL
            AND longitude IS NOT NULL
            AND latitude != 0
            AND longitude != 0
            {exclusion_clause}
            AND NOT EXISTS (
                SELECT 1 FROM MonthlyRoutePlan_temp
                WHERE MonthlyRoutePlan_temp.CustNo = prospective.tdlinx
                AND MonthlyRoutePlan_temp.DistributorID = '{distributor_id}'
                AND MonthlyRoutePlan_temp.AgentID = '{agent_id}'
                AND MonthlyRoutePlan_temp.RouteDate = CONVERT(DATE, '{route_date}')
            )
            AND NOT EXISTS (
                SELECT 1 FROM custvisit
                WHERE custvisit.CustID = prospective.tdlinx
            )
            """

            all_prospects_df = db.execute_query_df(prospect_query)

            if all_prospects_df is None or all_prospects_df.empty:
                self.logger.warning("No unvisited prospects found in prospective table")
                return pd.DataFrame()

            self.logger.info(f"Found {len(all_prospects_df)} total unvisited prospects, filtering by distance...")

            # Calculate distance from center point to each prospect
            distances = []
            for _, prospect in all_prospects_df.iterrows():
                dist = self.haversine_distance(
                    center_lat, center_lon,
                    prospect['latitude'], prospect['longitude']
                )
                distances.append(dist)

            all_prospects_df['distance_km'] = distances

            # Filter prospects within max_distance_km
            nearby_prospects = all_prospects_df[all_prospects_df['distance_km'] <= max_distance_km].copy()

            if nearby_prospects.empty:
                self.logger.warning(f"No prospects found within {max_distance_km} km of customer locations")
                return pd.DataFrame()

            self.logger.info(f"Found {len(nearby_prospects)} prospects within {max_distance_km} km")

            # Sort by distance (closest first) and take only what we need
            nearby_prospects = nearby_prospects.sort_values('distance_km').head(needed_prospects)

            # Remove the distance column before returning
            nearby_prospects = nearby_prospects.drop('distance_km', axis=1)

            self.logger.info(f"Selected {len(nearby_prospects)} nearest prospects")

            return nearby_prospects

        except Exception as e:
            self.logger.error(f"Error finding nearby prospects by location: {e}")
            return pd.DataFrame()

    def solve_tsp_nearest_neighbor(self, locations_df, start_lat=None, start_lon=None):
        """Solve TSP using nearest neighbor heuristic with straight-line distance

        Args:
            locations_df: DataFrame with customer locations
            start_lat: Starting latitude (optional)
            start_lon: Starting longitude (optional)
        """
        try:
            if len(locations_df) <= 1:
                locations_df = locations_df.copy()
                locations_df['stopno'] = 1
                return locations_df

            # Start from specified location or first customer
            unvisited = locations_df.copy().reset_index(drop=True)
            route = []

            # If starting location provided, find nearest customer to start
            if start_lat is not None and start_lon is not None:
                self.logger.info(f"Using starting location: ({start_lat}, {start_lon})")

                # Find nearest customer to starting location
                distances = []
                for _, row in unvisited.iterrows():
                    dist = self.haversine_distance(start_lat, start_lon, row['latitude'], row['longitude'])
                    distances.append(dist)

                current_idx = np.argmin(distances)
                self.logger.info(f"First customer is {distances[current_idx]:.2f} km from starting location")
            else:
                # Start from first location in dataset
                current_idx = 0

            current_location = unvisited.iloc[current_idx]
            route.append(current_location)
            unvisited = unvisited.drop(current_idx).reset_index(drop=True)

            # Build route using nearest neighbor with straight-line distance
            while not unvisited.empty:
                current_lat = current_location['latitude']
                current_lon = current_location['longitude']

                # Find nearest unvisited location using Haversine distance
                distances = []
                for _, row in unvisited.iterrows():
                    dist = self.haversine_distance(current_lat, current_lon, row['latitude'], row['longitude'])
                    distances.append(dist)

                nearest_idx = np.argmin(distances)
                current_location = unvisited.iloc[nearest_idx]
                route.append(current_location)
                unvisited = unvisited.drop(unvisited.index[nearest_idx]).reset_index(drop=True)

            # Create result dataframe with stop numbers
            result_df = pd.DataFrame(route)
            result_df['stopno'] = range(1, len(result_df) + 1)

            return result_df

        except Exception as e:
            self.logger.error(f"Error in TSP optimization: {e}")
            return locations_df

    def enrich_monthly_plan_data(self, db, distributor_id, agent_id, route_date):
        """
        Enrich MonthlyRoutePlan_temp data with coordinates and addresses from customer table
        """
        try:
            self.logger.info(f"Enriching data for Distributor: {distributor_id}, Agent: {agent_id}, Date: {route_date}")

            # Step 1: Get data from MonthlyRoutePlan_temp (IGNORE existing StopNo)
            monthly_plan_query = f"""
            SELECT
                CustNo, RouteDate, Name, WD, SalesManTerritory,
                AgentID, RouteName, DistributorID, RouteCode,
                SalesOfficeID
            FROM MonthlyRoutePlan_temp
            WHERE DistributorID = '{distributor_id}'
                AND AgentID = '{agent_id}'
                AND RouteDate = '{route_date}'
                AND CustNo IS NOT NULL
            """
            monthly_plan_df = db.execute_query_df(monthly_plan_query)

            if monthly_plan_df is None or monthly_plan_df.empty:
                self.logger.warning(f"No data found in MonthlyRoutePlan_temp for {distributor_id}/{agent_id} on {route_date}")
                return pd.DataFrame(), pd.DataFrame()

            self.logger.info(f"Found {len(monthly_plan_df)} records in MonthlyRoutePlan_temp")

            # Step 2: Get coordinates and barangay_code from customer table
            # Performance optimization: Use batch fetching with caching
            customer_nos_list = monthly_plan_df['CustNo'].astype(str).tolist()
            customer_coords_df = self.get_customer_coordinates_batch(db, customer_nos_list)

            if customer_coords_df is not None and not customer_coords_df.empty:
                self.logger.info(f"Found coordinates for {len(customer_coords_df)} customers (using cache)")
            else:
                self.logger.warning("No customer coordinates found")
                customer_coords_df = pd.DataFrame()

            # Step 3: Merge monthly plan data with customer coordinates
            if not customer_coords_df.empty:
                enriched_df = monthly_plan_df.merge(
                    customer_coords_df,
                    on='CustNo',
                    how='left'
                )
            else:
                enriched_df = monthly_plan_df.copy()
                enriched_df['latitude'] = None
                enriched_df['longitude'] = None
                enriched_df['barangay_code'] = None

            # Step 4: Detect custype by checking source tables
            # OPTIMIZED: Use cache-aware custype detection
            self.logger.info("Detecting custype from source tables...")

            # Use cached custype lookups to avoid repeated queries
            with self._cache_lock:
                uncached_custnos = [cno for cno in monthly_plan_df['CustNo'] if cno not in getattr(self, '_custype_cache', {})]

                if not hasattr(self, '_custype_cache'):
                    self._custype_cache = {}

            if uncached_custnos:
                customer_nos = "', '".join([str(c) for c in uncached_custnos])

                # OPTIMIZED: Single query with UNION ALL instead of 2 separate queries
                combined_query = f"""
                SELECT CustNo, 'customer' as custype FROM customer WHERE CustNo IN ('{customer_nos}')
                UNION ALL
                SELECT tdlinx as CustNo, 'prospect' as custype FROM prospective WHERE tdlinx IN ('{customer_nos}')
                """
                custype_results = db.execute_query_df(combined_query)

                # Cache results
                with self._cache_lock:
                    if custype_results is not None and not custype_results.empty:
                        for _, row in custype_results.iterrows():
                            self._custype_cache[row['CustNo']] = row['custype']

            # Apply cached custype
            enriched_df['custype'] = enriched_df['CustNo'].map(lambda x: self._custype_cache.get(x, 'unknown'))

            # Log custype distribution
            custype_counts = enriched_df['custype'].value_counts()
            self.logger.info(f"Custype distribution: {custype_counts.to_dict()}")

            # Separate customers with and without coordinates
            customers_with_coords = enriched_df[
                (enriched_df['latitude'].notna()) &
                (enriched_df['longitude'].notna()) &
                (enriched_df['latitude'] != 0) &
                (enriched_df['longitude'] != 0)
            ].copy()

            customers_without_coords = enriched_df[
                (enriched_df['latitude'].isna()) |
                (enriched_df['longitude'].isna()) |
                (enriched_df['latitude'] == 0) |
                (enriched_df['longitude'] == 0)
            ].copy()

            self.logger.info(f"Customers with coordinates: {len(customers_with_coords)}")
            self.logger.info(f"Customers without coordinates: {len(customers_without_coords)}")

            # Step 5: Get prospects if needed (target 60 total)
            # SMART PROSPECT ADDITION: Only add prospects when customers have coordinates or address3
            # Do NOT add random prospects when no barangay information is available
            total_customers = len(enriched_df)
            prospects_df = pd.DataFrame()

            if total_customers < 60:
                needed_prospects = 60 - total_customers
                self.logger.info(f"Need {needed_prospects} prospects to reach 60 total")

                # Get barangay codes from customers with coordinates, or use address3 from customer table
                barangay_codes = []
                if not customers_with_coords.empty:
                    # Use barangay codes from customers with coordinates
                    barangay_codes = customers_with_coords['barangay_code'].dropna().unique()
                    self.logger.info(f"Found {len(barangay_codes)} barangay codes from customer coordinates")
                elif not enriched_df.empty:
                    # No customers with coordinates - get address3 from customer table to match barangay_code
                    self.logger.info("No customers with coordinates, getting address3 from customer table")
                    customer_nos = "', '".join(enriched_df['CustNo'].astype(str))
                    address3_query = f"""
                    SELECT DISTINCT address3
                    FROM customer
                    WHERE CustNo IN ('{customer_nos}')
                    AND address3 IS NOT NULL
                    AND address3 != ''
                    """
                    address3_df = db.execute_query_df(address3_query)

                    if address3_df is not None and not address3_df.empty:
                        barangay_codes = address3_df['address3'].dropna().unique()
                        self.logger.info(f"Found {len(barangay_codes)} barangay codes from customer address3: {list(barangay_codes)[:5]}")

                # Build prospect query ONLY if we have valid barangay codes
                if len(barangay_codes) > 0:
                    # Filter out empty/null barangay codes
                    valid_barangay_codes = [str(code).strip() for code in barangay_codes if code and str(code).strip()]

                    if len(valid_barangay_codes) == 0:
                        self.logger.warning("No valid barangay codes after filtering - will attempt location-based search in post-processing")
                        prospects_df = pd.DataFrame()
                    else:
                        # Use barangay codes from existing customers (either from coordinates or address3)
                        barangay_codes_str = "', '".join(valid_barangay_codes)
                        # OPTIMIZED: Use LEFT JOIN with IS NULL instead of NOT EXISTS for better performance
                        prospect_query = f"""
                        SELECT TOP {needed_prospects}
                            p.tdlinx as CustNo, p.latitude, p.longitude,
                            p.barangay_code, p.store_name_nielsen as Name
                        FROM prospective p
                        LEFT JOIN MonthlyRoutePlan_temp mrp ON mrp.CustNo = p.tdlinx
                            AND mrp.DistributorID = '{distributor_id}'
                            AND mrp.AgentID = '{agent_id}'
                            AND mrp.RouteDate = CONVERT(DATE, '{route_date}')
                        LEFT JOIN custvisit cv ON cv.CustID = p.tdlinx
                        WHERE p.barangay_code IN ('{barangay_codes_str}')
                        AND p.latitude IS NOT NULL
                        AND p.longitude IS NOT NULL
                        AND p.latitude != 0
                        AND p.longitude != 0
                        AND mrp.CustNo IS NULL
                        AND cv.CustID IS NULL
                        ORDER BY NEWID()
                        """
                        self.logger.info(f"Searching prospects in barangays: {barangay_codes_str[:100]}...")

                        prospects_df = db.execute_query_df(prospect_query)

                        # Log if barangay search returns insufficient prospects
                        # NOTE: Location-based fallback will be executed later, after all agents are processed
                        if prospects_df is None or prospects_df.empty:
                            self.logger.warning(f"No prospects found in barangay - will attempt location-based search in post-processing")
                        elif len(prospects_df) < needed_prospects:
                            found_count = len(prospects_df)
                            self.logger.warning(f"Barangay search found only {found_count}/{needed_prospects} prospects - will attempt location-based search in post-processing")
                else:
                    # No barangay codes found - will attempt location-based search in post-processing
                    self.logger.warning("No barangay codes found - will attempt location-based search in post-processing")
                    prospects_df = pd.DataFrame()

                if prospects_df is not None and not prospects_df.empty:
                    # Add required columns for prospects
                    prospects_df['RouteDate'] = route_date

                    # Get default values from any customer record
                    if not enriched_df.empty:
                        prospects_df['WD'] = enriched_df['WD'].iloc[0] if 'WD' in enriched_df.columns else 1
                        prospects_df['SalesManTerritory'] = enriched_df['SalesManTerritory'].iloc[0] if 'SalesManTerritory' in enriched_df.columns else ''
                        prospects_df['RouteName'] = enriched_df['RouteName'].iloc[0] if 'RouteName' in enriched_df.columns else ''
                        prospects_df['RouteCode'] = enriched_df['RouteCode'].iloc[0] if 'RouteCode' in enriched_df.columns else ''
                        prospects_df['SalesOfficeID'] = enriched_df['SalesOfficeID'].iloc[0] if 'SalesOfficeID' in enriched_df.columns else ''
                    else:
                        prospects_df['WD'] = 1
                        prospects_df['SalesManTerritory'] = ''
                        prospects_df['RouteName'] = ''
                        prospects_df['RouteCode'] = ''
                        prospects_df['SalesOfficeID'] = ''

                    prospects_df['AgentID'] = agent_id
                    prospects_df['DistributorID'] = distributor_id
                    prospects_df['custype'] = 'prospect'

                    self.logger.info(f"Found {len(prospects_df)} prospects to add")
                else:
                    self.logger.warning("No prospects found")

            # Step 6: Combine all data for TSP optimization
            # Avoid FutureWarning by checking both DataFrames before concatenation
            if customers_with_coords.empty and prospects_df.empty:
                all_data_for_tsp = pd.DataFrame()
            elif customers_with_coords.empty:
                all_data_for_tsp = prospects_df.copy()
            elif prospects_df.empty:
                all_data_for_tsp = customers_with_coords.copy()
            else:
                all_data_for_tsp = pd.concat([customers_with_coords, prospects_df], ignore_index=True)

            # Keep customers without coordinates separate (StopNo will be assigned later)

            return all_data_for_tsp, customers_without_coords

        except Exception as e:
            self.logger.error(f"Error enriching monthly plan data: {e}")
            return pd.DataFrame(), pd.DataFrame()

    def process_single_combination(self, distributor_id, agent_id, date_info):
        """Process a single distributor-agent-date combination"""
        route_date = date_info['RouteDate']
        customer_count = date_info['customer_count']

        try:
            self.logger.info(f"Processing: Distributor {distributor_id} -> Agent {agent_id} -> Date {route_date} ({customer_count} customers)")

            # Step 1: Check scenario conditions
            should_process, scenario_info = self.check_scenario_conditions(distributor_id, agent_id, route_date, customer_count)

            if not should_process:
                self.logger.info(f"Skipping based on scenario conditions: {scenario_info.get('scenario', 'unknown')}")
                return {"status": "skipped", "reason": "scenario_conditions", "scenario": scenario_info}

            # Step 2: Get database connection
            db = DatabaseConnection()
            db.connect()

            try:
                # Step 3: Enrich data with coordinates and prospects
                all_data_for_tsp, customers_without_coords = self.enrich_monthly_plan_data(db, distributor_id, agent_id, route_date)

                # Step 4: Apply TSP optimization (only if there's data with coordinates)
                if not all_data_for_tsp.empty:
                    self.logger.info(f"Applying TSP optimization to {len(all_data_for_tsp)} locations")
                    optimized_data = self.solve_tsp_nearest_neighbor(all_data_for_tsp)
                    self.logger.info(f"TSP optimized {len(optimized_data)} locations")
                else:
                    self.logger.info("No customers with coordinates - skipping TSP optimization")
                    optimized_data = pd.DataFrame()

                # Step 5: Combine optimized data with customers without coordinates
                if not optimized_data.empty and not customers_without_coords.empty:
                    all_final_data = pd.concat([optimized_data, customers_without_coords], ignore_index=True)
                elif not optimized_data.empty:
                    all_final_data = optimized_data
                elif not customers_without_coords.empty:
                    all_final_data = customers_without_coords
                else:
                    self.logger.warning(f"No data found for {distributor_id}/{agent_id} on {route_date}")
                    return {"status": "no_data", "distributor": distributor_id, "agent": agent_id, "date": route_date}

                # Step 6: Update MonthlyRoutePlan_temp with new StopNo values
                updates_count = 0

                # Add custype column if it doesn't exist
                try:
                    db.execute_query("ALTER TABLE MonthlyRoutePlan_temp ADD custype VARCHAR(20)")
                    self.logger.info("Added custype column to MonthlyRoutePlan_temp")
                except:
                    pass  # Column may already exist

                for _, row in all_final_data.iterrows():
                    try:
                        # Determine new stop number with proper NaN handling
                        new_stop_no = None

                        if 'stopno' in row and pd.notna(row['stopno']) and not pd.isna(row['stopno']):
                            # From TSP optimization
                            new_stop_no = row['stopno']
                        elif 'new_stopno' in row and pd.notna(row['new_stopno']) and not pd.isna(row['new_stopno']):
                            # For customers without coordinates
                            new_stop_no = row['new_stopno']
                        else:
                            # Default case for customers without coordinates
                            new_stop_no = 100
                            self.logger.warning(f"No valid stopno found for {row['CustNo']}, defaulting to 100")

                        # Ensure new_stop_no is a valid integer
                        try:
                            if new_stop_no is None or pd.isna(new_stop_no):
                                new_stop_no = 100
                            new_stop_no = int(float(new_stop_no))  # Convert via float first to handle edge cases
                        except (ValueError, TypeError) as e:
                            self.logger.warning(f"Invalid stopno value for {row['CustNo']}: {new_stop_no}, using 100")
                            new_stop_no = 100

                        custype = row.get('custype', 'customer')

                        # Update query (without custype since column may not exist)
                        update_query = """
                        UPDATE MonthlyRoutePlan_temp
                        SET StopNo = ?
                        WHERE DistributorID = ? AND AgentID = ? AND RouteDate = ? AND CustNo = ?
                        """

                        db.execute_query(update_query, (
                            new_stop_no, distributor_id, agent_id, route_date, row['CustNo']
                        ))
                        updates_count += 1

                    except Exception as e:
                        self.logger.error(f"Error updating record for CustNo {row['CustNo']}: {e}")
                        continue

                self.logger.info(f"Successfully updated {updates_count} records in MonthlyRoutePlan_temp")

                return {
                    "status": "success",
                    "distributor": distributor_id,
                    "agent": agent_id,
                    "date": route_date,
                    "records_updated": updates_count,
                    "total_records": len(all_final_data),
                    "scenario": scenario_info
                }

            finally:
                db.close()

        except Exception as e:
            self.logger.error(f"Error processing {distributor_id}/{agent_id} on {route_date}: {e}")
            return {
                "status": "error",
                "distributor": distributor_id,
                "agent": agent_id,
                "date": route_date,
                "error": str(e)
            }

    def fill_gaps_with_nearby_prospects(self, db):
        """
        POST-PROCESSING: Fill gaps with nearby prospects for agents with < 60 customers
        This runs AFTER all agents have been processed to avoid conflicts
        """
        try:
            self.logger.info("\n" + "="*80)
            self.logger.info("POST-PROCESSING: Filling gaps with nearby prospects")
            self.logger.info("="*80)

            # Find all distributor/agent/date combinations with < 60 customers
            gap_query = """
            SELECT
                DistributorID,
                AgentID,
                RouteDate,
                COUNT(DISTINCT CustNo) as customer_count
            FROM MonthlyRoutePlan_temp
            GROUP BY DistributorID, AgentID, RouteDate
            HAVING COUNT(DISTINCT CustNo) < 60
            ORDER BY DistributorID, AgentID, RouteDate
            """
            gaps_df = db.execute_query_df(gap_query)

            if gaps_df is None or gaps_df.empty:
                self.logger.info("No gaps found - all routes have 60+ customers")
                return

            self.logger.info(f"Found {len(gaps_df)} routes with < 60 customers")

            # Process each gap
            for _, gap_row in gaps_df.iterrows():
                distributor_id = gap_row['DistributorID']
                agent_id = gap_row['AgentID']
                route_date = gap_row['RouteDate']
                current_count = gap_row['customer_count']
                needed_prospects = 60 - current_count

                self.logger.info(f"\nProcessing gap: {distributor_id}/{agent_id}/{route_date} - needs {needed_prospects} prospects")

                # Get customers with coordinates for this route
                customer_coords_query = f"""
                SELECT m.CustNo, c.latitude, c.longitude
                FROM MonthlyRoutePlan_temp m
                INNER JOIN customer c ON m.CustNo = c.CustNo
                WHERE m.DistributorID = '{distributor_id}'
                    AND m.AgentID = '{agent_id}'
                    AND m.RouteDate = '{route_date}'
                    AND c.latitude IS NOT NULL
                    AND c.longitude IS NOT NULL
                    AND c.latitude != 0
                    AND c.longitude != 0
                """
                customers_with_coords = db.execute_query_df(customer_coords_query)

                if customers_with_coords is None or customers_with_coords.empty:
                    self.logger.warning(f"No customers with coordinates for location-based search - skipping")
                    continue

                # Search for nearby prospects
                self.logger.info(f"Searching for {needed_prospects} nearby prospects...")
                nearby_prospects = self.find_nearby_prospects_by_location(
                    db, distributor_id, agent_id, route_date,
                    customers_with_coords, needed_prospects, max_distance_km=5.0
                )

                if nearby_prospects is None or nearby_prospects.empty:
                    self.logger.warning(f"No nearby prospects found within 5km")
                    continue

                # Insert the prospects into MonthlyRoutePlan_temp
                self.logger.info(f"Found {len(nearby_prospects)} nearby prospects - inserting into route plan")

                # Get route details from existing records
                route_details_query = f"""
                SELECT TOP 1 WD, SalesManTerritory, RouteName, RouteCode, SalesOfficeID
                FROM MonthlyRoutePlan_temp
                WHERE DistributorID = '{distributor_id}'
                    AND AgentID = '{agent_id}'
                    AND RouteDate = '{route_date}'
                """
                route_details = db.execute_query_df(route_details_query)

                if route_details is not None and not route_details.empty:
                    wd = route_details['WD'].iloc[0] if 'WD' in route_details.columns else 1
                    territory = route_details['SalesManTerritory'].iloc[0] if 'SalesManTerritory' in route_details.columns else ''
                    route_name = route_details['RouteName'].iloc[0] if 'RouteName' in route_details.columns else ''
                    route_code = route_details['RouteCode'].iloc[0] if 'RouteCode' in route_details.columns else ''
                    sales_office = route_details['SalesOfficeID'].iloc[0] if 'SalesOfficeID' in route_details.columns else ''
                else:
                    wd = 1
                    territory = route_name = route_code = sales_office = ''

                # Insert prospects
                connection = db.connection
                cursor = connection.cursor()
                insert_count = 0

                try:
                    insert_query = """
                    INSERT INTO MonthlyRoutePlan_temp
                    (DistributorID, AgentID, RouteDate, CustNo, StopNo, Name, WD, SalesManTerritory, RouteName, RouteCode, SalesOfficeID)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """

                    for _, prospect in nearby_prospects.iterrows():
                        cursor.execute(insert_query, (
                            str(distributor_id)[:50],
                            str(agent_id)[:50],
                            str(route_date),
                            str(prospect['CustNo'])[:50],
                            1,  # Will be re-optimized with TSP
                            str(prospect.get('Name', ''))[:50],  # Truncate to avoid SQL error
                            int(wd) if pd.notna(wd) else 1,
                            str(territory)[:50],
                            str(route_name)[:50],
                            str(route_code)[:50],
                            str(sales_office)[:50]
                        ))
                        insert_count += 1

                    connection.commit()
                    self.logger.info(f"Successfully inserted {insert_count} nearby prospects")

                except Exception as e:
                    self.logger.error(f"Error inserting prospects: {e}")
                    connection.rollback()
                finally:
                    cursor.close()

            self.logger.info("\n" + "="*80)
            self.logger.info("POST-PROCESSING COMPLETED")
            self.logger.info("="*80)

        except Exception as e:
            self.logger.error(f"Error in fill_gaps_with_nearby_prospects: {e}")
            import traceback
            traceback.print_exc()

    def update_custype_with_join(self, db):
        """Update custype in MonthlyRoutePlan_temp using JOIN with source tables"""
        try:
            self.logger.info("Starting custype update using JOIN...")

            # Update custype for customers
            update_customer_query = """
            UPDATE MonthlyRoutePlan_temp
            SET custype = 'customer'
            FROM MonthlyRoutePlan_temp m
            INNER JOIN customer c ON m.CustNo = c.CustNo
            WHERE m.custype IS NULL OR m.custype = ''
            """
            try:
                db.execute_query(update_customer_query)
            except Exception as e:
                # Ignore "No results" error for UPDATE queries
                if "No results" not in str(e):
                    raise
            self.logger.info("Updated custype for customers")

            # Update custype for prospects
            update_prospect_query = """
            UPDATE MonthlyRoutePlan_temp
            SET custype = 'prospect'
            FROM MonthlyRoutePlan_temp m
            INNER JOIN prospective p ON m.CustNo = p.tdlinx
            WHERE m.custype IS NULL OR m.custype = ''
            """
            try:
                db.execute_query(update_prospect_query)
            except Exception as e:
                # Ignore "No results" error for UPDATE queries
                if "No results" not in str(e):
                    raise
            self.logger.info("Updated custype for prospects")

            # Check for any unknown custype
            check_query = """
            SELECT COUNT(*) as unknown_count
            FROM MonthlyRoutePlan_temp
            WHERE custype IS NULL OR custype = '' OR custype = 'unknown'
            """
            result = db.execute_query(check_query)
            if result and result[0][0] > 0:
                self.logger.warning(f"Found {result[0][0]} records with unknown custype")
            else:
                self.logger.info("All records have valid custype")

        except Exception as e:
            self.logger.error(f"Error updating custype with JOIN: {e}")

    def run_hierarchical_pipeline(self, parallel=False):
        """Run the hierarchical monthly route pipeline"""
        self.start_time = time.time()
        self.logger.info("=" * 80)
        self.logger.info("STARTING HIERARCHICAL MONTHLY ROUTE PLAN PIPELINE")
        self.logger.info("Processing Order: DistributorID -> SalesAgent -> Date (chronological)")
        self.logger.info("Target Table: MonthlyRoutePlan_temp")
        self.logger.info("=" * 80)

        db = None
        try:
            # Get database connection
            db = DatabaseConnection()
            db.connect()

            # Build hierarchical structure
            hierarchy = self.get_distributors_hierarchy(db)

            if not hierarchy:
                self.logger.error("No hierarchy found to process")
                return

            # Process each level of the hierarchy
            results = []
            total_combinations = 0
            processed_combinations = 0

            # Count total combinations
            for distributor_id, agents in hierarchy.items():
                for agent_id, dates in agents.items():
                    total_combinations += len(dates)

            self.logger.info(f"Total combinations to process: {total_combinations}")

            # Process hierarchy: DistributorID -> SalesAgent -> Date (with sequential StopNo per agent)
            # PERFORMANCE OPTIMIZATION: Parallel agent processing within each distributor
            for distributor_id, agents in hierarchy.items():
                self.logger.info(f"\n{'='*60}")
                self.logger.info(f"PROCESSING DISTRIBUTORID: {distributor_id}")
                self.logger.info(f"{'='*60}")

                if parallel:
                    # PARALLEL MODE: Process multiple agents concurrently
                    self.logger.info(f"Using PARALLEL processing with {self.max_workers} workers for {len(agents)} agents")

                    with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                        # Submit all agents for this distributor to thread pool
                        future_to_agent = {}
                        for agent_id, dates in agents.items():
                            self.logger.info(f"Submitting Agent {agent_id} to thread pool ({len(dates)} dates)")
                            future = executor.submit(
                                self.process_agent_parallel_wrapper,
                                distributor_id, agent_id, dates
                            )
                            future_to_agent[future] = agent_id

                        # Collect results as agents complete
                        for future in as_completed(future_to_agent):
                            agent_id = future_to_agent[future]
                            try:
                                agent_results = future.result()
                                results.extend(agent_results)

                                # Thread-safe progress update
                                with self._progress_lock:
                                    for result in agent_results:
                                        processed_combinations += 1
                                        if result['status'] == 'success':
                                            self.processed_count += 1
                                        elif result['status'] == 'error':
                                            self.error_count += 1

                                    # Performance optimization: Enhanced progress tracking with ETA
                                    progress_pct = (processed_combinations / total_combinations) * 100
                                    elapsed_time = time.time() - self.start_time
                                    avg_time_per_combo = elapsed_time / processed_combinations if processed_combinations > 0 else 0
                                    remaining_combos = total_combinations - processed_combinations
                                    eta_seconds = avg_time_per_combo * remaining_combos
                                    eta_minutes = eta_seconds / 60

                                    self.logger.info(f"Agent {agent_id} completed | Progress: {processed_combinations}/{total_combinations} ({progress_pct:.1f}%) | "
                                                   f"ETA: {eta_minutes:.1f} min | "
                                                   f"Rate: {1/avg_time_per_combo if avg_time_per_combo > 0 else 0:.2f} combos/sec")

                            except Exception as e:
                                self.logger.error(f"Agent {agent_id} failed with error: {e}")
                                with self._progress_lock:
                                    self.error_count += 1

                else:
                    # SEQUENTIAL MODE: Process agents one at a time (original behavior)
                    self.logger.info(f"Using SEQUENTIAL processing for {len(agents)} agents")

                    for agent_id, dates in agents.items():
                        self.logger.info(f"\n--- Processing SalesAgent: {agent_id} with Sequential StopNo ---")

                        # Process all dates for this agent with sequential numbering
                        agent_results = self.process_agent_with_sequential_stopno(db, distributor_id, agent_id, dates)
                        results.extend(agent_results)

                        # Update progress counters
                        for result in agent_results:
                            processed_combinations += 1
                            if result['status'] == 'success':
                                self.processed_count += 1
                            elif result['status'] == 'error':
                                self.error_count += 1

                        # Performance optimization: Enhanced progress tracking with ETA
                        progress_pct = (processed_combinations / total_combinations) * 100
                        elapsed_time = time.time() - self.start_time
                        avg_time_per_combo = elapsed_time / processed_combinations if processed_combinations > 0 else 0
                        remaining_combos = total_combinations - processed_combinations
                        eta_seconds = avg_time_per_combo * remaining_combos
                        eta_minutes = eta_seconds / 60

                        self.logger.info(f"Progress: {processed_combinations}/{total_combinations} ({progress_pct:.1f}%) | "
                                       f"ETA: {eta_minutes:.1f} min | "
                                       f"Rate: {1/avg_time_per_combo if avg_time_per_combo > 0 else 0:.2f} combos/sec")

            # POST-PROCESSING: Fill gaps with nearby prospects (executed last to avoid conflicts)
            self.logger.info("\nStarting post-processing phase...")
            self.fill_gaps_with_nearby_prospects(db)

            # Update custype using JOIN at the end
            self.logger.info("Updating custype using JOIN...")
            self.update_custype_with_join(db)

            # Final summary
            self.print_final_summary(results, total_combinations)

        except Exception as e:
            self.logger.error(f"Error in hierarchical pipeline: {e}")
            import traceback
            traceback.print_exc()

        finally:
            if db:
                db.close()

    def print_final_summary(self, results, total_combinations):
        """Print final processing summary"""
        end_time = time.time()
        duration = end_time - self.start_time

        success_count = len([r for r in results if r['status'] == 'success'])
        error_count = len([r for r in results if r['status'] == 'error'])
        skipped_count = len([r for r in results if r['status'] == 'skipped'])

        self.logger.info("\n" + "="*80)
        self.logger.info("HIERARCHICAL MONTHLY ROUTE PIPELINE COMPLETED!")
        self.logger.info("="*80)
        self.logger.info(f"Processing Structure: DistributorID -> SalesAgent -> Date (chronological)")
        self.logger.info(f"Total Combinations: {total_combinations}")
        self.logger.info(f"Successful: {success_count}")
        self.logger.info(f"Errors: {error_count}")
        self.logger.info(f"Skipped: {skipped_count}")
        self.logger.info(f"Duration: {duration:.2f} seconds")
        self.logger.info(f"Rate: {total_combinations/duration:.2f} combinations/second")
        self.logger.info("="*80)

def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Hierarchical Monthly Route Plan Pipeline")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for processing")
    parser.add_argument("--max-workers", type=int, default=4, help="Maximum worker threads")
    parser.add_argument("--parallel", action="store_true", help="Enable parallel processing")
    parser.add_argument("--test-mode", action="store_true", help="Run in test mode")
    parser.add_argument("--distributor-id", type=str, default=None, help="Filter by specific distributor ID")
    parser.add_argument("--start-lat", type=float, default=None, help="Starting latitude for TSP optimization")
    parser.add_argument("--start-lon", type=float, default=None, help="Starting longitude for TSP optimization")

    args = parser.parse_args()

    print("=" * 80)
    print("HIERARCHICAL MONTHLY ROUTE PLAN OPTIMIZATION PIPELINE")
    print("=" * 80)
    print(f"Processing Order: DistributorID -> SalesAgent -> Date (chronological)")
    print(f"Target Table: MonthlyRoutePlan_temp")
    print(f"Batch Size: {args.batch_size}")
    print(f"Max Workers: {args.max_workers}")
    print(f"Parallel Processing: {'Enabled' if args.parallel else 'Disabled'}")
    print(f"Test Mode: {'Enabled' if args.test_mode else 'Disabled'}")
    if args.distributor_id:
        print(f"Distributor ID Filter: {args.distributor_id}")
    if args.start_lat and args.start_lon:
        print(f"Starting Location: ({args.start_lat}, {args.start_lon})")
    print("=" * 80)

    try:
        processor = HierarchicalMonthlyRoutePipelineProcessor(
            batch_size=args.batch_size,
            max_workers=args.max_workers,
            start_lat=args.start_lat,
            start_lon=args.start_lon,
            distributor_id=args.distributor_id
        )

        processor.run_hierarchical_pipeline(parallel=args.parallel)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()