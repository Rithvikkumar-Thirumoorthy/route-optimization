-- Find agents matching specific scenarios for distributor ID '11814'
-- Scenarios:
-- 1. Agent with >60 customers but ALL with valid coords
-- 2. Agent with >60 customers but MIXED valid/invalid coords
-- 3. Agent with 30-60 customers but ALL with valid coords
-- 4. Agent with 30-60 customers but MIXED valid/invalid coords
-- 5. Agent with <60 customers but NO valid coords

WITH AgentSummary AS (
    SELECT
        Code as agent_id,
        RouteDate as route_date,
        COUNT(DISTINCT CustNo) as total_customers,
        SUM(CASE
            WHEN latitude IS NOT NULL
            AND longitude IS NOT NULL
            AND latitude != 0
            AND longitude != 0
            THEN 1
            ELSE 0
        END) as valid_coord_customers,
        SUM(CASE
            WHEN latitude IS NULL
            OR longitude IS NULL
            OR latitude = 0
            OR longitude = 0
            THEN 1
            ELSE 0
        END) as invalid_coord_customers
    FROM routedata
    WHERE distributorID = '11814'
        AND Code IS NOT NULL
        AND RouteDate IS NOT NULL
        AND CustNo IS NOT NULL
    GROUP BY Code, RouteDate
    HAVING COUNT(DISTINCT CustNo) >= 1
),
ScenarioClassification AS (
    SELECT
        agent_id,
        route_date,
        total_customers,
        valid_coord_customers,
        invalid_coord_customers,
        CAST(valid_coord_customers * 100.0 / total_customers AS DECIMAL(5,1)) as coord_percentage,
        CASE
            -- Scenario 1: >60 customers, ALL valid coords
            WHEN total_customers > 60 AND invalid_coord_customers = 0 AND valid_coord_customers > 0
            THEN 1
            -- Scenario 2: >60 customers, MIXED valid/invalid coords
            WHEN total_customers > 60 AND valid_coord_customers > 0 AND invalid_coord_customers > 0
            THEN 2
            -- Scenario 3: 30-60 customers, ALL valid coords
            WHEN total_customers >= 30 AND total_customers <= 60 AND invalid_coord_customers = 0 AND valid_coord_customers > 0
            THEN 3
            -- Scenario 4: 30-60 customers, MIXED valid/invalid coords
            WHEN total_customers >= 30 AND total_customers <= 60 AND valid_coord_customers > 0 AND invalid_coord_customers > 0
            THEN 4
            -- Scenario 5: <60 customers, NO valid coords
            WHEN total_customers < 60 AND valid_coord_customers = 0
            THEN 5
            ELSE 0  -- Doesn't match any scenario
        END as scenario
    FROM AgentSummary
)

-- Summary by scenario
SELECT
    'SUMMARY' as report_type,
    scenario,
    CASE scenario
        WHEN 1 THEN '>60 customers, ALL valid coords'
        WHEN 2 THEN '>60 customers, MIXED valid/invalid coords'
        WHEN 3 THEN '30-60 customers, ALL valid coords'
        WHEN 4 THEN '30-60 customers, MIXED valid/invalid coords'
        WHEN 5 THEN '<60 customers, NO valid coords'
        ELSE 'Other scenarios'
    END as scenario_description,
    COUNT(*) as agent_count,
    MIN(total_customers) as min_customers,
    MAX(total_customers) as max_customers,
    AVG(CAST(total_customers AS FLOAT)) as avg_customers,
    AVG(coord_percentage) as avg_coord_percentage
FROM ScenarioClassification
WHERE scenario > 0
GROUP BY scenario
UNION ALL
-- Detailed results for each scenario
SELECT
    'SCENARIO_' + CAST(scenario AS VARCHAR(1)) as report_type,
    scenario,
    agent_id + ' (' + CAST(route_date AS VARCHAR(10)) + ')' as scenario_description,
    total_customers as agent_count,
    valid_coord_customers as min_customers,
    invalid_coord_customers as max_customers,
    coord_percentage as avg_customers,
    0 as avg_coord_percentage
FROM ScenarioClassification
WHERE scenario > 0
ORDER BY report_type, scenario, agent_count DESC;

-- Separate detailed query for each scenario
SELECT '=== SCENARIO 1: >60 customers, ALL valid coords ===' as header;
SELECT
    agent_id,
    route_date,
    total_customers,
    valid_coord_customers,
    invalid_coord_customers,
    coord_percentage
FROM ScenarioClassification
WHERE scenario = 1
ORDER BY total_customers DESC;

SELECT '=== SCENARIO 2: >60 customers, MIXED valid/invalid coords ===' as header;
SELECT
    agent_id,
    route_date,
    total_customers,
    valid_coord_customers,
    invalid_coord_customers,
    coord_percentage
FROM ScenarioClassification
WHERE scenario = 2
ORDER BY total_customers DESC;

SELECT '=== SCENARIO 3: 30-60 customers, ALL valid coords ===' as header;
SELECT
    agent_id,
    route_date,
    total_customers,
    valid_coord_customers,
    invalid_coord_customers,
    coord_percentage
FROM ScenarioClassification
WHERE scenario = 3
ORDER BY total_customers DESC;

SELECT '=== SCENARIO 4: 30-60 customers, MIXED valid/invalid coords ===' as header;
SELECT
    agent_id,
    route_date,
    total_customers,
    valid_coord_customers,
    invalid_coord_customers,
    coord_percentage
FROM ScenarioClassification
WHERE scenario = 4
ORDER BY total_customers DESC;

SELECT '=== SCENARIO 5: <60 customers, NO valid coords ===' as header;
SELECT
    agent_id,
    route_date,
    total_customers,
    valid_coord_customers,
    invalid_coord_customers,
    coord_percentage
FROM ScenarioClassification
WHERE scenario = 5
ORDER BY total_customers DESC;

-- Generate processing list for Python script
SELECT '=== PROCESSING COMMANDS ===' as header;
SELECT
    'Scenario ' + CAST(scenario AS VARCHAR(1)) + ' agents:' as processing_command
FROM ScenarioClassification
WHERE scenario > 0
GROUP BY scenario
UNION ALL
SELECT
    '("' + agent_id + '", "' + CAST(route_date AS VARCHAR(10)) + '"),' as processing_command
FROM ScenarioClassification
WHERE scenario > 0
ORDER BY processing_command;