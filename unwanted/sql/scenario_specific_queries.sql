-- SPECIFIC AGENT SCENARIO QUERIES
-- Get agent-ids and days for each scenario with barangay matching verification

-- =============================================================================
-- SCENARIO 1: AGENTS WITH EXACTLY 60 CUSTOMERS ON A PARTICULAR DAY
-- =============================================================================

-- Query 1: Get specific agents with exactly 60 customers
SELECT TOP 10
    SalesManTerritory as agent_id,
    RouteDate as day,
    COUNT(DISTINCT CustNo) as customer_count
FROM routedata
WHERE SalesManTerritory IS NOT NULL
GROUP BY SalesManTerritory, RouteDate
HAVING COUNT(DISTINCT CustNo) = 60
ORDER BY SalesManTerritory, RouteDate;

-- =============================================================================
-- SCENARIO 2: AGENTS WITH <60 CUSTOMERS + PROSPECTS IN SAME BARANGAY
-- =============================================================================

-- Query 2.1: Get agents with <60 customers
SELECT TOP 10
    SalesManTerritory as agent_id,
    RouteDate as day,
    COUNT(DISTINCT CustNo) as customer_count
FROM routedata
WHERE SalesManTerritory IS NOT NULL
GROUP BY SalesManTerritory, RouteDate
HAVING COUNT(DISTINCT CustNo) < 60
ORDER BY COUNT(DISTINCT CustNo) DESC;

-- Query 2.2: Get barangay codes for specific agent and day
-- Use parameters: agent_id = 'D305', day = '2025-09-25'
SELECT DISTINCT barangay_code
FROM routedata
WHERE SalesManTerritory = 'D305'
AND RouteDate = '2025-09-25'
AND barangay_code IS NOT NULL
AND barangay_code != '#'
AND barangay_code != '';

-- Query 2.3: Check prospects available for specific barangay code
-- Use parameter: barangay_code = '042108023' (from above query)
SELECT COUNT(DISTINCT CustNo) as prospect_count
FROM prospective
WHERE barangay_code = '042108023'
AND Latitude IS NOT NULL
AND Longitude IS NOT NULL
AND Latitude != 0
AND Longitude != 0;

-- Query 2.4: Complete scenario 2 analysis for specific agent
-- Shows matching: routedata.barangay_code = prospective.barangay_code
SELECT
    r.SalesManTerritory as agent_id,
    r.RouteDate as day,
    COUNT(DISTINCT r.CustNo) as current_customers,
    r.barangay_code as barangay_code,
    COUNT(DISTINCT p.CustNo) as available_prospects,
    (60 - COUNT(DISTINCT r.CustNo)) as needed_to_reach_60
FROM routedata r
LEFT JOIN prospective p ON r.barangay_code = p.barangay_code
    AND p.Latitude IS NOT NULL
    AND p.Longitude IS NOT NULL
    AND p.Latitude != 0
    AND p.Longitude != 0
WHERE r.SalesManTerritory = 'D305'
AND r.RouteDate = '2025-09-25'
AND r.barangay_code IS NOT NULL
AND r.barangay_code != '#'
GROUP BY r.SalesManTerritory, r.RouteDate, r.barangay_code
HAVING COUNT(DISTINCT p.CustNo) > 0;

-- =============================================================================
-- SCENARIO 3: AGENTS WITH <60 CUSTOMERS + STOP100 CONDITIONS
-- =============================================================================

-- Query 3.1: Get agents with <60 customers and stop100 conditions
SELECT TOP 10
    SalesManTerritory as agent_id,
    RouteDate as day,
    COUNT(DISTINCT CustNo) as total_customers,
    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
               AND latitude != 0 AND longitude != 0 THEN 1 END) as customers_with_coords,
    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
               OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_customers
FROM routedata
WHERE SalesManTerritory IS NOT NULL
GROUP BY SalesManTerritory, RouteDate
HAVING COUNT(DISTINCT CustNo) < 60
AND COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
               OR latitude = 0 OR longitude = 0 THEN 1 END) > 0
ORDER BY COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                     OR latitude = 0 OR longitude = 0 THEN 1 END) DESC;

