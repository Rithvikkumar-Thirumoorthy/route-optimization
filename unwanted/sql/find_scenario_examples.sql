-- FIND REAL AGENTS AND DAYS FOR ALL SCENARIOS
-- This script finds actual examples of each scenario type from the database
-- READ-ONLY: Only SELECT statements, no data modification

-- =============================================================================
-- SCENARIO 1: AGENTS WITH EXACTLY 60 CUSTOMERS
-- =============================================================================

-- Find agents with exactly 60 customers
SELECT TOP 5
    'SCENARIO_1_EXACTLY_60' as scenario_type,
    Code as agent_id,
    RouteDate as route_date,
    COUNT(DISTINCT CustNo) as customer_count,
    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
               AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
               OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count
FROM routedata
WHERE Code IS NOT NULL
GROUP BY Code, RouteDate
HAVING COUNT(DISTINCT CustNo) = 60
ORDER BY Code, RouteDate;

-- =============================================================================
-- SCENARIO 2: AGENTS WITH MORE THAN 60 CUSTOMERS
-- =============================================================================

-- Find agents with more than 60 customers
SELECT TOP 5
    'SCENARIO_2_MORE_THAN_60' as scenario_type,
    Code as agent_id,
    RouteDate as route_date,
    COUNT(DISTINCT CustNo) as customer_count,
    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
               AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
               OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count
FROM routedata
WHERE Code IS NOT NULL
GROUP BY Code, RouteDate
HAVING COUNT(DISTINCT CustNo) > 60
ORDER BY COUNT(DISTINCT CustNo) DESC;

-- =============================================================================
-- SCENARIO 3: AGENTS WITH LESS THAN 60 CUSTOMERS
-- =============================================================================

-- Find agents with less than 60 customers (most common scenario for optimization)
SELECT TOP 10
    'SCENARIO_3_LESS_THAN_60' as scenario_type,
    Code as agent_id,
    RouteDate as route_date,
    COUNT(DISTINCT CustNo) as customer_count,
    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
               AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
               OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count,
    (60 - COUNT(DISTINCT CustNo)) as prospects_needed
FROM routedata
WHERE Code IS NOT NULL
GROUP BY Code, RouteDate
HAVING COUNT(DISTINCT CustNo) < 60
ORDER BY COUNT(DISTINCT CustNo) DESC;

-- =============================================================================
-- SCENARIO 4: ALL CUSTOMERS HAVE VALID COORDINATES
-- =============================================================================

-- Find agents where ALL customers have valid coordinates
SELECT TOP 5
    'SCENARIO_4_ALL_VALID_COORDS' as scenario_type,
    Code as agent_id,
    RouteDate as route_date,
    COUNT(DISTINCT CustNo) as customer_count,
    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
               AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
               OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count
FROM routedata
WHERE Code IS NOT NULL
GROUP BY Code, RouteDate
HAVING COUNT(DISTINCT CustNo) < 60
AND COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
              OR latitude = 0 OR longitude = 0 THEN 1 END) = 0
ORDER BY COUNT(DISTINCT CustNo) DESC;

-- =============================================================================
-- SCENARIO 5: MIX OF CUSTOMERS WITH AND WITHOUT COORDINATES
-- =============================================================================

-- Find agents with mixed coordinate quality
SELECT TOP 5
    'SCENARIO_5_MIXED_COORDINATES' as scenario_type,
    Code as agent_id,
    RouteDate as route_date,
    COUNT(DISTINCT CustNo) as customer_count,
    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
               AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
               OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count,
    CAST(COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                   OR latitude = 0 OR longitude = 0 THEN 1 END) * 100.0 / COUNT(*) AS DECIMAL(5,1)) as stop100_percentage
FROM routedata
WHERE Code IS NOT NULL
GROUP BY Code, RouteDate
HAVING COUNT(DISTINCT CustNo) < 60
AND COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
              AND latitude != 0 AND longitude != 0 THEN 1 END) > 0
AND COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
              OR latitude = 0 OR longitude = 0 THEN 1 END) > 0
ORDER BY COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                   OR latitude = 0 OR longitude = 0 THEN 1 END) DESC;

-- =============================================================================
-- SCENARIO 6: ALL CUSTOMERS WITHOUT VALID COORDINATES
-- =============================================================================

