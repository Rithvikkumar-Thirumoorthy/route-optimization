#!/usr/bin/env python3
"""
Run Route Optimization Pipeline for agents from CSV file
Process all agents listed in distributor_11814_clustered_scenarios_20250929_145849.csv
"""

import sys
import os
import pandas as pd
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from core.scalable_route_optimizer import ScalableRouteOptimizer
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running from the project root directory")
    sys.exit(1)

def load_agents_from_csv(csv_file):
    """Load agents from CSV file"""
    try:
        df = pd.read_csv(csv_file)
        print(f"Loaded {len(df)} agents from {csv_file}")

        # Extract agent_id and route_date pairs
        agents = []
        for _, row in df.iterrows():
            agents.append({
                'agent_id': row['agent_id'],
                'route_date': row['route_date'],
                'scenario': row['scenario'],
                'total_customers': row['total_customers'],
                'valid_coords': row['valid_coord_customers'],
                'invalid_coords': row['invalid_coord_customers'],
                'priority': row['priority']
            })

        return agents
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        return []

def run_pipeline_for_csv_agents():
    """Run pipeline for all agents in the CSV"""
    print("=" * 80)
    print("ROUTE OPTIMIZATION PIPELINE - CSV AGENTS")
    print("Processing agents from distributor_11814_clustered_scenarios_20250929_145849.csv")
    print("=" * 80)

    # Load agents from CSV
    csv_file = "distributor_11814_clustered_scenarios_20250929_145849.csv"
    agents = load_agents_from_csv(csv_file)

    if not agents:
        print("No agents loaded from CSV file")
        return

    print(f"\nAgent breakdown by scenario:")
    scenario_counts = {}
    for agent in agents:
        scenario = agent['scenario']
        scenario_counts[scenario] = scenario_counts.get(scenario, 0) + 1

    for scenario, count in sorted(scenario_counts.items()):
        print(f"  Scenario {scenario}: {count} agents")

    print(f"\nStarting pipeline processing...")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    optimizer = None
    processed_count = 0
    success_count = 0
    error_count = 0
    skipped_count = 0

    try:
        optimizer = ScalableRouteOptimizer()

        for i, agent_data in enumerate(agents):
            agent_id = agent_data['agent_id']
            route_date = agent_data['route_date']
            scenario = agent_data['scenario']

            print(f"\n[{i+1}/{len(agents)}] Processing Agent: {agent_id}, Date: {route_date} (Scenario {scenario})")

            try:
                # Check if already processed
                check_query = f"""
                SELECT COUNT(*) as count
                FROM routeplan_ai
                WHERE salesagent = '{agent_id}' AND routedate = '{route_date}'
                """

                existing = optimizer.db.execute_query(check_query)
                if existing and existing[0][0] > 0:
                    print(f"  SKIPPED: Already processed ({existing[0][0]} records exist)")
                    skipped_count += 1
                    continue

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
                    print(f"  ERROR: No customer data found")
                    error_count += 1
                    continue

                customer_count = len(existing_customers)
                print(f"  Found {customer_count} customers")

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

                print(f"    With coordinates: {len(customers_with_coords)}")
                print(f"    Without coordinates: {len(customers_without_coords)}")

                # Get prospects if needed (target 60 total)
                nearby_prospects = pd.DataFrame()
                if customer_count < 60 and not customers_with_coords.empty:
                    needed_prospects = 60 - customer_count
                    print(f"    Adding {needed_prospects} prospects to reach 60 total")

                    try:
                        nearby_prospects = optimizer.get_barangay_prospects_2step_optimized(
                            customers_with_coords, customers_without_coords, needed_prospects
                        )
                        print(f"    Found {len(nearby_prospects)} prospects")
                    except Exception as e:
                        print(f"    Warning: Could not get prospects: {e}")
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
                        print(f"    TSP optimized {len(optimized_route)} locations")
                    except Exception as e:
                        print(f"    Warning: TSP optimization failed: {e}")
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
                    print(f"  SUCCESS: Inserted {len(results)} records")
                    success_count += 1
                else:
                    print(f"  ERROR: No results to insert")
                    error_count += 1

                processed_count += 1

                # Progress update every 5 agents
                if (i + 1) % 5 == 0:
                    print(f"\nProgress Update: {i+1}/{len(agents)} agents processed")
                    print(f"  Success: {success_count}, Errors: {error_count}, Skipped: {skipped_count}")

            except Exception as e:
                print(f"  ERROR: {e}")
                error_count += 1
                continue

    except Exception as e:
        print(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if optimizer:
            optimizer.close()

    # Final summary
    print("\n" + "=" * 80)
    print("PIPELINE COMPLETED!")
    print("=" * 80)
    print(f"Total agents in CSV: {len(agents)}")
    print(f"Successfully processed: {success_count}")
    print(f"Errors encountered: {error_count}")
    print(f"Already processed (skipped): {skipped_count}")
    print(f"Success rate: {(success_count/(len(agents)-skipped_count)*100):.1f}%" if (len(agents)-skipped_count) > 0 else "N/A")
    print(f"Results saved to 'routeplan_ai' table")
    print("=" * 80)

if __name__ == "__main__":
    run_pipeline_for_csv_agents()