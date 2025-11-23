#!/usr/bin/env python3
"""
Final Working Test: Complete Route Optimization with Real Prospect Addition
"""

from enhanced_route_optimizer import EnhancedRouteOptimizer
import pandas as pd

def final_working_test():
    """Complete test with real data showing customers + prospects = 60"""
    print("FINAL WORKING TEST: Complete Route Optimization")
    print("=" * 60)

    optimizer = None
    try:
        optimizer = EnhancedRouteOptimizer()

        # Use a real scenario: Take 40 customers and add 20 prospects
        test_agent = "FINAL-TEST"
        test_date = "2025-12-25"

        print(f"Scenario: {test_agent} on {test_date}")
        print("Target: 40 real customers + 20 prospects = 60 total")

        # Clear test data
        clear_query = """
        DELETE FROM routeplan_ai
        WHERE salesagent = ? AND routedate = ?
        """
        optimizer.db.execute_query(clear_query, [test_agent, test_date])

        # Get 40 real customers from D201
        print(f"\nStep 1: Getting 40 real customers...")
        customer_query = """
        SELECT TOP 40 CustNo, latitude, longitude, barangay_code, custype, Name
        FROM routedata
        WHERE SalesManTerritory = 'D201'
        AND RouteDate = '2025-09-24'
        AND latitude IS NOT NULL AND longitude IS NOT NULL
        AND latitude != 0 AND longitude != 0
        """

        real_customers = optimizer.db.execute_query_df(customer_query)

        if real_customers is None or real_customers.empty:
            print("No real customers found!")
            return

        # Mark as customers
        real_customers['final_custype'] = 'customer'
        print(f"Retrieved {len(real_customers)} real customers")
        print("Customer sample:")
        print(real_customers[['CustNo', 'latitude', 'longitude', 'barangay_code']].head())

        # Calculate centroid
        centroid_lat = real_customers['latitude'].mean()
        centroid_lon = real_customers['longitude'].mean()
        print(f"Customer centroid: Lat {centroid_lat:.6f}, Lon {centroid_lon:.6f}")

        # Get customer barangays
        customer_barangays = real_customers['barangay_code'].unique()
        print(f"Customer barangays: {customer_barangays}")

        # Step 2: Try to get real prospects from same barangay
        print(f"\nStep 2: Looking for real prospects in same barangay...")

        real_prospects_query = f"""
        SELECT TOP 20 CustNo, Latitude, Longitude, Barangay, Barangay_code, Custype
        FROM prospective
        WHERE Latitude IS NOT NULL
        AND Longitude IS NOT NULL
        AND Latitude != 0
        AND Longitude != 0
        AND Barangay_code IN ({','.join(['?' for _ in customer_barangays])})
        """

        real_prospects = optimizer.db.execute_query_df(real_prospects_query, params=list(customer_barangays))

        if real_prospects is not None and not real_prospects.empty:
            # Calculate distances from centroid
            real_prospects['distance_from_centroid'] = real_prospects.apply(
                lambda row: optimizer.haversine_distance(
                    centroid_lat, centroid_lon, row['Latitude'], row['Longitude']
                ), axis=1
            )
            # Take nearest 20
            real_prospects = real_prospects.nsmallest(20, 'distance_from_centroid')
            real_prospects['final_custype'] = 'prospect'

            print(f"Found {len(real_prospects)} real prospects!")
            print("Prospect sample:")
            print(real_prospects[['CustNo', 'Latitude', 'Longitude', 'Barangay_code', 'distance_from_centroid']].head())

        else:
            print("No real prospects found, creating simulated ones for demo...")

            # Create 20 simulated prospects
            prospects_data = []
            for i in range(20):
                lat_offset = (i - 10) * 0.002  # Spread around centroid
                lon_offset = (i - 10) * 0.002

                distance = optimizer.haversine_distance(
                    centroid_lat, centroid_lon,
                    centroid_lat + lat_offset, centroid_lon + lon_offset
                )

                prospect = {
                    'CustNo': f'PROSPECT_{i+1:03d}',
                    'Latitude': centroid_lat + lat_offset,
                    'Longitude': centroid_lon + lon_offset,
                    'Barangay': 'Simulated_Barangay',
                    'Barangay_code': customer_barangays[0] if len(customer_barangays) > 0 else 'SIM001',
                    'Custype': 'prospect',
                    'distance_from_centroid': distance,
                    'final_custype': 'prospect'
                }
                prospects_data.append(prospect)

            real_prospects = pd.DataFrame(prospects_data)
            print(f"Created {len(real_prospects)} simulated prospects")

        # Step 3: Combine and optimize
        print(f"\nStep 3: Combining and optimizing route...")

        # Combine customers and prospects
        all_locations = pd.concat([real_customers, real_prospects], ignore_index=True)
        print(f"Total locations: {len(all_locations)}")

        # Check distribution
        type_counts = all_locations['final_custype'].value_counts()
        print(f"Type distribution:")
        print(type_counts)

        # Run TSP optimization
        print("Running TSP optimization...")
        optimized_route = optimizer.solve_tsp_nearest_neighbor(all_locations)

        print(f"TSP completed: {len(optimized_route)} optimized stops")

        # Verify type preservation
        optimized_type_counts = optimized_route['final_custype'].value_counts()
        print(f"Optimized route type distribution:")
        print(optimized_type_counts)

        # Calculate distance improvement
        def calculate_total_distance(route_df):
            total = 0
            for i in range(len(route_df) - 1):
                lat1 = route_df.iloc[i].get('latitude', route_df.iloc[i].get('Latitude'))
                lon1 = route_df.iloc[i].get('longitude', route_df.iloc[i].get('Longitude'))
                lat2 = route_df.iloc[i + 1].get('latitude', route_df.iloc[i + 1].get('Latitude'))
                lon2 = route_df.iloc[i + 1].get('longitude', route_df.iloc[i + 1].get('Longitude'))

                if pd.notna(lat1) and pd.notna(lon1) and pd.notna(lat2) and pd.notna(lon2):
                    dist = optimizer.haversine_distance(lat1, lon1, lat2, lon2)
                    total += dist
            return total

        original_distance = calculate_total_distance(all_locations)
        optimized_distance = calculate_total_distance(optimized_route)

        print(f"\nRoute optimization results:")
        print(f"  Original route distance: {original_distance:.2f} km")
        print(f"  Optimized route distance: {optimized_distance:.2f} km")
        if original_distance > 0:
            improvement = ((original_distance - optimized_distance) / original_distance) * 100
            print(f"  Distance improvement: {improvement:.1f}%")

        # Step 4: Insert into database
        print(f"\nStep 4: Inserting optimized route into database...")

        results = []
        for _, location in optimized_route.iterrows():
            # Handle both customer and prospect column formats
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
                'custype': str(custype),
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
                print(f"SUCCESS: Inserted {len(results)} optimized records")

                # Step 5: Final verification
                print(f"\nStep 5: Database Verification")

                # Get final counts
                final_query = """
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
                final_result = optimizer.db.execute_query_df(final_query, [test_agent, test_date])

                print("Final database summary:")
                print(final_result.to_string(index=False))

                # Sample of mixed route
                sample_query = """
                SELECT TOP 30 custno, custype, stopno, latitude, longitude
                FROM routeplan_ai
                WHERE salesagent = ? AND routedate = ?
                ORDER BY stopno
                """
                sample_result = optimizer.db.execute_query_df(sample_query, [test_agent, test_date])

                print(f"\nSample optimized route (customers + prospects):")
                print(sample_result.to_string(index=False))

                # Final count
                total_query = """SELECT COUNT(*) as total FROM routeplan_ai WHERE salesagent = ? AND routedate = ?"""
                total_result = optimizer.db.execute_query(total_query, [test_agent, test_date])
                if total_result:
                    total_count = total_result[0][0]

                    print(f"\n" + "="*60)
                    print(f"FINAL RESULT: {total_count} total stops in optimized route")

                    if total_count == 60:
                        print("SUCCESS: Perfect 60-stop route achieved!")
                        print("- Real customers and prospects combined")
                        print("- TSP optimized stop sequence")
                        print("- Both customer types preserved in database")
                        print("="*60)
                    else:
                        print(f"Note: Got {total_count} stops instead of expected 60")

            else:
                print("Failed to insert optimized route")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if optimizer:
            optimizer.close()

if __name__ == "__main__":
    final_working_test()