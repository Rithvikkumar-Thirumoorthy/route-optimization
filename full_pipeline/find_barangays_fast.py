#!/usr/bin/env python3
"""
Find barangays near the starting location - FAST VERSION
"""

import sys
import os
from math import radians, cos, sin, asin, sqrt

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on Earth (in km)"""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371
    return c * r

def find_nearby_barangays(start_lat=14.663813, start_lon=121.122687, max_distance_km=10):
    """Find barangays near the starting location with available prospects"""

    db = None
    try:
        print("=" * 80)
        print("FINDING BARANGAYS NEAR STARTING LOCATION")
        print("=" * 80)
        print(f"Starting Location: ({start_lat}, {start_lon})")
        print(f"Maximum Distance: {max_distance_km} km")
        print("=" * 80)

        db = DatabaseConnection()
        db.connect()

        # Simplified query - just get barangays with prospects
        query = """
        SELECT TOP 200
            p.barangay_code,
            p.Barangay,
            AVG(p.Latitude) as avg_lat,
            AVG(p.Longitude) as avg_lon,
            COUNT(*) as prospect_count
        FROM prospective p
        WHERE p.Latitude IS NOT NULL
            AND p.Longitude IS NOT NULL
            AND p.Latitude != 0
            AND p.Longitude != 0
            AND p.barangay_code IS NOT NULL
            AND p.Barangay IS NOT NULL
        GROUP BY p.barangay_code, p.Barangay
        ORDER BY COUNT(*) DESC
        """

        print("\nQuerying database for barangays...")
        df = db.execute_query_df(query)

        if df is None or df.empty:
            print("No barangays found in database!")
            return

        print(f"Found {len(df)} barangays with prospects")

        # Calculate distances and filter
        barangays_near = []

        for _, row in df.iterrows():
            distance = haversine_distance(
                start_lat, start_lon,
                row['avg_lat'], row['avg_lon']
            )

            if distance <= max_distance_km:
                barangays_near.append({
                    'barangay_code': row['barangay_code'],
                    'barangay_name': row['Barangay'],
                    'distance_km': distance,
                    'latitude': row['avg_lat'],
                    'longitude': row['avg_lon'],
                    'prospect_count': row['prospect_count']
                })

        # Sort by distance
        barangays_near.sort(key=lambda x: x['distance_km'])

        print("\n" + "=" * 80)
        print(f"BARANGAYS WITHIN {max_distance_km} KM")
        print("=" * 80)
        print(f"{'Code':<15} {'Name':<35} {'Dist(km)':<10} {'Prospects':<10}")
        print("-" * 80)

        total_prospects = 0
        barangay_codes = []

        for i, brgy in enumerate(barangays_near[:30], 1):  # Show top 30
            print(f"{brgy['barangay_code']:<15} {brgy['barangay_name']:<35} "
                  f"{brgy['distance_km']:<10.2f} {brgy['prospect_count']:<10}")
            total_prospects += brgy['prospect_count']
            barangay_codes.append(brgy['barangay_code'])

        print("-" * 80)
        print(f"Total Barangays Found: {len(barangays_near)}")
        print(f"Total Prospects: {total_prospects}")
        print("=" * 80)

        # Generate command with top barangays
        if barangay_codes:
            # Show different options
            for num_barangays in [5, 10, 15]:
                codes = ','.join(barangay_codes[:num_barangays])
                print(f"\n{'=' * 80}")
                print(f"OPTION {num_barangays//5}: Using TOP {num_barangays} CLOSEST BARANGAYS")
                print("=" * 80)
                print(f'Barangay codes: "{codes}"')
                print(f"\nCommand:")
                print(f"""python run_prospect_only_routes.py --distributor 11814 --agent SK-DP4 --start-date 2025-11-01 --num-days 30 --prospects-per-day 60 --barangays "{codes}" --start-lat {start_lat} --start-lon {start_lon} --test""")

            print("\n" + "=" * 80)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    find_nearby_barangays()
