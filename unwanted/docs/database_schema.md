# Database Schema Documentation

## Tables and Columns Used in Route Optimization Pipeline

### 📋 Overview
The route optimization system uses 3 main tables:
1. **routedata** - Source customer data
2. **prospective** - Source prospect data
3. **routeplan** - Target optimized route data

---

## 🏢 Table 1: `routedata` (Source - Customer Data)

### Purpose
Contains existing customer data with sales agent assignments and route dates.

### Key Columns Used
| Column | Data Type | Description | Usage |
|--------|-----------|-------------|-------|
| `Code` | VARCHAR | Sales agent identifier | **Primary filter** for agent selection |
| `SalesManTerritory` | VARCHAR | Alternative agent field | Used in some queries |
| `RouteDate` | DATE | Route date | **Primary filter** for date selection |
| `CustNo` | VARCHAR | Customer number/ID | **Primary key** for customer identification |
| `latitude` | DECIMAL | Latitude coordinate | **GPS coordinate** for mapping and TSP |
| `longitude` | DECIMAL | Longitude coordinate | **GPS coordinate** for mapping and TSP |
| `address3` | VARCHAR | **Barangay code** | **Matching key** = prospective.barangay_code |
| `custype` | VARCHAR | Customer type | Classification (usually 'customer') |
| `Name` | VARCHAR | Customer name | Display information |

### Important Notes
- **Primary matching logic**: `routedata.address3 = prospective.barangay_code`
- **Coordinate filtering**: NULL, 0 values assigned stopno=100
- **Agent identification**: Uses `Code` column (not `SalesManTerritory`)

---

## 🎯 Table 2: `prospective` (Source - Prospect Data)

### Purpose
Contains potential customers (prospects) that can be added to routes.

### Key Columns Used
| Column | Data Type | Description | Usage |
|--------|-----------|-------------|-------|
| `CustNo` | VARCHAR | Prospect ID | **Primary key** for prospect identification |
| `Latitude` | DECIMAL | Latitude coordinate | **GPS coordinate** for distance calculations |
| `Longitude` | DECIMAL | Longitude coordinate | **GPS coordinate** for distance calculations |
| `barangay_code` | VARCHAR | **Barangay code** | **Matching key** = routedata.address3 |
| `Barangay` | VARCHAR | Barangay name | Display information |
| `Custype` | VARCHAR | Customer type | Usually 'prospect' |

### Important Notes
- **Matching logic**: `prospective.barangay_code = routedata.address3`
- **Geographic filtering**: Bounding box queries for performance
- **Quality filters**: Must have valid Latitude/Longitude (NOT NULL, != 0)

---

## 📈 Table 3: `routeplan` (Target - Optimized Route Data)

### Purpose
Stores the final optimized routes with customers and added prospects.

### All Columns
| Column | Data Type | Description | Source |
|--------|-----------|-------------|---------|
| `salesagent` | VARCHAR | Sales agent ID | routedata.Code |
| `custno` | VARCHAR | Customer/prospect ID | routedata.CustNo OR prospective.CustNo |
| `custype` | VARCHAR | Type classification | 'customer' OR 'prospect' |
| `latitude` | DECIMAL | Latitude coordinate | routedata.latitude OR prospective.Latitude |
| `longitude` | DECIMAL | Longitude coordinate | routedata.longitude OR prospective.Longitude |
| `stopno` | INTEGER | **Stop sequence number** | TSP optimization result (100 = no coords) |
| `routedate` | DATE | Route date | routedata.RouteDate |
| `barangay` | VARCHAR | Barangay name/info | routedata.address3 OR prospective.Barangay |
| `barangay_code` | VARCHAR | **Barangay code** | routedata.address3 OR prospective.barangay_code |
| `is_visited` | INTEGER | Visit status flag | Default: 0 (not visited) |

### Important Notes
- **Stop numbering**: 1,2,3... = TSP optimized sequence, 100 = no coordinates
- **Data source mix**: Combines customers + prospects
- **Barangay code fix**: Uses correct source field per record type

---

## 🔄 Data Flow & Relationships

```
[routedata] ─────────────┐
     │                   │
     │ address3          │ Data
     │     ║             │ Combination
     │     ║ EQUALS      │     │
     │     ║             │     ▼
     │     ▼             │ [routeplan]
[prospective] ───────────┘
   barangay_code
```

### Matching Logic
```sql
routedata.address3 = prospective.barangay_code
```

---

## 📊 Usage by Component

### 🔍 **Query Analysis**
- **Agent selection**: `routedata.Code`, `routedata.RouteDate`
- **Customer counting**: `COUNT(DISTINCT routedata.CustNo)`
- **Geographic filtering**: `routedata.latitude`, `routedata.longitude`
- **Barangay matching**: `routedata.address3 = prospective.barangay_code`

### 🗺️ **Route Optimization**
- **TSP algorithm**: Uses `latitude`, `longitude` coordinates
- **Centroid calculation**: Average of customer coordinates
- **Distance calculations**: Haversine formula on lat/lng pairs
- **Stop sequencing**: Assigns `stopno` 1,2,3... or 100

### 📱 **Visualization**
- **Map markers**: `latitude`, `longitude` from routeplan
- **Color coding**: `custype` (customer=blue, prospect=red)
- **Route paths**: Connected by `stopno` sequence
- **Popups**: `custno`, `barangay_code`, coordinates

---

## ⚡ Performance Indexes

### Required Indexes
```sql
-- routedata performance
CREATE INDEX IX_routedata_agent_date ON routedata (Code, RouteDate);
CREATE INDEX IX_routedata_location ON routedata (latitude, longitude);

-- prospective performance
CREATE INDEX IX_prospective_coords ON prospective (Latitude, Longitude);
CREATE INDEX IX_prospective_barangay ON prospective (barangay_code);

-- routeplan queries
CREATE INDEX IX_routeplan_agent_date ON routeplan (salesagent, routedate);
```

---

## 🚨 Critical Data Quality Notes

1. **Barangay Code Matching**:
   - `routedata.address3` contains barangay codes (NOT names)
   - `prospective.barangay_code` contains barangay codes
   - Both fields must match exactly for prospect selection

2. **Coordinate Handling**:
   - NULL or 0 coordinates get `stopno = 100`
   - Valid coordinates get TSP optimization
   - Bounding box filtering improves query performance

3. **Agent Identification**:
   - Primary field: `routedata.Code`
   - Alternative: `routedata.SalesManTerritory`
   - Pipeline uses `Code` for consistency

4. **Customer Type Classification**:
   - Existing records: `custype = 'customer'`
   - Added records: `custype = 'prospect'`
   - Fixed in pipeline to prevent 'nan' values

This schema supports the full route optimization pipeline from source data analysis through final route visualization.