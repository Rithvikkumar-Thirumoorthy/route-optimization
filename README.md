# Hierarchical Route Pipeline

A comprehensive route optimization pipeline that processes monthly route plans with a hierarchical structure (Distributor → Agent → Date). This system optimizes delivery routes using TSP (Traveling Salesman Problem) algorithms and intelligently adds prospect customers to routes.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Pipeline Flow](#pipeline-flow)
- [Database Schema](#database-schema)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Overview

The Hierarchical Route Pipeline is designed to optimize monthly route plans by:
- Processing routes in a hierarchical manner (Distributor → Agent → Date)
- Applying TSP optimization using nearest neighbor algorithm
- Intelligently adding prospect customers based on proximity and barangay matching
- Handling both customers with and without coordinates
- Tracking customer types (customer vs prospect)

## Features

### Core Capabilities
- **Hierarchical Processing**: Processes routes by distributor, then agent, then date
- **TSP Optimization**: Uses nearest neighbor heuristic for route optimization
- **Prospect Integration**: Automatically finds and adds nearby prospects to routes
- **Geospatial Matching**: Uses haversine distance for proximity calculations
- **Flexible Configuration**: Supports custom start points, distributor filtering, and batch processing
- **Comprehensive Logging**: Detailed logging with progress tracking

### Route Optimization
- Optimizes routes based on straight-line distances (haversine)
- Supports custom starting points for route optimization
- Handles customers without coordinates (assigned to StopNo 100)
- Maintains route consistency within each distributor-agent-date combination

### Prospect Management
- Searches for prospects within specified radius of existing customers
- Matches prospects by barangay (administrative region)
- Excludes already-visited prospects
- Limits prospect additions per route for balanced workload

## Architecture

```
hierarchical-route-pipeline/
├── src/
│   ├── __init__.py           # Package initialization
│   ├── database.py           # Database connection module
│   └── pipeline.py           # Main pipeline logic
├── logs/                     # Execution logs
├── docs/                     # Additional documentation
├── config.py                 # Configuration management
├── run_pipeline.py           # Main entry point
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
└── README.md                 # This file
```

### Components

#### 1. Database Module (`src/database.py`)
- Manages SQL Server connections using pyodbc
- Supports both pyodbc and SQLAlchemy engines
- Provides query execution methods for both raw results and pandas DataFrames

#### 2. Pipeline Module (`src/pipeline.py`)
- `HierarchicalMonthlyRoutePipelineProcessor`: Main pipeline class
- Methods:
  - `get_hierarchical_structure()`: Retrieves distributor-agent-date combinations
  - `enrich_monthly_plan_data()`: Enriches data with coordinates and customer types
  - `find_nearby_prospects()`: Searches for prospects within radius
  - `solve_tsp_nearest_neighbor()`: Optimizes routes using TSP
  - `process_single_combination()`: Processes one distributor-agent-date combination
  - `run_hierarchical_pipeline()`: Orchestrates entire pipeline execution

## Installation

### Prerequisites
- Python 3.8 or higher
- SQL Server with ODBC Driver 17
- Access to the route optimization database

### Steps

1. **Clone or extract the project**
   ```bash
   cd hierarchical-route-pipeline
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv

   # On Windows
   venv\Scripts\activate

   # On Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   # Copy the example file
   cp .env.example .env

   # Edit .env with your database credentials
   ```

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Database Configuration
DB_SERVER=your-server.database.windows.net
DB_DATABASE=your_database_name
DB_USERNAME=your_username
DB_PASSWORD=your_password
DB_USE_WINDOWS_AUTH=False
```

### Pipeline Configuration

Edit `config.py` to customize pipeline behavior:

```python
# Processing parameters
BATCH_SIZE = 50              # Number of routes to process in batch
MAX_WORKERS = 4              # Maximum parallel workers
MAX_DISTANCE_KM = 5.0        # Maximum distance for prospect search (km)
TARGET_PROSPECTS_PER_ROUTE = 5   # Target number of prospects to add
MIN_ROUTE_SIZE = 60          # Minimum route size before adding prospects

# TSP parameters
START_LAT = None             # Optional: Starting latitude
START_LON = None             # Optional: Starting longitude

# Filtering
DISTRIBUTOR_ID = None        # Optional: Filter by specific distributor
```

## Usage

### Basic Usage

Run the pipeline for all distributors, agents, and dates:

```bash
python run_pipeline.py
```

### Advanced Usage

#### Filter by Distributor
```bash
python run_pipeline.py --distributor-id "DIST001"
```

#### Specify Starting Point
```bash
python run_pipeline.py --start-lat 14.5995 --start-lon 120.9842
```

#### Custom Batch Size and Workers
```bash
python run_pipeline.py --batch-size 100 --max-workers 8
```

#### Test Mode (Process First 10 Combinations)
```bash
python run_pipeline.py --test-mode
```

#### All Options
```bash
python run_pipeline.py \
  --distributor-id "DIST001" \
  --start-lat 14.5995 \
  --start-lon 120.9842 \
  --batch-size 50 \
  --max-workers 4 \
  --max-distance-km 10.0 \
  --test-mode
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--distributor-id` | Filter by specific distributor ID | None (all) |
| `--start-lat` | Starting latitude for TSP | None |
| `--start-lon` | Starting longitude for TSP | None |
| `--batch-size` | Batch size for processing | 50 |
| `--max-workers` | Maximum parallel workers | 4 |
| `--max-distance-km` | Max distance for prospect search (km) | 5.0 |
| `--test-mode` | Process only first 10 combinations | False |

## Pipeline Flow

### High-Level Flow

```
1. Get Hierarchical Structure
   ↓
2. For each (Distributor, Agent, Date):
   ↓
   2a. Enrich with Coordinates
   ↓
   2b. Detect Customer Types
   ↓
   2c. Find Nearby Prospects
   ↓
   2d. Apply TSP Optimization
   ↓
   2e. Update Database
   ↓
3. Final Cleanup (Update Customer Types)
```

### Detailed Pipeline Steps

#### Step 1: Get Hierarchical Structure
- Queries `MonthlyRoutePlan_temp` for all unique (DistributorID, AgentID, RouteDate) combinations
- Orders by DistributorID, AgentID, RouteDate DESC
- Returns structure for iterative processing

#### Step 2: Process Each Combination

##### 2a. Enrich with Coordinates
- Fetches base data from `MonthlyRoutePlan_temp`
- Joins with `customer` table to get latitude, longitude, barangay
- Separates customers with and without coordinates

##### 2b. Detect Customer Types
- Checks if CustNo exists in `customer` table → marks as 'customer'
- Checks if CustNo exists in `prospective` table (tdlinx) → marks as 'prospect'
- Otherwise marks as 'unknown'

##### 2c. Find Nearby Prospects
- If route has < 60 customers, searches for prospects
- Calculates center point of existing customers
- Searches within MAX_DISTANCE_KM radius
- Filters out already-visited prospects
- Limits to target number per route

##### 2d. Apply TSP Optimization
- Combines customers and prospects with coordinates
- Applies nearest neighbor TSP algorithm
- Assigns new StopNo values based on optimal route
- Customers without coordinates get StopNo = 100

##### 2e. Update Database
- Updates existing records with new StopNo and custype
- Inserts new prospect records
- Commits transaction

#### Step 3: Final Cleanup
- Updates custype using JOIN with source tables
- Ensures all records have correct customer type classification

## Database Schema

### Input Tables

#### `MonthlyRoutePlan_temp`
Main table containing route plans to be optimized.

| Column | Type | Description |
|--------|------|-------------|
| CustNo | VARCHAR | Customer/Prospect ID |
| RouteDate | DATE | Scheduled route date |
| Name | VARCHAR | Customer name |
| WD | INT | Weekday indicator |
| SalesManTerritory | VARCHAR | Sales territory |
| AgentID | VARCHAR | Agent identifier |
| RouteName | VARCHAR | Route name |
| DistributorID | VARCHAR | Distributor identifier |
| RouteCode | VARCHAR | Route code |
| SalesOfficeID | VARCHAR | Sales office ID |
| StopNo | INT | Stop sequence number |
| custype | VARCHAR | Customer type (customer/prospect) |

#### `customer`
Contains customer master data with coordinates.

| Column | Type | Description |
|--------|------|-------------|
| CustNo | VARCHAR | Customer ID |
| latitude | DECIMAL | Latitude coordinate |
| longitude | DECIMAL | Longitude coordinate |
| address3 | VARCHAR | Barangay code |

#### `prospective`
Contains prospect data with coordinates.

| Column | Type | Description |
|--------|------|-------------|
| tdlinx | VARCHAR | Prospect ID (maps to CustNo) |
| latitude | DECIMAL | Latitude coordinate |
| longitude | DECIMAL | Longitude coordinate |
| barangay | VARCHAR | Barangay name |
| store_name_nielsen | VARCHAR | Store name |

#### `custvisit`
Tracks customer visits to avoid re-adding prospects.

| Column | Type | Description |
|--------|------|-------------|
| CustID | VARCHAR | Customer/Prospect ID |
| AgentID | VARCHAR | Agent who visited |
| TransDate | DATE | Visit date |

### Output

The pipeline updates `MonthlyRoutePlan_temp` with:
- Optimized `StopNo` values
- Correct `custype` classification
- New prospect records inserted

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed
```
Error: Error connecting to database: ('08001', '[08001] [Microsoft][ODBC Driver 17 for SQL Server]...')
```

**Solution:**
- Verify `.env` file exists and contains correct credentials
- Check network connectivity to database server
- Ensure ODBC Driver 17 is installed
- Verify firewall rules allow connection

#### 2. Import Error: No module named 'database'
```
Import error: No module named 'database'
```

**Solution:**
- Ensure you're running from the project root directory
- Verify `src/__init__.py` exists
- Check Python path includes the src directory

#### 3. No Data Found in MonthlyRoutePlan_temp
```
WARNING - No data found in MonthlyRoutePlan_temp for processing
```

**Solution:**
- Verify the table exists and contains data
- Check date filters in your query
- Ensure DistributorID filter (if used) matches existing data

#### 4. Column Name Errors
```
Error: Invalid column name 'CustNo'
```

**Solution:**
- Verify table schema matches expected structure
- Check recent schema updates for the prospective table
- Update column mappings in pipeline.py if needed

### Debug Mode

Enable detailed logging by editing `pipeline.py`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s',
    ...
)
```

### Performance Tuning

For large datasets:
- Increase `--max-workers` for parallel processing
- Increase `--batch-size` for bulk operations
- Consider processing by distributor separately
- Use database indexes on CustNo, AgentID, RouteDate

## Logs

Logs are automatically created in the `logs/` directory with format:
```
hierarchical_monthly_route_pipeline_YYYYMMDD_HHMMSS.log
```

Each log contains:
- Pipeline start/end times
- Progress updates every 10 combinations
- Error details with stack traces
- Summary statistics

## Contributing

### Code Style
- Follow PEP 8 guidelines
- Use meaningful variable names
- Add docstrings to functions and classes
- Include type hints where appropriate

### Testing
Before submitting changes:
1. Run in test mode: `python run_pipeline.py --test-mode`
2. Verify logs for errors
3. Check database for expected updates
4. Test with different configurations

### Submitting Changes
1. Create a new branch for your feature
2. Make your changes
3. Test thoroughly
4. Submit a pull request with description

## License

Internal use only. All rights reserved.

## Support

For questions or issues:
- Check the logs directory for error details
- Review this README and docs/
- Contact the development team

## Version History

### v1.0.0 (Current)
- Initial project structure
- Hierarchical processing implementation
- TSP optimization with nearest neighbor
- Prospect integration with proximity search
- Comprehensive logging and error handling
- Fixed prospective table column mappings (tdlinx, barangay)
