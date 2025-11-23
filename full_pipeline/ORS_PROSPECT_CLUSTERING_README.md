# ORS Prospect Clustering Pipeline - User Guide

## Overview

This pipeline creates prospect routes using **ORS API** (not Haversine) with intelligent spatial clustering.

## 📋 Pipeline Flow

### Step 1: Get Sales Agents (Access = 15)
```sql
SELECT Code, nodetreevalue, Name
FROM salesagent
WHERE access = 15
```
- Gets all sales agents with access level 15
- Retrieves their `nodetreevalue` (territory)

### Step 2: Get Distributor Barangays
```sql
SELECT DISTINCT
    N.DistributorID,
    Barangay.Code AS BarangayCode,
    Barangay.BarangayName
FROM nodetree N
INNER JOIN salesagent S ON N.SalesmanTerritory = S.Code
INNER JOIN customer C ON S.Code = C.SalesAgent
INNER JOIN Barangay ON Barangay.Code = C.Address3
INNER JOIN Distributor D ON D.DistributorID = N.DistributorID
WHERE C.Active = 1
    AND D.DistributorID = '11814'
ORDER BY N.DistributorID, Barangay.BarangayName
```
- Matches `nodetreevalue` from Step 1 with `nodetree.SalesmanTerritory`
- Gets all barangays that belong to the distributor
- Links through active customers

### Step 3: Spatial Clustering per Barangay
For each barangay:
1. Get prospect count from `prospective` table (matching `barangay_code`)
2. Perform **ORS-based spatial clustering**
3. **Max 60 stores per cluster**
4. Uses DBSCAN algorithm with ORS distance matrix
5. Randomly assign sales agents (from Step 1) to each cluster

### Step 4: Post-Processing Small Barangays
- Identifies clusters with **< 20 stores**
- Merges them with **nearest larger clusters** using ORS distance
- Ensures optimal cluster sizes

### Step 5: Exclusions & Date Assignment
**Exclusions:**
- ✗ Stores already in `MonthlyRoutePlan_temp` (latest month)
- ✗ Stores with history in `custvisit` table

**Date Assignment:**
- Starts from **Weekday 1 (Monday)**
- Each cluster gets consecutive weekdays
- Automatically skips weekends (Sat/Sun)
- Format: `YYYY-MM-DD`

### Step 6: Output to MonthlyRoutePlan_temp
**Format:**
```
CustNo | RouteDate | Name | WD | SalesManTerritory | AgentID | RouteName | DistributorID | RouteCode | SalesOfficeID | StopNo
```

**RouteCode Format:** `{Territory}_W{WeekNo}_D{Weekday}`
- Example: `EastSales_W23_D1` (East Sales territory, Week 23, Monday)

## 🚀 Usage

### Test Mode (Dry-Run)
```bash
python run_ors_prospect_clustering.py \
  --test \
  --distributor 11814 \
  --start-date 2025-01-06
```

**Output:** CSV file in `full_pipeline/output/` directory

### Production Mode
```bash
python run_ors_prospect_clustering.py \
  --distributor 11814 \
  --start-date 2025-01-06 \
  --max-cluster-size 60 \
  --min-cluster-size 20
```

**Output:** Inserts into `MonthlyRoutePlan_temp` table

### With Custom Distributor Location
```bash
python run_ors_prospect_clustering.py \
  --distributor 11814 \
  --start-date 2025-01-06 \
  --distributor-lat 14.5995 \
  --distributor-lon 120.9842
```

## 📊 Command Line Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--test` | No | False | Test mode (no DB changes, exports CSV) |
| `--distributor` | **Yes** | - | Distributor ID (e.g., 11814) |
| `--start-date` | **Yes** | - | Start date (auto-adjusts to Monday) |
| `--max-cluster-size` | No | 60 | Maximum stores per cluster |
| `--min-cluster-size` | No | 20 | Minimum stores for standalone cluster |
| `--distributor-lat` | No | None | Starting latitude for routes |
| `--distributor-lon` | No | None | Starting longitude for routes |

## 🔍 How It Works

### Spatial Clustering with ORS