-- Find agents where ALL customers lack coordinates (rare but possible)
SELECT TOP 3
    'SCENARIO_6_ALL_INVALID_COORDS' as scenario_type,
    Code as agent_id,
    RouteDate as route_date,
    COUNT(DISTINCT CustNo) as customer_count,
    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
               AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
               OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count
FROM routedata
WHERE Code IS NOT NULL
GROUP BY Code, RouteDate
HAVING COUNT(DISTINCT CustNo) < 60
AND COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
              AND latitude != 0 AND longitude != 0 THEN 1 END) = 0
ORDER BY COUNT(DISTINCT CustNo) DESC;

-- =============================================================================
-- SCENARIO 8: CUSTOMERS WITH VALID BARANGAY CODES
-- =============================================================================

-- Find agents with valid barangay codes for prospect matching
SELECT TOP 5
    'SCENARIO_8_VALID_BARANGAY_CODES' as scenario_type,
    Code as agent_id,
    RouteDate as route_date,
    COUNT(DISTINCT CustNo) as customer_count,
    COUNT(DISTINCT CASE WHEN barangay_code IS NOT NULL
                        AND barangay_code != '#'
                        AND barangay_code != ''
                        THEN CustNo END) as customers_with_valid_barangay,
    COUNT(DISTINCT CASE WHEN barangay_code IS NOT NULL
                        AND barangay_code != '#'
                        AND barangay_code != ''
                        THEN barangay_code END) as unique_barangay_codes
FROM routedata
WHERE Code IS NOT NULL
GROUP BY Code, RouteDate
HAVING COUNT(DISTINCT CustNo) < 60
AND COUNT(DISTINCT CASE WHEN barangay_code IS NOT NULL
                         AND barangay_code != '#'
                         AND barangay_code != ''
                         THEN CustNo END) > 0
ORDER BY COUNT(DISTINCT CASE WHEN barangay_code IS NOT NULL
                             AND barangay_code != '#'
                             AND barangay_code != ''
                             THEN barangay_code END) DESC;

-- =============================================================================
-- SCENARIO 9: CUSTOMERS WITH INVALID BARANGAY CODES
-- =============================================================================

-- Find agents with mostly invalid barangay codes
SELECT TOP 5
    'SCENARIO_9_INVALID_BARANGAY_CODES' as scenario_type,
    Code as agent_id,
    RouteDate as route_date,
    COUNT(DISTINCT CustNo) as customer_count,
    COUNT(DISTINCT CASE WHEN barangay_code IS NULL
                        OR barangay_code = '#'
                        OR barangay_code = ''
                        THEN CustNo END) as customers_with_invalid_barangay,
    COUNT(DISTINCT CASE WHEN barangay_code IS NOT NULL
                        AND barangay_code != '#'
                        AND barangay_code != ''
                        THEN CustNo END) as customers_with_valid_barangay
FROM routedata
WHERE Code IS NOT NULL
GROUP BY Code, RouteDate
HAVING COUNT(DISTINCT CustNo) < 60
AND COUNT(DISTINCT CASE WHEN barangay_code IS NULL
                         OR barangay_code = '#'
                         OR barangay_code = ''
                         THEN CustNo END) >
    COUNT(DISTINCT CASE WHEN barangay_code IS NOT NULL
                         AND barangay_code != '#'
                         AND barangay_code != ''
                         THEN CustNo END)
ORDER BY COUNT(DISTINCT CASE WHEN barangay_code IS NULL
                             OR barangay_code = '#'
                             OR barangay_code = ''
                             THEN CustNo END) DESC;

-- =============================================================================
-- SCENARIO 10: MIXED BARANGAY CODE QUALITY
-- =============================================================================

-- Find agents with mixed barangay code quality
SELECT TOP 5
    'SCENARIO_10_MIXED_BARANGAY_QUALITY' as scenario_type,
    Code as agent_id,
    RouteDate as route_date,
    COUNT(DISTINCT CustNo) as customer_count,
    COUNT(DISTINCT CASE WHEN barangay_code IS NOT NULL
                        AND barangay_code != '#'
                        AND barangay_code != ''
                        THEN CustNo END) as valid_barangay_customers,
    COUNT(DISTINCT CASE WHEN barangay_code IS NULL
                        OR barangay_code = '#'
                        OR barangay_code = ''
                        THEN CustNo END) as invalid_barangay_customers,
    COUNT(DISTINCT CASE WHEN barangay_code IS NOT NULL
                        AND barangay_code != '#'
                        AND barangay_code != ''
                        THEN barangay_code END) as unique_valid_barangay_codes
