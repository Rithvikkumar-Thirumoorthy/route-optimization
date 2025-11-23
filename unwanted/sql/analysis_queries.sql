-- AGENT SCENARIO ANALYSIS QUERIES
-- Used to analyze sales agents and their days based on multiple scenarios

-- =============================================================================
-- SCENARIO 1: AGENTS WITH EXACTLY 60 CUSTOMERS
-- =============================================================================

-- Query 1.1: Count agent-days with exactly 60 customers
SELECT COUNT(*)
FROM (
    SELECT SalesManTerritory, RouteDate, COUNT(DISTINCT CustNo) as cust_count
    FROM routedata
    WHERE SalesManTerritory IS NOT NULL
    GROUP BY SalesManTerritory, RouteDate
    HAVING COUNT(DISTINCT CustNo) = 60
) sub;

-- Query 1.2: Get sample agents with exactly 60 customers
SELECT TOP 10
    SalesManTerritory as agent_id,
    RouteDate,
    COUNT(DISTINCT CustNo) as customer_count,
    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
               AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
               OR latitude = 0 OR longitude = 0 THEN 1 END) as without_coordinates
FROM routedata
WHERE SalesManTerritory IS NOT NULL
GROUP BY SalesManTerritory, RouteDate
HAVING COUNT(DISTINCT CustNo) = 60
ORDER BY SalesManTerritory, RouteDate;

-- =============================================================================
-- SCENARIO 2: AGENTS WITH <60 CUSTOMERS + PROSPECTS IN SAME BARANGAY
-- =============================================================================

-- Query 2.1: Get agents with <60 customers (basic version)
SELECT TOP 15
    SalesManTerritory as agent_id,
    RouteDate,
    COUNT(DISTINCT CustNo) as customer_count,
    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
               AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coords,
    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
               OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count
FROM routedata
WHERE SalesManTerritory IS NOT NULL
GROUP BY SalesManTerritory, RouteDate
HAVING COUNT(DISTINCT CustNo) < 60
ORDER BY COUNT(DISTINCT CustNo) DESC;

-- Query 2.2: Get barangay codes for specific agent and date
SELECT DISTINCT barangay_code
FROM routedata
WHERE SalesManTerritory = ? AND RouteDate = ?
AND barangay_code IS NOT NULL AND barangay_code != '#' AND barangay_code != '';

-- Query 2.3: Check prospects available for specific barangay code
SELECT COUNT(DISTINCT CustNo)
FROM prospective
WHERE barangay_code = ?
AND Latitude IS NOT NULL AND Longitude IS NOT NULL
AND Latitude != 0 AND Longitude != 0;

-- Query 2.4: Customer details for specific agent and date
SELECT COUNT(DISTINCT CustNo) as customers,
       COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                  AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coords,
       COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                  OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100
FROM routedata
WHERE SalesManTerritory = ? AND RouteDate = ?;

-- =============================================================================
-- SCENARIO 3: AGENTS WITH <60 CUSTOMERS + STOP100 CONDITIONS
-- =============================================================================

-- Query 3.1: Get agents with <60 customers and stop100 conditions
SELECT TOP 10
    SalesManTerritory as agent_id,
    RouteDate,
    COUNT(DISTINCT CustNo) as customer_count,
    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
               AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
               OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_customers,
    CAST(COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
               OR latitude = 0 OR longitude = 0 THEN 1 END) * 100.0 / COUNT(*) AS DECIMAL(5,1)) as stop100_percentage
FROM routedata
WHERE SalesManTerritory IS NOT NULL
GROUP BY SalesManTerritory, RouteDate
HAVING COUNT(DISTINCT CustNo) < 60
AND COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
               OR latitude = 0 OR longitude = 0 THEN 1 END) > 0
ORDER BY COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                     OR latitude = 0 OR longitude = 0 THEN 1 END) DESC;

-- =============================================================================
-- BARANGAY MATCHING VERIFICATION QUERIES
-- =============================================================================

-- Query 4.1: Verify barangay matching (barangay_code = barangay_code)
SELECT TOP 10
    r.barangay_code as routedata_barangay_code,
    COUNT(DISTINCT r.CustNo) as customers_with_this_code,
    COUNT(DISTINCT p.CustNo) as prospects_with_this_code
FROM routedata r
LEFT JOIN prospective p ON r.barangay_code = p.barangay_code
    AND p.Latitude IS NOT NULL AND p.Longitude IS NOT NULL
    AND p.Latitude != 0 AND p.Longitude != 0
WHERE r.barangay_code IS NOT NULL
AND r.barangay_code != '#'
AND r.barangay_code != ''
GROUP BY r.barangay_code
HAVING COUNT(DISTINCT p.CustNo) > 0
ORDER BY COUNT(DISTINCT p.CustNo) DESC;

-- Query 4.2: Count customers with specific barangay code
SELECT COUNT(DISTINCT CustNo)
FROM routedata
WHERE barangay_code = ?;

-- Query 4.3: Count prospects with specific barangay code
SELECT COUNT(DISTINCT CustNo)
FROM prospective
WHERE barangay_code = ?
AND Latitude IS NOT NULL AND Longitude IS NOT NULL;

