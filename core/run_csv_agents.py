#!/usr/bin/env python3
"""
Run pipeline for agents from CSV file
Process all agents listed in distributor_11814_clustered_scenarios_20250929_145849.csv
"""

from scalable_route_optimizer import ScalableRouteOptimizer
import sys
import pandas as pd
from datetime import datetime

def load_agents_from_csv():
    """Load agents from CSV file"""
    csv_file = "../distributor_11814_clustered_scenarios_20250929_145849.csv"
    try:
        df = pd.read_csv(csv_file)
        print(f"Loaded {len(df)} agents from CSV")

        # Convert to list of tuples
        agents = []
        for _, row in df.iterrows():
            agents.append((row['agent_id'], row['route_date']))

        return agents
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return []

def run_csv_agents():
    """Run pipeline for agents from CSV file"""
    print("RUNNING PIPELINE FOR CSV AGENTS")
    print("=" * 50)

    # Load agents from CSV
    specific_agents = load_agents_from_csv()

    if not specific_agents:
        print("No agents loaded from CSV")
        return

    print(f"Total agents to process: {len(specific_agents)}")
    print("First 5 agents:")
    for i, (agent, date) in enumerate(specific_agents[:5]):
        print(f"  - Agent: {agent}, Date: {date}")
    if len(specific_agents) > 5:
        print(f"  ... and {len(specific_agents) - 5} more")

    optimizer = None
    try:
        optimizer = ScalableRouteOptimizer()

        total_processed = 0
        success_count = 0

        for agent_id, route_date in specific_agents:
            print(f"\n{'='*60}")
            print(f"Processing Agent: {agent_id}, Date: {route_date}")
            print(f"{'='*60}")

            try:
                # Check if this agent-date exists
                check_query = f"""
                SELECT COUNT(DISTINCT CustNo) as customer_count
                FROM routedata
                WHERE Code = '{agent_id}' AND RouteDate = '{route_date}'
                """

                result = optimizer.db.execute_query(check_query)
                if result and result[0][0] > 0:
                    customer_count = result[0][0]
                    print(f"Found {customer_count} customers for {agent_id} on {route_date}")

                    # Get customers for this agent-date
                    customers_query = f"""
                    SELECT CustNo, latitude, longitude, barangay_code, custype, Name
                    FROM routedata
                    WHERE Code = '{agent_id}' AND RouteDate = '{route_date}'
                    AND CustNo IS NOT NULL
                    """

                    existing_customers = optimizer.db.execute_query_df(customers_query)

                    if existing_customers is not None and not existing_customers.empty:
                        print(f"  Processing {len(existing_customers)} existing customers")

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
                        if customer_count < 60:
                            needed_prospects = 60 - customer_count
                            print(f"    Need {needed_prospects} prospects to reach 60")

                            if not customers_with_coords.empty:
                                try:
                                    nearby_prospects = optimizer.get_barangay_prospects_2step_optimized(
                                        customers_with_coords, customers_without_coords, needed_prospects
                                    )
                                    print(f"    Found {len(nearby_prospects)} prospects")
                                except Exception as e:
                                    print(f"    Warning: Could not get prospects: {e}")
                        else:
                            print(f"    Agent already has {customer_count} customers - no prospects needed")

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

                        # Process customers without coordinates - assign stopno = 100
                        customers_without_coords['stopno'] = 100

                        # Combine customers with coordinates and prospects for TSP
                        customers_for_tsp = pd.concat([customers_with_coords, nearby_prospects], ignore_index=True)

                        # Run TSP on locations with coordinates
                        if not customers_for_tsp.empty:
                            try:
                                optimized_route = optimizer.solve_tsp_nearest_neighbor(customers_for_tsp)
                                print(f"    TSP optimized {len(optimized_route)} locations")
                            except Exception as e:
                                print(f"    TSP failed: {e}, using sequential ordering")
                                customers_for_tsp['stopno'] = range(1, len(customers_for_tsp) + 1)
                                optimized_route = customers_for_tsp
                        else:
                            optimized_route = pd.DataFrame()

                        # Combine all results
                        final_route = pd.concat([optimized_route, customers_without_coords], ignore_index=True)

                        print(f"    Final route: {len(final_route)} total stops")

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
                            print(f"  SUCCESS: Inserted {len(results)} records for {agent_id}")
                            success_count += 1
                            total_processed += 1

                    else:
                        print(f"  No customer data found for {agent_id} on {route_date}")
                else:
                    print(f"  No customers found for {agent_id} on {route_date}")

            except Exception as e:
                print(f"  ERROR processing {agent_id}: {e}")
                continue

        print(f"\n{'='*60}")
        print(f"CSV PIPELINE COMPLETED!")
        print(f"Successfully processed {success_count} out of {len(specific_agents)} agents")
        print(f"Results saved to 'routeplan_ai' table")
        print(f"{'='*60}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if optimizer:
            optimizer.close()

if __name__ == "__main__":
    # Import pandas here since it's needed
    import pandas as pd
    run_csv_agents()