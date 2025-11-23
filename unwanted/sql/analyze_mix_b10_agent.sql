-- ANALYSIS FOR SPECIFIC AGENT: MIX-B10 ON 2025-09-03
-- Based on your query structure using Code instead of SalesManTerritory

-- Query 1: Basic agent information
SELECT
    Code as agent_id,
    RouteDate as day,
    COUNT(DISTINCT CustNo) as total_customers,
    COUNT(DISTINCT CASE
        WHEN barangay_code IS NOT NULL AND barangay_code != '#' AND barangay_code != ''
        THEN CustNo
    END) as customers_with_barangay_code,
    COUNT(DISTINCT CASE
        WHEN barangay_code IS NULL OR barangay_code = '#' OR barangay_code = ''
        THEN CustNo
    END) as customers_without_barangay_code,
    COUNT(DISTINCT CASE
        WHEN latitude IS NOT NULL AND longitude IS NOT NULL
        AND latitude != 0 AND longitude != 0
        THEN CustNo
    END) as customers_with_coords,
    COUNT(DISTINCT CASE
        WHEN latitude IS NULL OR longitude IS NULL
        OR latitude = 0 OR longitude = 0
        THEN CustNo
    END) as stop100_customers
FROM routedata
WHERE Code = 'MIX-B10'
AND RouteDate = '2025-09-03'
GROUP BY Code, RouteDate;

-- Query 2: Show all customers for this agent with their data quality
SELECT
    CustNo,
    latitude,
    longitude,
    barangay_code,
    CASE
        WHEN barangay_code IS NULL THEN 'NULL_ADDRESS3'
        WHEN barangay_code = '#' THEN 'HASH_ADDRESS3'
        WHEN barangay_code = '' THEN 'EMPTY_ADDRESS3'
        ELSE 'VALID_ADDRESS3'
    END as barangay_code_status,
    CASE
        WHEN latitude IS NULL OR longitude IS NULL OR latitude = 0 OR longitude = 0
        THEN 'STOP100'
        ELSE 'WITH_COORDS'
    END as coordinate_status
FROM routedata
WHERE Code = 'MIX-B10'
AND RouteDate = '2025-09-03'
ORDER BY barangay_code_status, coordinate_status, CustNo;

-- Query 3: Get unique barangay codes for this agent
SELECT DISTINCT
    barangay_code as barangay_code,
    COUNT(DISTINCT CustNo) as customers_with_this_code
FROM routedata
WHERE Code = 'MIX-B10'
AND RouteDate = '2025-09-03'
AND barangay_code IS NOT NULL
AND barangay_code != '#'
AND barangay_code != ''
GROUP BY barangay_code
ORDER BY COUNT(DISTINCT CustNo) DESC;

-- Query 4: Check prospects available for each barangay code
-- This shows the matching function: routedata.barangay_code = prospective.barangay_code
SELECT
    r.barangay_code as barangay_code,
    COUNT(DISTINCT r.CustNo) as customers,
    COUNT(DISTINCT p.CustNo) as available_prospects,
    'MATCHING: routedata.barangay_code = prospective.barangay_code' as matching_logic
FROM routedata r
LEFT JOIN prospective p ON r.barangay_code = p.barangay_code  -- THE MATCHING FUNCTION
    AND p.Latitude IS NOT NULL
    AND p.Longitude IS NOT NULL
    AND p.Latitude != 0
    AND p.Longitude != 0
WHERE r.Code = 'MIX-B10'
AND r.RouteDate = '2025-09-03'
AND r.barangay_code IS NOT NULL
AND r.barangay_code != '#'
AND r.barangay_code != ''
GROUP BY r.barangay_code
ORDER BY COUNT(DISTINCT p.CustNo) DESC;

