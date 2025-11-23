# Route Optimization Visualizer

Interactive Streamlit app to visualize optimized sales routes using Folium maps.

## Features

🗺️ **Interactive Maps**
- Visualize routes with interactive markers
- Different colors for customers vs prospects
- Route paths with optimized stop sequences
- Popup information for each stop

📊 **Statistics Dashboard**
- Route metrics and KPIs
- Barangay breakdown analysis
- Customer type distribution
- Interactive charts

📋 **Data Management**
- Complete route data tables
- Filtering and sorting options
- CSV export functionality
- Real-time data from routeplan table

## Quick Start

### Method 1: Windows Batch File
```bash
# Double-click run.bat or from command prompt:
run.bat
```

### Method 2: Command Line
```bash
# Install requirements
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

### Method 3: Python
```bash
python -m streamlit run app.py
```

## Data Source

The app visualizes data from the `routeplan` table with these key fields:
- `latitude`, `longitude` - Coordinate data for mapping
- `barangay_code` - Geographic grouping
- `custno` - Customer/prospect identifier
- `custype` - Customer type (customer/prospect)
- `stopno` - Stop sequence number
- `salesagent` - Sales agent identifier
- `routedate` - Route date

## Map Legend

- 🔵 **Blue markers** - Existing customers
- 🔴 **Red markers** - Added prospects
- ⚫ **Gray markers** - Stop100 (customers without coordinates)
- 🟣 **Purple line** - Optimized route path

## App Structure

```
visualization/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── run.bat            # Windows launcher script
└── README.md          # This file
```

## Requirements

- Python 3.7+
- Streamlit 1.28+
- Folium 0.14+
- Access to routeplan database table

## Troubleshooting

1. **Database connection issues**: Ensure `.env` file is configured in parent directory
2. **Import errors**: Make sure `core/database.py` is accessible
3. **No data**: Verify routeplan table has data for selected agents
4. **Map not loading**: Check internet connection for map tiles

## Usage Tips

1. **Select Agent**: Choose from dropdown of available agents and dates
2. **Explore Map**: Click markers for detailed stop information
3. **View Stats**: Check statistics tab for route analysis
4. **Export Data**: Download route data as CSV for further analysis
5. **Filter Data**: Use data table filters to focus on specific information

The app automatically connects to your database and loads available route data for visualization.