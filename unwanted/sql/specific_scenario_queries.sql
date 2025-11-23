-- SPECIFIC SCENARIO SQL QUERIES
-- Find agents and specific days for 3 targeted scenarios

-- =============================================================================
-- SCENARIO 1: AGENT WITH GREATER THAN 60 CUSTOMERS
-- =============================================================================

-- Find agents with more than 60 customers on specific days
SELECT TOP 10
    'SCENARIO_1_MORE_THAN_60' as scenario_type,
    Code as agent_id,
    RouteDate as route_date,
    COUNT(DISTINCT CustNo) as customer_count,
    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
               AND latitude != 0 AND longitude != 0 THEN 1 END) as customers_with_valid_coords,
    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
               OR latitude = 0 OR longitude = 0 THEN 1 END) as customers_without_coords,
    COUNT(DISTINCT CASE WHEN barangay_code IS NOT NULL
                        AND barangay_code != '#'
                        AND barangay_code != ''
                        THEN barangay_code END) as unique_barangay_codes,
    'NO_PROSPECTS_NEEDED' as optimization_status
FROM routedata
WHERE Code IS NOT NULL
GROUP BY Code, RouteDate
HAVING COUNT(DISTINCT CustNo) > 60
ORDER BY COUNT(DISTINCT CustNo) DESC;

-- Detailed breakdown for a specific agent with >60 customers
-- Usage: Replace 'AGENT_ID' and 'ROUTE_DATE' with actual values from above query
/*
SELECT
    CustNo,
    latitude,
    longitude,
    barangay_code,
    custype,
    Name,
    CASE
        WHEN latitude IS NULL OR longitude IS NULL OR latitude = 0 OR longitude = 0
        THEN 'STOP100_CUSTOMER'
        ELSE 'VALID_COORDINATES'
    END as coordinate_status,
    CASE
        WHEN barangay_code IS NULL OR barangay_code = '#' OR barangay_code = ''
        THEN 'INVALID_BARANGAY'
        ELSE 'VALID_BARANGAY'
    END as barangay_status
FROM routedata
WHERE Code = 'AGENT_ID' AND RouteDate = 'ROUTE_DATE'
ORDER BY coordinate_status, barangay_status, CustNo;
*/

-- =============================================================================
-- SCENARIO 2: AGENT WITH 20-60 CUSTOMERS + PROSPECTS (MAY HAVE INVALID COORDS)
-- =============================================================================

-- Find agents with 20-60 customers that have prospects available (coords not required for prospects)
SELECT TOP 10
    'SCENARIO_2_PROSPECTS_ANY_COORDS' as scenario_type,
    r.Code as agent_id,
    r.RouteDate as route_date,
    COUNT(DISTINCT r.CustNo) as customer_count,
    COUNT(CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
               AND r.latitude != 0 AND r.longitude != 0 THEN 1 END) as customers_with_coords,
    COUNT(CASE WHEN r.latitude IS NULL OR r.longitude IS NULL
               OR r.latitude = 0 OR r.longitude = 0 THEN 1 END) as customers_stop100,
    COUNT(DISTINCT r.barangay_code) as unique_customer_barangay_codes,
    COUNT(DISTINCT p.CustNo) as total_prospects_available,
    COUNT(DISTINCT CASE WHEN p.Latitude IS NOT NULL AND p.Longitude IS NOT NULL
                        AND p.Latitude != 0 AND p.Longitude != 0
                        THEN p.CustNo END) as prospects_with_valid_coords,
    COUNT(DISTINCT CASE WHEN p.Latitude IS NULL OR p.Longitude IS NULL
                        OR p.Latitude = 0 OR p.Longitude = 0
                        THEN p.CustNo END) as prospects_with_invalid_coords,
    (60 - COUNT(DISTINCT r.CustNo)) as prospects_needed,
    CASE
        WHEN COUNT(DISTINCT p.CustNo) >= (60 - COUNT(DISTINCT r.CustNo))
        THEN 'CAN_REACH_60'
        ELSE 'PARTIAL_FILL'
    END as optimization_capability
FROM routedata r
INNER JOIN prospective p ON r.barangay_code = p.barangay_code
WHERE r.Code IS NOT NULL
AND r.barangay_code IS NOT NULL
AND r.barangay_code != '#'
AND r.barangay_code != ''
GROUP BY r.Code, r.RouteDate
HAVING COUNT(DISTINCT r.CustNo) BETWEEN 20 AND 60
AND COUNT(DISTINCT p.CustNo) > 0
ORDER BY COUNT(DISTINCT p.CustNo) DESC;

