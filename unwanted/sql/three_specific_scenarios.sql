-- THREE SPECIFIC SCENARIOS - SQL QUERIES FOR EXACT AGENT EXAMPLES
-- Based on real agents found in the database

-- =============================================================================
-- SCENARIO 1: AGENT WITH MORE THAN 60 CUSTOMERS
-- Agent: SK-SAT8, Date: 2025-09-04 (61 customers)
-- =============================================================================

-- 1.1: Get all customer details for this agent
SELECT
    'SCENARIO_1_CUSTOMER_DETAILS' as query_type,
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
    END as coordinate_status,
    CASE
        WHEN barangay_code IS NULL OR barangay_code = '#' OR barangay_code = ''
        THEN 'INVALID_BARANGAY'
        ELSE 'VALID_BARANGAY'
    END as barangay_status
FROM routedata
WHERE Code = 'SK-SAT8' AND RouteDate = '2025-09-04'
ORDER BY coordinate_status, barangay_status, CustNo;

-- 1.2: Summary statistics for this agent
SELECT
    'SCENARIO_1_SUMMARY' as query_type,
    COUNT(DISTINCT CustNo) as total_customers,
    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
               AND latitude != 0 AND longitude != 0 THEN 1 END) as customers_with_coords,
    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
               OR latitude = 0 OR longitude = 0 THEN 1 END) as customers_stop100,
    COUNT(DISTINCT CASE WHEN barangay_code IS NOT NULL
                        AND barangay_code != '#'
                        AND barangay_code != ''
                        THEN barangay_code END) as unique_barangay_codes,
    'NO_PROSPECTS_NEEDED - PROCESS_AS_IS' as optimization_strategy
FROM routedata
WHERE Code = 'SK-SAT8' AND RouteDate = '2025-09-04';

-- 1.3: Expected pipeline behavior for this scenario
/*
SCENARIO 1 EXPECTED BEHAVIOR:
- Input: 61 customers (>60)
- Pipeline action: Process without adding prospects
- TSP optimization: Apply to customers with valid coordinates
- Stop100 assignment: Customers without coordinates get stopno=100
- Output: 61 records in routeplan_ai table
- Prospect addition: NONE
*/

-- =============================================================================
-- SCENARIO 2: AGENT WITH 20-60 CUSTOMERS + PROSPECTS (MAY HAVE INVALID COORDS)
-- Agent: D304, Date: 2025-09-16 (59 customers, 739 prospects available)
-- =============================================================================

-- 2.1: Get customer details
SELECT
    'SCENARIO_2_CUSTOMERS' as query_type,
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
    END as coordinate_status,
    CASE
        WHEN barangay_code IS NULL OR barangay_code = '#' OR barangay_code = ''
        THEN 'INVALID_BARANGAY'
        ELSE 'VALID_BARANGAY'
    END as barangay_status
FROM routedata
WHERE Code = 'D304' AND RouteDate = '2025-09-16'
ORDER BY coordinate_status, barangay_status, CustNo;

-- 2.2: Get ALL available prospects (including those with invalid coordinates)
SELECT
    'SCENARIO_2_ALL_PROSPECTS' as query_type,
    p.CustNo,
    p.Latitude,
    p.Longitude,
    p.barangay_code,
    p.OutletName,
    p.Address,
    CASE
        WHEN p.Latitude IS NULL OR p.Longitude IS NULL OR p.Latitude = 0 OR p.Longitude = 0
        THEN 'INVALID_COORDS'
        ELSE 'VALID_COORDS'
    END as coordinate_status,
    'prospect' as custype
FROM prospective p
WHERE p.barangay_code IN (
    SELECT DISTINCT barangay_code
    FROM routedata
    WHERE Code = 'D304' AND RouteDate = '2025-09-16'
    AND barangay_code IS NOT NULL AND barangay_code != '#' AND barangay_code != ''
)
ORDER BY coordinate_status, p.CustNo;

