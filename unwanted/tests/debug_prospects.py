#!/usr/bin/env python3
"""
Debug Prospect Addition - Simple Test
"""

from enhanced_route_optimizer import EnhancedRouteOptimizer
import pandas as pd

def debug_prospect_addition():
    """Debug why prospects aren't being added to the final route"""
    print("DEBUGGING: Prospect Addition Issue")
    print("=" * 50)

    optimizer = None
    try:
        optimizer = EnhancedRouteOptimizer()

        # Create a simple test with known data
        print("Step 1: Creating test customers (30 customers)")

        # Create 30 test customers with coordinates
        customers_data = []
        base_lat, base_lon = 14.296, 120.894

        for i in range(30):
            customers_data.append({
                'CustNo': f'CUST_{i+1:03d}',
                'latitude': base_lat + (i * 0.001),
                'longitude': base_lon + (i * 0.001),
                'barangay_code': '042108023',
                'custype': 'customer',
                'Name': f'Customer_{i+1}',
                'final_custype': 'customer'
            })

        customers_df = pd.DataFrame(customers_data)
        print(f"Created {len(customers_df)} test customers")
        print("Customer sample:")
        print(customers_df[['CustNo', 'latitude', 'longitude', 'final_custype']].head())

        print(f"\nStep 2: Creating test prospects (30 prospects)")

        # Create 30 test prospects with coordinates
        prospects_data = []
        for i in range(30):
            prospects_data.append({
                'CustNo': f'PROSPECT_{i+1:03d}',
                'Latitude': base_lat + 0.01 + (i * 0.001),  # Note: Capital L for prospects
                'Longitude': base_lon + 0.01 + (i * 0.001), # Note: Capital L for prospects
                'Barangay_code': '042108023',
                'Custype': 'prospect',
                'distance_from_centroid': i * 0.1,
                'final_custype': 'prospect'
            })

        prospects_df = pd.DataFrame(prospects_data)
        print(f"Created {len(prospects_df)} test prospects")
        print("Prospect sample:")
        print(prospects_df[['CustNo', 'Latitude', 'Longitude', 'final_custype']].head())

        print(f"\nStep 3: Combining customers and prospects")

        # Combine for TSP - this is the critical step
        combined_df = pd.concat([customers_df, prospects_df], ignore_index=True)
        print(f"Combined dataset: {len(combined_df)} total locations")
        print("Combined sample:")
        print(combined_df[['CustNo', 'final_custype']].head(10))

        # Check custype distribution
        custype_counts = combined_df['final_custype'].value_counts()
        print(f"\nCustomer type distribution in combined data:")
        print(custype_counts)

        print(f"\nStep 4: Running TSP on combined data")

        # Run TSP on combined data
        optimized_route = optimizer.solve_tsp_nearest_neighbor(combined_df)
        print(f"TSP result: {len(optimized_route)} locations")

        # Check if custype is preserved
        if not optimized_route.empty:
            tsp_custype_counts = optimized_route['final_custype'].value_counts()
            print(f"Customer type distribution after TSP:")
            print(tsp_custype_counts)

            print(f"\nTSP route sample:")
            print(optimized_route[['CustNo', 'final_custype', 'stopno']].head(10))
            print("...")
            print(optimized_route[['CustNo', 'final_custype', 'stopno']].tail(10))

        print(f"\nStep 5: Database insertion test")

        # Clear test data
        test_agent = "DEBUG-TEST"
        test_date = "2025-12-01"

        clear_query = """
        DELETE FROM routeplan_ai
        WHERE salesagent = ? AND routedate = ?
        """
        optimizer.db.execute_query(clear_query, [test_agent, test_date])

        # Prepare data for insertion
        results = []
        for _, location in optimized_route.iterrows():
            # Handle both customer and prospect column names
            latitude = location.get('latitude', location.get('Latitude'))
            longitude = location.get('longitude', location.get('Longitude'))
            stopno = location.get('stopno', 1)
            custype = location.get('final_custype', 'customer')

            try:
                latitude = float(latitude) if pd.notna(latitude) else None
                longitude = float(longitude) if pd.notna(longitude) else None
                stopno = int(stopno) if pd.notna(stopno) else 1
            except (ValueError, TypeError):
                latitude = longitude = None
                stopno = 1

            route_data = {
                'salesagent': str(test_agent),
                'custno': str(location.get('CustNo', '')),
                'custype': str(custype),  # This should preserve customer vs prospect
                'latitude': latitude,
                'longitude': longitude,
                'stopno': stopno,
                'routedate': test_date,
                'barangay': str(location.get('barangay_code', location.get('Barangay', ''))),
                'barangay_code': str(location.get('barangay_code', location.get('Barangay_code', ''))),
                'is_visited': 0
            }
            results.append(route_data)

        print(f"Prepared {len(results)} records for insertion")

        # Check prepared data custype distribution
        prepared_custypes = [r['custype'] for r in results]
        prepared_counts = pd.Series(prepared_custypes).value_counts()
        print(f"Prepared data custype distribution:")
        print(prepared_counts)

        # Insert data
        if results:
            success = optimizer.insert_route_plan(results)

            if success:
                print(f"SUCCESS: Inserted {len(results)} records")

                # Verify in database
                verify_query = """
                SELECT custype, COUNT(*) as count
                FROM routeplan_ai
                WHERE salesagent = ? AND routedate = ?
                GROUP BY custype
                ORDER BY custype
                """
                verify_result = optimizer.db.execute_query_df(verify_query, [test_agent, test_date])

                print(f"\nDatabase verification:")
                print(verify_result)

                # Show sample records
                sample_query = """
                SELECT TOP 20 custno, custype, stopno
                FROM routeplan_ai
                WHERE salesagent = ? AND routedate = ?
                ORDER BY stopno
                """
                sample_result = optimizer.db.execute_query_df(sample_query, [test_agent, test_date])

                print(f"\nSample database records:")
                print(sample_result)

            else:
                print("FAILED to insert data")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if optimizer:
            optimizer.close()

if __name__ == "__main__":
    debug_prospect_addition()