FROM routedata
WHERE Code IS NOT NULL
GROUP BY Code, RouteDate
HAVING COUNT(DISTINCT CustNo) < 60
AND COUNT(DISTINCT CASE WHEN barangay_code IS NOT NULL
                         AND barangay_code != '#'
                         AND barangay_code != ''
                         THEN CustNo END) > 0
AND COUNT(DISTINCT CASE WHEN barangay_code IS NULL
                         OR barangay_code = '#'
                         OR barangay_code = ''
                         THEN CustNo END) > 0
ORDER BY COUNT(DISTINCT CASE WHEN barangay_code IS NOT NULL
                             AND barangay_code != '#'
                             AND barangay_code != ''
                             THEN barangay_code END) DESC;

-- =============================================================================
-- SCENARIO 11: PROSPECTS AVAILABLE IN SAME BARANGAY
-- =============================================================================

-- Find agents with customers that have matching prospects in same barangay
SELECT TOP 5
    'SCENARIO_11_PROSPECTS_AVAILABLE' as scenario_type,
    r.Code as agent_id,
    r.RouteDate as route_date,
    COUNT(DISTINCT r.CustNo) as customer_count,
    COUNT(DISTINCT r.barangay_code) as unique_barangay_codes,
    COUNT(DISTINCT p.CustNo) as available_prospects,
    (60 - COUNT(DISTINCT r.CustNo)) as prospects_needed,
    CASE
        WHEN COUNT(DISTINCT p.CustNo) >= (60 - COUNT(DISTINCT r.CustNo))
        THEN 'CAN_REACH_60'
        ELSE 'PARTIAL_FILL'
    END as fill_capability
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
HAVING COUNT(DISTINCT r.CustNo) < 60
AND COUNT(DISTINCT p.CustNo) > 0
ORDER BY COUNT(DISTINCT p.CustNo) DESC;

-- =============================================================================
-- SCENARIO 12: NO PROSPECTS IN SAME BARANGAY (NEED FALLBACK)
-- =============================================================================

-- Find agents that need fallback prospect search (no same-barangay prospects)
SELECT TOP 5
    'SCENARIO_12_NO_SAME_BARANGAY_PROSPECTS' as scenario_type,
    Code as agent_id,
    RouteDate as route_date,
    COUNT(DISTINCT CustNo) as customer_count,
    COUNT(DISTINCT CASE WHEN barangay_code IS NOT NULL
                        AND barangay_code != '#'
                        AND barangay_code != ''
                        THEN barangay_code END) as unique_barangay_codes,
    (60 - COUNT(DISTINCT CustNo)) as prospects_needed
FROM routedata r
WHERE Code IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM prospective p
    WHERE p.barangay_code = r.barangay_code
    AND p.Latitude IS NOT NULL
    AND p.Longitude IS NOT NULL
    AND p.Latitude != 0
    AND p.Longitude != 0
)
GROUP BY Code, RouteDate
HAVING COUNT(DISTINCT CustNo) < 60
AND COUNT(DISTINCT CASE WHEN barangay_code IS NOT NULL
                         AND barangay_code != '#'
                         AND barangay_code != ''
                         THEN barangay_code END) > 0
ORDER BY COUNT(DISTINCT CustNo) DESC;

-- =============================================================================
-- SCENARIO 13: INSUFFICIENT PROSPECTS TO REACH 60
-- =============================================================================

