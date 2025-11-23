-- Check if there are sales agents with ≤60 customers, valid data, AND prospects in same barangay

SELECT TOP 10
    r.Code as agent_id,
    r.RouteDate as day,
    COUNT(DISTINCT r.CustNo) as customer_count,
    COUNT(DISTINCT r.barangay_code) as unique_barangay_codes,
    COUNT(DISTINCT p.CustNo) as available_prospects,
    STRING_AGG(DISTINCT r.barangay_code, ', ') as barangay_codes
FROM routedata r
INNER JOIN prospective p ON r.barangay_code = p.barangay_code  -- MATCHING FUNCTION
    AND p.Latitude IS NOT NULL
    AND p.Longitude IS NOT NULL
    AND p.Latitude != 0
    AND p.Longitude != 0
WHERE r.Code IS NOT NULL
    AND r.barangay_code IS NOT NULL
    AND r.barangay_code != '#'
    AND r.barangay_code != ''
    AND r.latitude IS NOT NULL
    AND r.longitude IS NOT NULL
    AND r.latitude != 0
    AND r.longitude != 0
GROUP BY r.Code, r.RouteDate
HAVING COUNT(DISTINCT r.CustNo) <= 60  -- Less than or equal to 60
    AND COUNT(DISTINCT p.CustNo) > 0   -- Must have prospects available
ORDER BY COUNT(DISTINCT p.CustNo) DESC, COUNT(DISTINCT r.CustNo) DESC;