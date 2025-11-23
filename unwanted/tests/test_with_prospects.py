#!/usr/bin/env python3
"""
Test Enhanced Route Optimization with Prospect Addition
"""

from enhanced_route_optimizer import EnhancedRouteOptimizer
import pandas as pd

def test_with_prospect_addition():
    """Test the complete process with prospect addition to reach 60 customers"""
    print("Testing Enhanced Route Optimization with Prospect Addition")
    print("=" * 65)

    optimizer = None
    try:
        optimizer = EnhancedRouteOptimizer()

        # Use SK-SAT6 who has 30 customers with coordinates in a barangay with 901 prospects
        test_agent = "SK-SAT6"
        test_date = "2025-09-08"

        print(f"Testing with: {test_agent} on {test_date}")
        print("Expected: 30 customers + 30 prospects = 60 total")

        # Clear any existing data for this test
        clear_query = """
        DELETE FROM routeplan_ai
        WHERE salesagent = ? AND routedate = ?
        """
        optimizer.db.execute_query(clear_query, [test_agent, test_date])

        # Get existing customers
        print(f"\nStep 1: Getting existing customers...")
        customers = optimizer.get_customers_for_agent_date(test_agent, test_date)

        if customers is None or customers.empty:
            print("No customers found!")
            return

        print(f"Found {len(customers)} existing customers")

        # Separate by coordinates
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

        print(f"  - With coordinates: {len(customers_with_coords)}")
        print(f"  - Without coordinates: {len(customers_without_coords)}")

        if not customers_with_coords.empty:
            print(f"\nCustomer sample:")
            sample = customers_with_coords[['CustNo', 'latitude', 'longitude', 'barangay_code']].head()
            print(sample)

            # Calculate centroid
            centroid_lat = customers_with_coords['latitude'].mean()
            centroid_lon = customers_with_coords['longitude'].mean()
            print(f"Customer centroid: Lat {centroid_lat:.6f}, Lon {centroid_lon:.6f}")

        # Step 2: Get prospects using 2-step process
        current_count = len(customers)
        needed_prospects = 60 - current_count
        print(f"\nStep 2: Need {needed_prospects} prospects to reach 60 total")

        prospects_added = pd.DataFrame()
        if current_count < 60 and not customers_with_coords.empty:
            print("Running 2-step prospect selection...")

            prospects_added = optimizer.get_barangay_prospects_2step(
                customers_with_coords, customers_without_coords, needed_prospects
            )

            if not prospects_added.empty:
                print(f"SUCCESS: Found {len(prospects_added)} prospects!")
                print("Prospect sample:")
                print(prospects_added[['CustNo', 'Latitude', 'Longitude', 'Barangay_code', 'distance_from_centroid']].head())

                print(f"\nProspect distance analysis:")
                print(f"  Min distance: {prospects_added['distance_from_centroid'].min():.3f} km")
                print(f"  Max distance: {prospects_added['distance_from_centroid'].max():.3f} km")
                print(f"  Avg distance: {prospects_added['distance_from_centroid'].mean():.3f} km")

                # Show barangay matching
                prospect_barangays = prospects_added['Barangay_code'].unique()
                customer_barangays = customers_with_coords['barangay_code'].unique()
                print(f"\nBarangay matching:")
                print(f"  Customer barangays: {customer_barangays}")
                print(f"  Prospect barangays: {prospect_barangays}")
            else:
                print("No prospects found in same barangays")

        # Step 3: Run complete optimization process
        print(f"\nStep 3: Running complete optimization process...")

        # Classify types
        customers['final_custype'] = 'customer'
        if not prospects_added.empty:
            prospects_added['final_custype'] = 'prospect'

        # Handle customers without coordinates (stopno = 100)
        if not customers_without_coords.empty:
            customers_without_coords['stopno'] = 100
            print(f"  Assigned stopno=100 to {len(customers_without_coords)} customers without coordinates")

        # Combine customers with coords and prospects for TSP
        locations_for_tsp = pd.concat([customers_with_coords, prospects_added], ignore_index=True)

        print(f"  TSP input: {len(locations_for_tsp)} locations with coordinates")
        print(f"    - {len(customers_with_coords)} customers")
        print(f"    - {len(prospects_added)} prospects")

        # Run TSP optimization
        optimized_route = pd.DataFrame()
        if not locations_for_tsp.empty:
            print("  Running TSP optimization...")
            optimized_route = optimizer.solve_tsp_nearest_neighbor(locations_for_tsp)

            # Calculate distance improvement
            def calculate_total_distance(route_df):
                total = 0
                for i in range(len(route_df) - 1):
                    lat1, lon1 = route_df.iloc[i]['latitude'], route_df.iloc[i]['longitude']
                    lat2, lon2 = route_df.iloc[i + 1]['latitude'], route_df.iloc[i]['longitude']
                    if pd.notna(lat1) and pd.notna(lon1) and pd.notna(lat2) and pd.notna(lon2):
                        dist = optimizer.haversine_distance(lat1, lon1, lat2, lon2)
                        total += dist
                return total

            original_distance = calculate_total_distance(locations_for_tsp)
            optimized_distance = calculate_total_distance(optimized_route)

            print(f"  Route optimization results:")
            print(f"    Original route: {original_distance:.2f} km")
            print(f"    Optimized route: {optimized_distance:.2f} km")
            if original_distance > 0:
                improvement = ((original_distance - optimized_distance) / original_distance) * 100
                print(f"    Improvement: {improvement:.1f}%")

        # Combine final route
        final_route = pd.concat([optimized_route, customers_without_coords], ignore_index=True)

        # Step 4: Summary
        print(f"\nStep 4: Final Route Summary")
        total_customers = len([r for _, r in final_route.iterrows() if r.get('final_custype') == 'customer'])
        total_prospects = len([r for _, r in final_route.iterrows() if r.get('final_custype') == 'prospect'])

        print(f"  - Original customers: {total_customers}")
        print(f"  - Added prospects: {total_prospects}")
        print(f"  - Total route stops: {len(final_route)}")
        print(f"  - TSP optimized: {len(optimized_route) if not optimized_route.empty else 0}")
        print(f"  - No coordinates (stopno=100): {len(customers_without_coords)}")

        # Step 5: Insert into database
        print(f"\nStep 5: Inserting route into database...")

        # Prepare data for insertion
        results = []
        for _, location in final_route.iterrows():
            # Handle data types
            latitude = location.get('latitude', location.get('Latitude'))
            longitude = location.get('longitude', location.get('Longitude'))
            stopno = location.get('stopno', 1)

            try:
                latitude = float(latitude) if pd.notna(latitude) else None
            except (ValueError, TypeError):
                latitude = None

            try:
                longitude = float(longitude) if pd.notna(longitude) else None
            except (ValueError, TypeError):
                longitude = None

            try:
                stopno = int(stopno) if pd.notna(stopno) else 1
            except (ValueError, TypeError):
                stopno = 1

            route_data = {
                'salesagent': str(test_agent),
                'custno': str(location.get('CustNo', '')),
                'custype': str(location.get('final_custype', location.get('custype', 'customer'))),
                'latitude': latitude,
                'longitude': longitude,
                'stopno': stopno,
                'routedate': test_date,
                'barangay': str(location.get('barangay_code', location.get('Barangay', ''))),
                'barangay_code': str(location.get('barangay_code', location.get('Barangay_code', ''))),
                'is_visited': 0
            }
            results.append(route_data)

        # Insert results
        if results:
            print(f"  Inserting {len(results)} records...")
            success = optimizer.insert_route_plan(results)

            if success:
                print("  Data inserted successfully!")

                # Step 6: Verification
                print(f"\nStep 6: Database Verification")

                # Summary by customer type
                summary_query = """
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
                summary = optimizer.db.execute_query_df(summary_query, [test_agent, test_date])

                if summary is not None and not summary.empty:
                    print("  Customer type breakdown:")
                    print(summary.to_string(index=False))

                # Sample route
                route_sample_query = """
                SELECT TOP 20
                    custno, custype, stopno, latitude, longitude, barangay_code
                FROM routeplan_ai
                WHERE salesagent = ? AND routedate = ?
                ORDER BY
                    CASE WHEN stopno = 100 THEN 1 ELSE 0 END,
                    stopno
                """
                route_sample = optimizer.db.execute_query_df(route_sample_query, [test_agent, test_date])

                if route_sample is not None and not route_sample.empty:
                    print("\n  Sample route (first 20 stops):")
                    print(route_sample.to_string(index=False))

                # Final count verification
                total_query = """
                SELECT COUNT(*) as total_records
                FROM routeplan_ai
                WHERE salesagent = ? AND routedate = ?
                """
                total_result = optimizer.db.execute_query(total_query, [test_agent, test_date])
                if total_result:
                    print(f"\n  FINAL VERIFICATION: {total_result[0][0]} total records in database")

                print(f"\n{'='*65}")
                print("SUCCESS: Route optimization with prospect addition completed!")
                print(f"{'='*65}")

            else:
                print("  Failed to insert data")
        else:
            print("  No data to insert")

    except Exception as e:
        print(f"Error during processing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if optimizer:
            optimizer.close()

if __name__ == "__main__":
    test_with_prospect_addition()