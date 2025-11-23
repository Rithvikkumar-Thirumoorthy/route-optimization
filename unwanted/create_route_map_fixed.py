import pandas as pd
import folium
from folium import plugins
import json

# Read the route optimization output
df = pd.read_csv('route_optimization_output.csv')

print(f"Loading {len(df)} stores across {df['dayno'].nunique()} days...")

# Get center coordinates
center_lat = df['latitude'].mean()
center_lon = df['longitude'].mean()

print(f"Map center: ({center_lat:.6f}, {center_lon:.6f})")

# Create base map
m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=15,
    tiles='OpenStreetMap',
    control_scale=True
)

# Define colors for different days
colors = [
    '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
    '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe',
    '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000',
    '#aaffc3', '#808000', '#ffd8b1', '#000075', '#808080',
    '#ffffff', '#000000'
]

# Group data by day
days = sorted(df['dayno'].unique())

# Create feature groups for each day
feature_groups = {}
for day in days:
    fg = folium.FeatureGroup(name=f'Day {day}')
    feature_groups[day] = fg
    fg.add_to(m)

print(f"Processing {len(days)} days...")

# Process each day
marker_count = 0
route_count = 0

for day in days:
    day_data = df[df['dayno'] == day].sort_values('sequence').reset_index(drop=True)
    color = colors[(day - 1) % len(colors)]

    print(f"  Day {day}: {len(day_data)} stores")

    # Add markers for each store
    for idx, row in day_data.iterrows():
        # Create popup content
        popup_html = f"""
        <b>Store:</b> {row['store']}<br>
        <b>Day:</b> {row['dayno']}<br>
        <b>Sequence:</b> {row['sequence']}<br>
        <b>Distance to Next:</b> {row['distancetonextstore']:.3f} km
        """

        # Add circle marker
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=8,
            popup=folium.Popup(popup_html, max_width=250),
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.8,
            weight=2,
            tooltip=f"Day {day} - Store {row['sequence']}: {row['store']}"
        ).add_to(feature_groups[day])

        marker_count += 1

        # Add text label with sequence number
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            icon=folium.DivIcon(html=f"""
                <div style="
                    font-size: 11px;
                    font-weight: bold;
                    color: #333;
                    text-align: center;
                    background-color: white;
                    border: 2px solid {color};
                    border-radius: 50%;
                    width: 22px;
                    height: 22px;
                    line-height: 18px;
                    box-shadow: 0 0 3px rgba(0,0,0,0.3);
                ">{row['sequence']}</div>
            """)
        ).add_to(feature_groups[day])

    # Add route lines between consecutive stores
    for i in range(len(day_data) - 1):
        start = day_data.iloc[i]
        end = day_data.iloc[i + 1]

        # Draw line
        folium.PolyLine(
            locations=[
                [start['latitude'], start['longitude']],
                [end['latitude'], end['longitude']]
            ],
            color=color,
            weight=4,
            opacity=0.7,
            tooltip=f"Day {day}: {start['sequence']} → {end['sequence']} ({start['distancetonextstore']:.3f} km)"
        ).add_to(feature_groups[day])

        # Add arrow in the middle of the line
        mid_lat = (start['latitude'] + end['latitude']) / 2
        mid_lon = (start['longitude'] + end['longitude']) / 2

        # Calculate angle for arrow
        import math
        angle = math.atan2(
            end['longitude'] - start['longitude'],
            end['latitude'] - start['latitude']
        ) * 180 / math.pi

        folium.Marker(
            location=[mid_lat, mid_lon],
            icon=folium.DivIcon(html=f"""
                <div style="
                    font-size: 20px;
                    color: {color};
                    transform: rotate({angle}deg);
                    text-shadow: 0 0 3px white;
                ">▲</div>
            """)
        ).add_to(feature_groups[day])

        route_count += 1

print(f"\nAdded {marker_count} markers and {route_count} route segments")

# Add layer control - IMPORTANT: positioned on the right
folium.LayerControl(
    collapsed=False,
    position='topright'
).add_to(m)

# Add custom legend with better positioning
legend_html = f'''
<div style="
    position: fixed;
    top: 10px;
    left: 50px;
    width: 250px;
    background-color: white;
    border: 2px solid grey;
    z-index: 9999;
    font-size: 14px;
    padding: 15px;
    border-radius: 5px;
    box-shadow: 3px 3px 10px rgba(0,0,0,0.3);
">
    <h3 style="margin: 0 0 10px 0; color: #333;">Route Optimization Map</h3>
    <hr style="margin: 10px 0;">
    <p style="margin: 5px 0;"><b>Total Stores:</b> {len(df)}</p>
    <p style="margin: 5px 0;"><b>Total Days:</b> {len(days)}</p>
    <p style="margin: 5px 0;"><b>Total Distance:</b> {df['distancetonextstore'].sum():.2f} km</p>
    <hr style="margin: 10px 0;">
    <p style="margin: 5px 0; font-size: 12px; color: #666;">
        <b>Use the Layer Control (top-right) to show/hide days</b>
    </p>
    <p style="margin: 5px 0; font-size: 11px; color: #999;">
        Click markers for details<br>
        Hover routes for distances
    </p>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# Add minimap for better navigation
plugins.MiniMap(toggle_display=True).add_to(m)

# Add fullscreen button
plugins.Fullscreen(
    position='topleft',
    title='Enter fullscreen mode',
    title_cancel='Exit fullscreen mode'
).add_to(m)

# Add locate control to find user's location
plugins.LocateControl(auto_start=False).add_to(m)

# Save the map
output_file = 'route_map_interactive.html'
m.save(output_file)

print("\n" + "=" * 70)
print("INTERACTIVE ROUTE MAP CREATED SUCCESSFULLY")
print("=" * 70)
print(f"Output file: {output_file}")
print(f"\nMap features:")
print(f"  * {marker_count} store markers with sequence numbers")
print(f"  * {route_count} route segments with direction arrows")
print(f"  * {len(days)} day layers (multi-select enabled)")
print(f"  * Layer control panel in top-right corner")
print(f"  * Click markers for store details")
print(f"  * Hover over routes for distance info")
print("\nIMPORTANT: Use the layer control (top-right) to select which days to display!")
print("=" * 70)