-- Find agents where available prospects < needed count
SELECT TOP 5
    'SCENARIO_13_INSUFFICIENT_PROSPECTS' as scenario_type,
    r.Code as agent_id,
    r.RouteDate as route_date,
    COUNT(DISTINCT r.CustNo) as customer_count,
    COUNT(DISTINCT p.CustNo) as available_prospects,
    (60 - COUNT(DISTINCT r.CustNo)) as prospects_needed,
    (COUNT(DISTINCT r.CustNo) + COUNT(DISTINCT p.CustNo)) as max_possible_total
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
HAVING COUNT(DISTINCT r.CustNo) < 60
AND COUNT(DISTINCT p.CustNo) > 0
AND COUNT(DISTINCT p.CustNo) < (60 - COUNT(DISTINCT r.CustNo))
ORDER BY COUNT(DISTINCT p.CustNo) ASC;

-- =============================================================================
-- SCENARIO 14: ABUNDANT PROSPECTS AVAILABLE
-- =============================================================================

-- Find agents with abundant prospects (more than needed)
SELECT TOP 5
    'SCENARIO_14_ABUNDANT_PROSPECTS' as scenario_type,
    r.Code as agent_id,
    r.RouteDate as route_date,
    COUNT(DISTINCT r.CustNo) as customer_count,
    COUNT(DISTINCT p.CustNo) as available_prospects,
    (60 - COUNT(DISTINCT r.CustNo)) as prospects_needed,
    (COUNT(DISTINCT p.CustNo) - (60 - COUNT(DISTINCT r.CustNo))) as excess_prospects
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
HAVING COUNT(DISTINCT r.CustNo) < 60
AND COUNT(DISTINCT p.CustNo) >= (60 - COUNT(DISTINCT r.CustNo))
ORDER BY (COUNT(DISTINCT p.CustNo) - (60 - COUNT(DISTINCT r.CustNo))) DESC;

-- =============================================================================
-- SCENARIO 33: SINGLE CUSTOMER AGENTS
-- =============================================================================

-- Find agents with only 1 customer (need 59 prospects)
SELECT TOP 3
    'SCENARIO_33_SINGLE_CUSTOMER' as scenario_type,
    Code as agent_id,
    RouteDate as route_date,
    COUNT(DISTINCT CustNo) as customer_count,
    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
               AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
               OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count,
    59 as prospects_needed
FROM routedata
WHERE Code IS NOT NULL
GROUP BY Code, RouteDate
HAVING COUNT(DISTINCT CustNo) = 1
ORDER BY Code, RouteDate;

-- =============================================================================
-- SCENARIO 34: AGENTS WITH ONLY STOP100 CUSTOMERS
-- =============================================================================

-- Find agents where ALL customers are Stop100 (no coordinates)
SELECT TOP 3
    'SCENARIO_34_ALL_STOP100' as scenario_type,
    Code as agent_id,
    RouteDate as route_date,
    COUNT(DISTINCT CustNo) as customer_count,
    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
               AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
               OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count
FROM routedata
WHERE Code IS NOT NULL
GROUP BY Code, RouteDate
HAVING COUNT(DISTINCT CustNo) < 60
AND COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
              AND latitude != 0 AND longitude != 0 THEN 1 END) = 0
AND COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
              OR latitude = 0 OR longitude = 0 THEN 1 END) > 0
ORDER BY COUNT(DISTINCT CustNo) DESC;

-- =============================================================================
-- HIGH-VALUE SCENARIO EXAMPLES
-- =============================================================================

-- Find the best examples for testing (agents with good data quality)
SELECT TOP 3
    'HIGH_VALUE_TESTING_AGENTS' as scenario_type,
    r.Code as agent_id,
    r.RouteDate as route_date,
    COUNT(DISTINCT r.CustNo) as customer_count,
    COUNT(DISTINCT CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
                        AND r.latitude != 0 AND r.longitude != 0
                        THEN r.CustNo END) as customers_with_coords,
    COUNT(DISTINCT CASE WHEN r.barangay_code IS NOT NULL
                        AND r.barangay_code != '#'
                        AND r.barangay_code != ''
                        THEN r.barangay_code END) as valid_barangay_codes,
    COUNT(DISTINCT p.CustNo) as available_prospects,
    (60 - COUNT(DISTINCT r.CustNo)) as prospects_needed,
    'IDEAL_FOR_TESTING' as recommendation
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
HAVING COUNT(DISTINCT r.CustNo) BETWEEN 40 AND 59  -- Good base for testing
AND COUNT(DISTINCT CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
                         AND r.latitude != 0 AND r.longitude != 0
                         THEN r.CustNo END) >= (COUNT(DISTINCT r.CustNo) * 0.8)  -- 80%+ have coordinates
