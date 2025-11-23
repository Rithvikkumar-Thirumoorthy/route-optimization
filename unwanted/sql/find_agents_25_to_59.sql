-- Find sales agents with barangay_code, latitude, longitude and store count between 25-59

SELECT TOP 20
    Code as agent_id,
    RouteDate as day,
    COUNT(DISTINCT CustNo) as store_count
FROM routedata
WHERE Code IS NOT NULL
    AND barangay_code IS NOT NULL
    AND barangay_code != '#'
    AND barangay_code != ''
    AND latitude IS NOT NULL
    AND longitude IS NOT NULL
    AND latitude != 0
    AND longitude != 0
GROUP BY Code, RouteDate
HAVING COUNT(DISTINCT CustNo) < 60
    AND COUNT(DISTINCT CustNo) > 25
ORDER BY COUNT(DISTINCT CustNo) DESC;