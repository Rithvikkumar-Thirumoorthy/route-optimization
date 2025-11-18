# Project Structure

This document describes the organization and structure of the Hierarchical Route Pipeline project.

## Directory Layout

```
hierarchical-route-pipeline/
├── src/                          # Source code directory
│   ├── __init__.py              # Package initialization
│   ├── database.py              # Database connection module
│   └── pipeline.py              # Main pipeline implementation
│
├── logs/                         # Execution logs (auto-generated)
│   └── hierarchical_monthly_route_pipeline_*.log
│
├── docs/                         # Documentation
│   ├── QUICKSTART.md            # Quick start guide
│   └── PROJECT_STRUCTURE.md     # This file
│
├── config.py                     # Configuration management
├── run_pipeline.py               # Main entry point
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variables template
├── .env                          # Actual credentials (git-ignored)
├── .gitignore                    # Git ignore rules
├── README.md                     # Main documentation
├── CHANGELOG.md                  # Version history
├── setup.bat                     # Windows setup script
└── setup.sh                      # Linux/Mac setup script
```

## Module Descriptions

### Core Modules

#### `src/database.py`
Database connection and query execution module.

**Classes:**
- `DatabaseConnection`: Manages SQL Server connections

**Key Methods:**
- `connect()`: Establishes database connection
- `execute_query()`: Executes SQL and returns raw results
- `execute_query_df()`: Executes SQL and returns pandas DataFrame
- `close()`: Closes database connection

**Dependencies:**
- pyodbc: ODBC database connectivity
- sqlalchemy: Database toolkit for pandas
- pandas: Data manipulation
- python-dotenv: Environment variable management

#### `src/pipeline.py`
Main pipeline implementation with hierarchical processing logic.

**Classes:**
- `HierarchicalMonthlyRoutePipelineProcessor`: Main pipeline class

**Key Methods:**
- `get_hierarchical_structure()`: Gets distributor-agent-date combinations
- `enrich_monthly_plan_data()`: Enriches route data with coordinates
- `find_nearby_prospects()`: Searches for nearby prospects
- `solve_tsp_nearest_neighbor()`: Optimizes route order using TSP
- `process_single_combination()`: Processes one route combination
- `run_hierarchical_pipeline()`: Main execution method
- `update_custype_with_join()`: Updates customer type classification

**Dependencies:**
- pandas, numpy: Data processing
- math: Distance calculations
- datetime, time: Time tracking
- logging: Execution logging
- database: Database connectivity

### Configuration

#### `config.py`
Centralized configuration management.

**Configuration Sections:**
1. **Database Configuration**
   - Connection parameters
   - Authentication settings

2. **Pipeline Processing Parameters**
   - Batch size
   - Worker threads
   - Progress reporting

3. **Route Optimization Parameters**
   - TSP algorithm settings
   - Starting point configuration
   - Stop number assignments

4. **Prospect Search Parameters**
   - Minimum route size
   - Maximum search distance
   - Target prospects per route

5. **Filtering Parameters**
   - Distributor/agent/date filters

6. **Logging Configuration**
   - Log level and format
   - Output destinations

7. **Column Mappings**
   - Table and column name mappings
   - Schema adaptation support

**Functions:**
- `validate_config()`: Validates configuration
- `print_config()`: Prints current configuration

### Entry Points

#### `run_pipeline.py`
Main command-line interface and entry point.

**Functions:**
- `parse_arguments()`: Parses command-line arguments
- `print_banner()`: Displays startup banner
- `print_configuration()`: Shows current configuration
- `main()`: Main execution function

**Command-Line Arguments:**
- `--batch-size`: Processing batch size
- `--max-workers`: Parallel worker threads
- `--start-lat/--start-lon`: TSP starting point
- `--distributor-id`: Distributor filter
- `--max-distance-km`: Prospect search radius
- `--test-mode`: Test mode flag
- `--validate-config`: Configuration validation only

## Data Flow

### Input Data Flow
```
MonthlyRoutePlan_temp (Database)
    ↓
get_hierarchical_structure()
    ↓
[DistributorID, AgentID, RouteDate] combinations
    ↓
process_single_combination() for each
```

### Processing Flow per Combination
```
enrich_monthly_plan_data()
    ↓
customer table (coordinates) ← JOIN → MonthlyRoutePlan_temp
    ↓
prospective table (prospects) → find_nearby_prospects()
    ↓
Combined data with coordinates
    ↓
solve_tsp_nearest_neighbor()
    ↓
Optimized route with new StopNo
    ↓
UPDATE MonthlyRoutePlan_temp
```

### Output Data Flow
```
Updated MonthlyRoutePlan_temp records
    ↓
update_custype_with_join()
    ↓
Final records with correct custype
    ↓
Execution logs → logs/ directory
```