```
1. For each barangay:
   ├─ Get prospects from prospective table
   ├─ Build ORS distance matrix (NxN)
   ├─ Apply DBSCAN clustering
   ├─ Enforce max 60 stores per cluster
   └─ Split large clusters if needed

2. Post-processing:
   ├─ Identify clusters < 20 stores
   ├─ Calculate ORS distance to nearest large cluster
   └─ Merge small clusters into nearest neighbors

3. Agent & Date Assignment:
   ├─ Random agent selection (from access=15 agents)
   ├─ Start from Monday (WD=1)
   ├─ Increment by weekday (skip weekends)
   └─ Each cluster gets unique date

4. TSP Optimization:
   ├─ Build ORS distance matrix per cluster
   ├─ Apply nearest neighbor TSP
   ├─ Assign stop numbers (1, 2, 3, ...)
   └─ Include distributor location if provided
```

## 📝 Example Output

### Test Mode Output (CSV)
```csv
CustNo,RouteDate,Name,WD,SalesManTerritory,AgentID,RouteName,DistributorID,RouteCode,SalesOfficeID,StopNo
K7887361,2025-01-06,Sample Store 1,1,EastSales,SK-SAT6,Prospect Route SK-SAT6 2025-01-06,11814,EastSales_W02_D1,,1
K7887362,2025-01-06,Sample Store 2,1,EastSales,SK-SAT6,Prospect Route SK-SAT6 2025-01-06,11814,EastSales_W02_D1,,2
K7887363,2025-01-06,Sample Store 3,1,EastSales,SK-SAT6,Prospect Route SK-SAT6 2025-01-06,11814,EastSales_W02_D1,,3
```

### Console Output
```
================================================================================
                    ORS PROSPECT CLUSTERING PIPELINE
================================================================================
Distributor ID: 11814
Start Date: 2025-01-06
Max Stores per Cluster: 60
Min Stores Threshold: 20
================================================================================

STEP 1: Getting sales agents with access = 15
Found 12 sales agents with access = 15

STEP 2: Getting distributor barangays
Found 45 barangays for distributor 11814

STEP 3: Processing barangays and clustering prospects
Processing Barangay: San Antonio (063005011)
  Barangay 063005011: 85 prospects
  Calling ORS Matrix API for 85 locations...
  ORS Matrix API success: (85, 85) matrix retrieved
  Created 2 clusters
  Cluster sizes: min=40, max=45, mean=42.5

Processing Barangay: Lawis (063005012)
  Barangay 063005012: 15 prospects
  Single cluster: 15 prospects

...

Total prospects clustered: 1250

STEP 4: Post-processing - Merging small clusters
Found 8 small clusters to merge
Merging cluster 15 (15 stores) into cluster 3 (distance: 3.24km)
Merging cluster 22 (18 stores) into cluster 7 (distance: 2.87km)
...

Final cluster distribution:
  Total clusters: 24
  Cluster sizes: min=25, max=60, mean=52.1

STEP 5: Assigning agents and dates to clusters
Start date (Monday): 2025-01-06
Assigning 24 clusters to 12 agents
Cluster 0: Agent SK-SAT6, Date 2025-01-06 (WD=1)
Cluster 1: Agent SK-SAT7, Date 2025-01-07 (WD=2)
...

STEP 6: Optimizing routes and preparing for insertion
Optimizing Cluster 0: 52 prospects
  Calling ORS Matrix API for 53 locations...
  ORS Matrix API success: (53, 53) matrix retrieved

...

TEST MODE COMPLETED - NO CHANGES MADE TO DATABASE
CSV EXPORTED: full_pipeline/output/ors_prospect_routes_11814_2025-01-06_20250119_143052.csv
Total records in CSV: 1250
Total clusters created: 24
Duration: 127.35 seconds (2.12 minutes)
================================================================================
```

## ⚙️ Configuration

### ORS Settings (.env)
```env
ORS_MATRIX_ENDPOINT=http://localhost:8080/ors/v2/matrix/driving-car
ORS_ENABLED=True
ORS_TIMEOUT=30
```

### Required Dependencies
```bash
pip install -r requirements.txt
```

**New dependencies:**
- `requests` - For ORS API calls
- `scikit-learn` - For DBSCAN clustering

