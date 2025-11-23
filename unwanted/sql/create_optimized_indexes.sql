-- Optimized Indexes for Route Optimization Pipeline
-- Run these SQL commands to improve performance

-- 1. Check current data types first
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH,
    IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'prospective'
AND COLUMN_NAME IN ('barangay_code', 'Latitude', 'Longitude', 'CustNo');

-- 2. Primary coordinate index (most important for distance calculations)
CREATE INDEX IX_prospective_coords
ON prospective (Latitude, Longitude)
WHERE Latitude IS NOT NULL AND Longitude IS NOT NULL;

-- 3. Include barangay_code in INCLUDE clause instead of key (works with any data type)
CREATE INDEX IX_prospective_location_include
ON prospective (Latitude, Longitude)
INCLUDE (barangay_code, CustNo)
WHERE Latitude IS NOT NULL AND Longitude IS NOT NULL;

-- 4. If barangay_code is varchar/nvarchar, limit the key length
-- (Adjust the length based on your actual data - check max length first)
CREATE INDEX IX_prospective_barangay
ON prospective (CAST(LEFT(barangay_code, 50) AS VARCHAR(50)))
INCLUDE (Latitude, Longitude, CustNo)
WHERE barangay_code IS NOT NULL;

-- 5. Alternative: Computed column approach if barangay_code is text type
-- First add a computed column (only if barangay_code is text/ntext)
-- ALTER TABLE prospective ADD barangay_code_key AS CAST(LEFT(barangay_code, 50) AS VARCHAR(50));
-- Then create index on the computed column:
-- CREATE INDEX IX_prospective_barangay_computed ON prospective (barangay_code_key);

-- 6. Indexes for routedata table
CREATE INDEX IX_routedata_agent_date
ON routedata (SalesManTerritory, RouteDate)
INCLUDE (CustNo, latitude, longitude, barangay_code);

CREATE INDEX IX_routedata_location
ON routedata (latitude, longitude)
WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

CREATE INDEX IX_routedata_barangay_code
ON routedata (CAST(LEFT(barangay_code, 50) AS VARCHAR(50)))
INCLUDE (SalesManTerritory, RouteDate, latitude, longitude)
WHERE barangay_code IS NOT NULL;

-- 7. Index for routeplan_ai table (result table)
CREATE INDEX IX_routeplan_ai_agent_date
ON routeplan_ai (salesagent, routedate)
INCLUDE (custype, stopno);

CREATE INDEX IX_routeplan_ai_custype
ON routeplan_ai (custype, salesagent);

-- Performance monitoring queries
-- Check index usage after running pipeline:
SELECT
    i.name AS IndexName,
    s.user_seeks,
    s.user_scans,
    s.user_lookups,
    s.user_updates
FROM sys.dm_db_index_usage_stats s
INNER JOIN sys.indexes i ON s.object_id = i.object_id AND s.index_id = i.index_id
WHERE OBJECT_NAME(s.object_id) IN ('prospective', 'routedata', 'routeplan_ai')
ORDER BY s.user_seeks + s.user_scans + s.user_lookups DESC;