# Updated Database Schema Documentation

## Tables and Columns Used in Route Optimization Pipeline (UPDATED)

### 📋 Overview
The route optimization system uses 3 main tables:
1. **routedata** - Source customer data (UPDATED SCHEMA)
2. **prospective** - Source prospect data (UPDATED SCHEMA)
3. **routeplan_ai** - Target optimized route data (NEW TABLE NAME)

---

## 🏢 Table 1: `routedata` (Source - Customer Data) - UPDATED

### Purpose
Contains existing customer data with sales agent assignments and route dates.

### Columns Structure
| Column | Data Type | Description | Usage |
|--------|-----------|-------------|-------|
| `Code` | VARCHAR | Sales agent identifier | **Primary filter** for agent selection |
| `NodeTreeValue` | VARCHAR | Node tree value | Organizational hierarchy |
| `CustNo` | VARCHAR | Customer number/ID | **Primary key** for customer identification |
| `RouteDate` | DATE | Route date | **Primary filter** for date selection |
| `SalesManTerritory` | VARCHAR | Sales territory | Territory assignment |
| `latitude` | DECIMAL | Latitude coordinate | **GPS coordinate** for mapping and TSP |
| `longitude` | DECIMAL | Longitude coordinate | **GPS coordinate** for mapping and TSP |
| `barangay_code` | VARCHAR | **Barangay code** | **Matching key** = prospective.barangay_code |
| `Name` | VARCHAR | Customer name | Display information |
| `WD` | VARCHAR | Working day/schedule | Schedule information |

### Key Changes from Previous Schema
- ✅ **Now has `barangay_code` column directly** (was `address3`)
- ✅ **Added `NodeTreeValue`** for hierarchy
- ✅ **Added `SalesManTerritory`** as separate field
- ✅ **Added `WD`** field for scheduling

---

## 🎯 Table 2: `prospective` (Source - Prospect Data) - UPDATED

### Purpose
Contains potential customers (prospects) that can be added to routes.

### Columns Structure
| Column | Data Type | Description | Usage |
|--------|-----------|-------------|-------|
| `CustNo` | VARCHAR | Prospect ID | **Primary key** for prospect identification |
| `OutletName` | VARCHAR | Outlet/business name | Display information |
| `Address` | VARCHAR | Primary address | Address information |
| `Address2` | VARCHAR | Secondary address | Additional address info |
| `Latitude` | DECIMAL | Latitude coordinate | **GPS coordinate** for distance calculations |
| `Longitude` | DECIMAL | Longitude coordinate | **GPS coordinate** for distance calculations |
| `IsVisited` | BOOLEAN | Visit status | Tracking field |
| `Remarks` | VARCHAR | Notes/comments | Additional information |
| `NextVisit` | DATE | Next visit date | Scheduling |
| `Active` | BOOLEAN | Active status | Status flag |
| `IsCustNo` | VARCHAR | Customer number flag | Classification |
| `NewCustNo` | VARCHAR | New customer number | ID mapping |
| `Barangay` | VARCHAR | Barangay name | Geographic name |
| `RD` | VARCHAR | Route designation | Route info |
| `Province` | VARCHAR | Province name | Geographic hierarchy |
| `barangay_code` | VARCHAR | **Barangay code** | **Matching key** = routedata.barangay_code |
| `City` | VARCHAR | City name | Geographic info |
| `Postalcode` | VARCHAR | Postal code | Address detail |

### Key Changes from Previous Schema
- ✅ **Enhanced address fields** (Address, Address2, City, Postalcode)
- ✅ **Added business info** (OutletName)
- ✅ **Added status tracking** (IsVisited, Active, NextVisit)
- ✅ **Added geographic hierarchy** (Province, City, Barangay)
- ✅ **Retained `barangay_code`** as matching key

---

## 📈 Table 3: `routeplan_ai` (Target - Optimized Route Data) - NEW NAME

### Purpose
Stores the final optimized routes with customers and added prospects.

### All Columns (Same as before)
| Column | Data Type | Description | Source |
|--------|-----------|-------------|---------|
| `salesagent` | VARCHAR | Sales agent ID | routedata.Code |
| `custno` | VARCHAR | Customer/prospect ID | routedata.CustNo OR prospective.CustNo |
| `custype` | VARCHAR | Type classification | 'customer' OR 'prospect' |
| `latitude` | DECIMAL | Latitude coordinate | routedata.latitude OR prospective.Latitude |
| `longitude` | DECIMAL | Longitude coordinate | routedata.longitude OR prospective.Longitude |
| `stopno` | INTEGER | **Stop sequence number** | TSP optimization result (100 = no coords) |
| `routedate` | DATE | Route date | routedata.RouteDate |
| `barangay` | VARCHAR | Barangay name/info | prospective.Barangay |
| `barangay_code` | VARCHAR | **Barangay code** | routedata.barangay_code OR prospective.barangay_code |
| `is_visited` | INTEGER | Visit status flag | Default: 0 (not visited) |

### Key Changes
- ✅ **Table renamed**: `routeplan` → `routeplan_ai`
- ✅ **Same column structure** as before
- ✅ **Updated source mapping** for new schema

---

## 🔄 Updated Data Flow & Relationships

```
[routedata] ─────────────┐
     │                   │
     │ barangay_code     │ Data
     │     ║             │ Combination
     │     ║ EQUALS      │     │
     │     ║             │     ▼
     │     ▼             │ [routeplan_ai]
[prospective] ───────────┘
   barangay_code
```

### **UPDATED Matching Logic**
```sql
routedata.barangay_code = prospective.barangay_code
```

**Key Change**: Both tables now have `barangay_code` columns directly!

---

## 📊 Code Changes Required

### 1. **Database Queries Update**
```sql
-- OLD
SELECT address3 FROM routedata WHERE ...

-- NEW
SELECT barangay_code FROM routedata WHERE ...
```

### 2. **Matching Logic Update**
```sql
-- OLD
ON r.address3 = p.barangay_code

-- NEW
ON r.barangay_code = p.barangay_code
```

### 3. **Target Table Update**
```sql
-- OLD
INSERT INTO routeplan ...

-- NEW
INSERT INTO routeplan_ai ...
```

### 4. **Pipeline Code Updates**
```python
# OLD
customer.get('address3')

# NEW
customer.get('barangay_code')
```

---

## 🚨 Critical Updates Needed

### **Files to Update:**
1. **`core/database.py`** - Update table references
2. **`core/scalable_route_optimizer.py`** - Update column names
3. **`core/enhanced_route_optimizer.py`** - Update column names
4. **`core/run_specific_agents.py`** - Update table/column references
5. **`sql/*.sql`** - Update all query files
6. **`visualization/app.py`** - Update table name to `routeplan_ai`

### **Key Changes Summary:**
- ✅ **Simplified matching**: Both tables use `barangay_code`
- ✅ **Enhanced prospect data**: More address and business info
- ✅ **New target table**: `routeplan_ai` instead of `routeplan`
- ✅ **Cleaner schema**: Direct barangay_code matching

The updated schema provides better data consistency and simpler matching logic! 🚀