-- Query 3.2: Detailed analysis for specific stop100 agent
-- Use parameters: agent_id = 'OL-07', day = '2025-09-02'
SELECT
    CustNo,
    CASE
        WHEN latitude IS NULL OR longitude IS NULL OR latitude = 0 OR longitude = 0
        THEN 'STOP100'
        ELSE 'WITH_COORDS'
    END as customer_type,
    latitude,
    longitude,
    barangay_code as barangay_code
FROM routedata
WHERE SalesManTerritory = 'OL-07'
AND RouteDate = '2025-09-02'
ORDER BY customer_type, CustNo;

-- =============================================================================
-- BARANGAY MATCHING VERIFICATION QUERIES
-- =============================================================================

-- Query 4.1: Verify barangay matching logic
-- Shows: routedata.barangay_code = prospective.barangay_code
SELECT TOP 5
    r.barangay_code as routedata_barangay_code,
    p.barangay_code as prospective_barangay_code,
    COUNT(DISTINCT r.CustNo) as customers,
    COUNT(DISTINCT p.CustNo) as prospects,
    'MATCH CONFIRMED' as status
FROM routedata r
INNER JOIN prospective p ON r.barangay_code = p.barangay_code
WHERE r.barangay_code IS NOT NULL
AND r.barangay_code != '#'
AND p.Latitude IS NOT NULL
AND p.Longitude IS NOT NULL
GROUP BY r.barangay_code, p.barangay_code
ORDER BY COUNT(DISTINCT p.CustNo) DESC;

-- Query 4.2: Show agents that can benefit from prospect addition
SELECT
    r.SalesManTerritory as agent_id,
    r.RouteDate as day,
    r.barangay_code as barangay_code,
    COUNT(DISTINCT r.CustNo) as current_customers,
    COUNT(DISTINCT p.CustNo) as available_prospects,
    (60 - COUNT(DISTINCT r.CustNo)) as spots_to_fill,
    CASE
        WHEN COUNT(DISTINCT p.CustNo) >= (60 - COUNT(DISTINCT r.CustNo))
        THEN 'CAN_REACH_60'
        ELSE 'PARTIAL_FILL'
    END as can_reach_target
FROM routedata r
LEFT JOIN prospective p ON r.barangay_code = p.barangay_code
    AND p.Latitude IS NOT NULL
    AND p.Longitude IS NOT NULL
WHERE r.barangay_code IS NOT NULL
AND r.barangay_code != '#'
GROUP BY r.SalesManTerritory, r.RouteDate, r.barangay_code
HAVING COUNT(DISTINCT r.CustNo) < 60
AND COUNT(DISTINCT p.CustNo) > 0
ORDER BY COUNT(DISTINCT p.CustNo) DESC;

-- =============================================================================
-- SPECIFIC EXAMPLES WITH KNOWN WORKING DATA
-- =============================================================================

-- Query 5.1: Specific working example
-- Agent with barangay code that has many prospects
SELECT
    SalesManTerritory as agent_id,
    RouteDate as day,
    COUNT(DISTINCT CustNo) as customers,
    '45808009' as barangay_code,
    'VERIFIED_WORKING_CODE' as status
FROM routedata
WHERE barangay_code = '45808009'
GROUP BY SalesManTerritory, RouteDate
ORDER BY RouteDate DESC;

-- Query 5.2: Show prospects for the working code
SELECT COUNT(DISTINCT CustNo) as prospect_count
FROM prospective
WHERE barangay_code = '45808009'
AND Latitude IS NOT NULL
AND Longitude IS NOT NULL;

-- Query 5.3: Complete example showing the matching
SELECT
    'MATCHING_DEMO' as example_type,
    r.SalesManTerritory as agent_id,
    r.RouteDate as day,
    COUNT(DISTINCT r.CustNo) as customers,
    r.barangay_code as barangay_code_from_routedata,
    p.barangay_code as barangay_code_from_prospective,
    COUNT(DISTINCT p.CustNo) as prospects,
    CASE
        WHEN r.barangay_code = p.barangay_code THEN 'MATCH_CONFIRMED'
        ELSE 'NO_MATCH'
    END as matching_status
FROM routedata r
LEFT JOIN prospective p ON r.barangay_code = p.barangay_code
    AND p.Latitude IS NOT NULL
    AND p.Longitude IS NOT NULL
WHERE r.barangay_code = '45808009'
GROUP BY r.SalesManTerritory, r.RouteDate, r.barangay_code, p.barangay_code
ORDER BY r.RouteDate DESC;

