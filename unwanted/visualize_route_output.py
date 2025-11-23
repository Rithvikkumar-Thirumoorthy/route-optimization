#!/usr/bin/env python3
"""
Visualize Route Optimization Output CSV on Interactive Map
Reads route_optimization_output.csv and creates Folium map with all clusters/days
"""

import pandas as pd
import folium
from folium import plugins
import os

def create_multi_day_route_map(csv_path):
    """Create interactive map showing all days' routes with different colors"""

    # Read CSV
    print(f"Loading data from: {csv_path}")
    df = pd.read_csv(csv_path)

    print(f"Total stores: {len(df)}")
    print(f"Total days: {df['dayno'].nunique()}")
    print(f"Stores per day: {df.groupby('dayno').size().tolist()}")

    # Calculate map center and bounds
    center_lat = df['latitude'].mean()
    center_lon = df['longitude'].mean()

    # Get bounds for all stores
    min_lat, max_lat = df['latitude'].min(), df['latitude'].max()
    min_lon, max_lon = df['longitude'].min(), df['longitude'].max()

    # Create base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles='CartoDB positron'
    )

    # Fit bounds to show all stores
    m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

    # Color palette for different days (16 colors for 16 days)
    colors = [
        '#FF0000', '#0000FF', '#00FF00', '#FF00FF', '#FFA500',
        '#800080', '#00FFFF', '#FFD700', '#FF1493', '#32CD32',
        '#8B4513', '#4169E1', '#FF69B4', '#2E8B57', '#DC143C',
        '#9370DB', '#FF8C00', '#20B2AA', '#FF6347', '#4682B4'
    ]

    # Create feature groups for each day (for layer control)
    day_groups = {}
    for day_no in sorted(df['dayno'].unique()):
        day_groups[day_no] = folium.FeatureGroup(name=f'Day {int(day_no)} ({len(df[df["dayno"]==day_no])} stores)')

    # Process each day
    for day_no in sorted(df['dayno'].unique()):
        day_data = df[df['dayno'] == day_no].sort_values('sequence')
        color = colors[int(day_no - 1) % len(colors)]

        print(f"\nDay {day_no}: {len(day_data)} stores, Color: {color}")

        # Create route coordinates
        route_coords = []

        # Add markers for each store
        for idx, store in day_data.iterrows():
            route_coords.append([store['latitude'], store['longitude']])

            # Create popup text
            popup_text = f"""
            <div style="font-family: Arial; font-size: 12px; min-width: 200px;">
            <b style="font-size: 14px; color: {color};">Day {store['dayno']} - Stop #{store['sequence']}</b><br>
            <hr style="margin: 5px 0;">
            <b>Store ID:</b> {store['store']}<br>
            <b>Coordinates:</b> {store['latitude']:.6f}, {store['longitude']:.6f}<br>
            <b>Distance to Next:</b> {store['distancetonextstore']:.3f} km<br>
            </div>
            """

            # Create custom marker - add to feature group
            folium.CircleMarker(
                location=[store['latitude'], store['longitude']],
                radius=6,
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=f"Day {store['dayno']}, Stop {store['sequence']}: {store['store']}",
                color='white',
                weight=2,
                fill=True,
                fillColor=color,
                fillOpacity=0.9
            ).add_to(day_groups[day_no])

            # Add sequence number as text label (every 5th store to avoid clutter)
            if store['sequence'] % 5 == 1 or store['sequence'] == len(day_data):
                folium.Marker(
                    location=[store['latitude'], store['longitude']],
                    icon=folium.DivIcon(
                        html=f'<div style="font-size: 10px; font-weight: bold; '
                             f'color: {color}; text-shadow: 1px 1px 2px white;">{int(store["sequence"])}</div>',
                        icon_size=(20, 20),
                        icon_anchor=(10, -5)
                    )
                ).add_to(day_groups[day_no])

        # Add route line for this day - add to feature group
        if len(route_coords) > 1:
            folium.PolyLine(
                locations=route_coords,
                color=color,
                weight=3,
                opacity=0.7,
                popup=f'Day {day_no} Route ({len(day_data)} stores)'
            ).add_to(day_groups[day_no])

            # Add direction arrows - add to feature group
            plugins.PolyLineTextPath(
                folium.PolyLine(route_coords, weight=0),
                '  ➤  ',
                repeat=True,
                offset=6,
                attributes={'fill': color, 'font-weight': 'bold', 'font-size': '12'}
            ).add_to(day_groups[day_no])

    # Add all feature groups to map
    for day_no, group in day_groups.items():
        group.add_to(m)

    # Add layer control to toggle days on/off
    folium.LayerControl(position='topleft', collapsed=False).add_to(m)

    # Create legend showing all days
    legend_items = ""
    for day_no in sorted(df['dayno'].unique()):
        color = colors[int(day_no - 1) % len(colors)]
        day_count = len(df[df['dayno'] == day_no])
        day_distance = df[df['dayno'] == day_no]['distancetonextstore'].sum()
        legend_items += f'<p style="margin: 2px 0;"><span style="background-color:{color}; color:white; padding:2px 8px; border-radius:10px; font-weight:bold;">Day {int(day_no)}</span> {day_count} stores, {day_distance:.2f} km</p>'

    legend_html = f'''
    <div style="position: fixed;
                bottom: 50px; right: 50px; width: 250px; max-height: 500px;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:11px; padding: 12px; border-radius: 5px;
                box-shadow: 0 0 15px rgba(0,0,0,0.3); overflow-y: auto;">
    <p style="margin: 0 0 10px 0; font-size: 14px;"><b>Route Clusters (Days)</b></p>
    <div style="max-height: 400px; overflow-y: auto;">
    {legend_items}
    </div>
    <hr style="margin: 8px 0;">
    <p style="margin: 0; font-size: 10px; color: gray;">
    Total: {len(df)} stores across {df['dayno'].nunique()} days<br>
    Total distance: {df['distancetonextstore'].sum():.2f} km<br>
    Avg per day: {df['distancetonextstore'].sum() / df['dayno'].nunique():.2f} km
    </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    # Add title overlay
    title_html = f'''
    <div style="position: fixed;
                top: 10px; left: 50%; transform: translateX(-50%);
                background-color: rgba(255, 255, 255, 0.95); border:2px solid grey;
                z-index:9999; padding: 10px 20px; border-radius: 5px;
                box-shadow: 0 0 15px rgba(0,0,0,0.3);">
    <h3 style="margin: 0; color: #333;">Route Optimization: {df['dayno'].nunique()} Days, {len(df)} Stores</h3>
    <p style="margin: 5px 0 0 0; font-size: 12px; color: #666;">
    Each color represents a different day. Click markers for details. Arrows show visit direction.
    </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))

    return m

