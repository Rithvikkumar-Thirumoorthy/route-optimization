# Quick Start Guide

Get the Hierarchical Route Pipeline up and running in 5 minutes.

## Prerequisites

- Python 3.8 or higher
- SQL Server access with ODBC Driver 17
- Database credentials

## Installation Steps

### 1. Set Up Python Environment

```bash
# Navigate to project directory
cd hierarchical-route-pipeline

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Database Connection

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your database credentials
# Use your favorite text editor (notepad, vim, nano, etc.)
notepad .env  # Windows
nano .env     # Linux/Mac
```

Update the `.env` file with your credentials:
```env
DB_SERVER=your-server.database.windows.net
DB_DATABASE=your_database_name
DB_USERNAME=your_username
DB_PASSWORD=your_password
DB_USE_WINDOWS_AUTH=False
```

### 3. Verify Configuration

```bash
# Test database connection
python -c "from src.database import DatabaseConnection; db = DatabaseConnection(); db.connect()"

# Should output:
# Connecting to: your-server.database.windows.net, Database: your_database_name
# Database connection successful!
```

### 4. Run the Pipeline

```bash
# Run with default settings
python run_pipeline.py

# Or run in test mode first (processes only 10 combinations)
python run_pipeline.py --test-mode
```

## Common Use Cases

### Run for Specific Distributor
```bash
python run_pipeline.py --distributor-id "DIST001"
```

### Specify Starting Point for Routes
```bash
python run_pipeline.py --start-lat 14.5995 --start-lon 120.9842
```

### Adjust Performance Settings
```bash
# For large datasets
python run_pipeline.py --batch-size 100 --max-workers 8
```

### Expand Prospect Search Radius
```bash
python run_pipeline.py --max-distance-km 10.0
```

## Checking Results

### 1. Review Logs
```bash
# Logs are saved in the logs/ directory
cd logs
ls -lt  # Linux/Mac
dir /O-D  # Windows

# View the most recent log
# Linux/Mac:
tail -f hierarchical_monthly_route_pipeline_*.log

# Windows:
type hierarchical_monthly_route_pipeline_*.log
```

### 2. Query Database
```sql
-- Check updated routes
SELECT TOP 100
    DistributorID,
    AgentID,
    RouteDate,
    CustNo,
    StopNo,
    custype,
    Name
FROM MonthlyRoutePlan_temp
ORDER BY DistributorID, AgentID, RouteDate, StopNo;

-- Check customer type distribution
SELECT
    custype,
    COUNT(*) as count,
    COUNT(DISTINCT AgentID) as agents,
    COUNT(DISTINCT DistributorID) as distributors
FROM MonthlyRoutePlan_temp
GROUP BY custype;

-- Check route sizes
SELECT
    DistributorID,
    AgentID,
    RouteDate,
    COUNT(*) as total_stops,
    SUM(CASE WHEN custype = 'customer' THEN 1 ELSE 0 END) as customers,
    SUM(CASE WHEN custype = 'prospect' THEN 1 ELSE 0 END) as prospects
FROM MonthlyRoutePlan_temp
GROUP BY DistributorID, AgentID, RouteDate
ORDER BY RouteDate DESC;
```

## Troubleshooting

### Issue: "Module not found" errors
**Solution:** Ensure you activated the virtual environment
```bash
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### Issue: "Database connection failed"
**Solution:** Check your `.env` file
1. Verify credentials are correct
2. Ensure no extra spaces in values
3. Check firewall allows connection
4. Test connection manually

### Issue: "No data found"
**Solution:** Verify MonthlyRoutePlan_temp has data
```sql
SELECT COUNT(*), MIN(RouteDate), MAX(RouteDate)
FROM MonthlyRoutePlan_temp;
```

### Issue: Pipeline runs but no updates
**Solution:** Check logs for errors
```bash
# Look for ERROR or WARNING messages in logs
grep -i error logs/*.log
grep -i warning logs/*.log
```

## Next Steps

- Read the full [README.md](../README.md) for detailed documentation
- Review [configuration options](../config.py) to customize behavior
- Check logs regularly to monitor performance
- Set up scheduled runs using cron (Linux) or Task Scheduler (Windows)

## Getting Help

If you encounter issues:
1. Check the logs directory for error details
2. Review the main README.md troubleshooting section
3. Verify your configuration with `python run_pipeline.py --validate-config`
4. Contact the development team with log files and error messages

## Performance Tips

For best performance:
- Run during off-peak hours
- Adjust `--max-workers` based on your CPU cores
- Increase `--batch-size` for bulk operations
- Filter by distributor to process in stages
- Monitor database server load

Happy optimizing! 🚀
