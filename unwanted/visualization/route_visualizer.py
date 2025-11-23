#!/usr/bin/env python3
"""
Route Optimization Visualizer
Streamlit app to visualize optimized routes using Folium maps
"""

import streamlit as st
import pandas as pd
import folium
from folium import plugins
import sys
import os
from streamlit_folium import folium_static
import numpy as np

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.database import DatabaseConnection
except ImportError:
    st.error("Could not import database module. Please ensure the core folder is accessible.")
    st.stop()

class RouteVisualizer:
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
        """Get list of available agents from monthlyrouteplan_temp"""
        if not self.db:
            return []

        try:
            query = """
            SELECT DISTINCT AgentID as salesagent, RouteDate as routedate, COUNT(*) as total_stops
            FROM monthlyrouteplan_temp
            GROUP BY AgentID, RouteDate
            ORDER BY AgentID, RouteDate DESC
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
                m.AgentID as salesagent,
                m.CustNo as custno,
                m.custype,
                COALESCE(c.latitude, p.latitude) AS latitude,
                COALESCE(c.longitude, p.longitude) AS longitude,
                m.StopNo as stopno,
                m.RouteDate as routedate,
                COALESCE(c.address3, p.barangay_code) AS barangay,
                COALESCE(c.address3, p.barangay_code) AS barangay_code,
                m.Name AS name,
                0 as is_visited
            FROM monthlyrouteplan_temp m
            LEFT JOIN customer c ON m.CustNo = c.custno
            LEFT JOIN prospective p ON m.CustNo = p.tdlinx
            WHERE m.AgentID = '{agent_id}' AND m.RouteDate = '{route_date}'
            ORDER BY m.StopNo
            """
            result = self.db.execute_query_df(query)
            return result if result is not None else pd.DataFrame()
        except Exception as e:
            st.error(f"Error fetching route data: {e}")
            return pd.DataFrame()

    def get_route_data_with_stop100(self, agent_id, route_date):
        """Get route data including Stop100 customers (without coordinates)"""
        if not self.db:
            return pd.DataFrame()

        try:
            query = f"""
            SELECT
                m.AgentID as salesagent,
                m.CustNo as custno,
                m.custype,
                COALESCE(c.latitude, p.latitude) AS latitude,
                COALESCE(c.longitude, p.longitude) AS longitude,
                m.StopNo as stopno,
                m.RouteDate as routedate,
                COALESCE(c.address3, p.barangay_code) AS barangay,
                COALESCE(c.address3, p.barangay_code) AS barangay_code,
                m.Name AS name,
                0 as is_visited,
                CASE
                    WHEN COALESCE(c.latitude, p.latitude) IS NULL OR COALESCE(c.longitude, p.longitude) IS NULL THEN 'No Coordinates'
                    ELSE 'Has Coordinates'
                END as coord_status
            FROM monthlyrouteplan_temp m
            LEFT JOIN customer c ON m.CustNo = c.custno
            LEFT JOIN prospective p ON m.CustNo = p.tdlinx
            WHERE m.AgentID = '{agent_id}' AND m.RouteDate = '{route_date}'
            ORDER BY
                CASE WHEN m.StopNo = 100 THEN 1 ELSE 0 END,
                m.StopNo
            """
            result = self.db.execute_query_df(query)
            return result if result is not None else pd.DataFrame()
        except Exception as e:
            st.error(f"Error fetching complete route data: {e}")
            return pd.DataFrame()

    def calculate_route_distance(self, route_data):
        """Calculate total route distance using Haversine formula"""
        if len(route_data) < 2:
            return 0

        def haversine_distance(lat1, lon1, lat2, lon2):
            from math import radians, cos, sin, asin, sqrt
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * asin(sqrt(a))
            r = 6371  # Radius of earth in kilometers
            return c * r

        total_distance = 0
        for i in range(len(route_data) - 1):
            if route_data.iloc[i]['stopno'] != 100 and route_data.iloc[i+1]['stopno'] != 100:
                dist = haversine_distance(
                    route_data.iloc[i]['latitude'], route_data.iloc[i]['longitude'],
                    route_data.iloc[i+1]['latitude'], route_data.iloc[i+1]['longitude']
                )
                total_distance += dist

        return total_distance

    def create_route_map(self, route_data):
        """Create Folium map with route visualization showing ALL stops"""
        if route_data.empty:
            return None

        # Filter locations with coordinates for map center calculation
        # FIXED: Better coordinate filtering with data type conversion
        route_data = route_data.copy()
        route_data['latitude'] = pd.to_numeric(route_data['latitude'], errors='coerce')
        route_data['longitude'] = pd.to_numeric(route_data['longitude'], errors='coerce')

        valid_coords = route_data[
            (route_data['latitude'].notna()) &
            (route_data['longitude'].notna()) &
            (route_data['latitude'] != 0) &
            (route_data['longitude'] != 0)
        ]

        if valid_coords.empty:
            # If no coordinates available, show error message in Streamlit
            return None

        # Calculate map center based on valid coordinates
        center_lat = valid_coords['latitude'].mean()
        center_lon = valid_coords['longitude'].mean()

        # Create map with better tiles
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13,
            tiles='CartoDB positron'
        )

        # Color mapping for customer types
        color_map = {
            'customer': 'blue',
            'prospect': 'red',
            'stop100': 'gray'
        }

        # Add ALL stops - both with and without coordinates
        stop100_count = 0
        for idx, stop in route_data.iterrows():
            # Check if stop has coordinates
            has_coords = (pd.notna(stop['latitude']) and pd.notna(stop['longitude'])
                         and stop['latitude'] != 0 and stop['longitude'] != 0)

            if has_coords:
                # Stop with coordinates - add as normal marker
                if stop['stopno'] == 100:
                    color = color_map.get('stop100', 'gray')
                    marker_text = '100'
                else:
                    custype_key = stop['custype'] if pd.notna(stop['custype']) else 'customer'
                    color = color_map.get(custype_key, 'green')
                    marker_text = str(stop['stopno'])

                # Create popup text with coordinates
                store_name = stop.get('name', 'N/A') if pd.notna(stop.get('name')) else 'N/A'
                custype = stop['custype'].title() if pd.notna(stop['custype']) else 'N/A'
                barangay = stop['barangay'] if pd.notna(stop['barangay']) else 'N/A'
                barangay_code = stop['barangay_code'] if pd.notna(stop['barangay_code']) else 'N/A'
                popup_text = f"""
                <div style="font-family: Arial; font-size: 12px;">
                <b>Stop #{stop['stopno']}</b><br>
                <b>Customer:</b> {stop['custno']}<br>
                <b>Name:</b> {store_name}<br>
                <b>Type:</b> {custype}<br>
                <b>Barangay:</b> {barangay}<br>
                <b>Barangay Code:</b> {barangay_code}<br>
                <b>Coordinates:</b> {stop['latitude']:.4f}, {stop['longitude']:.4f}<br>
                <b>Visited:</b> {'Yes' if stop['is_visited'] else 'No'}
                </div>
                """

                # Add marker with custom numbering
                tooltip_custype = stop['custype'] if pd.notna(stop['custype']) else 'N/A'
                folium.Marker(
                    location=[stop['latitude'], stop['longitude']],
                    popup=folium.Popup(popup_text, max_width=350),
                    tooltip=f"Stop {stop['stopno']}: {stop['custno']} ({tooltip_custype})",
                    icon=folium.DivIcon(
                        html=f'<div style="background-color: {color}; color: white; '
                             f'border-radius: 50%; width: 25px; height: 25px; '
                             f'text-align: center; line-height: 25px; font-weight: bold; '
                             f'font-size: 10px; border: 2px solid white;">{marker_text}</div>',
                        icon_size=(25, 25),
                        icon_anchor=(12, 12)
                    )
                ).add_to(m)
            else:
                # Stop without coordinates - add to Stop100 list for display
                stop100_count += 1

        # Add optimized route line (only for stops with coordinates, excluding stop100)
        route_coords = []
        sorted_stops = valid_coords[valid_coords['stopno'] != 100].sort_values('stopno')

        for idx, stop in sorted_stops.iterrows():
            route_coords.append([stop['latitude'], stop['longitude']])

        if len(route_coords) > 1:
            # Add route line with arrows
            folium.PolyLine(
                locations=route_coords,
                color='#8B008B',
                weight=4,
                opacity=0.8,
                popup='TSP Optimized Route'
            ).add_to(m)

            # Add direction arrows
            plugins.PolyLineTextPath(
                folium.PolyLine(route_coords, weight=0),
                '  ➤  ',
                repeat=True,
                offset=7,
                attributes={'fill': '#8B008B', 'font-weight': 'bold'}
            ).add_to(m)

        # Enhanced legend with Stop100 information
        stop100_info = f"<p style=\"margin: 0 0 5px 0;\"><span style=\"background-color:orange; color:white; padding:2px 6px; border-radius:10px;\">100</span> Stop100: {stop100_count} customers</p>" if stop100_count > 0 else ""

        legend_html = f'''
        <div style="position: fixed;
                    bottom: 50px; left: 50px; width: 240px; height: 160px;
                    background-color: white; border:2px solid grey; z-index:9999;
                    font-size:12px; padding: 10px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.3);">
        <p style="margin: 0 0 8px 0;"><b>🗺️ Route Legend</b></p>
        <p style="margin: 0 0 5px 0;"><span style="background-color:blue; color:white; padding:2px 6px; border-radius:10px;">●</span> Customer (mapped)</p>
        <p style="margin: 0 0 5px 0;"><span style="background-color:red; color:white; padding:2px 6px; border-radius:10px;">●</span> Prospect (mapped)</p>
        {stop100_info}
        <p style="margin: 0 0 5px 0;"><span style="color:#8B008B; font-weight:bold;">━━━➤</span> TSP Route</p>
        <p style="margin: 0; font-size:10px; color:gray;">Numbers show visit order</p>
        <p style="margin: 0; font-size:10px; color:orange;">Stop100 = No coordinates (not mapped)</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))

        return m

    def create_barangay_heatmap(self, route_data):
        """Create heatmap of stops by barangay"""
        if route_data.empty:
            return None

        # Group by barangay
        barangay_stats = route_data.groupby('barangay_code').agg({
            'custno': 'count',
            'latitude': 'mean',
            'longitude': 'mean'
        }).reset_index()
        barangay_stats.columns = ['barangay_code', 'stop_count', 'avg_lat', 'avg_lon']

        # Calculate map center
        center_lat = barangay_stats['avg_lat'].mean()
        center_lon = barangay_stats['avg_lon'].mean()

        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=11,
            tiles='OpenStreetMap'
        )

        # Add heatmap data
        heat_data = []
        for idx, barangay in barangay_stats.iterrows():
            heat_data.append([
                barangay['avg_lat'],
                barangay['avg_lon'],
                barangay['stop_count']
            ])

        # Add heatmap layer
        plugins.HeatMap(heat_data, radius=20, blur=15, max_zoom=1).add_to(m)

        # Add markers for each barangay
        for idx, barangay in barangay_stats.iterrows():
            folium.CircleMarker(
                location=[barangay['avg_lat'], barangay['avg_lon']],
                radius=barangay['stop_count'] * 2,
                popup=f"Barangay: {barangay['barangay_code']}<br>Stops: {barangay['stop_count']}",
                color='red',
                fill=True,
                fillOpacity=0.6
            ).add_to(m)

        return m

def main():
    """Main Streamlit app"""
    st.set_page_config(
        page_title="Route Optimization Visualizer",
        page_icon="🗺️",
        layout="wide"
    )

    st.title("🗺️ Route Optimization Visualizer")
    st.markdown("Visualize optimized sales routes with interactive maps")

    # Initialize visualizer
    visualizer = RouteVisualizer()

    # Connect to database
    if not visualizer.connect_database():
        st.stop()

    # Sidebar for controls
    st.sidebar.header("🎯 Route Selection")

    # Get available agents
    agents_df = visualizer.get_agents()

    if agents_df.empty:
        st.error("No route data found in monthlyrouteplan_temp table")
        st.stop()

    # Enhanced agent selection with search
    st.sidebar.subheader("Available Agents")

    # Add search filter
    search_agent = st.sidebar.text_input("🔍 Search Agent:", placeholder="Type agent name...")

    # Filter agents based on search
    filtered_agents = agents_df
    if search_agent:
        filtered_agents = agents_df[agents_df['salesagent'].str.contains(search_agent, case=False, na=False)]

    if filtered_agents.empty:
        st.sidebar.error("No agents found matching search criteria")
        st.stop()

    # Create better formatted options
    agent_options = []
    for idx, row in filtered_agents.iterrows():
        agent_options.append(f"{row['salesagent']} ({row['routedate']}) - {row['total_stops']} stops")

    selected_option = st.sidebar.selectbox(
        "Select Agent and Date:",
        agent_options,
        help="Choose an agent to visualize their optimized route"
    )

    # Parse selection
    agent_id = selected_option.split(' (')[0]
    route_date = selected_option.split('(')[1].split(')')[0]

    # Display agent summary in sidebar
    selected_row = agents_df[(agents_df['salesagent'] == agent_id) & (agents_df['routedate'] == route_date)]
    if not selected_row.empty:
        st.sidebar.info(f"""
        **Selected Agent:** {agent_id}
        **Route Date:** {route_date}
        **Total Stops:** {selected_row.iloc[0]['total_stops']}
        """)

    # Visualization options
    st.sidebar.header("📊 Visualization Options")
    show_route_map = st.sidebar.checkbox("🗺️ Route Map", value=True)
    show_heatmap = st.sidebar.checkbox("🔥 Barangay Heatmap", value=False)
    show_statistics = st.sidebar.checkbox("📈 Statistics", value=True)
    show_detailed_table = st.sidebar.checkbox("📋 Detailed Data Table", value=False)

    # Get route data (including Stop100)
    route_data_all = visualizer.get_route_data_with_stop100(agent_id, route_date)
    route_data_mapped = route_data_all.dropna(subset=['latitude', 'longitude'])  # Only for heatmap

    if route_data_all.empty:
        st.error(f"No route data found for agent {agent_id} on {route_date}")
        st.stop()

    # Stop100 summary
    stop100_data = route_data_all[
        (route_data_all['latitude'].isna()) |
        (route_data_all['longitude'].isna()) |
        (route_data_all['stopno'] == 100)
    ]

    # Main content
    col1, col2 = st.columns([2, 1])

    with col1:
        if show_route_map:
            st.subheader(f"🗺️ Route Map: {agent_id} - {route_date}")

            # Pass ALL route data to show complete picture
            route_map = visualizer.create_route_map(route_data_all)
            if route_map:
                folium_static(route_map, width=800, height=600)

            # Show Stop100 summary if exists
            if not stop100_data.empty:
                with st.expander(f"📋 Stop100 Details ({len(stop100_data)} customers without coordinates)"):
                    st.dataframe(
                        stop100_data[['custno', 'custype', 'barangay', 'barangay_code']],
                        use_container_width=True
                    )
                    st.info(f"""
                    **Stop100 Explanation:**
                    These {len(stop100_data)} customers don't have valid GPS coordinates and are assigned to "Stop100".
                    They appear in the route data but cannot be mapped or included in TSP optimization.
                    """)

        if show_heatmap:
            st.subheader("🔥 Barangay Heatmap")
            if not route_data_mapped.empty:
                heatmap = visualizer.create_barangay_heatmap(route_data_mapped)
                if heatmap:
                    folium_static(heatmap, width=800, height=600)
            else:
                st.warning("No coordinates available for heatmap visualization")

    with col2:
        if show_statistics:
            st.subheader("📊 Route Statistics")

            # Enhanced basic stats with all data
            total_stops = len(route_data_all)
            customers = len(route_data_all[route_data_all['custype'] == 'customer'])
            prospects = len(route_data_all[route_data_all['custype'] == 'prospect'])
            stop100 = len(route_data_all[route_data_all['stopno'] == 100])
            with_coords = len(route_data_all[route_data_all['coord_status'] == 'Has Coordinates'])

            # Calculate route distance (only for mapped stops)
            route_distance = visualizer.calculate_route_distance(route_data_mapped)

            # Display metrics with better formatting
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("🎯 Total Stops", total_stops)
                st.metric("👥 Customers", customers)
                st.metric("📍 With Coords", with_coords)

            with col_b:
                st.metric("⭐ Prospects", prospects)
                st.metric("❌ Stop100", stop100)
                st.metric("📏 Route Distance", f"{route_distance:.2f} km" if route_distance > 0 else "N/A")

            # Route efficiency metrics
            if route_distance > 0 and with_coords > 0:
                avg_distance = route_distance / max(1, with_coords - 1)
                st.metric("📈 Avg Distance/Stop", f"{avg_distance:.2f} km")

            # Barangay breakdown with enhanced visualization
            st.subheader("🏘️ Barangay Distribution")
            if not route_data_all['barangay_code'].isna().all():
                barangay_counts = route_data_all['barangay_code'].value_counts().head(10)
                st.bar_chart(barangay_counts)

                # Show barangay summary
                st.write(f"**Coverage:** {len(barangay_counts)} unique barangays")
                if len(barangay_counts) > 0:
                    st.write(f"**Top Barangay:** {barangay_counts.index[0]} ({barangay_counts.iloc[0]} stops)")

            # Customer type pie chart
            st.subheader("📈 Customer Type Distribution")
            type_counts = route_data_all['custype'].value_counts()

            # Create pie chart data
            chart_data = pd.DataFrame({
                'Type': type_counts.index,
                'Count': type_counts.values
            })

            if not chart_data.empty:
                st.bar_chart(chart_data.set_index('Type'))

        # Detailed data table
        if show_detailed_table:
            st.subheader("📋 Complete Route Data")

            # Prepare display data
            display_data = route_data_all[['stopno', 'custno', 'custype', 'barangay_code', 'coord_status', 'is_visited']].copy()
            display_data['is_visited'] = display_data['is_visited'].map({0: '❌ No', 1: '✅ Yes'})

            # Color code the dataframe
            st.dataframe(
                display_data,
                use_container_width=True,
                height=400
            )

            # Download option
            csv = display_data.to_csv(index=False)
            st.download_button(
                label="📥 Download Route Data",
                data=csv,
                file_name=f"route_{agent_id}_{route_date}.csv",
                mime="text/csv"
            )

    # Performance Summary
    st.markdown("---")
    st.subheader("🚀 Route Optimization Summary")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info(f"""
        **Agent Performance**
        🎯 Total Coverage: {total_stops} stops
        📍 Mappable Locations: {with_coords} stops
        📊 Optimization Rate: {(with_coords/total_stops*100):.1f}%
        """)

    with col2:
        if route_distance > 0:
            st.success(f"""
            **Route Efficiency**
            📏 Total Distance: {route_distance:.2f} km
            ⚡ Avg per Stop: {route_distance/max(1,with_coords-1):.2f} km
            🎯 TSP Optimized: Yes
            """)
        else:
            st.warning("**Route Efficiency**\n📍 No coordinates available for route calculation")

    with col3:
        prospect_rate = (prospects / total_stops * 100) if total_stops > 0 else 0
        st.metric("🌟 Prospect Addition", f"{prospect_rate:.1f}%", delta=f"+{prospects} prospects")

    # Enhanced legend and instructions
    st.markdown("---")
    st.markdown("""
    ### 🗺️ Map Legend & Instructions

    **Markers:**
    - 🟦 **Blue numbered circles**: Existing customers (visit order shown)
    - 🟥 **Red numbered circles**: Added prospects (visit order shown)
    - ⚫ **Gray "100" markers**: Stop100 (customers without coordinates)

    **Route Line:**
    - 🟣 **Purple line with arrows**: TSP-optimized route path showing visit sequence
    - ➤ **Direction arrows**: Show optimal travel direction between stops

    **Interactive Features:**
    - 🖱️ **Click markers**: View detailed customer information
    - 🔍 **Zoom/Pan**: Explore different areas of the route
    - 📊 **Toggle options**: Use sidebar to show/hide different visualizations

    **TSP Optimization:** Route sequence calculated using Traveling Salesman Problem algorithm with Haversine distance formula for accurate geographic distances.
    """)

    # Quick tips
    with st.expander("💡 Tips for Using the Visualizer"):
        st.markdown("""
        1. **Search Agents**: Use the search box in the sidebar to quickly find specific agents
        2. **Compare Routes**: Select different agents to compare their route efficiency
        3. **Download Data**: Use the "Detailed Data Table" option to download route information
        4. **Heatmap View**: Enable "Barangay Heatmap" to see geographic distribution of stops
        5. **Performance Metrics**: Check the route distance and efficiency metrics in the statistics panel
        """)

    # Footer with app info
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: gray; font-size: 12px;">
    🗺️ Route Optimization Visualizer | Powered by TSP Algorithm & Haversine Distance Calculations
    <br>📊 Data Source: monthlyrouteplan_temp database | 🌐 Interactive Maps: Folium & Streamlit
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()