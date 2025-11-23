#!/usr/bin/env python3
"""
Run pipeline for specific agents with prospect addition
Agents: SK-SAT5, SK-SAT4, PVM-PRE01, PVM-PRE02 with their dates
"""

import sys
import os
import pandas as pd

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.enhanced_route_optimizer import EnhancedRouteOptimizer

def run_agents_with_prospects():
    """Run pipeline for specific agents with prospect addition"""
    print("RUNNING PIPELINE FOR SPECIFIC AGENTS WITH PROSPECTS")
    print("=" * 55)

    # Define specific agents and days
    specific_agents = [
        ("SK-SAT5", "2025-09-03"),
        ("SK-SAT4", "2025-09-11"),
        ("PVM-PRE01", "2025-09-08"),
        ("SK-SAT4", "2025-09-27"),
        ("PVM-PRE02", "2025-09-25")
    ]

    optimizer = None
    try:
        optimizer = EnhancedRouteOptimizer()

        print("Target agents and days:")
        for agent, date in specific_agents:
            print(f"  - Agent: {agent}, Date: {date}")

        total_processed = 0

        # Clear existing data for these specific agents first
        print("\nClearing existing optimized routes for these agents...")
        for agent_id, route_date in specific_agents:
            clear_query = f"""
            DELETE FROM routeplan_ai
            WHERE salesagent = '{agent_id}' AND routedate = '{route_date}'
            """
            optimizer.db.execute_insert(clear_query, ())
        print("Previous routes cleared.")

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
                                nearby_prospects = optimizer.get_barangay_prospects_2step_optimized(
                                    customers_with_coords, customers_without_coords, needed_prospects
                                )
                                print(f"    Found {len(nearby_prospects)} nearby prospects")
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
                            optimized_route = optimizer.solve_tsp_nearest_neighbor(customers_for_tsp)
                            print(f"    TSP optimized {len(optimized_route)} locations")
                        else:
                            optimized_route = pd.DataFrame()

                        # Combine all results
                        final_route = pd.concat([optimized_route, customers_without_coords], ignore_index=True)

                        print(f"    Final route: {len(final_route)} total stops")

                        # Count by type
                        with_coords_count = len(optimized_route) if not optimized_route.empty else 0
                        without_coords_count = len(customers_without_coords)
                        prospects_count = len(nearby_prospects) if not nearby_prospects.empty else 0

                        print(f"      - With coordinates: {with_coords_count}")
                        print(f"      - Without coordinates: {without_coords_count}")
                        print(f"      - Prospects added: {prospects_count}")

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

                            # Handle barangay_code properly for both customers and prospects
                            if custype_value == 'prospect':
                                # For prospects, use barangay_code from prospective table
                                barangay_code_value = customer.get('barangay_code', '')
                                barangay_value = customer.get('Barangay', '')
                            else:
                                # For customers, use barangay_code from routedata table
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
                            total_processed += 1

                    else:
                        print(f"  No customer data found for {agent_id} on {route_date}")
                else:
                    print(f"  No customers found for {agent_id} on {route_date}")

            except Exception as e:
                print(f"  ERROR processing {agent_id}: {e}")
                continue

        print(f"\n{'='*60}")
        print(f"PIPELINE COMPLETED!")
        print(f"Successfully processed {total_processed} out of {len(specific_agents)} agents")
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
    run_agents_with_prospects()