-- =============================================================================
-- SUMMARY QUERIES FOR EACH SCENARIO
-- =============================================================================

-- Summary: Count of agent-days by scenario
SELECT
    'Exactly 60 customers' as scenario,
    COUNT(*) as agent_day_count
FROM (
    SELECT SalesManTerritory, RouteDate
    FROM routedata
    WHERE SalesManTerritory IS NOT NULL
    GROUP BY SalesManTerritory, RouteDate
    HAVING COUNT(DISTINCT CustNo) = 60
) sub

UNION ALL

SELECT
    'Less than 60 customers' as scenario,
    COUNT(*) as agent_day_count
FROM (
    SELECT SalesManTerritory, RouteDate
    FROM routedata
    WHERE SalesManTerritory IS NOT NULL
    GROUP BY SalesManTerritory, RouteDate
    HAVING COUNT(DISTINCT CustNo) < 60
) sub

UNION ALL

SELECT
    'More than 60 customers' as scenario,
    COUNT(*) as agent_day_count
FROM (
    SELECT SalesManTerritory, RouteDate
    FROM routedata
    WHERE SalesManTerritory IS NOT NULL
    GROUP BY SalesManTerritory, RouteDate
    HAVING COUNT(DISTINCT CustNo) > 60
) sub;

-- =============================================================================
-- SCENARIO 4: AGENTS WITH <60 CUSTOMERS + MISSING ADDRESS3 + PROSPECTS AVAILABLE
-- =============================================================================

-- Query 6: Find agents with <60 customers, some missing barangay_code, but prospects available
-- This shows the complex scenario where some customers lack barangay codes
SELECT
    r.SalesManTerritory as agent_id,
    r.RouteDate as day,
    COUNT(DISTINCT r.CustNo) as total_customers,
    COUNT(DISTINCT CASE WHEN r.barangay_code IS NOT NULL AND r.barangay_code != '#' AND r.barangay_code != ''
                        THEN r.CustNo END) as customers_with_barangay_code,
    COUNT(DISTINCT CASE WHEN r.barangay_code IS NULL OR r.barangay_code = '#' OR r.barangay_code = ''
                        THEN r.CustNo END) as customers_without_barangay_code,
    r.barangay_code as barangay_code,
    COUNT(DISTINCT p.CustNo) as available_prospects,
    (60 - COUNT(DISTINCT r.CustNo)) as spots_to_fill
FROM routedata r
LEFT JOIN prospective p ON r.barangay_code = p.barangay_code
    AND p.Latitude IS NOT NULL
    AND p.Longitude IS NOT NULL
    AND p.Latitude != 0
    AND p.Longitude != 0
WHERE r.SalesManTerritory IS NOT NULL
GROUP BY r.SalesManTerritory, r.RouteDate, r.barangay_code
HAVING COUNT(DISTINCT r.CustNo) < 60
AND COUNT(DISTINCT CASE WHEN r.barangay_code IS NULL OR r.barangay_code = '#' OR r.barangay_code = ''
                        THEN r.CustNo END) > 0
AND COUNT(DISTINCT p.CustNo) > 0
AND r.barangay_code IS NOT NULL
AND r.barangay_code != '#'
AND r.barangay_code != ''
ORDER BY COUNT(DISTINCT p.CustNo) DESC, COUNT(DISTINCT r.CustNo) DESC;

-- Query 6.1: Detailed breakdown for specific agent showing mixed barangay_code data
-- Use parameters: agent_id and day from above query results
-- Example: agent_id = 'AGENT_X', day = '2025-09-XX'
SELECT
    r.CustNo,
    r.latitude,
    r.longitude,
    r.barangay_code,
    CASE
        WHEN r.barangay_code IS NULL THEN 'NULL_ADDRESS3'
        WHEN r.barangay_code = '#' THEN 'HASH_ADDRESS3'
        WHEN r.barangay_code = '' THEN 'EMPTY_ADDRESS3'
        ELSE 'VALID_ADDRESS3'
    END as barangay_code_status,
    CASE
        WHEN r.latitude IS NULL OR r.longitude IS NULL OR r.latitude = 0 OR r.longitude = 0
        THEN 'STOP100'
        ELSE 'WITH_COORDS'
    END as coordinate_status
FROM routedata r
WHERE r.SalesManTerritory = ? -- Replace with specific agent
AND r.RouteDate = ? -- Replace with specific date
ORDER BY barangay_code_status, coordinate_status, r.CustNo;