-- Detailed analysis for a specific agent from Scenario 2
-- Usage: Replace 'AGENT_ID' and 'ROUTE_DATE' with values from above query
/*
-- Customer details
SELECT
    'CUSTOMERS' as record_type,
    CustNo,
    latitude,
    longitude,
    barangay_code,
    custype,
    Name,
    CASE
        WHEN latitude IS NULL OR longitude IS NULL OR latitude = 0 OR longitude = 0
        THEN 'STOP100'
        ELSE 'VALID_COORDS'
    END as coordinate_status
FROM routedata
WHERE Code = 'AGENT_ID' AND RouteDate = 'ROUTE_DATE'

UNION ALL

-- Available prospects (any coordinates)
SELECT
    'PROSPECTS' as record_type,
    CustNo,
    Latitude as latitude,
    Longitude as longitude,
    barangay_code,
    'prospect' as custype,
    OutletName as Name,
    CASE
        WHEN Latitude IS NULL OR Longitude IS NULL OR Latitude = 0 OR Longitude = 0
        THEN 'INVALID_COORDS'
        ELSE 'VALID_COORDS'
    END as coordinate_status
FROM prospective p
WHERE barangay_code IN (
    SELECT DISTINCT barangay_code
    FROM routedata
    WHERE Code = 'AGENT_ID' AND RouteDate = 'ROUTE_DATE'
    AND barangay_code IS NOT NULL AND barangay_code != '#' AND barangay_code != ''
)
ORDER BY record_type, coordinate_status, CustNo;
*/

-- =============================================================================
-- SCENARIO 3: AGENT WITH 20-60 CUSTOMERS + PROSPECTS WITH VALID COORDINATES
-- =============================================================================


-- Find agents with 20-60 customers that have prospects with valid coordinates
SELECT TOP 10
    'SCENARIO_3_PROSPECTS_VALID_COORDS' as scenario_type,
    r.Code as agent_id,
    r.RouteDate as route_date,
    COUNT(DISTINCT r.CustNo) as customer_count,
    COUNT(CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
               AND r.latitude != 0 AND r.longitude != 0 THEN 1 END) as customers_with_coords,
    COUNT(CASE WHEN r.latitude IS NULL OR r.longitude IS NULL
               OR r.latitude = 0 OR r.longitude = 0 THEN 1 END) as customers_stop100,
    COUNT(DISTINCT r.barangay_code) as unique_customer_barangay_codes,
    COUNT(DISTINCT p.CustNo) as prospects_with_valid_coords,
    (60 - COUNT(DISTINCT r.CustNo)) as prospects_needed,
    CASE
        WHEN COUNT(DISTINCT p.CustNo) >= (60 - COUNT(DISTINCT r.CustNo))
        THEN 'CAN_REACH_60_WITH_VALID_COORDS'
        ELSE 'PARTIAL_FILL_VALID_COORDS'
    END as optimization_capability,
    AVG(CAST(p.Latitude AS FLOAT)) as avg_prospect_latitude,
    AVG(CAST(p.Longitude AS FLOAT)) as avg_prospect_longitude
FROM routedata r
INNER JOIN prospective p ON r.barangay_code = p.barangay_code
    AND p.Latitude IS NOT NULL
    AND p.Longitude IS NOT NULL
    AND p.Latitude != 0
    AND p.Longitude != 0
WHERE r.Code IS NOT NULL
AND r.barangay_code IS NOT NULL
AND r.barangay_code != '#'
AND r.barangay_code != ''
GROUP BY r.Code, r.RouteDate
HAVING COUNT(DISTINCT r.CustNo) BETWEEN 20 AND 60
AND COUNT(DISTINCT p.CustNo) > 0
ORDER BY COUNT(DISTINCT p.CustNo) DESC;

-- Detailed analysis for a specific agent from Scenario 3
-- Usage: Replace 'AGENT_ID' and 'ROUTE_DATE' with values from above query
/*
-- Customer and prospect details with distance calculations
WITH CustomerCentroid AS (
    SELECT
        AVG(CAST(latitude AS FLOAT)) as center_lat,
        AVG(CAST(longitude AS FLOAT)) as center_lon
    FROM routedata
    WHERE Code = 'AGENT_ID' AND RouteDate = 'ROUTE_DATE'
    AND latitude IS NOT NULL AND longitude IS NOT NULL
    AND latitude != 0 AND longitude != 0
),
CustomerData AS (
    SELECT
        'CUSTOMER' as record_type,
        CustNo,
        CAST(latitude AS FLOAT) as lat,
        CAST(longitude AS FLOAT) as lon,
        barangay_code,
        custype,
        Name,
        CASE
            WHEN latitude IS NULL OR longitude IS NULL OR latitude = 0 OR longitude = 0
            THEN 'STOP100'
            ELSE 'VALID_COORDS'
        END as coordinate_status
    FROM routedata
    WHERE Code = 'AGENT_ID' AND RouteDate = 'ROUTE_DATE'
),
ProspectData AS (
    SELECT
        'PROSPECT' as record_type,
        CustNo,
        CAST(Latitude AS FLOAT) as lat,
        CAST(Longitude AS FLOAT) as lon,
        barangay_code,
        'prospect' as custype,
        OutletName as Name,
        'VALID_COORDS' as coordinate_status
    FROM prospective p
    WHERE barangay_code IN (
        SELECT DISTINCT barangay_code
        FROM routedata
        WHERE Code = 'AGENT_ID' AND RouteDate = 'ROUTE_DATE'
        AND barangay_code IS NOT NULL AND barangay_code != '#' AND barangay_code != ''
    )
    AND Latitude IS NOT NULL AND Longitude IS NOT NULL
    AND Latitude != 0 AND Longitude != 0
)
SELECT
    cd.record_type,
    cd.CustNo,
    cd.lat,
    cd.lon,
    cd.barangay_code,
    cd.custype,
    cd.Name,
    cd.coordinate_status,
    CASE
        WHEN cd.coordinate_status = 'VALID_COORDS' AND cc.center_lat IS NOT NULL
        THEN SQRT(POWER(cd.lat - cc.center_lat, 2) + POWER(cd.lon - cc.center_lon, 2)) * 111.0
        ELSE NULL
    END as approx_distance_from_centroid_km
FROM (
    SELECT * FROM CustomerData
    UNION ALL
    SELECT * FROM ProspectData
) cd
CROSS JOIN CustomerCentroid cc
ORDER BY cd.record_type, cd.coordinate_status, approx_distance_from_centroid_km;
*/

