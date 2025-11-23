#!/usr/bin/env python3
"""
Full Route Optimization Pipeline - Process ALL Agents
Run TSP optimization for all agent-date combinations in the database
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.scalable_route_optimizer import ScalableRouteOptimizer
    from core.database import DatabaseConnection
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running from the project root directory")
    sys.exit(1)

class FullPipelineProcessor:
    def __init__(self, batch_size=50, max_workers=4):
        """Initialize full pipeline processor"""
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.processed_count = 0
        self.error_count = 0
        self.start_time = None

        # Setup logging
        self.setup_logging()

    def setup_logging(self):
        """Setup logging configuration"""
        log_filename = f"full_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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

    def get_all_agents(self, db):
        """Get all unique agent-date combinations from routedata"""
        try:
            query = """
            SELECT
                Code as agent_id,
                RouteDate as route_date,
                COUNT(DISTINCT CustNo) as customer_count,
                COUNT(*) as total_records
            FROM routedata
            WHERE Code IS NOT NULL
                AND RouteDate IS NOT NULL
                AND CustNo IS NOT NULL
            GROUP BY Code, RouteDate
            HAVING COUNT(DISTINCT CustNo) >= 5  -- Minimum 5 customers to process
            ORDER BY Code, RouteDate DESC
            """

            result_df = db.execute_query_df(query)

            if result_df is not None and not result_df.empty:
                self.logger.info(f"Found {len(result_df)} agent-date combinations to process")
                return result_df
            else:
                self.logger.error("No agent data found in routedata table")
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error fetching agent data: {e}")
            return pd.DataFrame()

    def process_single_agent(self, agent_data):
        """Process a single agent-date combination"""
        agent_id = agent_data['agent_id']
        route_date = agent_data['route_date']
        customer_count = agent_data['customer_count']

        optimizer = None
        try:
            self.logger.info(f"Processing Agent: {agent_id}, Date: {route_date} ({customer_count} customers)")

            optimizer = ScalableRouteOptimizer()

            # Check if already processed
            check_query = f"""
            SELECT COUNT(*) as count
            FROM routeplan_ai
            WHERE salesagent = '{agent_id}' AND routedate = '{route_date}'
            """

            existing = optimizer.db.execute_query(check_query)
            if existing and existing[0][0] > 0:
                self.logger.info(f"  Agent {agent_id} on {route_date} already processed - skipping")
                return {"status": "skipped", "agent": agent_id, "date": route_date}

            # Get customers for this agent-date
            customers_query = f"""
            SELECT
                CustNo,
                latitude,
                longitude,
                barangay_code,
                custype,
                Name,
                distributorID
            FROM routedata
            WHERE Code = '{agent_id}' AND RouteDate = '{route_date}'
            AND CustNo IS NOT NULL
            """

            existing_customers = optimizer.db.execute_query_df(customers_query)

            if existing_customers is None or existing_customers.empty:
                self.logger.warning(f"  No customer data found for {agent_id} on {route_date}")
                return {"status": "no_data", "agent": agent_id, "date": route_date}

            # Separate customers with and without coordinates
            customers_with_coords = existing_customers[
                (existing_customers['latitude'].notna()) &
                (existing_customers['longitude'].notna()) &
                (existing_customers['latitude'] != 0) &
                (existing_customers['longitude'] != 0)
            ].copy()

            customers_without_coords = existing_customers[
                (existing_customers['latitude'].isna()) |
                (existing_customers['longitude'].isna()) |
                (existing_customers['latitude'] == 0) |
                (existing_customers['longitude'] == 0)
            ].copy()

            self.logger.info(f"    With coordinates: {len(customers_with_coords)}")
            self.logger.info(f"    Without coordinates: {len(customers_without_coords)}")

            # Get prospects if needed (target 60 total)
            nearby_prospects = pd.DataFrame()
            if customer_count < 60 and not customers_with_coords.empty:
                needed_prospects = 60 - customer_count
                self.logger.info(f"    Adding {needed_prospects} prospects to reach 60 total")

                try:
                    nearby_prospects = optimizer.get_barangay_prospects_2step_optimized(
                        customers_with_coords, customers_without_coords, needed_prospects
                    )
                    self.logger.info(f"    Found {len(nearby_prospects)} prospects")
                except Exception as e:
                    self.logger.warning(f"    Error getting prospects: {e}")
                    nearby_prospects = pd.DataFrame()

            # Classify customer types
            existing_customers, nearby_prospects = optimizer.classify_customer_type(
                existing_customers, nearby_prospects
            )

            # Update separated dataframes with classification
            customers_with_coords = existing_customers[
                (existing_customers['latitude'].notna()) &
                (existing_customers['longitude'].notna()) &
                (existing_customers['latitude'] != 0) &
                (existing_customers['longitude'] != 0)
            ].copy()

            customers_without_coords = existing_customers[
                (existing_customers['latitude'].isna()) |
                (existing_customers['longitude'].isna()) |
                (existing_customers['latitude'] == 0) |
                (existing_customers['longitude'] == 0)
            ].copy()

            # Assign stopno = 100 for customers without coordinates
            customers_without_coords['stopno'] = 100

            # Combine customers with coordinates and prospects for TSP
            customers_for_tsp = pd.concat([customers_with_coords, nearby_prospects], ignore_index=True)

            # Run TSP optimization
            optimized_route = pd.DataFrame()
            if not customers_for_tsp.empty:
                try:
                    optimized_route = optimizer.solve_tsp_nearest_neighbor(customers_for_tsp)
                    self.logger.info(f"    TSP optimized {len(optimized_route)} locations")
                except Exception as e:
                    self.logger.error(f"    TSP optimization failed: {e}")
                    # Fallback: assign sequential stop numbers
                    customers_for_tsp['stopno'] = range(1, len(customers_for_tsp) + 1)
                    optimized_route = customers_for_tsp

            # Combine all results
            final_route = pd.concat([optimized_route, customers_without_coords], ignore_index=True)

            # Prepare results for routeplan_ai table
            results = []
            for _, customer in final_route.iterrows():
                # Get custype with proper fallback
                custype_value = customer.get('final_custype')
                if pd.isna(custype_value) or custype_value is None:
                    custype_value = customer.get('custype', 'customer')
                if pd.isna(custype_value) or custype_value is None:
                    custype_value = 'customer'

                # Handle data type conversions
                latitude = customer.get('latitude', customer.get('Latitude'))
                longitude = customer.get('longitude', customer.get('Longitude'))
                stopno = customer.get('stopno', 1)

                try:
                    latitude = float(latitude) if pd.notna(latitude) else None
                    longitude = float(longitude) if pd.notna(longitude) else None
                    stopno = int(stopno) if pd.notna(stopno) else 1
                except (ValueError, TypeError):
                    latitude = longitude = None
                    stopno = 1

                # Handle barangay_code properly
                if custype_value == 'prospect':
                    barangay_code_value = customer.get('barangay_code', '')
                    barangay_value = customer.get('Barangay', '')
                else:
                    barangay_code_value = customer.get('barangay_code', '')
                    barangay_value = customer.get('barangay_code', '')

                route_data = {
                    'salesagent': str(agent_id),
                    'custno': str(customer.get('CustNo', '')),
                    'custype': str(custype_value),
                    'latitude': latitude,
                    'longitude': longitude,
                    'stopno': stopno,
                    'routedate': route_date,
                    'barangay': str(barangay_value),
                    'barangay_code': str(barangay_code_value),
                    'is_visited': 0
                }
                results.append(route_data)

            # Insert results into routeplan_ai table
            if results:
                optimizer.insert_route_plan(results)
                self.logger.info(f"  SUCCESS: Inserted {len(results)} records for {agent_id}")

                return {
                    "status": "success",
                    "agent": agent_id,
                    "date": route_date,
                    "records": len(results),
                    "prospects_added": len(nearby_prospects)
                }
            else:
                self.logger.warning(f"  No results to insert for {agent_id}")
                return {"status": "no_results", "agent": agent_id, "date": route_date}

        except Exception as e:
            self.logger.error(f"  ERROR processing {agent_id} on {route_date}: {e}")
            return {"status": "error", "agent": agent_id, "date": route_date, "error": str(e)}

        finally:
            if optimizer:
                optimizer.close()

    def process_batch(self, agent_batch):
        """Process a batch of agents"""
        results = []
        for agent_data in agent_batch:
            result = self.process_single_agent(agent_data.to_dict())
            results.append(result)

            # Update counters
            if result["status"] == "success":
                self.processed_count += 1
            elif result["status"] == "error":
                self.error_count += 1

        return results

    def run_full_pipeline(self, parallel=False):
        """Run the complete pipeline for all agents"""
        self.start_time = time.time()
        self.logger.info("=" * 80)
        self.logger.info("STARTING FULL ROUTE OPTIMIZATION PIPELINE")
        self.logger.info("=" * 80)

        db = None
        try:
            # Get database connection
            db = DatabaseConnection()
            db.connect()

            # Get all agents to process
            all_agents = self.get_all_agents(db)

            if all_agents.empty:
                self.logger.error("No agents found to process")
                return

            total_agents = len(all_agents)
            self.logger.info(f"Total agent-date combinations to process: {total_agents}")

            # Process in batches
            all_results = []

            if parallel and total_agents > 10:
                self.logger.info(f"Processing in parallel with {self.max_workers} workers")

                # Split into batches
                batches = [all_agents[i:i + self.batch_size]
                          for i in range(0, len(all_agents), self.batch_size)]

                with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                    batch_results = list(executor.map(self.process_batch, batches))

                # Flatten results
                for batch_result in batch_results:
                    all_results.extend(batch_result)
            else:
                self.logger.info("Processing sequentially")

                for idx, (_, agent_data) in enumerate(all_agents.iterrows()):
                    self.logger.info(f"Progress: {idx + 1}/{total_agents}")

                    result = self.process_single_agent(agent_data.to_dict())
                    all_results.append(result)

                    # Update counters
                    if result["status"] == "success":
                        self.processed_count += 1
                    elif result["status"] == "error":
                        self.error_count += 1

                    # Progress update every 10 agents
                    if (idx + 1) % 10 == 0:
                        elapsed = time.time() - self.start_time
                        rate = (idx + 1) / elapsed
                        remaining = (total_agents - idx - 1) / rate if rate > 0 else 0

                        self.logger.info(f"  Processed: {idx + 1}/{total_agents} "
                                       f"| Success: {self.processed_count} "
                                       f"| Errors: {self.error_count} "
                                       f"| ETA: {remaining/60:.1f} min")

            # Final summary
            self.print_final_summary(all_results, total_agents)

        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            import traceback
            traceback.print_exc()

        finally:
            if db:
                db.connection.close()

    def print_final_summary(self, results, total_agents):
        """Print final pipeline summary"""
        elapsed_time = time.time() - self.start_time

        # Count results by status
        status_counts = {}
        total_records = 0
        total_prospects = 0

        for result in results:
            status = result["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

            if result["status"] == "success":
                total_records += result.get("records", 0)
                total_prospects += result.get("prospects_added", 0)

        self.logger.info("=" * 80)
        self.logger.info("FULL PIPELINE COMPLETED!")
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
        self.logger.info(f"  Total Records Inserted: {total_records:,}")
        self.logger.info(f"  Total Prospects Added: {total_prospects:,}")
        self.logger.info(f"  Average Records per Agent: {total_records/max(1, status_counts.get('success', 1)):.1f}")
        self.logger.info("")
        self.logger.info("Results saved to 'routeplan_ai' table")
        self.logger.info("=" * 80)

def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Full Route Optimization Pipeline')
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
    print("ROUTE OPTIMIZATION - FULL PIPELINE")
    print("=" * 80)
    print(f"Batch Size: {args.batch_size}")
    print(f"Max Workers: {args.max_workers}")
    print(f"Parallel Processing: {'Enabled' if args.parallel else 'Disabled'}")
    print(f"Test Mode: {'Enabled' if args.test_mode else 'Disabled'}")
    print("=" * 80)

    if args.test_mode:
        args.batch_size = 10
        print("TEST MODE: Processing only first 10 agents")

    # Create processor
    processor = FullPipelineProcessor(
        batch_size=args.batch_size,
        max_workers=args.max_workers
    )

    # Run pipeline
    processor.run_full_pipeline(parallel=args.parallel)

if __name__ == "__main__":
    main()