def create_single_day_map(csv_path, day_no):
    """Create map for a specific day only"""

    df = pd.read_csv(csv_path)
    day_data = df[df['dayno'] == day_no].sort_values('sequence')

    if day_data.empty:
        print(f"No data found for Day {day_no}")
        return None

    print(f"\nDay {day_no}: {len(day_data)} stores")

    # Calculate map center
    center_lat = day_data['latitude'].mean()
    center_lon = day_data['longitude'].mean()

    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=14,
        tiles='CartoDB positron'
    )

    # Route coordinates
    route_coords = []

    # Add markers
    for idx, store in day_data.iterrows():
        route_coords.append([store['latitude'], store['longitude']])

        popup_text = f"""
        <div style="font-family: Arial; font-size: 12px;">
        <b style="font-size: 14px; color: #FF0000;">Stop #{store['sequence']}</b><br>
        <hr style="margin: 5px 0;">
        <b>Store ID:</b> {store['store']}<br>
        <b>Coordinates:</b> {store['latitude']:.6f}, {store['longitude']:.6f}<br>
        <b>Distance to Next:</b> {store['distancetonextstore']:.3f} km<br>
        </div>
        """

        folium.Marker(
            location=[store['latitude'], store['longitude']],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=f"Stop {store['sequence']}: {store['store']}",
            icon=folium.DivIcon(
                html=f'<div style="background-color: #FF0000; color: white; '
                     f'border-radius: 50%; width: 30px; height: 30px; '
                     f'text-align: center; line-height: 30px; font-weight: bold; '
                     f'font-size: 12px; border: 3px solid white; '
                     f'box-shadow: 0 0 5px rgba(0,0,0,0.5);">{int(store["sequence"])}</div>',
                icon_size=(30, 30),
                icon_anchor=(15, 15)
            )
        ).add_to(m)

    # Add route line
    if len(route_coords) > 1:
        folium.PolyLine(
            locations=route_coords,
            color='#8B008B',
            weight=4,
            opacity=0.8,
            popup=f'Day {day_no} Route'
        ).add_to(m)

        # Add arrows
        plugins.PolyLineTextPath(
            folium.PolyLine(route_coords, weight=0),
            '  ➤  ',
            repeat=True,
            offset=7,
            attributes={'fill': '#8B008B', 'font-weight': 'bold'}
        ).add_to(m)

    # Stats box
    total_distance = day_data['distancetonextstore'].sum()
    stats_html = f'''
    <div style="position: fixed;
                bottom: 50px; right: 50px; width: 220px;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:12px; padding: 12px; border-radius: 5px;
                box-shadow: 0 0 15px rgba(0,0,0,0.3);">
    <p style="margin: 0 0 8px 0; font-size: 14px;"><b>Day {int(day_no)} Statistics</b></p>
    <p style="margin: 0;"><b>Total Stores:</b> {len(day_data)}</p>
    <p style="margin: 0;"><b>Total Distance:</b> {total_distance:.2f} km</p>
    <p style="margin: 0;"><b>Avg per Store:</b> {total_distance/max(1, len(day_data)-1):.3f} km</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(stats_html))

    return m

def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Visualize Route Optimization Output')
    parser.add_argument('--csv', type=str, default='route_optimization_output.csv',
                       help='Path to CSV file (default: route_optimization_output.csv)')
    parser.add_argument('--day', type=int, default=None,
                       help='Visualize specific day only (default: show all days)')
    parser.add_argument('--output', type=str, default='route_map.html',
                       help='Output HTML file name (default: route_map.html)')

    args = parser.parse_args()

    # Check if CSV exists
    if not os.path.exists(args.csv):
        print(f"Error: CSV file not found: {args.csv}")
        return

    print("=" * 70)
    print("ROUTE OPTIMIZATION VISUALIZER")
    print("=" * 70)

    # Create map
    if args.day:
        print(f"\nCreating map for Day {args.day} only...")
        m = create_single_day_map(args.csv, args.day)
        output_file = f'route_map_day{args.day}.html'
    else:
        print(f"\nCreating map for all days...")
        m = create_multi_day_route_map(args.csv)
        output_file = args.output

    if m is None:
        print("Error: Failed to create map")
        return

    # Save map
    m.save(output_file)

    print("=" * 70)
    print(f"SUCCESS: Map saved to: {output_file}")
    print(f"Full path: {os.path.abspath(output_file)}")
    print("=" * 70)
    print("\nOpen the HTML file in your web browser to view the interactive map!")
    print("Tip: Click on markers to see store details, zoom/pan to explore")

    # Try to open in browser automatically
    try:
        import webbrowser
        webbrowser.open('file://' + os.path.abspath(output_file))
        print("Opening map in your default browser...")
    except:
        print("WARNING: Could not auto-open browser. Please open the HTML file manually.")

if __name__ == "__main__":
    main()
