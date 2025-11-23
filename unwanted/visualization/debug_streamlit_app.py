#!/usr/bin/env python3
"""
Debug version of Streamlit app specifically for PVM-PRE01
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import sys
import os

# Add parent directory to path
sys.path.append('..')

from core.database import DatabaseConnection

def debug_pvm_pre01():
    """Debug PVM-PRE01 specifically"""

    st.title("Debug PVM-PRE01 Map Issue")

    # Connect to database
    db = DatabaseConnection()
    db.connect()

    # Get data with detailed debugging
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
        is_visited
    FROM routeplan_ai
    WHERE salesagent = 'PVM-PRE01' AND routedate = '2025-09-08'
    ORDER BY stopno
    """

    route_data = db.execute_query_df(query)

    st.write(f"**Total records found:** {len(route_data)}")

    if route_data.empty:
        st.error("No data found!")
        return

    # Debug data types
    st.write("**Data types:**")
    st.write(route_data.dtypes)

    # Check coordinate validation step by step
    st.write("**Coordinate validation:**")

    # Step 1: Check for nulls
    lat_nulls = route_data['latitude'].isnull().sum()
    lon_nulls = route_data['longitude'].isnull().sum()
    st.write(f"- Latitude nulls: {lat_nulls}")
    st.write(f"- Longitude nulls: {lon_nulls}")

    # Step 2: Check for zeros
    lat_zeros = (route_data['latitude'] == 0).sum()
    lon_zeros = (route_data['longitude'] == 0).sum()
    st.write(f"- Latitude zeros: {lat_zeros}")
    st.write(f"- Longitude zeros: {lon_zeros}")

    # Step 3: Apply same filtering as visualization
    valid_coords_dropna = route_data.dropna(subset=['latitude', 'longitude'])
    st.write(f"- After dropna(): {len(valid_coords_dropna)}")

    # Step 4: Filter for non-zero coordinates
    valid_coords = valid_coords_dropna[
        (valid_coords_dropna['latitude'] != 0) &
        (valid_coords_dropna['longitude'] != 0)
    ]
    st.write(f"- After removing zeros: {len(valid_coords)}")

    # Show sample of valid coordinates
    if not valid_coords.empty:
        st.write("**Sample valid coordinates:**")
        st.write(valid_coords[['custno', 'custype', 'latitude', 'longitude', 'stopno']].head(10))

        # Calculate map center
        center_lat = valid_coords['latitude'].mean()
        center_lon = valid_coords['longitude'].mean()
        st.write(f"**Map center:** {center_lat:.6f}, {center_lon:.6f}")

        # Create map
        st.write("**Creating map...**")

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13,
            tiles='CartoDB positron'
        )

        # Add markers with debugging
        marker_count = 0
        for idx, stop in valid_coords.iterrows():
            try:
                # Determine color
                color = 'red' if stop['custype'] == 'prospect' else 'blue'

                # Create marker
                folium.Marker(
                    location=[float(stop['latitude']), float(stop['longitude'])],
                    popup=f"Stop {stop['stopno']}: {stop['custno']} ({stop['custype']})",
                    tooltip=f"{stop['custno']} - {stop['custype']}",
                    icon=folium.Icon(color=color)
                ).add_to(m)

                marker_count += 1

            except Exception as e:
                st.error(f"Error adding marker for {stop['custno']}: {e}")

        st.write(f"**Markers added:** {marker_count}")

        # Display the map
        st.write("**Map:**")
        folium_static(m, width=800, height=600)

        # Summary
        customers = len(valid_coords[valid_coords['custype'] == 'customer'])
        prospects = len(valid_coords[valid_coords['custype'] == 'prospect'])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Locations", len(valid_coords))
        with col2:
            st.metric("Customers", customers)
        with col3:
            st.metric("Prospects", prospects)

    else:
        st.error("No valid coordinates found after filtering!")

        # Show what we have
        st.write("**All data (including invalid coordinates):**")
        st.write(route_data[['custno', 'custype', 'latitude', 'longitude', 'stopno']])

    db.close()

if __name__ == "__main__":
    debug_pvm_pre01()