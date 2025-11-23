#!/usr/bin/env python3
"""
Test Enhanced Route Optimization Logic with 2-step prospect selection
"""

from enhanced_route_optimizer import EnhancedRouteOptimizer
import pandas as pd

def test_enhanced_logic():
    """Test the enhanced route optimization with 2-step prospect selection"""
    print("Testing Enhanced Route Optimization Logic")
    print("=" * 60)

    optimizer = None
    try:
        # Initialize the enhanced optimizer
        optimizer = EnhancedRouteOptimizer()

        # Find a sales agent with fewer customers (< 60) to test prospect selection
        print("Finding sales agent with < 60 customers...")

        # Look for agents with reasonable customer counts
        query = """
        SELECT TOP 10
            r.SalesManTerritory,
            r.RouteDate,
            COUNT(*) as total_customers,
            SUM(CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
                     AND r.latitude != 0 AND r.longitude != 0 THEN 1 ELSE 0 END) as customers_with_coords,
            SUM(CASE WHEN r.latitude IS NULL OR r.longitude IS NULL
                     OR r.latitude = 0 OR r.longitude = 0 THEN 1 ELSE 0 END) as customers_without_coords
        FROM routedata r
        WHERE r.SalesManTerritory IS NOT NULL
        AND r.RouteDate IS NOT NULL
        GROUP BY r.SalesManTerritory, r.RouteDate
        HAVING COUNT(*) BETWEEN 30 AND 55
        AND SUM(CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
                     AND r.latitude != 0 AND r.longitude != 0 THEN 1 ELSE 0 END) > 15
        ORDER BY total_customers DESC
        """

        suitable_agents = optimizer.db.execute_query_df(query)

        if suitable_agents is None or suitable_agents.empty:
            print("No suitable agents found for testing. Using CARL as fallback...")
            test_agent = "CARL"
            test_date = "2025-09-01"
        else:
            print("Found suitable agents:")
            print(suitable_agents[['SalesManTerritory', 'RouteDate', 'total_customers', 'customers_with_coords', 'customers_without_coords']])

            # Pick the first one
            test_agent = suitable_agents.iloc[0]['SalesManTerritory']
            test_date = suitable_agents.iloc[0]['RouteDate']

        print(f"\nTesting with: {test_agent} on {test_date}")

        # Get existing customers
        customers = optimizer.get_customers_for_agent_date(test_agent, test_date)

        if customers is None or customers.empty:
            print("No customers found!")
            return

        print(f"Found {len(customers)} existing customers")

        # Separate customers by coordinates
        customers_with_coords = customers[
            (customers['latitude'].notna()) &
            (customers['longitude'].notna()) &
            (customers['latitude'] != 0) &
            (customers['longitude'] != 0)
        ].copy()

        customers_without_coords = customers[
            (customers['latitude'].isna()) |
            (customers['longitude'].isna()) |
            (customers['latitude'] == 0) |
            (customers['longitude'] == 0)
        ].copy()

        print(f"Customers with coordinates: {len(customers_with_coords)}")
        print(f"Customers without coordinates: {len(customers_without_coords)}")

        if not customers_with_coords.empty:
            print("\nSample customers with coordinates:")
            print(customers_with_coords[['CustNo', 'latitude', 'longitude', 'barangay_code']].head())

        if not customers_without_coords.empty:
            print("\nSample customers without coordinates:")
            print(customers_without_coords[['CustNo', 'barangay_code']].head())

        # Test 2-step prospect selection
        current_count = len(customers)
        if current_count < 60:
            needed_prospects = 60 - current_count
            print(f"\nNeed {needed_prospects} prospects to reach 60 total")

            if not customers_with_coords.empty:
                print("\nTesting 2-step prospect selection...")

                # Test the 2-step process
                prospects = optimizer.get_barangay_prospects_2step(
                    customers_with_coords, customers_without_coords, needed_prospects
                )

                if not prospects.empty:
                    print(f"Found {len(prospects)} prospects:")
                    print(prospects[['CustNo', 'Latitude', 'Longitude', 'Barangay_code', 'distance_from_centroid']].head(10))

                    # Show distance statistics
                    print(f"\nDistance statistics:")
                    print(f"Min distance: {prospects['distance_from_centroid'].min():.2f} km")
                    print(f"Max distance: {prospects['distance_from_centroid'].max():.2f} km")
                    print(f"Avg distance: {prospects['distance_from_centroid'].mean():.2f} km")

                    # Show barangay distribution
                    barangay_counts = prospects['Barangay_code'].value_counts()
                    print(f"\nProspects by barangay:")
                    print(barangay_counts.head())

                else:
                    print("No prospects found in same barangays")

        # Clear previous test data
        clear_query = """
        DELETE FROM routeplan_ai
        WHERE salesagent = ? AND routedate = ?
        """
        optimizer.db.execute_query(clear_query, [test_agent, test_date])

        # Test the complete enhanced process
        print(f"\n" + "="*60)
        print("Testing complete enhanced process...")

        # Process this specific agent and date using enhanced logic
        results = []

        # Get existing customers again
        existing_customers = customers.copy()

        # Separate by coordinates
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

        print(f"Processing {len(customers_with_coords)} customers with coords")
        print(f"Processing {len(customers_without_coords)} customers without coords")

        # Get prospects using 2-step process
        prospects = pd.DataFrame()
        if len(existing_customers) < 60 and not customers_with_coords.empty:
            needed = 60 - len(existing_customers)
            prospects = optimizer.get_barangay_prospects_2step(
                customers_with_coords, customers_without_coords, needed
            )

        # Classify types
        existing_customers['final_custype'] = 'customer'
        if not prospects.empty:
            prospects['final_custype'] = 'prospect'

        # Assign stopno = 100 for customers without coordinates
        customers_without_coords['stopno'] = 100

        # Combine customers with coords and prospects for TSP
        customers_for_tsp = pd.concat([customers_with_coords, prospects], ignore_index=True)

        # Run TSP
        if not customers_for_tsp.empty:
            print(f"Running TSP on {len(customers_for_tsp)} locations with coordinates...")
            optimized_route = optimizer.solve_tsp_nearest_neighbor(customers_for_tsp)
        else:
            optimized_route = pd.DataFrame()

        # Combine final results
        final_route = pd.concat([optimized_route, customers_without_coords], ignore_index=True)

        print(f"\nFinal route breakdown:")
        print(f"- Customers with coords (TSP optimized): {len(optimized_route) if not optimized_route.empty else 0}")
        print(f"- Customers without coords (stopno=100): {len(customers_without_coords)}")
        print(f"- Prospects included: {len(prospects) if not prospects.empty else 0}")
        print(f"- Total stops: {len(final_route)}")

        # Prepare data for insertion
        for _, customer in final_route.iterrows():
            route_data = {
                'salesagent': test_agent,
                'custno': customer.get('CustNo'),
                'custype': customer.get('final_custype', customer.get('custype', 'customer')),
                'latitude': customer.get('latitude', customer.get('Latitude')),
                'longitude': customer.get('longitude', customer.get('Longitude')),
                'stopno': customer.get('stopno', 1),
                'routedate': test_date,
                'barangay': customer.get('barangay_code', customer.get('Barangay', '')),
                'barangay_code': customer.get('barangay_code', customer.get('Barangay_code', '')),
                'is_visited': 0
            }
            results.append(route_data)

        # Insert into routeplan_ai table
        if results:
            print(f"\nInserting {len(results)} records into routeplan_ai table...")
            success = optimizer.insert_route_plan(results)

            if success:
                print("Data inserted successfully!")

                # Verify insertion
                verify_query = """
                SELECT
                    custype,
                    COUNT(*) as count,
                    COUNT(CASE WHEN stopno = 100 THEN 1 END) as stopno_100_count,
                    COUNT(CASE WHEN stopno != 100 THEN 1 END) as tsp_optimized_count
                FROM routeplan_ai
                WHERE salesagent = ? AND routedate = ?
                GROUP BY custype
                """
                summary = optimizer.db.execute_query_df(verify_query, [test_agent, test_date])
                if summary is not None and not summary.empty:
                    print("\nInsertion summary:")
                    print(summary)

                # Show sample optimized route
                sample_query = """
                SELECT TOP 15 salesagent, custno, custype, stopno, latitude, longitude, barangay_code
                FROM routeplan_ai
                WHERE salesagent = ? AND routedate = ?
                ORDER BY
                    CASE WHEN stopno = 100 THEN 1 ELSE 0 END,
                    stopno
                """
                sample_results = optimizer.db.execute_query_df(sample_query, [test_agent, test_date])
                if sample_results is not None and not sample_results.empty:
                    print("\nSample route (first 15 stops):")
                    print(sample_results)

            else:
                print("Failed to insert data")

    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if optimizer:
            optimizer.close()

if __name__ == "__main__":
    test_enhanced_logic()