## 🔄 Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Get Sales Agents (access = 15)                    │
│  └─ Query: salesagent WHERE access = 15                     │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Get Distributor Barangays                          │
│  └─ Join: nodetree → salesagent → customer → barangay       │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Cluster Prospects per Barangay                     │
│  ├─ Get prospects from prospective table                    │
│  ├─ Exclude: MonthlyRoutePlan_temp (latest month)           │
│  ├─ Exclude: custvisit                                      │
│  ├─ Build ORS distance matrix                               │
│  └─ DBSCAN clustering (max 60 stores)                       │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: Merge Small Clusters (< 20 stores)                 │
│  └─ Use ORS to find nearest large cluster                   │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 5: Assign Agents & Dates                              │
│  ├─ Random agent selection                                  │
│  ├─ Start from Monday (WD=1)                                │
│  └─ Skip weekends                                            │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 6: TSP Optimization & Insert                          │
│  ├─ Build ORS distance matrix per cluster                   │
│  ├─ Nearest neighbor TSP                                    │
│  ├─ Assign stop numbers                                     │
│  └─ Insert into MonthlyRoutePlan_temp                       │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Key Differences from Original run_prospect_only_routes.py

| Feature | Original | ORS Clustering Pipeline |
|---------|----------|-------------------------|
| **Distance Calculation** | Haversine only | **ORS API (road-based)** |
| **Data Flow** | User specifies agent/barangay | **Auto-discovers from access=15** |
| **Barangay Discovery** | User provides codes | **Auto-queries from distributor** |
| **Clustering** | Simple by barangay | **Spatial clustering with DBSCAN** |
| **Cluster Size** | Fixed by barangay | **Dynamic (max 60, min 20)** |
| **Small Barangays** | Ignored | **Merged with nearest clusters** |
| **Agent Assignment** | Fixed per route | **Random per cluster** |
| **Date Logic** | User controlled | **Auto from Monday (WD=1)** |
| **Exclusions** | Basic | **Latest month + custvisit** |

## 🛠️ Troubleshooting

### ORS Connection Error
```bash
# Check if ORS is running
curl http://localhost:8080/ors/health

# Start ORS if needed
docker start ors-app
```

### No Sales Agents Found
- Verify agents exist with `access = 15`
- Check query: `SELECT * FROM salesagent WHERE access = 15`

### No Barangays Found
- Verify distributor ID exists
- Check active customers: `SELECT * FROM customer WHERE Active = 1`
- Ensure `nodetree.SalesmanTerritory` matches `salesagent.Code`

### Clustering Fails
- Pipeline automatically falls back to Haversine if ORS fails
- Check logs for "falling back to Haversine" warnings
- Verify coordinates are valid (lat/lon not NULL/0)

## 📊 Performance Tips

1. **Use Test Mode First**: Always run with `--test` to verify before production
2. **ORS Caching**: Automatic - second run on same data is 10-100x faster
3. **Parallel Processing**: Not yet implemented but can be added
4. **Adjust Cluster Sizes**: Use `--max-cluster-size` and `--min-cluster-size` to tune

## 📌 Notes

- **Start date auto-adjusts to Monday** - If you provide Tuesday, it shifts to next Monday
- **Weekends are automatically skipped** - Routes only assigned Mon-Fri
- **Random agent assignment** - Each cluster gets random agent from access=15 pool
- **ORS fallback** - If ORS fails, automatically uses Haversine distance
- **Thread-safe caching** - Safe for parallel processing (future enhancement)

## 🔐 Database Safety

**Test Mode (Recommended):**
- ✓ No database changes
- ✓ Exports CSV for review
- ✓ Can verify before production run

**Production Mode:**
- ⚠️ Inserts directly into MonthlyRoutePlan_temp
- ⚠️ Requires confirmation prompt
- ⚠️ Cannot undo - backup database first!

## 📞 Support

For issues or questions:
1. Check logs in `full_pipeline/logs/`
2. Review ORS integration guide: `hierarchical-route-pipeline/ORS_INTEGRATION_GUIDE.md`
3. Verify ORS service: `python hierarchical-route-pipeline/test_ors_integration.py`