-- =============================================================================
-- DATA DISTRIBUTION QUERIES
-- =============================================================================

-- Query 5.1: Customer count distribution
SELECT COUNT(*)
FROM (
    SELECT SalesManTerritory, RouteDate, COUNT(DISTINCT CustNo) as cust_count
    FROM routedata
    WHERE SalesManTerritory IS NOT NULL
    GROUP BY SalesManTerritory, RouteDate
    HAVING COUNT(DISTINCT CustNo) = 60  -- Change this number for different counts
) sub;

-- Query 5.2: Summary of barangay code distribution in routedata
SELECT
    CASE
        WHEN barangay_code = '#' THEN 'Hash symbol'
        WHEN barangay_code IS NULL THEN 'NULL'
        WHEN barangay_code = '' THEN 'Empty string'
        ELSE 'Valid code'
    END as code_type,
    COUNT(*) as count
FROM routedata
GROUP BY
    CASE
        WHEN barangay_code = '#' THEN 'Hash symbol'
        WHEN barangay_code IS NULL THEN 'NULL'
        WHEN barangay_code = '' THEN 'Empty string'
        ELSE 'Valid code'
    END
ORDER BY count DESC;

-- Query 5.3: Top barangay codes in routedata (non-# values)
SELECT TOP 10 barangay_code, COUNT(*) as count
FROM routedata
WHERE barangay_code IS NOT NULL
AND barangay_code != '#'
AND barangay_code != ''
GROUP BY barangay_code
ORDER BY count DESC;

-- Query 5.4: Top barangay codes in prospective table
SELECT TOP 10 barangay_code, COUNT(*) as count
FROM prospective
WHERE barangay_code IS NOT NULL
AND Latitude IS NOT NULL
AND Longitude IS NOT NULL
AND Latitude != 0
AND Longitude != 0
GROUP BY barangay_code
ORDER BY count DESC;

-- =============================================================================
-- PIPELINE VALIDATION QUERIES
-- =============================================================================

-- Query 6.1: Overall scenario distribution
SELECT
    CASE
        WHEN COUNT(DISTINCT CustNo) = 60 THEN 'Exactly 60 customers'
        WHEN COUNT(DISTINCT CustNo) > 60 THEN 'More than 60 customers'
        ELSE 'Less than 60 customers'
    END as scenario,
    COUNT(*) as agent_day_count,
    AVG(CAST(COUNT(DISTINCT CustNo) AS FLOAT)) as avg_customers,
    MIN(COUNT(DISTINCT CustNo)) as min_customers,
    MAX(COUNT(DISTINCT CustNo)) as max_customers
FROM routedata
WHERE SalesManTerritory IS NOT NULL
GROUP BY SalesManTerritory, RouteDate
GROUP BY
    CASE
        WHEN COUNT(DISTINCT CustNo) = 60 THEN 'Exactly 60 customers'
        WHEN COUNT(DISTINCT CustNo) > 60 THEN 'More than 60 customers'
        ELSE 'Less than 60 customers'
    END
ORDER BY scenario;

-- Query 6.2: Test specific agent's customers and barangay codes
SELECT r.CustNo, r.latitude, r.longitude, r.barangay_code, r.custype, r.Name
FROM routedata r
WHERE r.SalesManTerritory = ? AND r.RouteDate = ?
AND r.CustNo IS NOT NULL;

-- Query 6.3: Check overlapping barangay codes between tables
SELECT p.barangay_code, COUNT(DISTINCT p.CustNo) as prospect_count
FROM prospective p
WHERE p.barangay_code IN (
    SELECT DISTINCT barangay_code
    FROM routedata
    WHERE barangay_code IS NOT NULL
    AND barangay_code != '#'
    AND barangay_code != ''
)
AND p.Latitude IS NOT NULL
AND p.Longitude IS NOT NULL
AND p.Latitude != 0
AND p.Longitude != 0
GROUP BY p.barangay_code
ORDER BY prospect_count DESC;

-- =============================================================================
-- SAMPLE USAGE PARAMETERS
-- =============================================================================

-- Example parameters used in the analysis:
-- ? = 'D305' (agent_id)
-- ? = '2025-09-25' (route_date)
-- ? = '042108023' (barangay_code)
-- ? = '45808009' (working_barangay_code)
-- ? = 'SK-SAT5' (agent_id)
-- ? = '2025-09-27' (route_date)
-- ? = '45813002' (barangay_code)

-- =============================================================================
-- KEY FINDINGS FROM ANALYSIS:
-- =============================================================================
/*
SCENARIO 1: 330 agent-days with exactly 60 customers (skip these)
SCENARIO 2: Multiple agents with <60 customers and available prospects in same barangay
SCENARIO 3: Agents like OL-07, SMDLZ-1 with stop100 conditions

BARANGAY MATCHING CONFIRMED: routedata.barangay_code = prospective.barangay_code
- Working example: '45808009' has 11 customers and 2,840 prospects
- Many other successful matches found

STOP100 DEFINITION: Customers with NULL/0 coordinates get stopno=100
*/