-- Query 5: Complete optimization analysis for this agent
SELECT
    r.Code as agent_id,
    r.RouteDate as day,
    COUNT(DISTINCT r.CustNo) as current_customers,
    COUNT(DISTINCT CASE
        WHEN r.barangay_code IS NOT NULL AND r.barangay_code != '#' AND r.barangay_code != ''
        THEN r.CustNo
    END) as customers_with_valid_barangay_code,
    COUNT(DISTINCT CASE
        WHEN r.barangay_code IS NULL OR r.barangay_code = '#' OR r.barangay_code = ''
        THEN r.CustNo
    END) as customers_without_valid_barangay_code,
    COUNT(DISTINCT p.CustNo) as total_prospects_available,
    (60 - COUNT(DISTINCT r.CustNo)) as need_to_reach_60,
    CASE
        WHEN COUNT(DISTINCT p.CustNo) >= (60 - COUNT(DISTINCT r.CustNo))
        THEN 'CAN_REACH_60_WITH_PROSPECTS'
        WHEN COUNT(DISTINCT p.CustNo) > 0
        THEN 'PARTIAL_FILL_POSSIBLE'
        ELSE 'NO_PROSPECTS_AVAILABLE'
    END as optimization_potential,
    STRING_AGG(DISTINCT r.barangay_code, ', ') as barangay_codes_used
FROM routedata r
LEFT JOIN prospective p ON r.barangay_code = p.barangay_code  -- THE MATCHING FUNCTION
    AND p.Latitude IS NOT NULL
    AND p.Longitude IS NOT NULL
    AND p.Latitude != 0
    AND p.Longitude != 0
WHERE r.Code = 'MIX-B10'
AND r.RouteDate = '2025-09-03'
GROUP BY r.Code, r.RouteDate;

-- Query 6: Show sample prospects that would be added
-- Based on the matching function results
SELECT TOP 10
    p.CustNo as prospect_id,
    p.Latitude,
    p.Longitude,
    p.barangay_code,
    r.barangay_code as customer_barangay_code,
    'MATCH_CONFIRMED' as matching_status
FROM routedata r
INNER JOIN prospective p ON r.barangay_code = p.barangay_code  -- THE MATCHING FUNCTION
WHERE r.Code = 'MIX-B10'
AND r.RouteDate = '2025-09-03'
AND r.barangay_code IS NOT NULL
AND r.barangay_code != '#'
AND r.barangay_code != ''
AND p.Latitude IS NOT NULL
AND p.Longitude IS NOT NULL
AND p.Latitude != 0
AND p.Longitude != 0
ORDER BY p.CustNo;

-- Query 7: Route optimization simulation
-- Shows what the final route would look like
SELECT
    'CURRENT_CUSTOMERS' as customer_type,
    CustNo,
    latitude,
    longitude,
    barangay_code as barangay_code,
    CASE
        WHEN latitude IS NULL OR longitude IS NULL OR latitude = 0 OR longitude = 0
        THEN 100  -- Stop100 for customers without coordinates
        ELSE ROW_NUMBER() OVER (ORDER BY CustNo)  -- Sequential stop numbers for TSP
    END as suggested_stopno
FROM routedata
WHERE Code = 'MIX-B10'
AND RouteDate = '2025-09-03'

UNION ALL

SELECT
    'ADDED_PROSPECTS' as customer_type,
    p.CustNo,
    p.Latitude as latitude,
    p.Longitude as longitude,
    p.barangay_code,
    (SELECT COUNT(DISTINCT CustNo) FROM routedata WHERE Code = 'MIX-B10' AND RouteDate = '2025-09-03')
    + ROW_NUMBER() OVER (ORDER BY p.CustNo) as suggested_stopno
FROM routedata r
INNER JOIN prospective p ON r.barangay_code = p.barangay_code  -- THE MATCHING FUNCTION
WHERE r.Code = 'MIX-B10'
AND r.RouteDate = '2025-09-03'
AND r.barangay_code IS NOT NULL
AND r.barangay_code != '#'
AND r.barangay_code != ''
AND p.Latitude IS NOT NULL
AND p.Longitude IS NOT NULL
AND p.Latitude != 0
AND p.Longitude != 0
AND p.CustNo IN (
    SELECT TOP 20 p2.CustNo  -- Add up to 20 prospects to reach closer to 60
    FROM routedata r2
    INNER JOIN prospective p2 ON r2.barangay_code = p2.barangay_code
    WHERE r2.Code = 'MIX-B10'
    AND r2.RouteDate = '2025-09-03'
    AND p2.Latitude IS NOT NULL
    AND p2.Longitude IS NOT NULL
    ORDER BY p2.CustNo
)
ORDER BY customer_type, suggested_stopno;