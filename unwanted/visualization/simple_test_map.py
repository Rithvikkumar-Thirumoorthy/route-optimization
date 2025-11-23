#!/usr/bin/env python3
"""
Simple test for PVM-PRE01 map
"""

import sys
import os
import pandas as pd
import folium

# Add parent directory to path
sys.path.append('..')

from core.database import DatabaseConnection

def test_map():
    print("Testing PVM-PRE01 map creation")
    print("=" * 35)

    db = None
    try:
        # Connect
        db = DatabaseConnection()
        db.connect()
        print("Database connected successfully")

        # Get data
        query = """
        SELECT custno, custype, latitude, longitude, stopno
        FROM routeplan_ai
        WHERE salesagent = 'PVM-PRE01' AND routedate = '2025-09-08'
        AND latitude IS NOT NULL AND longitude IS NOT NULL
        AND latitude != 0 AND longitude != 0
        ORDER BY stopno
        """

        data = db.execute_query_df(query)
        print(f"Found {len(data)} valid coordinates")

        if data.empty:
            print("ERROR: No valid coordinates found")
            return

        # Show sample data
        print("\nSample data:")
        print(data.head()[['custno', 'custype', 'latitude', 'longitude', 'stopno']].to_string())

        # Calculate center
        center_lat = data['latitude'].mean()
        center_lon = data['longitude'].mean()
        print(f"\nMap center: {center_lat:.6f}, {center_lon:.6f}")

        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13
        )

        # Add markers
        for idx, row in data.iterrows():
            color = 'red' if row['custype'] == 'prospect' else 'blue'

            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=f"{row['custno']} ({row['custype']})",
                icon=folium.Icon(color=color)
            ).add_to(m)

        # Save map
        output_file = 'pvm_pre01_test.html'
        m.save(output_file)
        print(f"\nMap saved as: {output_file}")
        print("Open this file in your browser to view the map")

        # Summary
        customers = len(data[data['custype'] == 'customer'])
        prospects = len(data[data['custype'] == 'prospect'])
        print(f"\nSummary:")
        print(f"- Total locations: {len(data)}")
        print(f"- Customers: {customers}")
        print(f"- Prospects: {prospects}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    test_map()