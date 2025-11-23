#!/usr/bin/env python3
"""
Find barangays near the starting location with available prospects
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

        # Get all prospects with their barangay info
        query = """
        SELECT DISTINCT
            p.barangay_code,
            p.Barangay,
            p.Latitude,
            p.Longitude,
            COUNT(*) as total_prospects
        FROM prospective p
        WHERE p.Latitude IS NOT NULL
            AND p.Longitude IS NOT NULL
            AND p.Latitude != 0
            AND p.Longitude != 0
            AND p.barangay_code IS NOT NULL
            AND p.Barangay IS NOT NULL
        GROUP BY p.barangay_code, p.Barangay, p.Latitude, p.Longitude
        """

        print("\nQuerying database for barangays...")
        df = db.execute_query_df(query)

        if df is None or df.empty:
            print("No barangays found in database!")
            return

        print(f"Found {len(df)} unique barangay locations")

        # Calculate distances and filter
        barangays_with_distance = []

        for _, row in df.iterrows():
            distance = haversine_distance(
                start_lat, start_lon,
                row['Latitude'], row['Longitude']
            )

            if distance <= max_distance_km:
                # Count available prospects (not in routes or visited)
                available_query = f"""
                SELECT COUNT(*) as available_count
                FROM prospective p
                WHERE p.barangay_code = '{row['barangay_code']}'
                    AND p.Latitude IS NOT NULL
                    AND p.Longitude IS NOT NULL
                    AND p.Latitude != 0
                    AND p.Longitude != 0
                    AND NOT EXISTS (
                        SELECT 1 FROM MonthlyRoutePlan_temp mrp
                        WHERE mrp.CustNo = p.CustNo
                    )
                    AND NOT EXISTS (
                        SELECT 1 FROM custvisit cv
                        WHERE cv.CustID = p.CustNo
                    )
                """

                available_df = db.execute_query_df(available_query)
                available_count = available_df['available_count'].iloc[0] if available_df is not None else 0

                if available_count > 0:
                    barangays_with_distance.append({
                        'barangay_code': row['barangay_code'],
                        'barangay_name': row['Barangay'],
                        'distance_km': distance,
                        'latitude': row['Latitude'],
                        'longitude': row['Longitude'],
                        'total_prospects': row['total_prospects'],
                        'available_prospects': available_count
                    })

        # Sort by distance
        barangays_with_distance.sort(key=lambda x: x['distance_km'])

        print("\n" + "=" * 80)
        print(f"BARANGAYS WITHIN {max_distance_km} KM WITH AVAILABLE PROSPECTS")
        print("=" * 80)
        print(f"{'Code':<15} {'Name':<30} {'Dist(km)':<10} {'Total':<8} {'Available':<10}")
        print("-" * 80)

        total_available = 0
        barangay_codes = []

        for i, brgy in enumerate(barangays_with_distance[:20], 1):  # Show top 20
            print(f"{brgy['barangay_code']:<15} {brgy['barangay_name']:<30} "
                  f"{brgy['distance_km']:<10.2f} {brgy['total_prospects']:<8} {brgy['available_prospects']:<10}")
            total_available += brgy['available_prospects']
            barangay_codes.append(brgy['barangay_code'])

        print("-" * 80)
        print(f"Total Barangays Found: {len(barangays_with_distance)}")
        print(f"Total Available Prospects: {total_available}")
        print("=" * 80)

        # Generate command with top barangays
        if barangay_codes:
            print("\n" + "=" * 80)
            print("RECOMMENDED COMMAND (Top 10 barangays):")
            print("=" * 80)
            top_10_codes = ','.join(barangay_codes[:10])
            print(f"""
python run_prospect_only_routes.py \\
  --distributor 11814 \\
  --agent SK-DP4 \\
  --start-date 2025-11-01 \\
  --num-days 30 \\
  --prospects-per-day 60 \\
  --barangays "{top_10_codes}" \\
  --start-lat {start_lat} \\
  --start-lon {start_lon} \\
  --test
""")
            print("=" * 80)

            # Also show just the codes for easy copy-paste
            print("\nBarangay codes (for copy-paste):")
            print(f'"{top_10_codes}"')
            print("=" * 80)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    find_nearby_barangays()