-- Query 6.2: Show prospect matching for valid barangay codes from mixed data
-- This demonstrates how prospects can still be found despite some missing barangay_code
SELECT
    r.barangay_code as barangay_code,
    COUNT(DISTINCT r.CustNo) as customers_with_this_code,
    COUNT(DISTINCT p.CustNo) as prospects_available,
    'MATCHING: barangay_code = barangay_code' as matching_logic
FROM routedata r
INNER JOIN prospective p ON r.barangay_code = p.barangay_code
    AND p.Latitude IS NOT NULL
    AND p.Longitude IS NOT NULL
    AND p.Latitude != 0
    AND p.Longitude != 0
WHERE r.SalesManTerritory = ? -- Replace with specific agent
AND r.RouteDate = ? -- Replace with specific date
AND r.barangay_code IS NOT NULL
AND r.barangay_code != '#'
AND r.barangay_code != ''
GROUP BY r.barangay_code
ORDER BY COUNT(DISTINCT p.CustNo) DESC;

-- Query 6.3: Complete scenario analysis showing the challenge
-- Shows agents who have mixed data quality but can still benefit from prospects
SELECT
    agent_summary.agent_id,
    agent_summary.day,
    agent_summary.total_customers,
    agent_summary.valid_barangay_code_customers,
    agent_summary.invalid_barangay_code_customers,
    prospect_summary.total_prospects_available,
    prospect_summary.unique_barangay_codes,
    (60 - agent_summary.total_customers) as need_to_add,
    CASE
        WHEN prospect_summary.total_prospects_available >= (60 - agent_summary.total_customers)
        THEN 'CAN_REACH_60'
        ELSE 'PARTIAL_FILL_POSSIBLE'
    END as optimization_potential
FROM (
    SELECT
        r.SalesManTerritory as agent_id,
        r.RouteDate as day,
        COUNT(DISTINCT r.CustNo) as total_customers,
        COUNT(DISTINCT CASE WHEN r.barangay_code IS NOT NULL AND r.barangay_code != '#' AND r.barangay_code != ''
                            THEN r.CustNo END) as valid_barangay_code_customers,
        COUNT(DISTINCT CASE WHEN r.barangay_code IS NULL OR r.barangay_code = '#' OR r.barangay_code = ''
                            THEN r.CustNo END) as invalid_barangay_code_customers
    FROM routedata r
    WHERE r.SalesManTerritory IS NOT NULL
    GROUP BY r.SalesManTerritory, r.RouteDate
    HAVING COUNT(DISTINCT r.CustNo) < 60
    AND COUNT(DISTINCT CASE WHEN r.barangay_code IS NULL OR r.barangay_code = '#' OR r.barangay_code = ''
                            THEN r.CustNo END) > 0
) agent_summary
LEFT JOIN (
    SELECT
        r.SalesManTerritory as agent_id,
        r.RouteDate as day,
        COUNT(DISTINCT p.CustNo) as total_prospects_available,
        COUNT(DISTINCT r.barangay_code) as unique_barangay_codes
    FROM routedata r
    INNER JOIN prospective p ON r.barangay_code = p.barangay_code
        AND p.Latitude IS NOT NULL
        AND p.Longitude IS NOT NULL
        AND p.Latitude != 0
        AND p.Longitude != 0
    WHERE r.barangay_code IS NOT NULL
    AND r.barangay_code != '#'
    AND r.barangay_code != ''
    GROUP BY r.SalesManTerritory, r.RouteDate
) prospect_summary ON agent_summary.agent_id = prospect_summary.agent_id
                  AND agent_summary.day = prospect_summary.day
WHERE prospect_summary.total_prospects_available > 0
ORDER BY prospect_summary.total_prospects_available DESC, agent_summary.total_customers DESC;

-- =============================================================================
-- SCENARIO 5: FUNCTION-LIKE MATCHING DEMONSTRATION
-- =============================================================================

