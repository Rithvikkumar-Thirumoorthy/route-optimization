#!/usr/bin/env python3
"""
Prospect-Only Route Creation Pipeline
Creates routes using ONLY prospects from the prospective table
No existing customers - pure prospect routes
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from math import radians, cos, sin, asin, sqrt
import argparse

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

class ProspectOnlyRoutePipeline:
    def __init__(self, start_lat=14.663813, start_lon=121.122687, test_mode=False):
        """Initialize prospect-only route pipeline

        Args:
            start_lat: Starting latitude for TSP
            start_lon: Starting longitude for TSP
            test_mode: If True, runs without updating database (dry-run)
        """
        self.start_lat = start_lat
        self.start_lon = start_lon
        self.test_mode = test_mode
        self.start_time = None
        self.all_test_records = []  # Store all records in test mode

        # Setup logging
        self.setup_logging()

    def setup_logging(self):
        """Setup logging configuration"""
        log_filename = f"prospect_only_routes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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

    def get_salesman_territory(self, db, agent_id):
        """Get SalesManTerritory (nodetreevalue) from salesagent table based on AgentID"""
        try:
            query = """
            SELECT nodetreevalue
            FROM salesagent
            WHERE code = ?
            """
            result = db.execute_query_df(query, params=(agent_id,))

            if result is not None and not result.empty:
                territory = result.iloc[0]['nodetreevalue']
                self.logger.info(f"Found SalesManTerritory for {agent_id}: {territory}")
                return str(territory) if territory else ''
            else:
                self.logger.warning(f"No SalesManTerritory found for AgentID: {agent_id}")
                return ''
        except Exception as e:
            self.logger.error(f"Error getting SalesManTerritory: {e}")
            return ''

    def calculate_week_number(self, date_obj):
        """Calculate week number from date (ISO week number)"""
        return date_obj.isocalendar()[1]

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate the great circle distance between two points on Earth (in km)"""
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371
        return c * r

    def solve_tsp_nearest_neighbor(self, locations_df):
        """Solve TSP using nearest neighbor heuristic"""
        try:
            if len(locations_df) <= 1:
                locations_df = locations_df.copy()
                locations_df['stopno'] = 1
                return locations_df

            unvisited = locations_df.copy().reset_index(drop=True)
            route = []

            # Find nearest to starting location
            distances = []
            for _, row in unvisited.iterrows():
                dist = self.haversine_distance(self.start_lat, self.start_lon, row['latitude'], row['longitude'])
                distances.append(dist)

            current_idx = np.argmin(distances)
            self.logger.info(f"Starting from prospect {unvisited.iloc[current_idx]['CustNo']} ({distances[current_idx]:.2f} km from start)")

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

    def get_prospects_by_barangay(self, db, barangay_codes, limit=60):
        """Get prospects from specific barangays - excluding those already in routes or visited"""
        try:
            if not barangay_codes or len(barangay_codes) == 0:
                self.logger.warning("No barangay codes provided")
                return pd.DataFrame()

            barangay_codes_str = "', '".join(str(code) for code in barangay_codes)

            query = f"""
            SELECT TOP {limit}
                p.tdlinx as CustNo,
                p.latitude,
                p.longitude,
                p.barangay_code,
                p.store_name_nielsen as Name,
                p.barangay_code as Barangay
            FROM prospective p
            WHERE p.barangay_code IN ('{barangay_codes_str}')
            AND p.latitude IS NOT NULL
            AND p.longitude IS NOT NULL
            AND p.latitude != 0
            AND p.longitude != 0
            AND NOT EXISTS (
                SELECT 1 FROM MonthlyRoutePlan_temp mrp
                WHERE mrp.CustNo = p.tdlinx
            )
            AND NOT EXISTS (
                SELECT 1 FROM custvisit cv
                WHERE cv.CustID = p.tdlinx
            )
            ORDER BY NEWID()
            """

            prospects_df = db.execute_query_df(query)

            if prospects_df is not None and not prospects_df.empty:
                self.logger.info(f"Found {len(prospects_df)} NEW prospects from barangays: {barangay_codes_str[:100]}...")
                self.logger.info(f"(Excluded prospects already in MonthlyRoutePlan_temp or custvisit)")
                return prospects_df
            else:
                self.logger.warning(f"No new prospects found in barangays: {barangay_codes_str}")
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error getting prospects: {e}")
            return pd.DataFrame()

    def get_nearby_prospects_by_location(self, db, center_lat, center_lon, limit=60, max_distance_km=5.0):
        """Get prospects near a location using geospatial distance - excluding those already in routes or visited"""
        try:
            self.logger.info(f"Searching for nearby prospects around ({center_lat:.6f}, {center_lon:.6f})")
            self.logger.info(f"Search radius: {max_distance_km} km")

            # Get all available prospects with coordinates
            query = """
            SELECT
                p.tdlinx as CustNo,
                p.latitude,
                p.longitude,
                p.barangay_code,
                p.store_name_nielsen as Name,
                p.barangay_code as Barangay
            FROM prospective p
            WHERE p.latitude IS NOT NULL
            AND p.longitude IS NOT NULL
            AND p.latitude != 0
            AND p.longitude != 0
            AND NOT EXISTS (
                SELECT 1 FROM MonthlyRoutePlan_temp mrp
                WHERE mrp.CustNo = p.tdlinx
            )
            AND NOT EXISTS (
                SELECT 1 FROM custvisit cv
                WHERE cv.CustID = p.tdlinx
            )
            """

            all_prospects_df = db.execute_query_df(query)

            if all_prospects_df is None or all_prospects_df.empty:
                self.logger.warning("No unvisited prospects found in database")
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
                self.logger.warning(f"No prospects found within {max_distance_km} km")
                return pd.DataFrame()

            self.logger.info(f"Found {len(nearby_prospects)} prospects within {max_distance_km} km")

            # Sort by distance (closest first) and take only what we need
            nearby_prospects = nearby_prospects.sort_values('distance_km').head(limit)

            # Remove the distance column before returning
            nearby_prospects = nearby_prospects.drop('distance_km', axis=1)

            self.logger.info(f"Selected {len(nearby_prospects)} nearest prospects")

            return nearby_prospects

        except Exception as e:
            self.logger.error(f"Error getting nearby prospects: {e}")
            return pd.DataFrame()

    def create_prospect_route(self, db, distributor_id, agent_id, route_date,
                            barangay_codes=None, target_prospects=60,
                            route_metadata=None):
        """Create a single prospect-only route

        Args:
            db: Database connection
            distributor_id: Distributor ID
            agent_id: Agent ID
            route_date: Route date (YYYY-MM-DD)
            barangay_codes: List of barangay codes to filter prospects (optional)
            target_prospects: Number of prospects to include (default: 60)
            route_metadata: Dict with WD, SalesManTerritory, RouteName, etc. (optional)
        """
        try:
            self.logger.info(f"Creating prospect route for {distributor_id}/{agent_id}/{route_date}")
            self.logger.info(f"Target prospects: {target_prospects}")

            # Get prospects
            if barangay_codes and len(barangay_codes) > 0:
                self.logger.info(f"Filtering by barangays: {barangay_codes}")
                prospects_df = self.get_prospects_by_barangay(db, barangay_codes, target_prospects)

                # FALLBACK: If insufficient prospects from barangay, search nearby
                if prospects_df is None or len(prospects_df) < target_prospects:
                    found_count = 0 if prospects_df is None or prospects_df.empty else len(prospects_df)
                    remaining_needed = target_prospects - found_count

                    if found_count > 0:
                        self.logger.warning(f"Barangay search found only {found_count}/{target_prospects} prospects")
                    else:
                        self.logger.warning(f"No prospects found in specified barangays")

                    # Use start location as center for nearby search
                    self.logger.info(f"Attempting location-based search for {remaining_needed} additional prospects")
                    additional_prospects = self.get_nearby_prospects_by_location(
                        db, self.start_lat, self.start_lon, remaining_needed, max_distance_km=5.0
                    )

                    # Combine barangay prospects with nearby prospects
                    if additional_prospects is not None and not additional_prospects.empty:
                        if prospects_df is None or prospects_df.empty:
                            prospects_df = additional_prospects
                        else:
                            prospects_df = pd.concat([prospects_df, additional_prospects], ignore_index=True)
                        self.logger.info(f"Location-based search added {len(additional_prospects)} prospects")
                        self.logger.info(f"Total prospects after fallback: {len(prospects_df)}")
                    else:
                        self.logger.error("Location-based search found no additional prospects")
            else:
                # No barangay codes provided - use location-based search directly
                self.logger.info(f"No barangay codes provided - using location-based search around starting point")
                prospects_df = self.get_nearby_prospects_by_location(
                    db, self.start_lat, self.start_lon, target_prospects, max_distance_km=5.0
                )

            if prospects_df is None or prospects_df.empty:
                self.logger.error("No prospects found")
                return None

            self.logger.info(f"Retrieved {len(prospects_df)} prospects")

            # Apply TSP optimization
            self.logger.info("Applying TSP optimization...")
            optimized_route = self.solve_tsp_nearest_neighbor(prospects_df)
            self.logger.info(f"TSP optimization completed - {len(optimized_route)} stops")

            # Calculate weekday (1=Monday, 2=Tuesday, ..., 7=Sunday)
            route_date_obj = datetime.strptime(route_date, '%Y-%m-%d')
            weekday = route_date_obj.isoweekday()  # Monday=1, Sunday=7
            week_number = self.calculate_week_number(route_date_obj)

            # Get SalesManTerritory from salesagent table
            salesman_territory = self.get_salesman_territory(db, agent_id)

            # Prepare metadata
            if route_metadata is None:
                route_metadata = {}

            # Always override WD with actual weekday calculated from date
            route_metadata['WD'] = weekday

            # Set SalesManTerritory from database (override any provided value)
            route_metadata['SalesManTerritory'] = salesman_territory

            # Generate RouteCode: SalesManTerritory_WeekNo_WD
            if salesman_territory:
                route_code = f"{salesman_territory}_W{week_number:02d}_D{weekday}"
                self.logger.info(f"Generated RouteCode: {route_code} (Territory: {salesman_territory}, Week: {week_number}, Day: {weekday})")
            else:
                route_code = f"W{week_number:02d}_D{weekday}"
                self.logger.warning(f"No territory found, using simplified RouteCode: {route_code}")
            route_metadata['RouteCode'] = route_code

            # Set defaults for other fields if not provided
            route_metadata.setdefault('RouteName', f'Prospect Route {route_date}')
            route_metadata.setdefault('SalesOfficeID', '')

            # Prepare insert records
            insert_records = []
            for _, prospect in optimized_route.iterrows():
                record = {
                    'DistributorID': str(distributor_id),
                    'AgentID': str(agent_id),
                    'RouteDate': route_date,
                    'CustNo': str(prospect['CustNo']),
                    'StopNo': int(prospect['stopno']),
                    'Name': str(prospect.get('Name', '')),
                    'WD': int(route_metadata.get('WD', 1)),
                    'SalesManTerritory': str(route_metadata.get('SalesManTerritory', '')),
                    'RouteName': str(route_metadata.get('RouteName', '')),
                    'RouteCode': str(route_metadata.get('RouteCode', '')),
                    'SalesOfficeID': str(route_metadata.get('SalesOfficeID', ''))
                }
                insert_records.append(record)

            self.logger.info(f"Prepared {len(insert_records)} records for insertion")

            return {
                'insert_records': insert_records,
                'distributor_id': distributor_id,
                'agent_id': agent_id,
                'route_date': route_date
            }

        except Exception as e:
            self.logger.error(f"Error creating prospect route: {e}", exc_info=True)
            return None

    def insert_into_monthlyrouteplan(self, db, result):
        """Insert prospect routes into MonthlyRoutePlan_temp"""
        try:
            if result is None or not result['insert_records']:
                self.logger.warning("No records to insert")
                return 0

            if self.test_mode:
                # Store records for CSV export
                self.all_test_records.extend(result['insert_records'])

                self.logger.info("=" * 60)
                self.logger.info("TEST MODE - NO DATABASE CHANGES")
                self.logger.info("=" * 60)
                self.logger.info(f"WOULD INSERT: {len(result['insert_records'])} prospect records")
                self.logger.info("\nSample Inserts (first 5):")
                for i, rec in enumerate(result['insert_records'][:5]):
                    self.logger.info(f"  {i+1}. CustNo={rec['CustNo']}, StopNo={rec['StopNo']}, Date={rec['RouteDate']}")
                self.logger.info("=" * 60)
                return len(result['insert_records'])
            else:
                # Real insertion
                connection = db.connection
                cursor = connection.cursor()

                insert_query = """
                INSERT INTO MonthlyRoutePlan_temp
                (DistributorID, AgentID, RouteDate, CustNo, StopNo, Name, WD, SalesManTerritory, RouteName, RouteCode, SalesOfficeID)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                insert_params = [
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
                ]

                cursor.executemany(insert_query, insert_params)
                connection.commit()
                cursor.close()

                self.logger.info(f"Successfully inserted {len(insert_params)} prospect records")
                return len(insert_params)

        except Exception as e:
            self.logger.error(f"Error inserting records: {e}", exc_info=True)
            if not self.test_mode:
                connection.rollback()
            return 0

    def create_multi_day_prospect_routes(self, db, distributor_id, agent_id,
                                        start_date, num_days=5,
                                        barangay_codes=None, prospects_per_day=60,
                                        route_metadata=None, weekdays_only=True):
        """Create multiple days of prospect-only routes

        Args:
            db: Database connection
            distributor_id: Distributor ID
            agent_id: Agent ID
            start_date: Starting date (YYYY-MM-DD)
            num_days: Number of consecutive days to create routes for
            barangay_codes: List of barangay codes (optional)
            prospects_per_day: Number of prospects per day
            route_metadata: Route metadata dict (optional)
            weekdays_only: If True, skip weekends (Saturday/Sunday) (default: True)
        """
        try:
            self.logger.info(f"Creating routes for {num_days} days (weekdays only: {weekdays_only})")
            self.logger.info(f"Starting from: {start_date}")
            self.logger.info(f"Prospects per day: {prospects_per_day}")

            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            total_inserted = 0
            routes_created = 0
            days_skipped = 0

            for day_offset in range(num_days):
                current_date = start_date_obj + timedelta(days=day_offset)
                route_date = current_date.strftime('%Y-%m-%d')
                weekday = current_date.isoweekday()  # 1=Monday, 7=Sunday
                day_name = current_date.strftime('%A')

                # Skip weekends if weekdays_only is True
                if weekdays_only and weekday > 5:  # Saturday=6, Sunday=7
                    self.logger.info(f"\n{'='*60}")
                    self.logger.info(f"Day {day_offset + 1}/{num_days}: {route_date} ({day_name}) - SKIPPED (Weekend)")
                    self.logger.info(f"{'='*60}")
                    days_skipped += 1
                    continue

                routes_created += 1
                self.logger.info(f"\n{'='*60}")
                self.logger.info(f"Day {day_offset + 1}/{num_days}: {route_date} ({day_name}, WD={weekday})")
                self.logger.info(f"{'='*60}")

                # Create route for this day
                result = self.create_prospect_route(
                    db, distributor_id, agent_id, route_date,
                    barangay_codes, prospects_per_day, route_metadata
                )

                # Insert into database
                if result:
                    inserted = self.insert_into_monthlyrouteplan(db, result)
                    total_inserted += inserted
                else:
                    self.logger.error(f"Failed to create route for {route_date}")

            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Multi-day route creation completed")
            self.logger.info(f"Routes created: {routes_created} (Skipped: {days_skipped} weekend days)")
            self.logger.info(f"Total prospects inserted: {total_inserted}")
            self.logger.info(f"{'='*60}")

            return total_inserted

        except Exception as e:
            self.logger.error(f"Error creating multi-day routes: {e}", exc_info=True)
            return 0

    def run_pipeline(self, config):
        """Run the prospect-only route pipeline with given configuration

        Args:
            config: Dict with keys:
                - distributor_id: Required
                - agent_id: Required
                - start_date: Required (YYYY-MM-DD)
                - num_days: Optional (default: 5)
                - barangay_codes: Optional list
                - prospects_per_day: Optional (default: 60)
                - route_metadata: Optional dict
        """
        self.start_time = datetime.now()

        self.logger.info("=" * 80)
        if self.test_mode:
            self.logger.info("TEST MODE - PROSPECT-ONLY ROUTE CREATION (DRY RUN)")
            self.logger.info("NO DATABASE CHANGES WILL BE MADE")
        else:
            self.logger.info("PROSPECT-ONLY ROUTE CREATION PIPELINE")
        self.logger.info("=" * 80)

        db = None
        try:
            db = DatabaseConnection()
            db.connect()

            # Run multi-day route creation
            total_inserted = self.create_multi_day_prospect_routes(
                db,
                config['distributor_id'],
                config['agent_id'],
                config['start_date'],
                config.get('num_days', 5),
                config.get('barangay_codes'),
                config.get('prospects_per_day', 60),
                config.get('route_metadata'),
                config.get('weekdays_only', True)
            )

            # Summary
            duration = (datetime.now() - self.start_time).total_seconds()
            self.logger.info("\n" + "=" * 80)
            if self.test_mode:
                self.logger.info("TEST MODE COMPLETED - NO CHANGES MADE TO DATABASE")

                # Export to CSV
                if self.all_test_records:
                    csv_filename = f"prospect_routes_{config['agent_id']}_{config['start_date']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    csv_path = os.path.join(os.path.dirname(__file__), 'output', csv_filename)
                    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

                    df = pd.DataFrame(self.all_test_records)
                    df.to_csv(csv_path, index=False)

                    self.logger.info(f"CSV EXPORTED: {csv_path}")
                    self.logger.info(f"Total records in CSV: {len(self.all_test_records)}")
                    print(f"\n>>> CSV file saved: {csv_path}")
            else:
                self.logger.info("PIPELINE COMPLETED!")
            self.logger.info(f"Total prospects processed: {total_inserted}")
            self.logger.info(f"Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
            self.logger.info("=" * 80)

        except Exception as e:
            self.logger.error(f"Pipeline error: {e}", exc_info=True)

        finally:
            if db:
                db.close()


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Prospect-Only Route Creation Pipeline")
    parser.add_argument("--test", "--dry-run", action="store_true",
                        help="Test mode - run without making database changes")
    parser.add_argument("--distributor", "-d", type=str, required=True,
                        help="DistributorID (e.g., 11814)")
    parser.add_argument("--agent", "-a", type=str, required=True,
                        help="AgentID (e.g., SK-SAT6)")
    parser.add_argument("--start-date", type=str, required=True,
                        help="Start date (YYYY-MM-DD)")
    parser.add_argument("--num-days", type=int, default=5,
                        help="Number of consecutive days (default: 5)")
    parser.add_argument("--prospects-per-day", type=int, default=60,
                        help="Number of prospects per day (default: 60)")
    parser.add_argument("--barangays", type=str, default=None,
                        help="Comma-separated barangay codes (e.g., '137403027,137403028')")
    parser.add_argument("--start-lat", type=float, default=14.663813,
                        help="Starting latitude for TSP (default: 14.663813)")
    parser.add_argument("--start-lon", type=float, default=121.122687,
                        help="Starting longitude for TSP (default: 121.122687)")
    parser.add_argument("--weekdays-only", action="store_true", default=True,
                        help="Create routes only for weekdays (Mon-Fri), skip weekends (default: True)")
    parser.add_argument("--include-weekends", action="store_true",
                        help="Include weekends (Sat-Sun) in route creation")

    args = parser.parse_args()

    print("=" * 80)
    if args.test:
        print("TEST MODE - PROSPECT-ONLY ROUTE CREATION")
        print("DRY RUN - NO DATABASE CHANGES WILL BE MADE")
    else:
        print("PROSPECT-ONLY ROUTE CREATION PIPELINE")
        print("WARNING: THIS WILL MODIFY THE DATABASE")
    print("=" * 80)
    print(f"Distributor: {args.distributor}")
    print(f"Agent: {args.agent}")
    print(f"Start Date: {args.start_date}")
    print(f"Number of Days: {args.num_days}")
    print(f"Prospects per Day: {args.prospects_per_day}")
    if args.barangays:
        print(f"Barangays: {args.barangays}")
    else:
        print(f"Barangays: ALL (random selection)")
    print(f"Starting Location: ({args.start_lat}, {args.start_lon})")
    print("=" * 80)

    if not args.test:
        confirm = input("\nContinue with database modifications? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled by user")
            return

    try:
        # Parse barangay codes if provided
        barangay_codes = None
        if args.barangays:
            barangay_codes = [b.strip() for b in args.barangays.split(',')]

        # Determine if weekdays only (default True unless --include-weekends is specified)
        weekdays_only = not args.include_weekends

        # Create configuration
        config = {
            'distributor_id': args.distributor,
            'agent_id': args.agent,
            'start_date': args.start_date,
            'num_days': args.num_days,
            'barangay_codes': barangay_codes,
            'prospects_per_day': args.prospects_per_day,
            'weekdays_only': weekdays_only,
            'route_metadata': {
                # WD, SalesManTerritory, and RouteCode are calculated automatically
                # WD: based on route date
                # SalesManTerritory: fetched from salesagent.nodetreevalue
                # RouteCode: generated as SalesManTerritory_WeekNo_WD
                'RouteName': f'Prospect Route {args.agent}',
                'SalesOfficeID': ''
            }
        }

        # Run pipeline
        pipeline = ProspectOnlyRoutePipeline(
            start_lat=args.start_lat,
            start_lon=args.start_lon,
            test_mode=args.test
        )
        pipeline.run_pipeline(config)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
