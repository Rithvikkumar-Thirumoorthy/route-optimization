#!/usr/bin/env python3
"""
Route Optimization Visualizer - Streamlit App
Visualize route data from routeplan_ai table using Folium maps
"""

import streamlit as st
import pandas as pd
import folium
from folium import plugins
import sys
import os
from streamlit_folium import st_folium
import numpy as np

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.database import DatabaseConnection
except ImportError:
    st.error("Could not import database module. Please ensure the core folder is accessible.")
    st.stop()

# Page config
st.set_page_config(
    page_title="Route Visualizer",
    page_icon="🗺️",
    layout="wide"
)

@st.cache_data
def get_agents():
    """Get list of available agents from routeplan_ai"""
    try:
        db = DatabaseConnection()
        db.connect()

        query = """
        SELECT DISTINCT salesagent, routedate, COUNT(*) as total_stops
        FROM routeplan_ai
        GROUP BY salesagent, routedate
        ORDER BY salesagent, routedate DESC
        """
        result = db.execute_query_df(query)
        db.close()
        return result if result is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching agents: {e}")
        return pd.DataFrame()

@st.cache_data
def get_route_data(agent_id, route_date):
    """Get route data for specific agent and date"""
    try:
        db = DatabaseConnection()
        db.connect()

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
        WHERE salesagent = ? AND routedate = ?
        ORDER BY stopno
        """
        result = db.execute_query_df(query, params=[agent_id, route_date])
        db.close()
        return result if result is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching route data: {e}")
        return pd.DataFrame()

def create_route_map(route_data):
    """Create Folium map with route visualization"""
    if route_data.empty:
        return None

    # Filter out rows with missing coordinates
    valid_coords = route_data.dropna(subset=['latitude', 'longitude'])

    if valid_coords.empty:
        st.warning("No valid coordinates found for this route")
        return None

    # Calculate map center
    center_lat = valid_coords['latitude'].mean()
    center_lon = valid_coords['longitude'].mean()

    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles='OpenStreetMap'
    )

    # Color mapping for customer types
    color_map = {
        'customer': 'blue',
        'prospect': 'red'
    }

    # Add markers for each stop
    route_coords = []

    for idx, stop in valid_coords.iterrows():
        # Determine marker color and icon
        if stop['stopno'] == 100:
            color = 'gray'
            icon = 'pause'
        else:
            color = color_map.get(stop['custype'], 'green')
            icon = 'user' if stop['custype'] == 'customer' else 'star'
            route_coords.append([stop['latitude'], stop['longitude']])

        # Create popup text
        popup_text = f"""
        <b>Stop #{stop['stopno']}</b><br>
        Customer: {stop['custno']}<br>
        Type: {stop['custype']}<br>
        Barangay Code: {stop['barangay_code']}<br>
        Coordinates: {stop['latitude']:.4f}, {stop['longitude']:.4f}
        """

        # Add marker
        folium.Marker(
            location=[stop['latitude'], stop['longitude']],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=f"Stop {stop['stopno']}: {stop['custno']}",
            icon=folium.Icon(color=color, icon=icon)
        ).add_to(m)

    # Add route line (excluding stop100)
    if len(route_coords) > 1:
        folium.PolyLine(
            locations=route_coords,
            color='purple',
            weight=3,
            opacity=0.8,
            popup='Optimized Route'
        ).add_to(m)

    return m

def create_barangay_summary(route_data):
    """Create barangay summary statistics"""
    if route_data.empty:
        return pd.DataFrame()

    summary = route_data.groupby('barangay_code').agg({
        'custno': 'count',
        'custype': lambda x: ', '.join(x.unique()),
        'latitude': 'first',
        'longitude': 'first'
    }).reset_index()

    summary.columns = ['Barangay Code', 'Total Stops', 'Customer Types', 'Latitude', 'Longitude']
    return summary

def main():
    """Main Streamlit app"""
    st.title("🗺️ Route Optimization Visualizer")
    st.markdown("Visualize optimized sales routes with interactive maps")

    # Sidebar
    st.sidebar.header("🔧 Controls")

    # Get available agents
    agents_df = get_agents()

    if agents_df.empty:
        st.error("No route data found in routeplan_ai table")
        st.stop()

    # Agent selection
    agent_options = []
    for idx, row in agents_df.iterrows():
        agent_options.append(f"{row['salesagent']} ({row['routedate']}) - {row['total_stops']} stops")

    selected_option = st.sidebar.selectbox(
        "Select Agent and Date:",
        agent_options,
        help="Choose an agent and date to visualize their route"
    )

    # Parse selection
    agent_id = selected_option.split(' (')[0]
    route_date = selected_option.split('(')[1].split(')')[0]

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Legend:**")
    st.sidebar.markdown("🔵 **Blue** - Customers")
    st.sidebar.markdown("🔴 **Red** - Prospects")
    st.sidebar.markdown("⚫ **Gray** - Stop100 (No coords)")
    st.sidebar.markdown("🟣 **Purple line** - Route path")

    # Get route data
    route_data = get_route_data(agent_id, route_date)

    if route_data.empty:
        st.error(f"No route data found for agent {agent_id} on {route_date}")
        st.stop()

    # Main content
    tab1, tab2, tab3 = st.tabs(["🗺️ Route Map", "📊 Statistics", "📋 Data Table"])

    with tab1:
        st.subheader(f"Route Map: {agent_id} - {route_date}")

        route_map = create_route_map(route_data)
        if route_map:
            st_folium(route_map, width=1000, height=600)
        else:
            st.warning("Cannot display map - no valid coordinates found")

    with tab2:
        st.subheader("📊 Route Statistics")

        col1, col2, col3, col4 = st.columns(4)

        # Calculate statistics
        total_stops = len(route_data)
        customers = len(route_data[route_data['custype'] == 'customer'])
        prospects = len(route_data[route_data['custype'] == 'prospect'])
        stop100 = len(route_data[route_data['stopno'] == 100])

        with col1:
            st.metric("Total Stops", total_stops)
        with col2:
            st.metric("Customers", customers)
        with col3:
            st.metric("Prospects", prospects)
        with col4:
            st.metric("Stop100", stop100)

        # Barangay breakdown
        st.subheader("Barangay Breakdown")
        barangay_summary = create_barangay_summary(route_data)
        if not barangay_summary.empty:
            st.dataframe(barangay_summary, use_container_width=True)

            # Bar chart of stops per barangay
            barangay_counts = route_data['barangay_code'].value_counts()
            st.bar_chart(barangay_counts)

    with tab3:
        st.subheader("📋 Complete Route Data")

        # Display options
        col1, col2 = st.columns(2)
        with col1:
            show_all = st.checkbox("Show all columns", value=False)
        with col2:
            filter_custype = st.selectbox(
                "Filter by customer type:",
                ["All", "customer", "prospect"],
                index=0
            )

        # Filter data
        display_data = route_data.copy()
        if filter_custype != "All":
            display_data = display_data[display_data['custype'] == filter_custype]

        # Select columns to display
        if show_all:
            st.dataframe(display_data, use_container_width=True)
        else:
            columns = ['stopno', 'custno', 'custype', 'barangay_code', 'latitude', 'longitude']
            st.dataframe(display_data[columns], use_container_width=True)

        # Download button
        csv = display_data.to_csv(index=False)
        st.download_button(
            label="📥 Download route data as CSV",
            data=csv,
            file_name=f"route_{agent_id}_{route_date}.csv",
            mime="text/csv"
        )

    # Footer
    st.markdown("---")
    st.markdown(
        """
        **Route Optimization Visualizer** |
        Built with Streamlit & Folium |
        Data source: routeplan_ai table
        """
    )

if __name__ == "__main__":
    main()