-- 2.3: Summary for Scenario 2
SELECT
    'SCENARIO_2_SUMMARY' as query_type,
    customer_data.total_customers,
    customer_data.customers_with_coords,
    customer_data.customers_stop100,
    customer_data.unique_barangay_codes,
    prospect_data.total_prospects,
    prospect_data.prospects_with_valid_coords,
    prospect_data.prospects_with_invalid_coords,
    (60 - customer_data.total_customers) as prospects_needed,
    CASE
        WHEN prospect_data.total_prospects >= (60 - customer_data.total_customers)
        THEN 'CAN_REACH_60_WITH_ANY_COORDS'
        ELSE 'PARTIAL_FILL'
    END as optimization_capability
FROM (
    SELECT
        COUNT(DISTINCT CustNo) as total_customers,
        COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                   AND latitude != 0 AND longitude != 0 THEN 1 END) as customers_with_coords,
        COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                   OR latitude = 0 OR longitude = 0 THEN 1 END) as customers_stop100,
        COUNT(DISTINCT CASE WHEN barangay_code IS NOT NULL
                            AND barangay_code != '#'
                            AND barangay_code != ''
                            THEN barangay_code END) as unique_barangay_codes
    FROM routedata
    WHERE Code = 'D304' AND RouteDate = '2025-09-16'
) customer_data
CROSS JOIN (
    SELECT
        COUNT(DISTINCT p.CustNo) as total_prospects,
        COUNT(DISTINCT CASE WHEN p.Latitude IS NOT NULL AND p.Longitude IS NOT NULL
                            AND p.Latitude != 0 AND p.Longitude != 0
                            THEN p.CustNo END) as prospects_with_valid_coords,
        COUNT(DISTINCT CASE WHEN p.Latitude IS NULL OR p.Longitude IS NULL
                            OR p.Latitude = 0 OR p.Longitude = 0
                            THEN p.CustNo END) as prospects_with_invalid_coords
    FROM prospective p
    WHERE p.barangay_code IN (
        SELECT DISTINCT barangay_code
        FROM routedata
        WHERE Code = 'D304' AND RouteDate = '2025-09-16'
        AND barangay_code IS NOT NULL AND barangay_code != '#' AND barangay_code != ''
    )
) prospect_data;

-- 2.4: Expected pipeline behavior for this scenario
/*
SCENARIO 2 EXPECTED BEHAVIOR:
- Input: 59 customers (<60)
- Prospects needed: 1 prospect to reach 60
- Available prospects: 739 (including invalid coordinates)
- Pipeline action: Add 1 nearest prospect (TSP optimization on valid coords only)
- Prospect selection: Distance-based from centroid of customers with coordinates
- Output: 60 records in routeplan_ai table (59 customers + 1 prospect)
- Coordinate handling: Prospects with invalid coords may get stopno=100
*/

-- =============================================================================
-- SCENARIO 3: AGENT WITH 20-60 CUSTOMERS + PROSPECTS WITH VALID COORDINATES ONLY
-- Agent: D304, Date: 2025-09-16 (59 customers, 739 prospects with valid coords)
-- =============================================================================

-- 3.1: Get customer details (same as Scenario 2)
SELECT
    'SCENARIO_3_CUSTOMERS' as query_type,
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
WHERE Code = 'D304' AND RouteDate = '2025-09-16'
ORDER BY coordinate_status, CustNo;

-- 3.2: Get ONLY prospects with valid coordinates
SELECT
    'SCENARIO_3_VALID_PROSPECTS' as query_type,
    p.CustNo,
    p.Latitude,
    p.Longitude,
    p.barangay_code,
    p.OutletName,
    p.Address,
    'VALID_COORDS' as coordinate_status,
    'prospect' as custype
FROM prospective p
WHERE p.barangay_code IN (
    SELECT DISTINCT barangay_code
    FROM routedata
    WHERE Code = 'D304' AND RouteDate = '2025-09-16'
    AND barangay_code IS NOT NULL AND barangay_code != '#' AND barangay_code != ''
)
AND p.Latitude IS NOT NULL
AND p.Longitude IS NOT NULL
AND p.Latitude != 0
AND p.Longitude != 0
ORDER BY p.CustNo;