## Database Interaction

### Tables Used

#### Read Operations
- `MonthlyRoutePlan_temp`: Route plan data
- `customer`: Customer master data
- `prospective`: Prospect data
- `custvisit`: Visit history

#### Write Operations
- `MonthlyRoutePlan_temp`: Updates and inserts

### Query Patterns

1. **Hierarchical Structure Query**
   ```sql
   SELECT DISTINCT DistributorID, AgentID, RouteDate
   FROM MonthlyRoutePlan_temp
   ORDER BY DistributorID, AgentID, RouteDate DESC
   ```

2. **Coordinate Enrichment**
   ```sql
   SELECT CustNo, latitude, longitude, address3
   FROM customer
   WHERE CustNo IN (...)
   ```

3. **Prospect Search**
   ```sql
   SELECT tdlinx, latitude, longitude, barangay
   FROM prospective
   WHERE [distance and availability filters]
   ```

4. **Route Update**
   ```sql
   UPDATE MonthlyRoutePlan_temp
   SET StopNo = ?, custype = ?
   WHERE AgentID = ? AND RouteDate = ? AND CustNo = ?
   ```

## Logging

### Log Structure
- **Location**: `logs/` directory
- **Naming**: `hierarchical_monthly_route_pipeline_YYYYMMDD_HHMMSS.log`
- **Format**: `YYYY-MM-DD HH:MM:SS - LEVEL - Message`

### Log Levels
- **INFO**: Normal operation progress
- **WARNING**: Non-critical issues (e.g., no prospects found)
- **ERROR**: Processing errors with stack traces

### Log Contents
1. Pipeline startup information
2. Configuration summary
3. Progress updates (every 10 combinations)
4. Error details with context
5. Final summary statistics

## Extension Points

### Adding New TSP Algorithms

1. Add algorithm implementation in `pipeline.py`:
   ```python
   def solve_tsp_new_algorithm(self, locations_df):
       # Implementation
       pass
   ```

2. Update configuration in `config.py`:
   ```python
   TSP_CONFIG = {
       'algorithm': 'new_algorithm'
   }
   ```

3. Add algorithm selection in pipeline class

### Adding New Prospect Scoring

1. Add scoring function in `pipeline.py`:
   ```python
   def score_prospects(self, prospects_df, customers_df):
       # Calculate scores
       return scored_prospects_df
   ```

2. Integrate into `find_nearby_prospects()` method

### Adding New Data Sources

1. Create new query methods in `database.py`
2. Add column mappings in `config.py`
3. Integrate into `enrich_monthly_plan_data()` method

## Testing

### Unit Testing (Planned)
```
tests/
├── test_database.py
├── test_pipeline.py
├── test_tsp.py
└── test_config.py
```

### Integration Testing
Use `--test-mode` flag to process first 10 combinations:
```bash
python run_pipeline.py --test-mode
```

### Configuration Testing
```bash
python run_pipeline.py --validate-config
```

## Dependencies Graph

```
run_pipeline.py
    ├── config.py
    │   └── python-dotenv
    │
    └── src/pipeline.py
        ├── src/database.py
        │   ├── pyodbc
        │   ├── sqlalchemy
        │   ├── pandas
        │   └── python-dotenv
        │
        ├── pandas
        ├── numpy
        └── math (built-in)
```

## File Purposes

| File | Purpose | Key Features |
|------|---------|--------------|
| `src/database.py` | Database connectivity | Connection pooling, query execution |
| `src/pipeline.py` | Pipeline logic | TSP, prospect search, hierarchical processing |
| `config.py` | Configuration | Centralized settings, validation |
| `run_pipeline.py` | Entry point | CLI, argument parsing, orchestration |
| `.env` | Credentials | Database connection secrets |
| `requirements.txt` | Dependencies | Python package list |
| `README.md` | Documentation | Usage guide, architecture overview |
| `CHANGELOG.md` | Version history | Release notes, breaking changes |
| `setup.bat/.sh` | Setup automation | Installation scripts |

## Best Practices

### Code Organization
1. Keep modules focused and single-purpose
2. Use clear, descriptive names
3. Document complex logic with comments
4. Use type hints for function signatures

### Configuration Management
1. Keep secrets in `.env` file
2. Use `config.py` for application settings
3. Validate configuration on startup
4. Provide sensible defaults

### Error Handling
1. Log errors with context
2. Use try-except blocks appropriately
3. Provide helpful error messages
4. Don't swallow exceptions silently

### Database Interaction
1. Use parameterized queries
2. Handle connection failures gracefully
3. Close connections properly
4. Use transactions for consistency

## Future Enhancements

See [CHANGELOG.md](../CHANGELOG.md) for planned features.
