#!/usr/bin/env python3
"""
Test Enhanced Logic with Simulated Prospect Data
"""

import pandas as pd
import numpy as np
from enhanced_route_optimizer import EnhancedRouteOptimizer

def create_simulated_prospects(customers_with_coords, customers_without_coords, needed_count=15):
    """Create simulated prospect data to test the 2-step logic"""

    if customers_with_coords.empty:
        return pd.DataFrame()

    # Calculate centroid
    centroid_lat = customers_with_coords['latitude'].mean()
    centroid_lon = customers_with_coords['longitude'].mean()

    print(f"Centroid: Lat {centroid_lat:.4f}, Lon {centroid_lon:.4f}")

    # Get barangays from existing customers
    barangays = set()
    for _, customer in customers_with_coords.iterrows():
        if pd.notna(customer.get('barangay_code')):
            barangays.add(customer['barangay_code'])

    for _, customer in customers_without_coords.iterrows():
        if pd.notna(customer.get('barangay_code')):
            barangays.add(customer['barangay_code'])

    if not barangays:
        # Create simulated barangay if none exist
        barangays = {'042108023', '042108024', '042108025'}
        print("Using simulated barangays since none found in customer data")

    print(f"Barangays: {list(barangays)}")

    # Create simulated prospects around the centroid in same barangays
    prospects = []

    for i in range(needed_count):
        # Generate random coordinates around centroid (within ~2km radius)
        lat_offset = np.random.normal(0, 0.01)  # ~1km std deviation
        lon_offset = np.random.normal(0, 0.01)

        prospect_lat = centroid_lat + lat_offset
        prospect_lon = centroid_lon + lon_offset

        # Calculate distance from centroid
        from math import radians, cos, sin, asin, sqrt

        def haversine_distance(lat1, lon1, lat2, lon2):
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * asin(sqrt(a))
            r = 6371
            return c * r

        distance = haversine_distance(centroid_lat, centroid_lon, prospect_lat, prospect_lon)

        prospect = {
            'CustNo': f'PROSPECT_{i+1:03d}',
            'Latitude': prospect_lat,
            'Longitude': prospect_lon,
            'Barangay': f'Barangay_{i%3 + 1}',
            'Barangay_code': list(barangays)[i % len(barangays)],
            'Custype': 'prospect',
            'distance_from_centroid': distance
        }
        prospects.append(prospect)

    prospects_df = pd.DataFrame(prospects)

    # Sort by distance and return
    prospects_df = prospects_df.sort_values('distance_from_centroid')

    return prospects_df