-- 3.3: Calculate distances from customer centroid for TSP optimization preview
WITH CustomerCentroid AS (
    SELECT
        AVG(CAST(latitude AS FLOAT)) as center_lat,
        AVG(CAST(longitude AS FLOAT)) as center_lon
    FROM routedata
    WHERE Code = 'D304' AND RouteDate = '2025-09-16'
    AND latitude IS NOT NULL AND longitude IS NOT NULL
    AND latitude != 0 AND longitude != 0
),
ProspectsWithDistance AS (
    SELECT
        'SCENARIO_3_PROSPECT_DISTANCES' as query_type,
        p.CustNo,
        p.Latitude,
        p.Longitude,
        p.barangay_code,
        p.OutletName,
        -- Calculate approximate distance using Haversine formula
        (6371 * ACOS(
            COS(RADIANS(cc.center_lat)) *
            COS(RADIANS(CAST(p.Latitude AS FLOAT))) *
            COS(RADIANS(CAST(p.Longitude AS FLOAT)) - RADIANS(cc.center_lon)) +
            SIN(RADIANS(cc.center_lat)) *
            SIN(RADIANS(CAST(p.Latitude AS FLOAT)))
        )) as distance_from_centroid_km
    FROM prospective p
    CROSS JOIN CustomerCentroid cc
    WHERE p.barangay_code IN (
        SELECT DISTINCT barangay_code
        FROM routedata
        WHERE Code = 'D304' AND RouteDate = '2025-09-16'
        AND barangay_code IS NOT NULL AND barangay_code != '#' AND barangay_code != ''
    )
    AND p.Latitude IS NOT NULL AND p.Longitude IS NOT NULL
    AND p.Latitude != 0 AND p.Longitude != 0
)
SELECT TOP 10 *
FROM ProspectsWithDistance
ORDER BY distance_from_centroid_km ASC;

-- 3.4: Summary for Scenario 3
SELECT
    'SCENARIO_3_SUMMARY' as query_type,
    customer_data.total_customers,
    customer_data.customers_with_coords,
    customer_data.customers_stop100,
    prospect_data.prospects_with_valid_coords,
    (60 - customer_data.total_customers) as prospects_needed,
    'CAN_REACH_60_WITH_PERFECT_TSP' as optimization_capability,
    'ALL_PROSPECTS_HAVE_VALID_COORDINATES' as coordinate_quality
FROM (
    SELECT
        COUNT(DISTINCT CustNo) as total_customers,
        COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                   AND latitude != 0 AND longitude != 0 THEN 1 END) as customers_with_coords,
        COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                   OR latitude = 0 OR longitude = 0 THEN 1 END) as customers_stop100
    FROM routedata
    WHERE Code = 'D304' AND RouteDate = '2025-09-16'
) customer_data
CROSS JOIN (
    SELECT
        COUNT(DISTINCT p.CustNo) as prospects_with_valid_coords
    FROM prospective p
    WHERE p.barangay_code IN (
        SELECT DISTINCT barangay_code
        FROM routedata
        WHERE Code = 'D304' AND RouteDate = '2025-09-16'
        AND barangay_code IS NOT NULL AND barangay_code != '#' AND barangay_code != ''
    )
    AND p.Latitude IS NOT NULL AND p.Longitude IS NOT NULL
    AND p.Latitude != 0 AND p.Longitude != 0
) prospect_data;

-- 3.5: Expected pipeline behavior for this scenario
/*
SCENARIO 3 EXPECTED BEHAVIOR:
- Input: 59 customers (<60)
- Prospects needed: 1 prospect to reach 60
- Available prospects: 739 (ALL with valid coordinates)
- Pipeline action: Add 1 nearest prospect with perfect TSP optimization
- Prospect selection: Distance-based from centroid, guaranteed valid coordinates
- TSP optimization: Perfect optimization possible (all points have coordinates)
- Output: 60 records in routeplan_ai table with optimized stop sequence
- No Stop100 prospects: All added prospects will have valid coordinates
*/

