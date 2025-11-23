# External Dependencies - Hierarchical Route Pipeline

This document lists **ALL** external dependencies and resources used by the hierarchical route pipeline.

## Summary

✅ **The pipeline is SELF-CONTAINED** - All code is within the `hierarchical-route-pipeline\` directory
❌ **NO dependencies on parent project or outside directories**
⚠️ **REQUIRES external resources**: Database server, Python packages, ODBC Driver

---

## 1. File System Dependencies

### ✅ All Files Are Inside `hierarchical-route-pipeline\`

The pipeline does NOT access any files outside its directory. All imports use local paths:

```python
# run_pipeline.py - Line 39
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
```

**Directory Structure:**
```
hierarchical-route-pipeline\
├── run_pipeline.py           # Main entry point
├── config.py                 # Configuration
├── requirements.txt          # Python dependencies
├── .env (user creates)       # Database credentials
├── src\
│   ├── __init__.py
│   ├── pipeline.py           # Core pipeline logic
│   ├── database.py           # Database connection
│   └── scenario_tracker.py  # Scenario tracking
├── docs\                     # Documentation
└── logs\                     # Generated logs (created at runtime)
```

**No references to:**
- Parent directories (`../` or `..\`)
- Absolute paths outside the project
- Other projects or modules

---

## 2. External Database Server

### ⚠️ REQUIRED: SQL Server Database

**Connection Details (from .env file):**
- `DB_SERVER` - SQL Server address (e.g., localhost, Azure SQL)
- `DB_DATABASE` - Database name
- `DB_USERNAME` - SQL Server username
- `DB_PASSWORD` - SQL Server password
- `DB_USE_WINDOWS_AUTH` - Use Windows Authentication (True/False)

**Database Tables Required:**
1. **MonthlyRoutePlan_temp** - Main route plan data (READ/WRITE)
2. **customer** - Customer master data with GPS coordinates (READ)
3. **prospective** - Prospective customers (READ)
4. **custvisit** - Visit history (READ)
5. **distributors** - Distributor locations (READ)

**Connection Method:**
- Uses `pyodbc` with ODBC Driver 17 for SQL Server
- Connection pooling via SQLAlchemy
- Configured in `src/database.py`

---

## 3. Python Package Dependencies

### Required Packages (from requirements.txt)

**Database Connectivity:**
```
pyodbc==4.0.39              # ODBC database driver
sqlalchemy==2.0.19          # Database ORM and pooling
```

**Data Processing:**
```
pandas==2.0.3               # Data manipulation
numpy==1.24.3               # Numerical computations
```

**Configuration:**
```
python-dotenv==1.0.0        # Environment variable management
```

**Additional (for documentation generation):**
```
python-docx                 # Word document generation (generate_database_documentation.py)
```

**Installation:**
```bash
pip install -r requirements.txt
pip install python-docx  # For documentation generation only
```

---

## 4. System Dependencies

### ⚠️ REQUIRED: ODBC Driver

**ODBC Driver 17 for SQL Server**
- Required for database connectivity
- Referenced in: `src/database.py` line 43

**Installation:**
- **Windows:** Download from Microsoft
- **Linux:** Install via package manager
- **macOS:** Download from Microsoft

**Check if installed:**
```bash
# Windows
odbcad32.exe

