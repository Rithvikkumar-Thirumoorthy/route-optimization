import pandas as pd
import folium
from folium import plugins
import json

# Read the route optimization output
df = pd.read_csv('route_optimization_output.csv')

# Get center coordinates
center_lat = df['latitude'].mean()
center_lon = df['longitude'].mean()

# Create base map
m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=14,
    tiles='OpenStreetMap'
)

# Define colors for different days (cycling through colors)
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
    feature_groups[day] = folium.FeatureGroup(name=f'Day {day}', show=True, overlay=True)

# Process each day
for day in days:
    day_data = df[df['dayno'] == day].sort_values('sequence')
    color = colors[day % len(colors)]

    # Add markers for each store
    for idx, row in day_data.iterrows():
        popup_html = f"""
        <div style="font-family: Arial; width: 200px;">
            <b>Store:</b> {row['store']}<br>
            <b>Day:</b> {row['dayno']}<br>
            <b>Sequence:</b> {row['sequence']}<br>
            <b>Distance to Next:</b> {row['distancetonextstore']:.3f} km<br>
            <b>Coordinates:</b><br>
            {row['latitude']:.6f}, {row['longitude']:.6f}
        </div>
        """

        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=6,
            popup=folium.Popup(popup_html, max_width=250),
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=2,
            tooltip=f"Day {row['dayno']}: {row['store']} (Seq: {row['sequence']})"
        ).add_to(feature_groups[day])

        # Add sequence number label
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            icon=folium.DivIcon(html=f"""
                <div style="
                    font-size: 10px;
                    font-weight: bold;
                    color: white;
                    text-align: center;
                    background-color: {color};
                    border: 1px solid white;
                    border-radius: 50%;
                    width: 20px;
                    height: 20px;
                    line-height: 20px;
                    margin-left: -10px;
                    margin-top: -10px;
                ">{row['sequence']}</div>
            """)
        ).add_to(feature_groups[day])

    # Add routing arrows between consecutive stores
    for i in range(len(day_data) - 1):
        start = day_data.iloc[i]
        end = day_data.iloc[i + 1]

        # Create line with arrow
        folium.PolyLine(
            locations=[
                [start['latitude'], start['longitude']],
                [end['latitude'], end['longitude']]
            ],
            color=color,
            weight=3,
            opacity=0.7,
            tooltip=f"Day {day}: {start['store']} → {end['store']} ({start['distancetonextstore']:.3f} km)"
        ).add_to(feature_groups[day])

        # Add arrow decorator
        plugins.PolyLineTextPath(
            folium.PolyLine(
                locations=[
                    [start['latitude'], start['longitude']],
                    [end['latitude'], end['longitude']]
                ],
                color=color,
                weight=3,
                opacity=0
            ),
            '→',
            repeat=False,
            offset=10,
            attributes={
                'fill': color,
                'font-weight': 'bold',
                'font-size': '20'
            }
        ).add_to(feature_groups[day])

# Add all feature groups to map
for day, fg in feature_groups.items():
    m.add_child(fg)

# Add layer control with checkbox (allows multi-select)
folium.LayerControl(collapsed=False, position='topright').add_to(m)

# Add custom legend
legend_html = f'''
<div style="
    position: fixed;
    top: 10px;
    right: 10px;
    width: 220px;
    background-color: white;
    border: 2px solid grey;
    z-index: 9999;
    font-size: 14px;
    padding: 10px;
    border-radius: 5px;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.3);
">
    <h4 style="margin: 0 0 10px 0;">Route Optimization</h4>
    <p style="margin: 5px 0;"><b>Total Stores:</b> {len(df)}</p>
    <p style="margin: 5px 0;"><b>Total Days:</b> {len(days)}</p>
    <p style="margin: 5px 0;"><b>Total Distance:</b> {df['distancetonextstore'].sum():.2f} km</p>
    <hr style="margin: 10px 0;">
    <p style="margin: 5px 0; font-size: 12px;">
        <i>Use the layer control to select which days to display</i>
    </p>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# Add fullscreen option
plugins.Fullscreen(
    position='topleft',
    title='Enter fullscreen',
    title_cancel='Exit fullscreen',
    force_separate_button=True
).add_to(m)

# Save the map
output_file = 'route_map_interactive.html'
m.save(output_file)

print("=" * 70)
print("INTERACTIVE ROUTE MAP CREATED")
print("=" * 70)
print(f"Output file: {output_file}")
print(f"Total stores: {len(df)}")
print(f"Total days: {len(days)}")
print(f"Total distance: {df['distancetonextstore'].sum():.2f} km")
print("\nFeatures:")
print("  * Multi-select day filter (use layer control)")
print("  * Routing arrows showing direction")
print("  * Sequence numbers on markers")
print("  * Store information in popups")
print("  * Distance tooltips on routes")
print("  * Fullscreen mode")
print("=" * 70)