-- =============================================================================
-- COMBINED ANALYSIS: ALL THREE SCENARIOS
-- =============================================================================

-- Compare all three scenarios side by side
SELECT
    'COMBINED_SCENARIO_COMPARISON' as analysis_type,
    scenario_info.*
FROM (
    SELECT
        1 as scenario_number,
        'SCENARIO_1_MORE_THAN_60' as scenario_name,
        'SK-SAT8' as agent_id,
        '2025-09-04' as route_date,
        COUNT(DISTINCT CustNo) as customers,
        0 as prospects_needed,
        'NO_PROSPECTS' as prospect_strategy,
        COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                   AND latitude != 0 AND longitude != 0 THEN 1 END) as customers_with_coords
    FROM routedata
    WHERE Code = 'SK-SAT8' AND RouteDate = '2025-09-04'

    UNION ALL

    SELECT
        2 as scenario_number,
        'SCENARIO_2_PROSPECTS_ANY_COORDS' as scenario_name,
        'D304' as agent_id,
        '2025-09-16' as route_date,
        COUNT(DISTINCT r.CustNo) as customers,
        (60 - COUNT(DISTINCT r.CustNo)) as prospects_needed,
        'PROSPECTS_ANY_COORDS' as prospect_strategy,
        COUNT(CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
                   AND r.latitude != 0 AND r.longitude != 0 THEN 1 END) as customers_with_coords
    FROM routedata r
    WHERE r.Code = 'D304' AND r.RouteDate = '2025-09-16'

    UNION ALL

    SELECT
        3 as scenario_number,
        'SCENARIO_3_PROSPECTS_VALID_COORDS' as scenario_name,
        'D304' as agent_id,
        '2025-09-16' as route_date,
        COUNT(DISTINCT r.CustNo) as customers,
        (60 - COUNT(DISTINCT r.CustNo)) as prospects_needed,
        'PROSPECTS_VALID_COORDS_ONLY' as prospect_strategy,
        COUNT(CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
                   AND r.latitude != 0 AND r.longitude != 0 THEN 1 END) as customers_with_coords
    FROM routedata r
    WHERE r.Code = 'D304' AND r.RouteDate = '2025-09-16'
) scenario_info
ORDER BY scenario_number;

-- =============================================================================
-- USAGE INSTRUCTIONS
-- =============================================================================

/*
TO TEST THESE SCENARIOS:

1. Update core/run_specific_agents.py:
   specific_agents = [
       ("SK-SAT8", "2025-09-04"),  # SCENARIO 1: >60 customers
       ("D304", "2025-09-16"),     # SCENARIO 2: prospects any coords
       ("D304", "2025-09-16"),     # SCENARIO 3: prospects valid coords only
   ]

2. Run the pipeline:
   python core/run_specific_agents.py

3. Verify results in routeplan_ai table:
   SELECT salesagent, routedate, COUNT(*) as total_records,
          SUM(CASE WHEN custype='customer' THEN 1 ELSE 0 END) as customers,
          SUM(CASE WHEN custype='prospect' THEN 1 ELSE 0 END) as prospects
   FROM routeplan_ai
   WHERE (salesagent='SK-SAT8' AND routedate='2025-09-04')
      OR (salesagent='D304' AND routedate='2025-09-16')
   GROUP BY salesagent, routedate
   ORDER BY salesagent, routedate;

EXPECTED RESULTS:
- SK-SAT8, 2025-09-04: 61 records (61 customers, 0 prospects)
- D304, 2025-09-16: 60 records (59 customers, 1 prospect)

SCENARIO DIFFERENCES:
- Scenario 1: Tests processing >60 customers without prospect addition
- Scenario 2: Tests prospect addition with mixed coordinate quality
- Scenario 3: Tests prospect addition with guaranteed valid coordinates
*/