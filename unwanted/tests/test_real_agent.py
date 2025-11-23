#!/usr/bin/env python3
"""
Test Enhanced Route Optimization with Real Sales Agent Data
"""

from enhanced_route_optimizer import EnhancedRouteOptimizer
import pandas as pd

def test_real_agent_enhanced_process():
    """Test enhanced process with real sales agent having <60 stores"""
    print("Testing Enhanced Process with Real Sales Agent")
    print("=" * 60)

    optimizer = None
    try:
        optimizer = EnhancedRouteOptimizer()

        # Find sales agents with <60 stores and good coordinates
        print("Finding suitable sales agents...")

        query = """
        SELECT TOP 10
            r.SalesManTerritory,
            r.RouteDate,
            COUNT(*) as total_stores,
            SUM(CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
                     AND r.latitude != 0 AND r.longitude != 0 THEN 1 ELSE 0 END) as stores_with_coords,
            COUNT(CASE WHEN r.barangay_code IS NOT NULL AND r.barangay_code != '' THEN 1 END) as stores_with_barangay,
            AVG(r.latitude) as avg_lat,
            AVG(r.longitude) as avg_lon
        FROM routedata r
        WHERE r.SalesManTerritory IS NOT NULL
        AND r.RouteDate IS NOT NULL
        GROUP BY r.SalesManTerritory, r.RouteDate
        HAVING COUNT(*) BETWEEN 35 AND 55
        AND SUM(CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
                     AND r.latitude != 0 AND r.longitude != 0 THEN 1 ELSE 0 END) >= 20
        ORDER BY stores_with_coords DESC, total_stores DESC
        """

        suitable_agents = optimizer.db.execute_query_df(query)

        if suitable_agents is None or suitable_agents.empty:
            print("No suitable agents found!")
            return

        print("Found suitable sales agents:")
        print(suitable_agents[['SalesManTerritory', 'RouteDate', 'total_stores', 'stores_with_coords', 'stores_with_barangay']])

        # Pick the best candidate
        best_agent = suitable_agents.iloc[0]
        test_agent = best_agent['SalesManTerritory']
        test_date = best_agent['RouteDate']
        total_stores = best_agent['total_stores']
        stores_with_coords = best_agent['stores_with_coords']

        print(f"\nSelected Agent: {test_agent} on {test_date}")
        print(f"   Total stores: {total_stores}")
        print(f"   Stores with coordinates: {stores_with_coords}")
        print(f"   Need {60 - total_stores} prospects to reach 60")

        # Clear any existing data for this test
        clear_query = """
        DELETE FROM routeplan_ai
        WHERE salesagent = ? AND routedate = ?
        """
        optimizer.db.execute_query(clear_query, [test_agent, test_date])

        # Get existing customers
        print(f"\nGetting customer data...")
        customers = optimizer.get_customers_for_agent_date(test_agent, test_date)

        if customers is None or customers.empty:
            print("No customers found!")
            return

        print(f"Retrieved {len(customers)} customers")

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

        print(f"Breakdown:")
        print(f"  - With coordinates: {len(customers_with_coords)}")
        print(f"  - Without coordinates: {len(customers_without_coords)}")

        if not customers_with_coords.empty:
            print(f"\nCustomer coordinate sample:")
            sample = customers_with_coords[['CustNo', 'latitude', 'longitude', 'barangay_code']].head()
            print(sample)

            # Calculate centroid
            centroid_lat = customers_with_coords['latitude'].mean()
            centroid_lon = customers_with_coords['longitude'].mean()
            print(f"\nCentroid: Lat {centroid_lat:.6f}, Lon {centroid_lon:.6f}")

        # Test prospect selection if we need more
        prospects_added = pd.DataFrame()
        if len(customers) < 60:
            needed_prospects = 60 - len(customers)
            print(f"\nNeed {needed_prospects} prospects to reach 60 total")

            if not customers_with_coords.empty:
                print("Running 2-step prospect selection...")

                # Test our enhanced prospect selection
                prospects_added = optimizer.get_barangay_prospects_2step(
                    customers_with_coords, customers_without_coords, needed_prospects
                )

                if not prospects_added.empty:
                    print(f"Found {len(prospects_added)} prospects!")
                    print("Prospect details:")
                    print(prospects_added[['CustNo', 'Latitude', 'Longitude', 'Barangay_code', 'distance_from_centroid']].head())

                    print(f"\nProspect distance stats:")
                    print(f"  Min: {prospects_added['distance_from_centroid'].min():.3f} km")
                    print(f"  Max: {prospects_added['distance_from_centroid'].max():.3f} km")
                    print(f"  Avg: {prospects_added['distance_from_centroid'].mean():.3f} km")
                else:
                    print("No prospects found in same barangays")

        # Run the complete enhanced process
        print(f"\nRunning complete enhanced optimization process...")

        # Classify types
        customers['final_custype'] = 'customer'
        if not prospects_added.empty:
            prospects_added['final_custype'] = 'prospect'

        # Handle customers without coordinates (stopno = 100)
        if not customers_without_coords.empty:
            customers_without_coords['stopno'] = 100
            print(f"Assigned stopno=100 to {len(customers_without_coords)} stores without coordinates")

        # Combine customers with coords and prospects for TSP
        locations_for_tsp = pd.concat([customers_with_coords, prospects_added], ignore_index=True)

        print(f"TSP input: {len(locations_for_tsp)} locations with coordinates")

        # Run TSP optimization
        optimized_route = pd.DataFrame()
        if not locations_for_tsp.empty:
            print("Running TSP optimization...")
            optimized_route = optimizer.solve_tsp_nearest_neighbor(locations_for_tsp)

            # Calculate distance improvement
            def calculate_total_distance(route_df):
                total = 0
                for i in range(len(route_df) - 1):
                    lat1, lon1 = route_df.iloc[i]['latitude'], route_df.iloc[i]['longitude']
                    lat2, lon2 = route_df.iloc[i + 1]['latitude'], route_df.iloc[i + 1]['longitude']
                    if pd.notna(lat1) and pd.notna(lon1) and pd.notna(lat2) and pd.notna(lon2):
                        dist = optimizer.haversine_distance(lat1, lon1, lat2, lon2)
                        total += dist
                return total

            original_distance = calculate_total_distance(locations_for_tsp)
            optimized_distance = calculate_total_distance(optimized_route)

            print(f"Distance Analysis:")
            print(f"  Original route: {original_distance:.2f} km")
            print(f"  Optimized route: {optimized_distance:.2f} km")
            if original_distance > 0:
                improvement = ((original_distance - optimized_distance) / original_distance) * 100
                print(f"  Improvement: {improvement:.1f}%")

        # Combine final route
        final_route = pd.concat([optimized_route, customers_without_coords], ignore_index=True)

        print(f"\nFinal Route Summary:")
        print(f"  - TSP optimized locations: {len(optimized_route) if not optimized_route.empty else 0}")
        print(f"  - Locations without coords (stopno=100): {len(customers_without_coords)}")
        print(f"  - Total customers: {len(customers)}")
        print(f"  - Total prospects: {len(prospects_added) if not prospects_added.empty else 0}")
        print(f"  - Grand total stops: {len(final_route)}")

        # Prepare data for insertion
        results = []
        for _, location in final_route.iterrows():
            # Handle data types carefully
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

        # Insert into routeplan_ai table
        if results:
            print(f"\nInserting {len(results)} records into routeplan_ai table...")
            success = optimizer.insert_route_plan(results)

            if success:
                print("Data inserted successfully!")

                # Verify and show results
                summary_query = """
                SELECT
                    custype,
                    COUNT(*) as count,
                    MIN(stopno) as min_stop,
                    MAX(stopno) as max_stop,
                    COUNT(CASE WHEN stopno = 100 THEN 1 END) as no_coords_count
                FROM routeplan_ai
                WHERE salesagent = ? AND routedate = ?
                GROUP BY custype
                ORDER BY custype
                """
                summary = optimizer.db.execute_query_df(summary_query, [test_agent, test_date])

                if summary is not None and not summary.empty:
                    print("\nInsertion Summary:")
                    print(summary)

                # Show optimized route sample
                route_sample_query = """
                SELECT TOP 20
                    salesagent, custno, custype, stopno, latitude, longitude, barangay_code
                FROM routeplan_ai
                WHERE salesagent = ? AND routedate = ?
                ORDER BY
                    CASE WHEN stopno = 100 THEN 1 ELSE 0 END,
                    stopno
                """
                route_sample = optimizer.db.execute_query_df(route_sample_query, [test_agent, test_date])

                if route_sample is not None and not route_sample.empty:
                    print("\nSample Route (first 20 stops):")
                    print(route_sample)

                # Final verification
                total_query = """
                SELECT COUNT(*) as total_inserted
                FROM routeplan_ai
                WHERE salesagent = ? AND routedate = ?
                """
                total_result = optimizer.db.execute_query(total_query, [test_agent, test_date])
                if total_result:
                    print(f"\nTotal records verified in database: {total_result[0][0]}")

            else:
                print("Failed to insert data")
        else:
            print("No data to insert")

    except Exception as e:
        print(f"Error during processing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if optimizer:
            optimizer.close()

if __name__ == "__main__":
    test_real_agent_enhanced_process()