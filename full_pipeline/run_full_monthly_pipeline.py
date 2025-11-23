#!/usr/bin/env python3
"""
Complete Monthly Route Pipeline
Process entire MonthlyRoutePlan_temp table:
1. Check for unvisited prospects from previous month
2. Process hierarchy: DistributorID -> SalesAgent -> RouteDate -> CustNo
3. Apply route optimization
4. Populate database
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from math import radians, cos, sin, asin, sqrt
import calendar

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

class FullMonthlyRoutePipeline:
    def __init__(self, start_lat=14.663813, start_lon=121.122687, test_mode=False, distributor_filter=None):
        """Initialize full monthly route pipeline processor

        Args:
            start_lat: Starting latitude for TSP
            start_lon: Starting longitude for TSP
            test_mode: If True, runs without updating database (dry-run)
            distributor_filter: Optional distributor ID to process (e.g., '11814')
        """
        self.start_lat = start_lat
        self.start_lon = start_lon
        self.test_mode = test_mode
        self.distributor_filter = distributor_filter
        self.processed_count = 0
        self.error_count = 0
        self.start_time = None

        # Setup logging
        self.setup_logging()

    def setup_logging(self):
        """Setup logging configuration"""
        log_filename = f"full_monthly_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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

    def get_previous_month_date(self, current_date):
        """Get date from previous month"""
        current_dt = datetime.strptime(str(current_date), '%Y-%m-%d %H:%M:%S') if isinstance(current_date, pd.Timestamp) else datetime.strptime(current_date, '%Y-%m-%d')

        # Get first day of current month
        first_day = current_dt.replace(day=1)

        # Subtract one day to get last day of previous month
        last_day_prev = first_day - timedelta(days=1)

        # Get same day in previous month
        prev_month = last_day_prev.replace(day=current_dt.day if current_dt.day <= last_day_prev.day else last_day_prev.day)

        return prev_month.strftime('%Y-%m-%d')

    def get_unvisited_prospects_from_previous_month(self, db, distributor_id, agent_id, current_date):
        """
        Get prospects from previous month that were scheduled but not visited
        Checks routeplan vs custvisit table
        """
        try:
            prev_month_date = self.get_previous_month_date(current_date)
            self.logger.info(f"Checking for unvisited prospects from previous month ({prev_month_date})")

            # Query to find prospects in MonthlyRoutePlan_temp (previous month) but NOT visited
            # Need to check if prospect exists in MonthlyRoutePlan_temp AND is a prospect
            query = f"""
            SELECT DISTINCT
                m.CustNo as custno,
                c.latitude,
                c.longitude,
                c.barangay_code,
                c.store_name_nielsen as Name
            FROM MonthlyRoutePlan_temp m
            INNER JOIN prospective c ON m.CustNo = c.tdlinx
            LEFT JOIN custvisit cv ON m.CustNo = cv.CustID
                AND m.AgentID = cv.AgentID
                AND CONVERT(DATE, m.RouteDate) = CONVERT(DATE, cv.TransDate)
            WHERE m.AgentID = '{agent_id}'
                AND m.DistributorID = '{distributor_id}'
                AND MONTH(m.RouteDate) = MONTH('{prev_month_date}')
                AND YEAR(m.RouteDate) = YEAR('{prev_month_date}')
                AND cv.CustID IS NULL
                AND c.latitude IS NOT NULL
                AND c.longitude IS NOT NULL
                AND c.latitude != 0
                AND c.longitude != 0
            """

            unvisited_df = db.execute_query_df(query)

            if unvisited_df is not None and not unvisited_df.empty:
                self.logger.info(f"Found {len(unvisited_df)} unvisited prospects from previous month")
                return unvisited_df
            else:
                self.logger.info("No unvisited prospects from previous month")
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error getting unvisited prospects: {e}")
            return pd.DataFrame()

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate the great circle distance between two points on Earth (in km)"""
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371
        return c * r

    def solve_tsp_nearest_neighbor(self, locations_df, start_lat=None, start_lon=None):
        """Solve TSP using nearest neighbor heuristic"""
        try:
            if len(locations_df) <= 1:
                locations_df = locations_df.copy()
                locations_df['stopno'] = 1
                return locations_df

            unvisited = locations_df.copy().reset_index(drop=True)
            route = []

            # Find nearest to starting location
            if start_lat is not None and start_lon is not None:
                distances = []
                for _, row in unvisited.iterrows():
                    dist = self.haversine_distance(start_lat, start_lon, row['latitude'], row['longitude'])
                    distances.append(dist)
                current_idx = np.argmin(distances)
            else:
                current_idx = 0

            current_location = unvisited.iloc[current_idx]
            route.append(current_location)
            unvisited = unvisited.drop(current_idx).reset_index(drop=True)

            # Build route using nearest neighbor
            while not unvisited.empty:
                current_lat = current_location['latitude']
                current_lon = current_location['longitude']

                distances = []
                for _, row in unvisited.iterrows():
                    dist = self.haversine_distance(current_lat, current_lon, row['latitude'], row['longitude'])
                    distances.append(dist)

                nearest_idx = np.argmin(distances)
                current_location = unvisited.iloc[nearest_idx]
                route.append(current_location)
                unvisited = unvisited.drop(unvisited.index[nearest_idx]).reset_index(drop=True)

            result_df = pd.DataFrame(route)
            result_df['stopno'] = range(1, len(result_df) + 1)

            return result_df

        except Exception as e:
            self.logger.error(f"Error in TSP optimization: {e}")
            return locations_df

    def get_full_hierarchy(self, db):
        """Get complete hierarchy: DistributorID -> SalesAgent -> RouteDate"""
        try:
            if self.distributor_filter:
                self.logger.info(f"Building hierarchy for DistributorID: {self.distributor_filter}")
            else:
                self.logger.info("Building full hierarchy from MonthlyRoutePlan_temp...")

            # Get all distributors (or filtered distributor)
            if self.distributor_filter:
                distributor_query = f"""
                SELECT DISTINCT DistributorID
                FROM MonthlyRoutePlan_temp
                WHERE DistributorID = '{self.distributor_filter}'
                ORDER BY DistributorID
                """
            else:
                distributor_query = """
                SELECT DISTINCT DistributorID
                FROM MonthlyRoutePlan_temp
                WHERE DistributorID IS NOT NULL
                ORDER BY DistributorID
                """
            distributors_df = db.execute_query_df(distributor_query)

            if distributors_df is None or distributors_df.empty:
                self.logger.error("No distributors found")
                return {}

            hierarchy = {}

            for _, dist_row in distributors_df.iterrows():
                distributor_id = dist_row['DistributorID']
                self.logger.info(f"Processing DistributorID: {distributor_id}")

                # Get all agents for this distributor
                agents_query = f"""
                SELECT DISTINCT AgentID
                FROM MonthlyRoutePlan_temp
                WHERE DistributorID = '{distributor_id}'
                    AND AgentID IS NOT NULL
                ORDER BY AgentID
                """
                agents_df = db.execute_query_df(agents_query)

                if agents_df is None or agents_df.empty:
                    continue

                hierarchy[distributor_id] = {}

                for _, agent_row in agents_df.iterrows():
                    agent_id = agent_row['AgentID']

                    # Get all dates for this agent (chronological)
                    dates_query = f"""
                    SELECT
                        RouteDate,
                        COUNT(DISTINCT CustNo) as customer_count
                    FROM MonthlyRoutePlan_temp
                    WHERE DistributorID = '{distributor_id}'
                        AND AgentID = '{agent_id}'
                        AND RouteDate IS NOT NULL
                        AND CustNo IS NOT NULL
                    GROUP BY RouteDate
                    HAVING COUNT(DISTINCT CustNo) >= 5
                    ORDER BY RouteDate ASC
                    """
                    dates_df = db.execute_query_df(dates_query)

                    if dates_df is not None and not dates_df.empty:
                        hierarchy[distributor_id][agent_id] = dates_df.to_dict('records')
                        self.logger.info(f"  Agent {agent_id}: {len(dates_df)} dates")

            total_combinations = sum(
                len(dates) for dist in hierarchy.values()
                for dates in dist.values()
            )
            self.logger.info(f"Total combinations to process: {total_combinations}")

            return hierarchy

        except Exception as e:
            self.logger.error(f"Error building hierarchy: {e}")
            return {}

    def process_route_date(self, db, distributor_id, agent_id, route_date, customer_count):
        """Process a single route date with optimization"""
        try:
            self.logger.info(f"Processing: {distributor_id}/{agent_id}/{route_date} ({customer_count} customers)")

            # Step 1: Get existing customers from MonthlyRoutePlan_temp
            monthly_plan_query = f"""
            SELECT
                CustNo, RouteDate, Name, WD, SalesManTerritory,
                AgentID, RouteName, DistributorID, RouteCode, SalesOfficeID
            FROM MonthlyRoutePlan_temp
            WHERE DistributorID = '{distributor_id}'
                AND AgentID = '{agent_id}'
                AND RouteDate = '{route_date}'
                AND CustNo IS NOT NULL
            """
            monthly_plan_df = db.execute_query_df(monthly_plan_query)

            if monthly_plan_df is None or monthly_plan_df.empty:
                self.logger.warning("No customers found")
                return None

            # Step 2: Get coordinates from customer table
            customer_nos = "', '".join(monthly_plan_df['CustNo'].astype(str))
            customer_query = f"""
            SELECT CustNo, latitude, longitude, address3 as barangay_code
            FROM customer
            WHERE CustNo IN ('{customer_nos}')
            AND latitude IS NOT NULL AND longitude IS NOT NULL
            AND latitude != 0.0 AND longitude != 0.0
            """
            customer_coords_df = db.execute_query_df(customer_query)

            # Merge coordinates
            if customer_coords_df is not None and not customer_coords_df.empty:
                enriched_df = monthly_plan_df.merge(customer_coords_df, on='CustNo', how='left')
            else:
                enriched_df = monthly_plan_df.copy()
                enriched_df['latitude'] = None
                enriched_df['longitude'] = None
                enriched_df['barangay_code'] = None

            enriched_df['custype'] = 'customer'

            # Separate customers with/without coordinates
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

            self.logger.info(f"  Customers with coords: {len(customers_with_coords)}, without: {len(customers_without_coords)}")

            # Step 3: Get unvisited prospects from previous month
            unvisited_prospects = self.get_unvisited_prospects_from_previous_month(
                db, distributor_id, agent_id, route_date
            )

            # Add required columns to unvisited prospects
            if not unvisited_prospects.empty:
                unvisited_prospects['RouteDate'] = route_date
                unvisited_prospects['custype'] = 'prospect_reused'
                # Copy metadata from existing customers
                if not enriched_df.empty:
                    unvisited_prospects['WD'] = enriched_df['WD'].iloc[0]
                    unvisited_prospects['SalesManTerritory'] = enriched_df['SalesManTerritory'].iloc[0]
                    unvisited_prospects['RouteName'] = enriched_df['RouteName'].iloc[0]
                    unvisited_prospects['RouteCode'] = enriched_df['RouteCode'].iloc[0]
                    unvisited_prospects['SalesOfficeID'] = enriched_df['SalesOfficeID'].iloc[0]
                    unvisited_prospects['AgentID'] = agent_id
                    unvisited_prospects['DistributorID'] = distributor_id

            # Step 4: Add new prospects if still needed
            total_count = len(enriched_df) + len(unvisited_prospects)
            new_prospects = pd.DataFrame()

            if total_count < 60:
                needed_prospects = 60 - total_count
                self.logger.info(f"  Need {needed_prospects} more prospects (have {len(unvisited_prospects)} reused)")

                # Get barangay codes for matching
                barangay_codes = []
                if not customers_with_coords.empty:
                    barangay_codes = customers_with_coords['barangay_code'].dropna().unique()
                elif not enriched_df.empty:
                    # Get address3 from customer table
                    address3_query = f"""
                    SELECT DISTINCT address3
                    FROM customer
                    WHERE CustNo IN ('{customer_nos}')
                    AND address3 IS NOT NULL AND address3 != ''
                    """
                    address3_df = db.execute_query_df(address3_query)
                    if address3_df is not None and not address3_df.empty:
                        barangay_codes = address3_df['address3'].dropna().unique()

                # Query prospects
                if len(barangay_codes) > 0:
                    barangay_codes_str = "', '".join(str(code) for code in barangay_codes)
                    prospect_query = f"""
                    SELECT TOP {needed_prospects}
                        CustNo, Latitude as latitude, Longitude as longitude,
                        barangay_code, OutletName as Name
                    FROM prospective
                    WHERE barangay_code IN ('{barangay_codes_str}')
                    AND Latitude IS NOT NULL AND Longitude IS NOT NULL
                    AND Latitude != 0 AND Longitude != 0
                    ORDER BY NEWID()
                    """
                    new_prospects = db.execute_query_df(prospect_query)

                # Add metadata to new prospects
                if new_prospects is not None and not new_prospects.empty:
                    new_prospects['RouteDate'] = route_date
                    new_prospects['custype'] = 'prospect'
                    if not enriched_df.empty:
                        new_prospects['WD'] = enriched_df['WD'].iloc[0]
                        new_prospects['SalesManTerritory'] = enriched_df['SalesManTerritory'].iloc[0]
                        new_prospects['RouteName'] = enriched_df['RouteName'].iloc[0]
                        new_prospects['RouteCode'] = enriched_df['RouteCode'].iloc[0]
                        new_prospects['SalesOfficeID'] = enriched_df['SalesOfficeID'].iloc[0]
                    new_prospects['AgentID'] = agent_id
                    new_prospects['DistributorID'] = distributor_id
                    self.logger.info(f"  Added {len(new_prospects)} new prospects")

            # Step 5: Combine all data for TSP
            all_for_tsp = pd.concat([
                customers_with_coords,
                unvisited_prospects,
                new_prospects
            ], ignore_index=True)

            # Step 6: Apply TSP optimization
            if not all_for_tsp.empty:
                self.logger.info(f"  Applying TSP to {len(all_for_tsp)} locations")
                optimized = self.solve_tsp_nearest_neighbor(all_for_tsp, self.start_lat, self.start_lon)
            else:
                optimized = pd.DataFrame()

            # Step 7: Prepare update/insert records
            update_records = []
            insert_records = []

            # Process optimized records
            for _, row in optimized.iterrows():
                if row['custype'] == 'customer':
                    # UPDATE existing customer
                    update_records.append({
                        'CustNo': row['CustNo'],
                        'StopNo': int(row['stopno']),
                        'RouteDate': route_date
                    })
                else:
                    # INSERT prospect (both reused and new)
                    insert_records.append({
                        'DistributorID': distributor_id,
                        'AgentID': agent_id,
                        'RouteDate': route_date,
                        'CustNo': row['CustNo'],
                        'StopNo': int(row['stopno']),
                        'Name': str(row.get('Name', '')),
                        'WD': int(row.get('WD', 1)) if pd.notna(row.get('WD')) else 1,
                        'SalesManTerritory': str(row.get('SalesManTerritory', '')),
                        'RouteName': str(row.get('RouteName', '')),
                        'RouteCode': str(row.get('RouteCode', '')),
                        'SalesOfficeID': str(row.get('SalesOfficeID', ''))
                    })

            # Process customers without coordinates (StopNo = 100)
            for _, row in customers_without_coords.iterrows():
                update_records.append({
                    'CustNo': row['CustNo'],
                    'StopNo': 100,
                    'RouteDate': route_date
                })

            return {
                'update_records': update_records,
                'insert_records': insert_records,
                'distributor_id': distributor_id,
                'agent_id': agent_id,
                'route_date': route_date
            }

        except Exception as e:
            self.logger.error(f"Error processing route: {e}", exc_info=True)
            return None

    def execute_database_operations(self, db, results_batch):
        """Execute batch updates and inserts (or simulate in test mode)"""
        try:
            total_updates = 0
            total_inserts = 0

            # Collect all updates and inserts
            all_updates = []
            all_inserts = []

            for result in results_batch:
                if result is None:
                    continue

                all_updates.extend([
                    (
                        rec['StopNo'],
                        result['distributor_id'],
                        result['agent_id'],
                        rec['RouteDate'],
                        rec['CustNo']
                    )
                    for rec in result['update_records']
                ])

                all_inserts.extend([
                    (
                        rec['DistributorID'],
                        rec['AgentID'],
                        rec['RouteDate'],
                        rec['CustNo'],
                        rec['StopNo'],
                        rec['Name'],
                        rec['WD'],
                        rec['SalesManTerritory'],
                        rec['RouteName'],
                        rec['RouteCode'],
                        rec['SalesOfficeID']
                    )
                    for rec in result['insert_records']
                ])

            total_updates = len(all_updates)
            total_inserts = len(all_inserts)

            if self.test_mode:
                # TEST MODE - Just log what would happen
                self.logger.info("=" * 60)
                self.logger.info("TEST MODE - NO DATABASE CHANGES")
                self.logger.info("=" * 60)
                self.logger.info(f"WOULD UPDATE: {total_updates} records")
                self.logger.info(f"WOULD INSERT: {total_inserts} records")

                # Show sample of what would be updated
                if all_updates and len(all_updates) > 0:
                    self.logger.info("\nSample Updates (first 5):")
                    for i, update in enumerate(all_updates[:5]):
                        self.logger.info(f"  {i+1}. CustNo={update[4]}, StopNo={update[0]}, Date={update[3]}")

                # Show sample of what would be inserted
                if all_inserts and len(all_inserts) > 0:
                    self.logger.info("\nSample Inserts (first 5):")
                    for i, insert in enumerate(all_inserts[:5]):
                        self.logger.info(f"  {i+1}. CustNo={insert[3]}, StopNo={insert[4]}, Type=Prospect, Date={insert[2]}")

                self.logger.info("=" * 60)

            else:
                # REAL MODE - Execute database operations
                connection = db.connection
                cursor = connection.cursor()

                # Execute batch update
                if all_updates:
                    update_query = """
                    UPDATE MonthlyRoutePlan_temp
                    SET StopNo = ?
                    WHERE DistributorID = ? AND AgentID = ? AND RouteDate = ? AND CustNo = ?
                    """
                    cursor.executemany(update_query, all_updates)
                    self.logger.info(f"Updated {total_updates} records")

                # Execute batch insert
                if all_inserts:
                    insert_query = """
                    INSERT INTO MonthlyRoutePlan_temp
                    (DistributorID, AgentID, RouteDate, CustNo, StopNo, Name, WD, SalesManTerritory, RouteName, RouteCode, SalesOfficeID)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    cursor.executemany(insert_query, all_inserts)
                    self.logger.info(f"Inserted {total_inserts} records")

                connection.commit()
                cursor.close()

            return total_updates, total_inserts

        except Exception as e:
            self.logger.error(f"Database operation error: {e}", exc_info=True)
            if not self.test_mode:
                connection.rollback()
            raise

    def run_full_pipeline(self):
        """Run complete pipeline for entire table"""
        self.start_time = datetime.now()
        self.logger.info("=" * 80)
        if self.test_mode:
            self.logger.info("TEST MODE - FULL MONTHLY ROUTE PIPELINE (DRY RUN)")
            self.logger.info("NO DATABASE CHANGES WILL BE MADE")
        else:
            self.logger.info("STARTING FULL MONTHLY ROUTE PIPELINE")
        self.logger.info("Hierarchy: DistributorID -> SalesAgent -> RouteDate -> CustNo")
        self.logger.info("=" * 80)

        db = None
        try:
            db = DatabaseConnection()
            db.connect()

            # Build hierarchy
            hierarchy = self.get_full_hierarchy(db)

            if not hierarchy:
                self.logger.error("No hierarchy found")
                return

            # Process each level
            results_batch = []
            batch_size = 10  # Process 10 routes then commit

            for distributor_id, agents in hierarchy.items():
                self.logger.info(f"\n{'='*60}")
                self.logger.info(f"DISTRIBUTOR: {distributor_id}")
                self.logger.info(f"{'='*60}")

                for agent_id, dates in agents.items():
                    self.logger.info(f"\nAgent: {agent_id} ({len(dates)} dates)")

                    for date_info in dates:
                        route_date = date_info['RouteDate']
                        customer_count = date_info['customer_count']

                        # Process route
                        result = self.process_route_date(
                            db, distributor_id, agent_id, route_date, customer_count
                        )

                        if result:
                            results_batch.append(result)

                        # Batch commit
                        if len(results_batch) >= batch_size:
                            updates, inserts = self.execute_database_operations(db, results_batch)
                            self.logger.info(f"Batch committed: {updates} updates, {inserts} inserts")
                            results_batch = []

            # Final commit
            if results_batch:
                updates, inserts = self.execute_database_operations(db, results_batch)
                self.logger.info(f"Final batch: {updates} updates, {inserts} inserts")

            # Summary
            duration = (datetime.now() - self.start_time).total_seconds()
            self.logger.info("\n" + "="*80)
            if self.test_mode:
                self.logger.info("TEST MODE COMPLETED - NO CHANGES MADE TO DATABASE")
            else:
                self.logger.info("PIPELINE COMPLETED!")
            self.logger.info(f"Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
            self.logger.info("="*80)

        except Exception as e:
            self.logger.error(f"Pipeline error: {e}", exc_info=True)

        finally:
            if db:
                db.close()

def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Full Monthly Route Optimization Pipeline")
    parser.add_argument("--test", "--dry-run", action="store_true",
                        help="Test mode - run without making database changes")
    parser.add_argument("--distributor", "-d", type=str, default=None,
                        help="Optional: Process only this DistributorID (e.g., 11814)")
    parser.add_argument("--start-lat", type=float, default=14.663813,
                        help="Starting latitude for TSP (default: 14.663813)")
    parser.add_argument("--start-lon", type=float, default=121.122687,
                        help="Starting longitude for TSP (default: 121.122687)")

    args = parser.parse_args()

    print("=" * 80)
    if args.test:
        print("TEST MODE - FULL MONTHLY ROUTE OPTIMIZATION PIPELINE")
        print("DRY RUN - NO DATABASE CHANGES WILL BE MADE")
    else:
        print("FULL MONTHLY ROUTE OPTIMIZATION PIPELINE")
        print("WARNING: THIS WILL MODIFY THE DATABASE")

    if args.distributor:
        print(f"Processing: DistributorID {args.distributor} -> ALL Agents -> ALL Dates")
    else:
        print("Processing: ALL Distributors -> ALL Agents -> ALL Dates")
    print(f"Starting Location: ({args.start_lat}, {args.start_lon})")
    print("=" * 80)

    if not args.test:
        confirm = input("\nContinue with database modifications? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled by user")
            return

    try:
        pipeline = FullMonthlyRoutePipeline(
            start_lat=args.start_lat,
            start_lon=args.start_lon,
            test_mode=args.test,
            distributor_filter=args.distributor
        )
        pipeline.run_full_pipeline()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
