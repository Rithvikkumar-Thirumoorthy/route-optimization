#!/usr/bin/env python3
"""
Test TSP Algorithm with Sales Agent having valid coordinates
"""

from route_optimizer import RouteOptimizer
import pandas as pd

def test_tsp_with_coordinates():
    """Test TSP algorithm with sales agent having valid coordinates"""
    print("Testing TSP Algorithm with Valid Coordinates")
    print("=" * 60)

    optimizer = None
    try:
        # Initialize the route optimizer
        optimizer = RouteOptimizer()

        # Use the agent we found with valid coordinates
        test_agent = "SK-SAT4"
        test_date = "2025-09-23"

        print(f"Testing with: {test_agent} on {test_date}")

        # Get customers for this agent and date
        print("Getting customers...")
        customers = optimizer.get_customers_for_agent_date(test_agent, test_date)

        if customers is None or customers.empty:
            print("No customers found!")
            return

        print(f"Found {len(customers)} customers")

        # Check coordinates
        valid_coords = customers[
            (customers['latitude'].notna()) &
            (customers['longitude'].notna()) &
            (customers['latitude'] != 0) &
            (customers['longitude'] != 0)
        ]

        print(f"Customers with valid coordinates: {len(valid_coords)}")

        if len(valid_coords) > 0:
            print("\nSample customers with coordinates:")
            sample_display = valid_coords[['CustNo', 'latitude', 'longitude', 'Name']].head(10)
            print(sample_display)

            # Test TSP algorithm
            print(f"\nRunning TSP optimization on {len(valid_coords)} locations...")
            print("Original order (first 10):")
            print(valid_coords[['CustNo', 'latitude', 'longitude']].head(10))

            # Run TSP
            optimized_route = optimizer.solve_tsp_nearest_neighbor(valid_coords)

            print(f"\nOptimized route order (first 10):")
            print(optimized_route[['CustNo', 'latitude', 'longitude', 'stopno']].head(10))

            # Calculate total distance for comparison
            def calculate_route_distance(route_df):
                total_distance = 0
                for i in range(len(route_df) - 1):
                    lat1, lon1 = route_df.iloc[i]['latitude'], route_df.iloc[i]['longitude']
                    lat2, lon2 = route_df.iloc[i + 1]['latitude'], route_df.iloc[i + 1]['longitude']
                    distance = optimizer.haversine_distance(lat1, lon1, lat2, lon2)
                    total_distance += distance
                return total_distance

            original_distance = calculate_route_distance(valid_coords)
            optimized_distance = calculate_route_distance(optimized_route)

            print(f"\nDistance Comparison:")
            print(f"Original route distance: {original_distance:.2f} km")
            print(f"Optimized route distance: {optimized_distance:.2f} km")
            print(f"Distance saved: {original_distance - optimized_distance:.2f} km")
            print(f"Improvement: {((original_distance - optimized_distance) / original_distance * 100):.1f}%")

            # Clear previous test data
            clear_query = """
            DELETE FROM routeplan_ai
            WHERE salesagent = ? AND routedate = ?
            """
            optimizer.db.execute_query(clear_query, [test_agent, test_date])

            # Insert optimized route into routeplan_ai table
            results = []
            for _, customer in optimized_route.iterrows():
                route_data = {
                    'salesagent': test_agent,
                    'custno': customer['CustNo'],
                    'custype': 'customer',
                    'latitude': customer['latitude'],
                    'longitude': customer['longitude'],
                    'stopno': customer['stopno'],
                    'routedate': test_date,
                    'barangay': customer.get('barangay_code', ''),
                    'barangay_code': customer.get('barangay_code', ''),
                    'is_visited': 0
                }
                results.append(route_data)

            print(f"\nInserting {len(results)} optimized records into routeplan_ai table...")
            success = optimizer.insert_route_plan(results)

            if success:
                print("Data inserted successfully!")

                # Verify insertion
                verify_query = """
                SELECT COUNT(*) as count
                FROM routeplan_ai
                WHERE salesagent = ? AND routedate = ?
                """
                count_result = optimizer.db.execute_query(verify_query, [test_agent, test_date])
                if count_result:
                    print(f"Verified: {count_result[0][0]} records in routeplan_ai table")

                # Show optimized route from database
                route_query = """
                SELECT TOP 15 salesagent, custno, stopno, latitude, longitude
                FROM routeplan_ai
                WHERE salesagent = ? AND routedate = ?
                ORDER BY stopno
                """
                route_results = optimizer.db.execute_query_df(route_query, [test_agent, test_date])
                if route_results is not None and not route_results.empty:
                    print("\nOptimized route from database (first 15 stops):")
                    print(route_results)
            else:
                print("Failed to insert data")

        else:
            print("No customers with valid coordinates found for TSP testing")

    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if optimizer:
            optimizer.close()

if __name__ == "__main__":
    test_tsp_with_coordinates()