def test_simulated_enhanced_logic():
    """Test enhanced logic with simulated prospect data"""
    print("Testing Enhanced Logic with Simulated Prospect Data")
    print("=" * 60)

    optimizer = None
    try:
        optimizer = EnhancedRouteOptimizer()

        # Use an agent we know has some data
        test_agent = "D201"
        test_date = "2025-09-24"

        print(f"Testing with: {test_agent} on {test_date}")

        # Get existing customers
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

        print(f"Customers with coordinates: {len(customers_with_coords)}")
        print(f"Customers without coordinates: {len(customers_without_coords)}")

        if not customers_with_coords.empty:
            print("\nSample customers with coordinates:")
            print(customers_with_coords[['CustNo', 'latitude', 'longitude', 'barangay_code']].head())

        # Simulate scenario: Agent has 45 customers, needs 15 prospects
        # Let's take first 45 customers to simulate
        if len(customers) > 45:
            customers = customers.head(45)
            customers_with_coords = customers_with_coords.head(30)  # 30 with coords
            customers_without_coords = customers_without_coords.head(15)  # 15 without coords

            print(f"\n--- Simulating scenario ---")
            print(f"Agent has 45 customers total")
            print(f"30 customers with coordinates")
            print(f"15 customers without coordinates")
            print(f"Need 15 prospects to reach 60 total")

        # Create simulated prospects
        needed_prospects = 60 - len(customers)
        if needed_prospects > 0 and not customers_with_coords.empty:
            print(f"\nCreating {needed_prospects} simulated prospects...")

            prospects = create_simulated_prospects(
                customers_with_coords, customers_without_coords, needed_prospects
            )

            if not prospects.empty:
                print(f"\nGenerated {len(prospects)} prospects:")
                print(prospects[['CustNo', 'Latitude', 'Longitude', 'Barangay_code', 'distance_from_centroid']].head(10))

                print(f"\nDistance statistics:")
                print(f"Min distance: {prospects['distance_from_centroid'].min():.3f} km")
                print(f"Max distance: {prospects['distance_from_centroid'].max():.3f} km")
                print(f"Avg distance: {prospects['distance_from_centroid'].mean():.3f} km")

                # Test the complete process
                print(f"\n--- Testing Complete Process ---")

                # Clear previous test data
                clear_query = """
                DELETE FROM routeplan_ai
                WHERE salesagent = ? AND routedate = ?
                """
                optimizer.db.execute_query(clear_query, [test_agent, test_date])

                # Classify types
                customers['final_custype'] = 'customer'
                prospects['final_custype'] = 'prospect'

                # Process customers without coordinates (stopno = 100)
                customers_without_coords['stopno'] = 100

                # Combine customers with coords and prospects for TSP
                customers_for_tsp = pd.concat([customers_with_coords, prospects], ignore_index=True)

                print(f"Running TSP on {len(customers_for_tsp)} locations...")

                # Run TSP
                if not customers_for_tsp.empty:
                    optimized_route = optimizer.solve_tsp_nearest_neighbor(customers_for_tsp)

                    # Calculate distance improvement
                    def calculate_route_distance(route_df, optimizer):
                        total_distance = 0
                        for i in range(len(route_df) - 1):
                            lat1, lon1 = route_df.iloc[i]['latitude'], route_df.iloc[i]['longitude']
                            lat2, lon2 = route_df.iloc[i + 1]['latitude'], route_df.iloc[i + 1]['longitude']
                            if pd.notna(lat1) and pd.notna(lon1) and pd.notna(lat2) and pd.notna(lon2):
                                distance = optimizer.haversine_distance(lat1, lon1, lat2, lon2)
                                total_distance += distance
                        return total_distance

                    original_distance = calculate_route_distance(customers_for_tsp, optimizer)
                    optimized_distance = calculate_route_distance(optimized_route, optimizer)

                    print(f"\nDistance comparison:")
                    print(f"Original route: {original_distance:.2f} km")
                    print(f"Optimized route: {optimized_distance:.2f} km")
                    print(f"Improvement: {((original_distance - optimized_distance) / original_distance * 100):.1f}%")

                else:
                    optimized_route = pd.DataFrame()

                # Combine final results
                final_route = pd.concat([optimized_route, customers_without_coords], ignore_index=True)

                print(f"\nFinal route breakdown:")
                print(f"- TSP optimized (customers + prospects): {len(optimized_route) if not optimized_route.empty else 0}")
                print(f"- Customers without coords (stopno=100): {len(customers_without_coords)}")
                print(f"- Total stops: {len(final_route)}")

                # Prepare and insert data
                results = []
                for _, customer in final_route.iterrows():
                    # Handle data type conversions
                    latitude = customer.get('latitude', customer.get('Latitude'))
                    longitude = customer.get('longitude', customer.get('Longitude'))
                    stopno = customer.get('stopno', 1)

                    # Convert to proper types and handle NaN values
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
                        'custno': str(customer.get('CustNo', '')),
                        'custype': str(customer.get('final_custype', customer.get('custype', 'customer'))),
                        'latitude': latitude,
                        'longitude': longitude,
                        'stopno': stopno,
                        'routedate': test_date,
                        'barangay': str(customer.get('barangay_code', customer.get('Barangay', ''))),
                        'barangay_code': str(customer.get('barangay_code', customer.get('Barangay_code', ''))),
                        'is_visited': 0
                    }
                    results.append(route_data)

                # Insert results
                if results:
                    print(f"\nInserting {len(results)} records...")
                    success = optimizer.insert_route_plan(results)

                    if success:
                        print("Data inserted successfully!")

                        # Show summary
                        summary_query = """
                        SELECT
                            custype,
                            COUNT(*) as count,
                            AVG(CASE WHEN stopno != 100 THEN stopno END) as avg_stopno,
                            COUNT(CASE WHEN stopno = 100 THEN 1 END) as no_coords_count
                        FROM routeplan_ai
                        WHERE salesagent = ? AND routedate = ?
                        GROUP BY custype
                        """
                        summary = optimizer.db.execute_query_df(summary_query, [test_agent, test_date])
                        if summary is not None and not summary.empty:
                            print("\nInserted data summary:")
                            print(summary)

                        # Show sample optimized route
                        sample_query = """
                        SELECT TOP 20 salesagent, custno, custype, stopno, latitude, longitude
                        FROM routeplan_ai
                        WHERE salesagent = ? AND routedate = ?
                        ORDER BY
                            CASE WHEN stopno = 100 THEN 1 ELSE 0 END,
                            stopno
                        """
                        sample = optimizer.db.execute_query_df(sample_query, [test_agent, test_date])
                        if sample is not None and not sample.empty:
                            print("\nSample route (first 20 stops):")
                            print(sample)

                    else:
                        print("Failed to insert data")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if optimizer:
            optimizer.close()

if __name__ == "__main__":
    test_simulated_enhanced_logic()