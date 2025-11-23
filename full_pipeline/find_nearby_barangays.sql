-- Find barangays near the starting location (14.663813, 121.122687)
-- This will help you identify which barangay codes to use for SK-DP4

DECLARE @start_lat FLOAT = 14.663813;
DECLARE @start_lon FLOAT = 121.122687;
DECLARE @max_distance_km FLOAT = 10; -- Maximum distance in kilometers

-- Find barangays with prospects near the starting location
WITH BarangayDistances AS (
    SELECT DISTINCT
        p.barangay_code,
        p.Barangay,
        p.Latitude,
        p.Longitude,
        -- Calculate distance using Haversine formula
        6371 * 2 * ASIN(SQRT(
            POWER(SIN((RADIANS(p.Latitude) - RADIANS(@start_lat)) / 2), 2) +
            COS(RADIANS(@start_lat)) * COS(RADIANS(p.Latitude)) *
            POWER(SIN((RADIANS(p.Longitude) - RADIANS(@start_lon)) / 2), 2)
        )) AS distance_km,
        COUNT(*) OVER (PARTITION BY p.barangay_code) AS total_prospects,
        SUM(CASE
            WHEN NOT EXISTS (SELECT 1 FROM MonthlyRoutePlan_temp mrp WHERE mrp.CustNo = p.CustNo)
            AND NOT EXISTS (SELECT 1 FROM custvist cv WHERE cv.CustNo = p.CustNo)
            THEN 1 ELSE 0
        END) OVER (PARTITION BY p.barangay_code) AS available_prospects
    FROM prospective p
    WHERE p.Latitude IS NOT NULL
        AND p.Longitude IS NOT NULL
        AND p.Latitude != 0
        AND p.Longitude != 0
)
SELECT TOP 20
    barangay_code,
    Barangay,
    distance_km,
    total_prospects,
    available_prospects,
    Latitude,
    Longitude
FROM BarangayDistances
WHERE distance_km <= @max_distance_km
    AND available_prospects > 0
GROUP BY barangay_code, Barangay, distance_km, total_prospects, available_prospects, Latitude, Longitude
ORDER BY distance_km ASC, available_prospects DESC;

-- Summary of available prospects
SELECT
    COUNT(DISTINCT p.barangay_code) AS total_barangays_within_10km,
    SUM(CASE
        WHEN NOT EXISTS (SELECT 1 FROM MonthlyRoutePlan_temp mrp WHERE mrp.CustNo = p.CustNo)
        AND NOT EXISTS (SELECT 1 FROM custvist cv WHERE cv.CustNo = p.CustNo)
        THEN 1 ELSE 0
    END) AS total_available_prospects
FROM prospective p
WHERE p.Latitude IS NOT NULL
    AND p.Longitude IS NOT NULL
    AND p.Latitude != 0
    AND p.Longitude != 0
    AND 6371 * 2 * ASIN(SQRT(
        POWER(SIN((RADIANS(p.Latitude) - RADIANS(@start_lat)) / 2), 2) +
        COS(RADIANS(@start_lat)) * COS(RADIANS(p.Latitude)) *
        POWER(SIN((RADIANS(p.Longitude) - RADIANS(@start_lon)) / 2), 2)
    )) <= @max_distance_km;