-- Query 7: Function-like approach to demonstrate barangay matching
-- This query acts like a function that validates the matching logic
WITH BarangayMatcher AS (
    -- Step 1: Get agent customer data with barangay_code classification
    SELECT
        r.SalesManTerritory as agent_id,
        r.RouteDate as day,
        r.CustNo,
        r.barangay_code,
        r.latitude,
        r.longitude,
        CASE
            WHEN r.barangay_code IS NULL THEN 'NULL_ADDRESS3'
            WHEN r.barangay_code = '#' THEN 'HASH_ADDRESS3'
            WHEN r.barangay_code = '' THEN 'EMPTY_ADDRESS3'
            ELSE 'VALID_ADDRESS3'
        END as barangay_code_status,
        -- Function-like matching indicator
        CASE
            WHEN r.barangay_code IS NOT NULL AND r.barangay_code != '#' AND r.barangay_code != ''
            THEN 'CAN_MATCH_PROSPECTS'
            ELSE 'CANNOT_MATCH_PROSPECTS'
        END as matching_capability
    FROM routedata r
    WHERE r.SalesManTerritory IS NOT NULL
),
AgentSummary AS (
    -- Step 2: Aggregate by agent and day
    SELECT
        bm.agent_id,
        bm.day,
        COUNT(DISTINCT bm.CustNo) as total_customers,
        COUNT(DISTINCT CASE WHEN bm.barangay_code_status = 'VALID_ADDRESS3' THEN bm.CustNo END) as customers_with_valid_barangay_code,
        COUNT(DISTINCT CASE WHEN bm.barangay_code_status != 'VALID_ADDRESS3' THEN bm.CustNo END) as customers_without_valid_barangay_code,
        -- Get the valid barangay_code values for matching
        STRING_AGG(DISTINCT CASE WHEN bm.barangay_code_status = 'VALID_ADDRESS3' THEN bm.barangay_code END, ',') as valid_barangay_codes
    FROM BarangayMatcher bm
    GROUP BY bm.agent_id, bm.day
    HAVING COUNT(DISTINCT bm.CustNo) < 60  -- Less than 60 customers
    AND COUNT(DISTINCT CASE WHEN bm.barangay_code_status != 'VALID_ADDRESS3' THEN bm.CustNo END) > 0  -- Some without barangay_code
),
ProspectMatcher AS (
    -- Step 3: Function-like matching of routedata.barangay_code = prospective.barangay_code
    SELECT
        ags.agent_id,
        ags.day,
        ags.total_customers,
        ags.customers_with_valid_barangay_code,
        ags.customers_without_valid_barangay_code,
        ags.valid_barangay_codes,
        -- Apply the matching function: routedata.barangay_code = prospective.barangay_code
        COUNT(DISTINCT p.CustNo) as matched_prospects,
        COUNT(DISTINCT p.barangay_code) as unique_barangay_codes_with_prospects,
        'FUNCTION: routedata.barangay_code = prospective.barangay_code' as matching_function
    FROM AgentSummary ags
    CROSS APPLY STRING_SPLIT(ags.valid_barangay_codes, ',') as split_codes
    INNER JOIN prospective p ON split_codes.value = p.barangay_code  -- THE MATCHING FUNCTION
        AND p.Latitude IS NOT NULL
        AND p.Longitude IS NOT NULL
        AND p.Latitude != 0
        AND p.Longitude != 0
    GROUP BY ags.agent_id, ags.day, ags.total_customers, ags.customers_with_valid_barangay_code,
             ags.customers_without_valid_barangay_code, ags.valid_barangay_codes
)
-- Final result: Agents with mixed barangay_code data but prospect matching capability
SELECT
    pm.agent_id,
    pm.day,
    pm.total_customers,
    pm.customers_with_valid_barangay_code,
    pm.customers_without_valid_barangay_code,
    pm.valid_barangay_codes,
    pm.matched_prospects,
    pm.unique_barangay_codes_with_prospects,
    (60 - pm.total_customers) as need_to_add,
    CASE
        WHEN pm.matched_prospects >= (60 - pm.total_customers)
        THEN 'SUCCESS: Can reach 60 with prospects'
        ELSE 'PARTIAL: Can partially fill with prospects'
    END as optimization_result,
    pm.matching_function
FROM ProspectMatcher pm
WHERE pm.matched_prospects > 0
ORDER BY pm.matched_prospects DESC, pm.total_customers DESC;