AND COUNT(DISTINCT p.CustNo) >= (60 - COUNT(DISTINCT r.CustNo))  -- Sufficient prospects
ORDER BY COUNT(DISTINCT p.CustNo) DESC;

-- =============================================================================
-- SPECIFIC WORKING EXAMPLES (KNOWN GOOD AGENTS)
-- =============================================================================

-- Check specific agents mentioned in previous analysis
SELECT
    'KNOWN_WORKING_EXAMPLES' as scenario_type,
    agent_data.agent_id,
    agent_data.route_date,
    agent_data.customer_count,
    agent_data.customers_with_coords,
    agent_data.valid_barangay_codes,
    COALESCE(prospect_data.available_prospects, 0) as available_prospects,
    (60 - agent_data.customer_count) as prospects_needed,
    CASE
        WHEN COALESCE(prospect_data.available_prospects, 0) >= (60 - agent_data.customer_count)
        THEN 'CAN_REACH_60'
        ELSE 'PARTIAL_FILL'
    END as fill_capability
FROM (
    SELECT
        Code as agent_id,
        RouteDate as route_date,
        COUNT(DISTINCT CustNo) as customer_count,
        COUNT(DISTINCT CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                            AND latitude != 0 AND longitude != 0
                            THEN CustNo END) as customers_with_coords,
        COUNT(DISTINCT CASE WHEN barangay_code IS NOT NULL
                            AND barangay_code != '#'
                            AND barangay_code != ''
                            THEN barangay_code END) as valid_barangay_codes
    FROM routedata
    WHERE Code IN ('914', '10551', 'SK-PMS2', 'D305', 'SK-SAT5', 'MVP-SAT2', 'OL-07', 'SMDLZ-1')
    GROUP BY Code, RouteDate
) agent_data
LEFT JOIN (
    SELECT
        r.Code as agent_id,
        r.RouteDate as route_date,
        COUNT(DISTINCT p.CustNo) as available_prospects
    FROM routedata r
    INNER JOIN prospective p ON r.barangay_code = p.barangay_code
        AND p.Latitude IS NOT NULL
        AND p.Longitude IS NOT NULL
        AND p.Latitude != 0
        AND p.Longitude != 0
    WHERE r.Code IN ('914', '10551', 'SK-PMS2', 'D305', 'SK-SAT5', 'MVP-SAT2', 'OL-07', 'SMDLZ-1')
    AND r.barangay_code IS NOT NULL
    AND r.barangay_code != '#'
    AND r.barangay_code != ''
    GROUP BY r.Code, r.RouteDate
) prospect_data ON agent_data.agent_id = prospect_data.agent_id
                AND agent_data.route_date = prospect_data.route_date
ORDER BY agent_data.agent_id, agent_data.route_date;

-- =============================================================================
-- SUMMARY: SCENARIO DISTRIBUTION
-- =============================================================================

-- Get overall distribution of scenarios
SELECT
    'SCENARIO_DISTRIBUTION_SUMMARY' as analysis_type,
    SUM(CASE WHEN customer_count = 60 THEN 1 ELSE 0 END) as exactly_60_agents,
    SUM(CASE WHEN customer_count > 60 THEN 1 ELSE 0 END) as more_than_60_agents,
    SUM(CASE WHEN customer_count < 60 THEN 1 ELSE 0 END) as less_than_60_agents,
    SUM(CASE WHEN customer_count < 60 AND stop100_count = 0 THEN 1 ELSE 0 END) as all_valid_coords_agents,
    SUM(CASE WHEN customer_count < 60 AND stop100_count > 0 AND with_coords > 0 THEN 1 ELSE 0 END) as mixed_coords_agents,
    SUM(CASE WHEN customer_count < 60 AND with_coords = 0 THEN 1 ELSE 0 END) as all_stop100_agents,
    COUNT(*) as total_agent_days
FROM (
    SELECT
        Code,
        RouteDate,
        COUNT(DISTINCT CustNo) as customer_count,
        COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                   AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coords,
        COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                   OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count
    FROM routedata
    WHERE Code IS NOT NULL
    GROUP BY Code, RouteDate
) agent_summary;