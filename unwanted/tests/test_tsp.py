#!/usr/bin/env python3
"""
Test TSP Algorithm with Real Data
"""

from route_optimizer import RouteOptimizer
import pandas as pd
from datetime import datetime

def test_tsp_with_real_data():
    """Test TSP algorithm with actual sales agent data"""
    print("Testing TSP Algorithm with Real Data")
    print("=" * 50)

    optimizer = None
    try:
        # Initialize the route optimizer
        optimizer = RouteOptimizer()

        # First, let's see what sales agents we have
        print("Getting sales agents...")
        sales_agents = optimizer.get_sales_agents()

        if not sales_agents:
            print("No sales agents found!")
            return

        print(f"Found {len(sales_agents)} sales agents:")
        for i, agent in enumerate(sales_agents[:5]):  # Show first 5
            print(f"  {i+1}. {agent}")

        # Pick the first sales agent for testing
        test_agent = sales_agents[0]
        print(f"\nTesting with sales agent: {test_agent}")

        # Get customer counts by date for this agent
        print("Getting customer counts by date...")
        date_counts = optimizer.get_customer_count_by_date(test_agent)

        if date_counts is None or date_counts.empty:
            print("No date data found for this agent!")
            return

        print(f"Found {len(date_counts)} dates with data:")
        print(date_counts.head())

        # Find a date with reasonable customer count (less than 60)
        suitable_dates = date_counts[date_counts['customer_count'] <= 60]

        if suitable_dates.empty:
            print("No suitable dates found (all have >60 customers)")
            # Let's still test with the first date
            test_date = date_counts.iloc[0]['RouteDate']
            print(f"Using first available date: {test_date}")
        else:
            test_date = suitable_dates.iloc[0]['RouteDate']
            print(f"Using date with suitable customer count: {test_date}")

        # Get customers for this agent and date
        print(f"\nGetting customers for {test_agent} on {test_date}...")
        customers = optimizer.get_customers_for_agent_date(test_agent, test_date)

        if customers is None or customers.empty:
            print("No customers found for this date!")
            return

        print(f"Found {len(customers)} customers:")
        print(customers[['CustNo', 'latitude', 'longitude', 'custype', 'Name']].head())

        # Check how many have valid coordinates
        valid_coords = customers[
            (customers['latitude'].notna()) &
            (customers['longitude'].notna()) &
            (customers['latitude'] != 0) &
            (customers['longitude'] != 0)
        ]

        print(f"\nCustomers with valid coordinates: {len(valid_coords)}")
        print(f"Customers without coordinates: {len(customers) - len(valid_coords)}")

        if len(valid_coords) > 0:
            print("\nSample customers with coordinates:")
            print(valid_coords[['CustNo', 'latitude', 'longitude', 'Name']].head())

            # Test TSP algorithm
            print(f"\nRunning TSP optimization on {len(valid_coords)} locations...")
            optimized_route = optimizer.solve_tsp_nearest_neighbor(valid_coords)

            print("Optimized route order:")
            print(optimized_route[['CustNo', 'latitude', 'longitude', 'stopno', 'Name']].head(10))

        # Get nearby prospects if needed
        current_count = len(customers)
        if current_count < 60:
            print(f"\nCurrent count ({current_count}) < 60, getting nearby prospects...")
            nearby_prospects = optimizer.get_nearby_prospects(customers, 60)

            if not nearby_prospects.empty:
                print(f"Found {len(nearby_prospects)} nearby prospects:")
                print(nearby_prospects[['CustNo', 'Latitude', 'Longitude', 'distance']].head())
            else:
                print("No nearby prospects found")

        # Test the complete process for this agent and date
        print(f"\n" + "="*50)
        print("Testing complete process...")

        # Clear any existing data for this test
        clear_query = """
        DELETE FROM routeplan_ai
        WHERE salesagent = ? AND routedate = ?
        """
        optimizer.db.execute_query(clear_query, [test_agent, test_date])

        # Process this specific agent and date
        results = []

        # Get existing customers
        existing_customers = customers.copy()
        existing_customers['final_custype'] = 'customer'

        # Get prospects if needed
        nearby_prospects = pd.DataFrame()
        if current_count < 60:
            nearby_prospects = optimizer.get_nearby_prospects(existing_customers, 60)
            if not nearby_prospects.empty:
                nearby_prospects['final_custype'] = 'prospect'

        # Combine all customers
        all_customers = pd.concat([existing_customers, nearby_prospects], ignore_index=True)

        print(f"Total customers to process: {len(all_customers)}")

        # Separate by coordinates
        no_coords = all_customers[
            (all_customers['latitude'].isna()) |
            (all_customers['longitude'].isna()) |
            (all_customers['latitude'] == 0) |
            (all_customers['longitude'] == 0)
        ].copy()
        no_coords['stopno'] = 100

        with_coords = all_customers[
            (all_customers['latitude'].notna()) &
            (all_customers['longitude'].notna()) &
            (all_customers['latitude'] != 0) &
            (all_customers['longitude'] != 0)
        ].copy()

        # Optimize route for locations with coordinates
        if not with_coords.empty:
            print(f"Optimizing route for {len(with_coords)} locations with coordinates...")
            optimized_route = optimizer.solve_tsp_nearest_neighbor(with_coords)
        else:
            optimized_route = pd.DataFrame()

        # Combine results
        final_route = pd.concat([optimized_route, no_coords], ignore_index=True)

        # Prepare data for insertion
        for _, customer in final_route.iterrows():
            route_data = {
                'salesagent': test_agent,
                'custno': customer.get('CustNo'),
                'custype': customer.get('final_custype', customer.get('custype')),
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
                SELECT COUNT(*) as count
                FROM routeplan_ai
                WHERE salesagent = ? AND routedate = ?
                """
                count_result = optimizer.db.execute_query(verify_query, [test_agent, test_date])
                if count_result:
                    print(f"Verified: {count_result[0][0]} records in routeplan_ai table")

                # Show sample results
                sample_query = """
                SELECT TOP 10 salesagent, custno, custype, stopno, latitude, longitude
                FROM routeplan_ai
                WHERE salesagent = ? AND routedate = ?
                ORDER BY stopno
                """
                sample_results = optimizer.db.execute_query_df(sample_query, [test_agent, test_date])
                if sample_results is not None and not sample_results.empty:
                    print("\nSample inserted data:")
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
    test_tsp_with_real_data()