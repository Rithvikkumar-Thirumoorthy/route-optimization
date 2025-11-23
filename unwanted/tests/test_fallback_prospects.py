#!/usr/bin/env python3
"""
Test Fallback Prospect Selection - Regardless of Barangay
"""

from enhanced_route_optimizer import EnhancedRouteOptimizer
import pandas as pd

def test_fallback_prospects():
    """Test the fallback prospect selection when same barangay has no prospects"""
    print("Testing Fallback Prospect Selection")
    print("=" * 50)

    optimizer = None
    try:
        optimizer = EnhancedRouteOptimizer()

        # Use D201 (which we know has no prospects in barangay 042108023)
        test_agent = "FALLBACK-TEST"
        test_date = "2025-12-31"

        print(f"Test: {test_agent} on {test_date}")
        print("Scenario: 40 customers + 20 fallback prospects (any barangay) = 60 total")

        # Clear test data
        clear_query = """
        DELETE FROM routeplan_ai
        WHERE salesagent = ? AND routedate = ?
        """
        optimizer.db.execute_query(clear_query, [test_agent, test_date])

        # Get 40 real customers from D201 (they have barangay 042108023 which has no prospects)
        print(f"\nStep 1: Getting 40 customers from barangay with no prospects...")
        customer_query = """
        SELECT TOP 40 CustNo, latitude, longitude, barangay_code, custype, Name
        FROM routedata
        WHERE SalesManTerritory = 'D201'
        AND RouteDate = '2025-09-24'
        AND latitude IS NOT NULL AND longitude IS NOT NULL
        AND latitude != 0 AND longitude != 0
        """

        customers = optimizer.db.execute_query_df(customer_query)

        if customers is None or customers.empty:
            print("No customers found!")
            return

        print(f"Retrieved {len(customers)} customers")
        print("Customer sample:")
        print(customers[['CustNo', 'latitude', 'longitude', 'barangay_code']].head())

        # Calculate centroid
        centroid_lat = customers['latitude'].mean()
        centroid_lon = customers['longitude'].mean()
        print(f"Customer centroid: Lat {centroid_lat:.6f}, Lon {centroid_lon:.6f}")

        customer_barangays = customers['barangay_code'].unique()
        print(f"Customer barangays: {customer_barangays}")

        # Step 2: Test prospect selection with fallback
        print(f"\nStep 2: Testing fallback prospect selection...")

        needed_prospects = 60 - len(customers)
        print(f"Need {needed_prospects} prospects to reach 60")

        # This should trigger the fallback since barangay 042108023 has no prospects
        prospects = optimizer.get_barangay_prospects_2step(
            customers, pd.DataFrame(), needed_prospects
        )

        if not prospects.empty:
            print(f"SUCCESS: Found {len(prospects)} fallback prospects!")
            print("Prospect details:")
            print(prospects[['CustNo', 'Latitude', 'Longitude', 'Barangay_code', 'distance_from_centroid']].head(10))

            print(f"\nFallback prospect analysis:")
            print(f"  Min distance: {prospects['distance_from_centroid'].min():.3f} km")
            print(f"  Max distance: {prospects['distance_from_centroid'].max():.3f} km")
            print(f"  Avg distance: {prospects['distance_from_centroid'].mean():.3f} km")

            # Check barangay diversity
            prospect_barangays = prospects['Barangay_code'].value_counts()
            print(f"\nProspect barangay distribution:")
            print(prospect_barangays.head())

            print(f"\nBarangay comparison:")
            print(f"  Customer barangays: {customer_barangays}")
            print(f"  Prospect barangays: {prospects['Barangay_code'].unique()[:5]}...")

        else:
            print("No fallback prospects found")
            return

        # Step 3: Complete process test
        print(f"\nStep 3: Testing complete optimization process...")

        # Mark types
        customers['final_custype'] = 'customer'
        prospects['final_custype'] = 'prospect'

        # Combine for TSP
        all_locations = pd.concat([customers, prospects], ignore_index=True)
        print(f"Total locations for TSP: {len(all_locations)}")

        # Check type distribution
        type_counts = all_locations['final_custype'].value_counts()
        print(f"Type distribution:")
        print(type_counts)

        # Run TSP
        print("Running TSP optimization...")
        optimized_route = optimizer.solve_tsp_nearest_neighbor(all_locations)

        print(f"TSP completed: {len(optimized_route)} optimized stops")

        # Verify type preservation
        optimized_counts = optimized_route['final_custype'].value_counts()
        print(f"Optimized route type distribution:")
        print(optimized_counts)

        # Step 4: Database insertion
        print(f"\nStep 4: Inserting into database...")

        results = []
        for _, location in optimized_route.iterrows():
            # Handle both customer and prospect formats
            latitude = location.get('latitude', location.get('Latitude'))
            longitude = location.get('longitude', location.get('Longitude'))
            stopno = location.get('stopno', 1)

            # Get custype with fallback
            custype_value = location.get('final_custype')
            if pd.isna(custype_value) or custype_value is None:
                custype_value = location.get('custype', 'customer')
            if pd.isna(custype_value) or custype_value is None:
                custype_value = 'customer'

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
                'custype': str(custype_value),
                'latitude': latitude,
                'longitude': longitude,
                'stopno': stopno,
                'routedate': test_date,
                'barangay': str(location.get('barangay_code', location.get('Barangay', ''))),
                'barangay_code': str(location.get('barangay_code', location.get('Barangay_code', ''))),
                'is_visited': 0
            }
            results.append(route_data)

        # Insert all records
        if results:
            success = optimizer.insert_route_plan(results)

            if success:
                print(f"SUCCESS: Inserted {len(results)} records")

                # Step 5: Verification
                print(f"\nStep 5: Final Verification")

                # Check type distribution in database
                verify_query = """
                SELECT
                    custype,
                    COUNT(*) as count,
                    MIN(stopno) as min_stop,
                    MAX(stopno) as max_stop
                FROM routeplan_ai
                WHERE salesagent = ? AND routedate = ?
                GROUP BY custype
                ORDER BY custype
                """
                verify_result = optimizer.db.execute_query_df(verify_query, [test_agent, test_date])

                print("Database verification:")
                print(verify_result.to_string(index=False))

                # Sample mixed route
                sample_query = """
                SELECT TOP 20 custno, custype, stopno, barangay_code
                FROM routeplan_ai
                WHERE salesagent = ? AND routedate = ?
                ORDER BY stopno
                """
                sample_result = optimizer.db.execute_query_df(sample_query, [test_agent, test_date])

                print(f"\nSample route (customers + fallback prospects):")
                print(sample_result.to_string(index=False))

                # Final count
                total_query = """SELECT COUNT(*) as total FROM routeplan_ai WHERE salesagent = ? AND routedate = ?"""
                total_result = optimizer.db.execute_query(total_query, [test_agent, test_date])
                if total_result:
                    total_count = total_result[0][0]
                    print(f"\nFINAL RESULT: {total_count} total stops")

                    if total_count == 60:
                        print("=" * 50)
                        print("SUCCESS: Fallback prospect selection working!")
                        print("- 40 customers + 20 fallback prospects = 60 total")
                        print("- Prospects from different barangays included")
                        print("- All optimized and inserted successfully")
                        print("=" * 50)

            else:
                print("Failed to insert records")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if optimizer:
            optimizer.close()

if __name__ == "__main__":
    test_fallback_prospects()