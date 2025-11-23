-- SINGLE COMPREHENSIVE QUERY
-- Find sales agents with <60 customers, some without barangay_code, and prospects available
-- Demonstrates the matching function: routedata.barangay_code = prospective.barangay_code

SELECT
    r.SalesManTerritory as agent_id,
    r.RouteDate as day,
    COUNT(DISTINCT r.CustNo) as total_customers,
    COUNT(DISTINCT CASE
        WHEN r.barangay_code IS NOT NULL AND r.barangay_code != '#' AND r.barangay_code != ''
        THEN r.CustNo
    END) as customers_with_barangay_code,
    COUNT(DISTINCT CASE
        WHEN r.barangay_code IS NULL OR r.barangay_code = '#' OR r.barangay_code = ''
        THEN r.CustNo
    END) as customers_without_barangay_code,
    COUNT(DISTINCT CASE
        WHEN r.latitude IS NULL OR r.longitude IS NULL OR r.latitude = 0 OR r.longitude = 0
        THEN r.CustNo
    END) as stop100_customers,
    r.barangay_code,
    COUNT(DISTINCT p.CustNo) as matched_prospects,
    (60 - COUNT(DISTINCT r.CustNo)) as need_to_add,
    CASE
        WHEN COUNT(DISTINCT p.CustNo) >= (60 - COUNT(DISTINCT r.CustNo))
        THEN 'CAN_REACH_60'
        ELSE 'PARTIAL_FILL'
    END as optimization_status,
    'MATCHING_FUNCTION: routedata.barangay_code = prospective.barangay_code' as matching_logic,
    CONCAT('MATCH(', r.barangay_code, ' = ', r.barangay_code, ') -> ', COUNT(DISTINCT p.CustNo), ' prospects') as function_result
FROM routedata r
LEFT JOIN prospective p ON r.barangay_code = p.barangay_code  -- THE MATCHING FUNCTION
    AND p.Latitude IS NOT NULL
    AND p.Longitude IS NOT NULL
    AND p.Latitude != 0
    AND p.Longitude != 0
WHERE r.SalesManTerritory IS NOT NULL
    AND r.barangay_code IS NOT NULL
    AND r.barangay_code != '#'
    AND r.barangay_code != ''
GROUP BY r.SalesManTerritory, r.RouteDate, r.barangay_code
HAVING COUNT(DISTINCT r.CustNo) < 60  -- Less than 60 customers
    AND COUNT(DISTINCT CASE
        WHEN r.barangay_code IS NULL OR r.barangay_code = '#' OR r.barangay_code = ''
        THEN r.CustNo
    END) > 0  -- Some customers without barangay_code
    AND COUNT(DISTINCT p.CustNo) > 0  -- Prospects available
ORDER BY COUNT(DISTINCT p.CustNo) DESC, COUNT(DISTINCT r.CustNo) DESC;