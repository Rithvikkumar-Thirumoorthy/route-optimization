#!/usr/bin/env python3
"""
Monthly Route Plan Pipeline - Modified Flow
Process MonthlyRoutePlan_temp with customer and prospective data integration
Target: Update MonthlyRoutePlan_temp with optimized TSP routing
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import time
from math import radians, cos, sin, asin, sqrt

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.database import DatabaseConnection
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running from the project root directory")
    sys.exit(1)

class MonthlyRoutePipelineProcessor:
    def __init__(self, batch_size=50, max_workers=4):
        """Initialize monthly route pipeline processor"""
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.processed_count = 0
        self.error_count = 0
        self.start_time = None

        # Setup logging
        self.setup_logging()

    def setup_logging(self):
        """Setup logging configuration"""
        log_filename = f"monthly_route_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_path = os.path.join(os.path.dirname(__file__), 'logs', log_filename)

        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate the great circle distance between two points on Earth (straight line distance)"""
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Radius of earth in kilometers
        return c * r

    def solve_tsp_nearest_neighbor(self, locations_df):
        """Solve TSP using nearest neighbor heuristic based on straight line distance"""
        if len(locations_df) <= 1:
            locations_df['new_stopno'] = 1
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
            current_lat = current_location['latitude']
            current_lon = current_location['longitude']

            # Find nearest unvisited location
            distances = []
            for _, row in unvisited.iterrows():
                dist = self.haversine_distance(current_lat, current_lon, row['latitude'], row['longitude'])
                distances.append(dist)

            nearest_idx = np.argmin(distances)
            current_location = unvisited.iloc[nearest_idx]
            route.append(current_location)
            unvisited = unvisited.drop(unvisited.index[nearest_idx]).reset_index(drop=True)

        # Create result dataframe with new stop numbers
        result_df = pd.DataFrame(route)
        result_df['new_stopno'] = range(1, len(result_df) + 1)

        return result_df

    def get_all_agents_from_monthly_plan(self, db):
        """Get all unique agent-date combinations from MonthlyRoutePlan_temp"""
        try:
            query = """
            SELECT
                AgentID as agent_id,
                RouteDate as route_date,
                COUNT(DISTINCT CustNo) as customer_count,
                COUNT(*) as total_records
            FROM MonthlyRoutePlan_temp
            WHERE AgentID IS NOT NULL
                AND RouteDate IS NOT NULL
                AND CustNo IS NOT NULL
            GROUP BY AgentID, RouteDate
            ORDER BY AgentID, RouteDate DESC
            """

            result_df = db.execute_query_df(query)

            if result_df is not None and not result_df.empty:
                self.logger.info(f"Found {len(result_df)} agent-date combinations to process from MonthlyRoutePlan_temp")
                return result_df
            else:
                self.logger.error("No agent data found in MonthlyRoutePlan_temp table")
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error fetching agent data: {e}")
            return pd.DataFrame()

    def enrich_monthly_plan_data(self, db, agent_id, route_date):
        """
        Enrich MonthlyRoutePlan_temp data with coordinates and addresses from customer table
        Steps:
        1. Get partial data from MonthlyRoutePlan_temp
        2. Get coordinates and barangay_code from customer table
        3. Add custype column (customer/prospect)
        4. Match for prospect data if needed
        """
        try:
            self.logger.info(f"Enriching data for Agent: {agent_id}, Date: {route_date}")

            # Step 1: Get data from MonthlyRoutePlan_temp
            monthly_plan_query = f"""
            SELECT
                CustNo, RouteDate, Name, WD, SalesManTerritory,
                AgentID, RouteName, DistributorID, RouteCode,
                SalesOfficeID, StopNo
            FROM MonthlyRoutePlan_temp
            WHERE AgentID = '{agent_id}' AND RouteDate = '{route_date}'
            AND CustNo IS NOT NULL
            """

            monthly_plan_df = db.execute_query_df(monthly_plan_query)

            if monthly_plan_df is None or monthly_plan_df.empty:
                self.logger.warning(f"No data found in MonthlyRoutePlan_temp for {agent_id} on {route_date}")
                return pd.DataFrame()

            self.logger.info(f"Found {len(monthly_plan_df)} records in MonthlyRoutePlan_temp")

            # Step 2: Get coordinates and barangay_code from customer table
            customer_nos = "', '".join(monthly_plan_df['CustNo'].astype(str))
            customer_query = f"""
            SELECT
                CustNo, latitude, longitude, address3 as barangay_code
            FROM customer
            WHERE CustNo IN ('{customer_nos}')
            AND latitude IS NOT NULL
            AND longitude IS NOT NULL
            AND latitude != 0
            AND longitude != 0
            """

            customer_coords_df = db.execute_query_df(customer_query)

            if customer_coords_df is not None and not customer_coords_df.empty:
                self.logger.info(f"Found coordinates for {len(customer_coords_df)} customers")
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
            self.logger.info("Detecting custype from source tables...")
            customer_nos = "', '".join(monthly_plan_df['CustNo'].astype(str))

            # Check which CustNos exist in customer table
            customer_check_query = f"""
            SELECT DISTINCT CustNo
            FROM customer
            WHERE CustNo IN ('{customer_nos}')
            """
            customer_custnos = db.execute_query_df(customer_check_query)
            customer_set = set(customer_custnos['CustNo'].tolist()) if customer_custnos is not None and not customer_custnos.empty else set()

            # Check which CustNos exist in prospective table
            prospective_check_query = f"""
            SELECT DISTINCT tdlinx
            FROM prospective
            WHERE tdlinx IN ('{customer_nos}')
            """
            prospective_custnos = db.execute_query_df(prospective_check_query)
            prospective_set = set(prospective_custnos['tdlinx'].tolist()) if prospective_custnos is not None and not prospective_custnos.empty else set()

            # Assign custype based on source table
            def get_custype(custno):
                if custno in customer_set:
                    return 'customer'
                elif custno in prospective_set:
                    return 'prospect'
                else:
                    return 'unknown'

            enriched_df['custype'] = enriched_df['CustNo'].apply(get_custype)

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
            total_customers = len(enriched_df)
            prospects_df = pd.DataFrame()

            if total_customers < 60 and not customers_with_coords.empty:
                needed_prospects = 60 - total_customers
                self.logger.info(f"Need {needed_prospects} prospects to reach 60 total")

                # Get unique barangay codes from customers with coordinates
                barangay_codes = customers_with_coords['barangay_code'].dropna().unique()

                if len(barangay_codes) > 0:
                    # Filter out empty/null barangay codes
                    valid_barangay_codes = [str(code).strip() for code in barangay_codes if code and str(code).strip()]

                    if len(valid_barangay_codes) > 0:
                        barangay_codes_str = "', '".join(valid_barangay_codes)
                        prospect_query = f"""
                        SELECT TOP {needed_prospects}
                            tdlinx as CustNo, latitude, longitude,
                            barangay_code, store_name_nielsen as Name
                        FROM prospective
                        WHERE barangay_code IN ('{barangay_codes_str}')
                        AND latitude IS NOT NULL
                        AND longitude IS NOT NULL
                        AND latitude != 0
                        AND longitude != 0
                        AND NOT EXISTS (
                            SELECT 1 FROM MonthlyRoutePlan_temp
                            WHERE MonthlyRoutePlan_temp.CustNo = prospective.tdlinx
                            AND MonthlyRoutePlan_temp.AgentID = '{agent_id}'
                            AND MonthlyRoutePlan_temp.RouteDate = CONVERT(DATE, '{route_date}')
                        )
                        AND NOT EXISTS (
                            SELECT 1 FROM custvisit
                            WHERE custvisit.CustID = prospective.tdlinx
                        )
                        ORDER BY NEWID()
                        """
                    else:
                        self.logger.warning("No valid barangay codes after filtering")
                        prospect_query = None

                    if prospect_query:
                        prospects_df = db.execute_query_df(prospect_query)
                    else:
                        prospects_df = pd.DataFrame()

                    if prospects_df is not None and not prospects_df.empty:
                        # Add required columns for prospects
                        prospects_df['RouteDate'] = route_date
                        prospects_df['WD'] = customers_with_coords['WD'].iloc[0] if not customers_with_coords.empty else 1
                        prospects_df['SalesManTerritory'] = customers_with_coords['SalesManTerritory'].iloc[0] if not customers_with_coords.empty else ''
                        prospects_df['AgentID'] = agent_id
                        prospects_df['RouteName'] = customers_with_coords['RouteName'].iloc[0] if not customers_with_coords.empty else ''
                        prospects_df['DistributorID'] = customers_with_coords['DistributorID'].iloc[0] if not customers_with_coords.empty else ''
                        prospects_df['RouteCode'] = customers_with_coords['RouteCode'].iloc[0] if not customers_with_coords.empty else ''
                        prospects_df['SalesOfficeID'] = customers_with_coords['SalesOfficeID'].iloc[0] if not customers_with_coords.empty else ''
                        prospects_df['StopNo'] = 0  # Will be updated with TSP
                        prospects_df['custype'] = 'prospect'

                        self.logger.info(f"Found {len(prospects_df)} prospects to add")

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

            # Assign StopNo = 100 for customers without coordinates
            customers_without_coords['new_stopno'] = 100

            return all_data_for_tsp, customers_without_coords

        except Exception as e:
            self.logger.error(f"Error enriching monthly plan data: {e}")
            return pd.DataFrame(), pd.DataFrame()

    def process_single_agent(self, agent_data):
        """Process a single agent-date combination from MonthlyRoutePlan_temp"""
        agent_id = agent_data['agent_id']
        route_date = agent_data['route_date']
        customer_count = agent_data['customer_count']

        db = None
        try:
            self.logger.info(f"Processing Agent: {agent_id}, Date: {route_date} ({customer_count} records)")

            db = DatabaseConnection()
            db.connect()

            # Step 1: Enrich monthly plan data with coordinates and prospects
            tsp_data, no_coords_data = self.enrich_monthly_plan_data(db, agent_id, route_date)

            if tsp_data.empty and no_coords_data.empty:
                self.logger.warning(f"No data to process for {agent_id} on {route_date}")
                return {"status": "no_data", "agent": agent_id, "date": route_date}

            # Step 2: Apply TSP optimization to data with coordinates
            optimized_data = pd.DataFrame()
            if not tsp_data.empty:
                try:
                    optimized_data = self.solve_tsp_nearest_neighbor(tsp_data)
                    self.logger.info(f"TSP optimized {len(optimized_data)} locations")
                except Exception as e:
                    self.logger.error(f"TSP optimization failed: {e}")
                    # Fallback: use original stop numbers
                    tsp_data['new_stopno'] = range(1, len(tsp_data) + 1)
                    optimized_data = tsp_data

            # Step 3: Combine optimized data with no-coordinate data
            all_final_data = pd.concat([optimized_data, no_coords_data], ignore_index=True)

            if all_final_data.empty:
                self.logger.warning(f"No final data to update for {agent_id} on {route_date}")
                return {"status": "no_results", "agent": agent_id, "date": route_date}

            # Step 4: Update MonthlyRoutePlan_temp with new StopNo and custype
            updates_count = 0
            for _, row in all_final_data.iterrows():
                try:
                    # Determine the new StopNo
                    new_stop_no = row.get('new_stopno', row.get('StopNo', 1))
                    custype = row.get('custype', 'customer')
                    custno = row['CustNo']

                    # Update existing records
                    update_query = """
                    UPDATE MonthlyRoutePlan_temp
                    SET StopNo = ?, custype = ?
                    WHERE AgentID = ? AND RouteDate = ? AND CustNo = ?
                    """

                    result = db.execute_query(update_query, (
                        int(new_stop_no), custype, agent_id, route_date, str(custno)
                    ))

                    if result:
                        updates_count += 1

                    # If this is a prospect (new record), insert it
                    if custype == 'prospect':
                        insert_query = """
                        INSERT INTO MonthlyRoutePlan_temp
                        (CustNo, RouteDate, Name, WD, SalesManTerritory, AgentID,
                         RouteName, DistributorID, RouteCode, SalesOfficeID, StopNo, custype)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """

                        # Truncate fields to avoid SQL truncation error
                        db.execute_query(insert_query, (
                            str(row['CustNo']), route_date, str(row.get('Name', ''))[:50],
                            int(row.get('WD', 1)), str(row.get('SalesManTerritory', ''))[:50],
                            agent_id, str(row.get('RouteName', ''))[:50],
                            str(row.get('DistributorID', ''))[:50], str(row.get('RouteCode', ''))[:50],
                            str(row.get('SalesOfficeID', ''))[:50], int(new_stop_no), custype
                        ))

                except Exception as e:
                    self.logger.error(f"Error updating record for CustNo {row['CustNo']}: {e}")
                    continue

            self.logger.info(f"Successfully updated {updates_count} records in MonthlyRoutePlan_temp")

            return {
                "status": "success",
                "agent": agent_id,
                "date": route_date,
                "records_updated": updates_count,
                "total_records": len(all_final_data)
            }

        except Exception as e:
            self.logger.error(f"Error processing {agent_id} on {route_date}: {e}")
            return {"status": "error", "agent": agent_id, "date": route_date, "error": str(e)}

        finally:
            if db:
                db.close()

    def run_monthly_route_pipeline(self, parallel=False):
        """Run the complete monthly route pipeline"""
        self.start_time = time.time()
        self.logger.info("=" * 80)
        self.logger.info("STARTING MONTHLY ROUTE PLAN PIPELINE")
        self.logger.info("Target Table: MonthlyRoutePlan_temp")
        self.logger.info("=" * 80)

        db = None
        try:
            # Get database connection
            db = DatabaseConnection()
            db.connect()

            # Get all agents to process from MonthlyRoutePlan_temp
            all_agents = self.get_all_agents_from_monthly_plan(db)

            if all_agents.empty:
                self.logger.error("No agents found to process")
                return

            total_agents = len(all_agents)
            self.logger.info(f"Total agent-date combinations to process: {total_agents}")

            # Add custype column to MonthlyRoutePlan_temp if it doesn't exist
            try:
                alter_query = "ALTER TABLE MonthlyRoutePlan_temp ADD custype VARCHAR(20) DEFAULT 'customer'"
                db.execute_query(alter_query)
                self.logger.info("Added custype column to MonthlyRoutePlan_temp")
            except:
                self.logger.info("custype column already exists or could not be added")

            # Process agents
            all_results = []
            success_count = 0
            error_count = 0

            for idx, (_, agent_data) in enumerate(all_agents.iterrows()):
                self.logger.info(f"Progress: {idx + 1}/{total_agents}")

                result = self.process_single_agent(agent_data.to_dict())
                all_results.append(result)

                if result["status"] == "success":
                    success_count += 1
                elif result["status"] == "error":
                    error_count += 1

                # Progress update every 10 agents
                if (idx + 1) % 10 == 0:
                    elapsed = time.time() - self.start_time
                    rate = (idx + 1) / elapsed
                    remaining = (total_agents - idx - 1) / rate if rate > 0 else 0

                    self.logger.info(f"  Processed: {idx + 1}/{total_agents} "
                                   f"| Success: {success_count} "
                                   f"| Errors: {error_count} "
                                   f"| ETA: {remaining/60:.1f} min")

            # Update custype using JOIN at the end
            self.logger.info("Updating custype using JOIN...")
            self.update_custype_with_join(db)

            # Final summary
            self.print_final_summary(all_results, total_agents)

        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            import traceback
            traceback.print_exc()

        finally:
            if db:
                db.close()

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

    def print_final_summary(self, results, total_agents):
        """Print final pipeline summary"""
        elapsed_time = time.time() - self.start_time

        # Count results by status
        status_counts = {}
        total_updated = 0

        for result in results:
            status = result["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

            if result["status"] == "success":
                total_updated += result.get("records_updated", 0)

        self.logger.info("=" * 80)
        self.logger.info("MONTHLY ROUTE PIPELINE COMPLETED!")
        self.logger.info("=" * 80)
        self.logger.info(f"Total Processing Time: {elapsed_time/60:.2f} minutes")
        self.logger.info(f"Average Time per Agent: {elapsed_time/total_agents:.2f} seconds")
        self.logger.info("")
        self.logger.info("RESULTS SUMMARY:")
        self.logger.info(f"  Total Agent-Date Combinations: {total_agents}")

        for status, count in status_counts.items():
            percentage = (count / total_agents) * 100
            self.logger.info(f"  {status.title()}: {count} ({percentage:.1f}%)")

        self.logger.info("")
        self.logger.info("DATA SUMMARY:")
        self.logger.info(f"  Total Records Updated: {total_updated:,}")
        self.logger.info(f"  Average Records per Agent: {total_updated/max(1, status_counts.get('success', 1)):.1f}")
        self.logger.info(f"  Target Table: MonthlyRoutePlan_temp")
        self.logger.info("  TSP Optimization: Straight-line distance based")
        self.logger.info("=" * 80)

def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Monthly Route Plan Pipeline')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Batch size for processing (default: 50)')
    parser.add_argument('--max-workers', type=int, default=4,
                       help='Maximum number of parallel workers (default: 4)')
    parser.add_argument('--parallel', action='store_true',
                       help='Enable parallel processing')
    parser.add_argument('--test-mode', action='store_true',
                       help='Run in test mode (process only first 10 agents)')

    args = parser.parse_args()

    print("=" * 80)
    print("MONTHLY ROUTE PLAN OPTIMIZATION PIPELINE")
    print("=" * 80)
    print(f"Target Table: MonthlyRoutePlan_temp")
    print(f"Batch Size: {args.batch_size}")
    print(f"Max Workers: {args.max_workers}")
    print(f"Parallel Processing: {'Enabled' if args.parallel else 'Disabled'}")
    print(f"Test Mode: {'Enabled' if args.test_mode else 'Disabled'}")
    print("=" * 80)

    # Create processor
    processor = MonthlyRoutePipelineProcessor(
        batch_size=args.batch_size,
        max_workers=args.max_workers
    )

    # Run pipeline
    processor.run_monthly_route_pipeline(parallel=args.parallel)

if __name__ == "__main__":
    main()