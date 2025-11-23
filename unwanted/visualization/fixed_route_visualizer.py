#!/usr/bin/env python3
"""
Fixed Route Optimization Visualizer for PVM-PRE01 issue
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import sys
import os

# Add parent directory to path for imports
sys.path.append('..')

from core.database import DatabaseConnection

class FixedRouteVisualizer:
    def __init__(self):
        self.db = None

    def connect_database(self):
        """Connect to database"""
        try:
            self.db = DatabaseConnection()
            self.db.connect()
            return True
        except Exception as e:
            st.error(f"Database connection failed: {e}")
            return False

    def get_agents(self):
        """Get list of available agents from routeplan_ai"""
        if not self.db:
            return []

        try:
            query = """
            SELECT DISTINCT salesagent, routedate, COUNT(*) as total_stops
            FROM routeplan_ai
            GROUP BY salesagent, routedate
            ORDER BY salesagent, routedate DESC
            """
            result = self.db.execute_query_df(query)
            return result if result is not None else pd.DataFrame()
        except Exception as e:
            st.error(f"Error fetching agents: {e}")
            return pd.DataFrame()

    def get_route_data(self, agent_id, route_date):
        """Get route data for specific agent and date"""
        if not self.db:
            return pd.DataFrame()

        try:
            query = f"""
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
            WHERE salesagent = '{agent_id}' AND routedate = '{route_date}'
            ORDER BY stopno
            """
            result = self.db.execute_query_df(query)
            return result if result is not None else pd.DataFrame()
        except Exception as e:
            st.error(f"Error fetching route data: {e}")
            return pd.DataFrame()

    def create_route_map_fixed(self, route_data):
        """Fixed version of route map creation"""
        if route_data.empty:
            return None

        # FIXED: More careful coordinate filtering
        # First, ensure we have numeric data types
        route_data = route_data.copy()
        route_data['latitude'] = pd.to_numeric(route_data['latitude'], errors='coerce')
        route_data['longitude'] = pd.to_numeric(route_data['longitude'], errors='coerce')

        # Filter for valid coordinates with explicit checks
        valid_coords = route_data[
            (route_data['latitude'].notna()) &
            (route_data['longitude'].notna()) &
            (route_data['latitude'] != 0) &
            (route_data['longitude'] != 0) &
            (route_data['latitude'].between(-90, 90)) &  # Valid latitude range
            (route_data['longitude'].between(-180, 180))  # Valid longitude range
        ].copy()

        st.write(f"Debug: Total records: {len(route_data)}")
        st.write(f"Debug: Valid coordinates: {len(valid_coords)}")

        if valid_coords.empty:
            st.error("No valid coordinates found for mapping!")
            return None

        # Calculate map center
        center_lat = valid_coords['latitude'].mean()
        center_lon = valid_coords['longitude'].mean()

        st.write(f"Debug: Map center: {center_lat:.6f}, {center_lon:.6f}")

        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13,
            tiles='CartoDB positron'
        )

        # Color mapping
        color_map = {
            'customer': 'blue',
            'prospect': 'red'
        }

        # Add markers for valid coordinates only
        marker_count = 0
        for idx, stop in valid_coords.iterrows():
            try:
                # Determine color
                color = color_map.get(stop['custype'], 'green')

                # Create popup
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
                    icon=folium.Icon(color=color)
                ).add_to(m)

                marker_count += 1

            except Exception as e:
                st.error(f"Error adding marker for {stop['custno']}: {e}")

        st.write(f"Debug: Markers added: {marker_count}")

        # Add route line for ordered stops (excluding stop 100)
        ordered_stops = valid_coords[valid_coords['stopno'] != 100].sort_values('stopno')
        if len(ordered_stops) > 1:
            route_coords = []
            for idx, stop in ordered_stops.iterrows():
                route_coords.append([stop['latitude'], stop['longitude']])

            folium.PolyLine(
                locations=route_coords,
                color='purple',
                weight=3,
                opacity=0.8,
                popup='Optimized Route'
            ).add_to(m)

        # Add stop100 info if exists
        stop100_data = route_data[route_data['stopno'] == 100]
        if not stop100_data.empty:
            st.info(f"Note: {len(stop100_data)} customers have no coordinates (Stop100)")

        return m

def main():
    """Main Streamlit app"""
    st.set_page_config(
        page_title="Fixed Route Visualizer",
        page_icon="🗺️",
        layout="wide"
    )

    st.title("🗺️ Fixed Route Visualizer - Debug PVM-PRE01")

    # Initialize visualizer
    visualizer = FixedRouteVisualizer()

    # Connect to database
    if not visualizer.connect_database():
        st.stop()

    # Get available agents
    agents_df = visualizer.get_agents()

    if agents_df.empty:
        st.error("No route data found in routeplan_ai table")
        st.stop()

    # Focus on PVM-PRE01 for debugging
    st.sidebar.header("Agent Selection")

    # Check if PVM-PRE01 exists
    pvm_agents = agents_df[agents_df['salesagent'].str.contains('PVM-PRE01', na=False)]

    if not pvm_agents.empty:
        st.sidebar.success("PVM-PRE01 found in database!")

        # Show PVM-PRE01 options
        agent_options = []
        for idx, row in pvm_agents.iterrows():
            agent_options.append(f"{row['salesagent']} ({row['routedate']}) - {row['total_stops']} stops")

        selected_option = st.sidebar.selectbox("Select PVM-PRE01 Route:", agent_options)

        # Parse selection
        agent_id = selected_option.split(' (')[0]
        route_date = selected_option.split('(')[1].split(')')[0]

    else:
        st.sidebar.error("PVM-PRE01 not found!")
        st.sidebar.write("Available agents:")
        st.sidebar.write(agents_df['salesagent'].unique()[:10])
        st.stop()

    # Get route data
    route_data = visualizer.get_route_data(agent_id, route_date)

    if route_data.empty:
        st.error(f"No route data found for {agent_id} on {route_date}")
        st.stop()

    # Display information
    st.subheader(f"Route Analysis: {agent_id} - {route_date}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Records", len(route_data))
    with col2:
        customers = len(route_data[route_data['custype'] == 'customer'])
        st.metric("Customers", customers)
    with col3:
        prospects = len(route_data[route_data['custype'] == 'prospect'])
        st.metric("Prospects", prospects)

    # Show data sample
    if st.checkbox("Show Data Sample"):
        st.write("Sample route data:")
        st.write(route_data[['custno', 'custype', 'latitude', 'longitude', 'stopno']].head(10))

    # Create and display map
    st.subheader("Route Map")
    route_map = visualizer.create_route_map_fixed(route_data)

    if route_map:
        folium_static(route_map, width=800, height=600)
    else:
        st.error("Failed to create map")

if __name__ == "__main__":
    main()