# Linux/macOS
odbcinst -q -d
```

---

## 5. Environment Variables

### Required: .env File

**Location:** `hierarchical-route-pipeline\.env`

**Template:** `.env.example` (provided in directory)

**Required Variables:**
```bash
DB_SERVER=your-server.database.windows.net
DB_DATABASE=your_database_name
DB_USE_WINDOWS_AUTH=False
DB_USERNAME=your_username
DB_PASSWORD=your_password
```

**Usage:**
- Loaded by `python-dotenv` in `config.py` and `src/database.py`
- NOT committed to version control (in .gitignore)
- User must create from `.env.example`

---

## 6. Runtime Generated Resources

### Created During Execution (Inside hierarchical-route-pipeline\)

**Log Files:**
- Directory: `hierarchical-route-pipeline\logs\`
- Created automatically if doesn't exist
- Format: `hierarchical_monthly_route_pipeline_YYYYMMDD_HHMMSS.log`
- Location: `src/pipeline.py` line 69

**Cache (In-Memory):**
- Customer coordinates cache
- Barangay lookup cache
- Prospect query cache
- Distributor location cache
- No files written, stored in memory only

---

## 7. Network Access

### Database Server Connection

**Outbound Connections:**
- SQL Server (port 1433 typical)
- Azure SQL (port 1433)
- Connection string in `src/database.py`

**No Other Network Access:**
- ❌ No HTTP/HTTPS requests
- ❌ No API calls
- ❌ No external web services
- ❌ No file downloads

---

## 8. What's NOT Required

### ❌ No Dependencies On:

1. **Parent Project:**
   - Does NOT import from `Route-optimization\` parent directory
   - Does NOT use `../` paths
   - Completely standalone

2. **External Files:**
   - No configuration files outside directory
   - No shared modules
   - No external data files

3. **External Services:**
   - No cloud APIs
   - No web services
   - No email services
   - Only database server

4. **Operating System Specific:**
   - Works on Windows, Linux, macOS
   - Only requires ODBC Driver (platform-specific installation)

---

## 9. Quick Setup Checklist

To run the pipeline, you ONLY need:

✅ **Inside hierarchical-route-pipeline\:**
- [ ] Python 3.8+ installed
- [ ] Install packages: `pip install -r requirements.txt`
- [ ] Install ODBC Driver 17 for SQL Server
- [ ] Create `.env` file from `.env.example`
- [ ] Configure database credentials in `.env`

✅ **External (Database Server):**
- [ ] SQL Server accessible (local or remote)
- [ ] Database contains required tables (listed in Section 2)
- [ ] Database credentials valid
- [ ] Network access to database server

**That's ALL you need!**

---

## 10. Import Map

### All Imports Are Standard Library or Listed Dependencies

**Standard Library Imports:**
```python
import sys, os, argparse          # System utilities
import logging                    # Logging
import time                       # Performance tracking
from datetime import datetime     # Date handling
from concurrent.futures import... # Parallel processing
from math import radians, cos...  # Distance calculations
from urllib.parse import quote_plus  # URL encoding
import warnings                   # Warning suppression
from typing import Optional...    # Type hints
```

**Third-Party Imports (from requirements.txt):**
```python
import pyodbc                     # Database driver
import pandas as pd               # Data processing
import numpy as np                # Numerical operations
from dotenv import load_dotenv    # Environment variables
from sqlalchemy import...         # Database ORM
```

**Local Imports (within hierarchical-route-pipeline\):**
```python
import config                     # ./config.py
from src.pipeline import...       # ./src/pipeline.py
from src.database import...       # ./src/database.py
from src.scenario_tracker import... # ./src/scenario_tracker.py
```

**Documentation Generation (optional):**
```python
from docx import Document         # python-docx (optional)
```

---

## Summary Table

| Dependency Type | Required? | Location | Purpose |
|----------------|-----------|----------|---------|
| Python 3.8+ | ✅ Yes | System | Runtime environment |
| pyodbc | ✅ Yes | pip package | Database connectivity |
| sqlalchemy | ✅ Yes | pip package | Connection pooling |
| pandas | ✅ Yes | pip package | Data processing |
| numpy | ✅ Yes | pip package | TSP calculations |
| python-dotenv | ✅ Yes | pip package | Config management |
| ODBC Driver 17 | ✅ Yes | System | SQL Server driver |
| SQL Server | ✅ Yes | External | Data storage |
| .env file | ✅ Yes | Project root | DB credentials |
| python-docx | ❌ No | pip package | Doc generation only |
| Internet | ❌ No | N/A | Not required |
| Parent project | ❌ No | N/A | Independent |

---

## Verification Commands

**Check all dependencies:**
```bash
cd "hierarchical-route-pipeline"

# Check Python version
python --version

# Check installed packages
pip list | grep -E "pyodbc|sqlalchemy|pandas|numpy|dotenv"

# Check ODBC Driver (Windows)
odbcad32.exe

# Test database connection
python -c "from src.database import DatabaseConnection; db = DatabaseConnection(); db.connect()"

# Verify no external dependencies
python -c "import sys; print('All imports resolved successfully')"
```

**Expected Output:**
- Python 3.8 or higher
- All packages installed
- ODBC Driver 17 available
- Database connection successful
- No import errors

---

**Last Updated:** Generated automatically
**Pipeline Version:** 1.0
**Self-Contained:** ✅ Yes