-- =============================================================================
-- SUMMARY QUERY: GET ONE EXAMPLE FOR EACH SCENARIO
-- =============================================================================

-- Quick summary to get one example agent for each scenario
WITH Scenario1 AS (
    SELECT TOP 1
        1 as scenario_number,
        'MORE_THAN_60_CUSTOMERS' as scenario_name,
        Code as agent_id,
        RouteDate as route_date,
        COUNT(DISTINCT CustNo) as customer_count,
        0 as prospects_available
    FROM routedata
    WHERE Code IS NOT NULL
    GROUP BY Code, RouteDate
    HAVING COUNT(DISTINCT CustNo) > 60
    ORDER BY COUNT(DISTINCT CustNo) DESC
),
Scenario2 AS (
    SELECT TOP 1
        2 as scenario_number,
        'PROSPECTS_ANY_COORDS' as scenario_name,
        r.Code as agent_id,
        r.RouteDate as route_date,
        COUNT(DISTINCT r.CustNo) as customer_count,
        COUNT(DISTINCT p.CustNo) as prospects_available
    FROM routedata r
    INNER JOIN prospective p ON r.barangay_code = p.barangay_code
    WHERE r.Code IS NOT NULL
    AND r.barangay_code IS NOT NULL AND r.barangay_code != '#' AND r.barangay_code != ''
    GROUP BY r.Code, r.RouteDate
    HAVING COUNT(DISTINCT r.CustNo) BETWEEN 20 AND 60
    AND COUNT(DISTINCT p.CustNo) > 0
    ORDER BY COUNT(DISTINCT p.CustNo) DESC
),
Scenario3 AS (
    SELECT TOP 1
        3 as scenario_number,
        'PROSPECTS_VALID_COORDS' as scenario_name,
        r.Code as agent_id,
        r.RouteDate as route_date,
        COUNT(DISTINCT r.CustNo) as customer_count,
        COUNT(DISTINCT p.CustNo) as prospects_available
    FROM routedata r
    INNER JOIN prospective p ON r.barangay_code = p.barangay_code
        AND p.Latitude IS NOT NULL AND p.Longitude IS NOT NULL
        AND p.Latitude != 0 AND p.Longitude != 0
    WHERE r.Code IS NOT NULL
    AND r.barangay_code IS NOT NULL AND r.barangay_code != '#' AND r.barangay_code != ''
    GROUP BY r.Code, r.RouteDate
    HAVING COUNT(DISTINCT r.CustNo) BETWEEN 20 AND 60
    AND COUNT(DISTINCT p.CustNo) > 0
    ORDER BY COUNT(DISTINCT p.CustNo) DESC
)
SELECT * FROM Scenario1
UNION ALL
SELECT * FROM Scenario2
UNION ALL
SELECT * FROM Scenario3
ORDER BY scenario_number;

-- =============================================================================
-- USAGE INSTRUCTIONS
-- =============================================================================

/*
HOW TO USE THESE QUERIES:

1. Run the main scenario queries above to find agent examples
2. Copy the agent_id and route_date from the results
3. Uncomment and modify the detailed analysis queries
4. Replace 'AGENT_ID' and 'ROUTE_DATE' with actual values
5. Run the detailed queries to see customer and prospect breakdown

EXAMPLE WORKFLOW:
1. Run Scenario 3 query
2. Results show: Agent 'ABC123', Date '2025-09-15', 45 customers, 25 prospects
3. Uncomment the detailed analysis query for Scenario 3
4. Replace 'AGENT_ID' with 'ABC123' and 'ROUTE_DATE' with '2025-09-15'
5. Run to see all customers and prospects with coordinates and distances

TESTING WITH RUN_SPECIFIC_AGENTS.PY:
After finding your examples, update run_specific_agents.py:

specific_agents = [
    ("AGENT_FROM_SCENARIO_1", "DATE_FROM_SCENARIO_1"),  # >60 customers
    ("AGENT_FROM_SCENARIO_2", "DATE_FROM_SCENARIO_2"),  # 20-60 + prospects any coords
    ("AGENT_FROM_SCENARIO_3", "DATE_FROM_SCENARIO_3"),  # 20-60 + prospects valid coords
]
*/