-- Query 7.1: Detailed function execution for specific agent
-- Shows step-by-step how the matching function works
-- Replace ? with specific agent_id and day from above results
WITH MatchingFunction AS (
    SELECT
        r.CustNo as customer_id,
        r.barangay_code as customer_barangay_code,
        p.CustNo as prospect_id,
        p.barangay_code as prospect_barangay_code,
        CASE
            WHEN r.barangay_code = p.barangay_code THEN 'MATCH_SUCCESS'
            ELSE 'MATCH_FAILED'
        END as function_result,
        CASE
            WHEN r.barangay_code IS NULL OR r.barangay_code = '#' OR r.barangay_code = ''
            THEN 'CUSTOMER_NO_BARANGAY'
            ELSE 'CUSTOMER_HAS_BARANGAY'
        END as customer_status,
        CASE
            WHEN r.latitude IS NULL OR r.longitude IS NULL OR r.latitude = 0 OR r.longitude = 0
            THEN 'STOP100'
            ELSE 'WITH_COORDINATES'
        END as coordinate_status
    FROM routedata r
    LEFT JOIN prospective p ON r.barangay_code = p.barangay_code  -- MATCHING FUNCTION EXECUTION
        AND p.Latitude IS NOT NULL
        AND p.Longitude IS NOT NULL
        AND p.Latitude != 0
        AND p.Longitude != 0
    WHERE r.SalesManTerritory = ?  -- Replace with specific agent
    AND r.RouteDate = ?  -- Replace with specific day
)
SELECT
    'MATCHING_FUNCTION_EXECUTION' as execution_type,
    COUNT(DISTINCT customer_id) as total_customers,
    COUNT(DISTINCT CASE WHEN customer_status = 'CUSTOMER_HAS_BARANGAY' THEN customer_id END) as customers_with_barangay,
    COUNT(DISTINCT CASE WHEN customer_status = 'CUSTOMER_NO_BARANGAY' THEN customer_id END) as customers_without_barangay,
    COUNT(DISTINCT CASE WHEN function_result = 'MATCH_SUCCESS' THEN prospect_id END) as matched_prospects,
    COUNT(DISTINCT customer_barangay_code) as unique_customer_barangay_codes,
    'routedata.barangay_code = prospective.barangay_code' as function_definition
FROM MatchingFunction;

-- Query 7.2: Show the actual matching pairs
-- Demonstrates the function output for verification
SELECT TOP 10
    r.SalesManTerritory as agent_id,
    r.RouteDate as day,
    r.CustNo as customer_id,
    r.barangay_code as routedata_barangay_code,
    p.CustNo as prospect_id,
    p.barangay_code as prospective_barangay_code,
    CASE
        WHEN r.barangay_code = p.barangay_code THEN 'FUNCTION_MATCH_CONFIRMED'
        ELSE 'FUNCTION_MATCH_FAILED'
    END as matching_function_result,
    CONCAT('MATCH(', r.barangay_code, ' = ', p.barangay_code, ')') as function_call
FROM routedata r
INNER JOIN prospective p ON r.barangay_code = p.barangay_code  -- THE MATCHING FUNCTION
WHERE r.SalesManTerritory IS NOT NULL
AND r.barangay_code IS NOT NULL
AND r.barangay_code != '#'
AND r.barangay_code != ''
AND p.Latitude IS NOT NULL
AND p.Longitude IS NOT NULL
AND p.Latitude != 0
AND p.Longitude != 0
ORDER BY r.SalesManTerritory, r.RouteDate, r.CustNo;

-- =============================================================================
-- KEY EXAMPLES FROM ANALYSIS
-- =============================================================================

/*
SCENARIO 1 EXAMPLES:
- Multiple agents have exactly 60 customers (330 agent-days total)
- These agents don't need prospect addition

SCENARIO 2 EXAMPLES:
- Agent: D305, Day: 2025-09-25, Customers: 59, Barangay: 042108023
- Agent: SK-SAT5, Day: 2025-09-27, Customers: 59, Barangay: 45813002
- Agent: MVP-SAT2, Day: 2025-09-08, Customers: 59, Barangay: 112319011

SCENARIO 3 EXAMPLES:
- Agent: OL-07, Day: 2025-09-02, Customers: 59, Stop100: 118
- Agent: SMDLZ-1, Day: 2025-09-19, Customers: 58, Stop100: 116

BARANGAY MATCHING CONFIRMED:
- routedata.barangay_code = prospective.barangay_code
- Working example: barangay_code='45808009' = barangay_code='45808009'
- Results: 11 customers → 2,840 prospects available
*/