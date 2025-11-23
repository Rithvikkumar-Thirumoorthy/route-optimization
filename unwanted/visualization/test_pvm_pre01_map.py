#!/usr/bin/env python3
"""
Test script to debug PVM-PRE01 map visualization issue
"""

import sys
import os
import pandas as pd
import folium

# Add parent directory to path for imports
sys.path.append('..')

from core.database import DatabaseConnection

def test_pvm_pre01_map():
    """Test PVM-PRE01 map creation"""
    print("TESTING PVM-PRE01 MAP CREATION")
    print("=" * 40)

    db = None
    try:
        # Connect to database
        db = DatabaseConnection()
        db.connect()
        print("Database connected")

        # Get route data (same query as visualization app)
        query = """
        SELECT
            salesagent,
            custno,
            custype,
            latitude,
            longitude,
            stopno,
            routedate,
            barangay,
            barangay_code,
            is_visited,
            CASE
                WHEN latitude IS NULL OR longitude IS NULL THEN 'No Coordinates'
                ELSE 'Has Coordinates'
            END as coord_status
        FROM routeplan_ai
        WHERE salesagent = 'PVM-PRE01' AND routedate = '2025-09-08'
        ORDER BY
            CASE WHEN stopno = 100 THEN 1 ELSE 0 END,
            stopno
        """

        route_data = db.execute_query_df(query)
        print(f"Query executed: {len(route_data)} records found")

        if route_data.empty:
            print("ERROR: No data found!")
            return

        # Filter for valid coordinates (same logic as app)
        valid_coords = route_data.dropna(subset=['latitude', 'longitude'])
        valid_coords = valid_coords[
            (valid_coords['latitude'] != 0) &
            (valid_coords['longitude'] != 0)
        ]

        print(f"Valid coordinates: {len(valid_coords)} locations")
        print(f"  - Customers: {len(valid_coords[valid_coords['custype'] == 'customer'])}")
        print(f"  - Prospects: {len(valid_coords[valid_coords['custype'] == 'prospect'])}")

        if valid_coords.empty:
            print("ERROR: No valid coordinates found!")
            return

        # Calculate map center
        center_lat = valid_coords['latitude'].mean()
        center_lon = valid_coords['longitude'].mean()
        print(f"Map center: {center_lat:.6f}, {center_lon:.6f}")

        # Create test map
        print("Creating Folium map...")
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13,
            tiles='CartoDB positron'
        )

        # Color mapping
        color_map = {
            'customer': 'blue',
            'prospect': 'red',
            'stop100': 'gray'
        }

        # Add markers for each location
        marker_count = 0
        for idx, stop in valid_coords.iterrows():
            # Determine color and marker text
            if stop['stopno'] == 100:
                color = color_map.get('stop100', 'gray')
                marker_text = '100'
            else:
                color = color_map.get(stop['custype'], 'green')
                marker_text = str(stop['stopno'])

            # Create popup text
            popup_text = f"""
            <div style="font-family: Arial; font-size: 12px;">
            <b>Stop #{stop['stopno']}</b><br>
            <b>Customer:</b> {stop['custno']}<br>
            <b>Type:</b> {stop['custype'].title()}<br>
            <b>Coordinates:</b> {stop['latitude']:.6f}, {stop['longitude']:.6f}<br>
            </div>
            """

            # Add marker
            folium.Marker(
                location=[stop['latitude'], stop['longitude']],
                popup=folium.Popup(popup_text, max_width=350),
                tooltip=f"Stop {stop['stopno']}: {stop['custno']} ({stop['custype']})",
                icon=folium.DivIcon(
                    html=f'<div style="background-color: {color}; color: white; '
                         f'border-radius: 50%; width: 25px; height: 25px; '
                         f'text-align: center; line-height: 25px; font-weight: bold; '
                         f'font-size: 10px; border: 2px solid white;">{marker_text}</div>',
                    icon_size=(25, 25),
                    icon_anchor=(12, 12)
                )
            ).add_to(m)
            marker_count += 1

        print(f"✓ Added {marker_count} markers to map")

        # Add route line
        route_coords = []
        sorted_stops = valid_coords[valid_coords['stopno'] != 100].sort_values('stopno')

        for idx, stop in sorted_stops.iterrows():
            route_coords.append([stop['latitude'], stop['longitude']])

        if len(route_coords) > 1:
            folium.PolyLine(
                locations=route_coords,
                color='#8B008B',
                weight=4,
                opacity=0.8,
                popup='TSP Optimized Route'
            ).add_to(m)
            print(f"✓ Added route line with {len(route_coords)} points")

        # Save test map
        output_file = 'test_pvm_pre01_map.html'
        m.save(output_file)
        print(f"✓ Map saved to: {output_file}")

        # Print summary
        print("\nSUMMARY:")
        print(f"- Total records: {len(route_data)}")
        print(f"- Valid coordinates: {len(valid_coords)}")
        print(f"- Markers added: {marker_count}")
        print(f"- Route points: {len(route_coords)}")
        print(f"- Map center: {center_lat:.4f}, {center_lon:.4f}")
        print(f"- Output file: {output_file}")

        # Check coordinate ranges
        lat_min = valid_coords['latitude'].min()
        lat_max = valid_coords['latitude'].max()
        lon_min = valid_coords['longitude'].min()
        lon_max = valid_coords['longitude'].max()

        print(f"- Latitude range: {lat_min:.6f} to {lat_max:.6f}")
        print(f"- Longitude range: {lon_min:.6f} to {lon_max:.6f}")

        # Verify coordinates are in reasonable range for Philippines
        if 4 <= lat_min <= 22 and 4 <= lat_max <= 22 and 116 <= lon_min <= 127 and 116 <= lon_max <= 127:
            print("✓ Coordinates are within Philippines bounds")
        else:
            print("✗ WARNING: Coordinates may be outside Philippines bounds")

        print(f"\nOpen {output_file} in your browser to view the map")

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    test_pvm_pre01_map()