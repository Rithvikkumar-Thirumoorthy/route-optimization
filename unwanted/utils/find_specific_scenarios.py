#!/usr/bin/env python3
"""
Find Specific Scenario Examples
Get real agents for the 3 specific scenarios requested
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def find_specific_scenarios():
    """Find agents for the 3 specific scenarios"""
    db = DatabaseConnection()
    db.connect()

    print("Finding Specific Scenario Examples")
    print("=" * 50)

    # SCENARIO 1: Agent with more than 60 customers
    print("\n1. SCENARIO 1: Agents with MORE than 60 customers")
    print("-" * 45)

    query1 = """
    SELECT TOP 5
        Code as agent_id,
        RouteDate as route_date,
        COUNT(DISTINCT CustNo) as customer_count,
        COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                   AND latitude != 0 AND longitude != 0 THEN 1 END) as customers_with_coords,
        COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                   OR latitude = 0 OR longitude = 0 THEN 1 END) as customers_stop100
    FROM routedata
    WHERE Code IS NOT NULL
    GROUP BY Code, RouteDate
    HAVING COUNT(DISTINCT CustNo) > 60
    ORDER BY COUNT(DISTINCT CustNo) DESC
    """

    result1 = db.execute_query_df(query1)
    if result1 is not None and not result1.empty:
        for _, row in result1.iterrows():
            print(f"   Agent: {row['agent_id']}, Date: {row['route_date']}")
            print(f"     Customers: {row['customer_count']} (>60)")
            print(f"     With coords: {row['customers_with_coords']}, Stop100: {row['customers_stop100']}")
            print(f"     Status: NO PROSPECTS NEEDED")
    else:
        print("   No agents found with >60 customers")

    # SCENARIO 2: Agent 20-60 customers + prospects (any coordinates)
    print(f"\n2. SCENARIO 2: Agents 20-60 customers + prospects (any coords)")
    print("-" * 45)

    query2 = """
    SELECT TOP 5
        r.Code as agent_id,
        r.RouteDate as route_date,
        COUNT(DISTINCT r.CustNo) as customer_count,
        COUNT(CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
                   AND r.latitude != 0 AND r.longitude != 0 THEN 1 END) as customers_with_coords,
        COUNT(DISTINCT p.CustNo) as total_prospects,
        COUNT(DISTINCT CASE WHEN p.Latitude IS NOT NULL AND p.Longitude IS NOT NULL
                            AND p.Latitude != 0 AND p.Longitude != 0
                            THEN p.CustNo END) as prospects_valid_coords,
        COUNT(DISTINCT CASE WHEN p.Latitude IS NULL OR p.Longitude IS NULL
                            OR p.Latitude = 0 OR p.Longitude = 0
                            THEN p.CustNo END) as prospects_invalid_coords,
        (60 - COUNT(DISTINCT r.CustNo)) as prospects_needed
    FROM routedata r
    INNER JOIN prospective p ON r.barangay_code = p.barangay_code
    WHERE r.Code IS NOT NULL
    AND r.barangay_code IS NOT NULL AND r.barangay_code != '#' AND r.barangay_code != ''
    GROUP BY r.Code, r.RouteDate
    HAVING COUNT(DISTINCT r.CustNo) BETWEEN 20 AND 60
    AND COUNT(DISTINCT p.CustNo) > 0
    ORDER BY COUNT(DISTINCT p.CustNo) DESC
    """

    result2 = db.execute_query_df(query2)
    if result2 is not None and not result2.empty:
        for _, row in result2.iterrows():
            print(f"   Agent: {row['agent_id']}, Date: {row['route_date']}")
            print(f"     Customers: {row['customer_count']} (20-60 range)")
            print(f"     Customer coords: {row['customers_with_coords']} valid")
            print(f"     Total prospects: {row['total_prospects']}")
            print(f"     Prospect coords: {row['prospects_valid_coords']} valid, {row['prospects_invalid_coords']} invalid")
            print(f"     Needed: {row['prospects_needed']} prospects")
            status = "CAN REACH 60" if row['total_prospects'] >= row['prospects_needed'] else "PARTIAL FILL"
            print(f"     Status: {status}")
    else:
        print("   No agents found for this scenario")

    # SCENARIO 3: Agent 20-60 customers + prospects with valid coordinates only
    print(f"\n3. SCENARIO 3: Agents 20-60 customers + prospects (valid coords only)")
    print("-" * 45)

    query3 = """
    SELECT TOP 5
        r.Code as agent_id,
        r.RouteDate as route_date,
        COUNT(DISTINCT r.CustNo) as customer_count,
        COUNT(CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
                   AND r.latitude != 0 AND r.longitude != 0 THEN 1 END) as customers_with_coords,
        COUNT(DISTINCT p.CustNo) as prospects_valid_coords,
        (60 - COUNT(DISTINCT r.CustNo)) as prospects_needed,
        AVG(CAST(p.Latitude AS FLOAT)) as avg_prospect_lat,
        AVG(CAST(p.Longitude AS FLOAT)) as avg_prospect_lon
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
    """

    result3 = db.execute_query_df(query3)
    if result3 is not None and not result3.empty:
        for _, row in result3.iterrows():
            print(f"   Agent: {row['agent_id']}, Date: {row['route_date']}")
            print(f"     Customers: {row['customer_count']} (20-60 range)")
            print(f"     Customer coords: {row['customers_with_coords']} valid")
            print(f"     Prospects (valid coords): {row['prospects_valid_coords']}")
            print(f"     Needed: {row['prospects_needed']} prospects")
            print(f"     Prospect center: {row['avg_prospect_lat']:.4f}, {row['avg_prospect_lon']:.4f}")
            status = "CAN REACH 60" if row['prospects_valid_coords'] >= row['prospects_needed'] else "PARTIAL FILL"
            print(f"     Status: {status}")
    else:
        print("   No agents found for this scenario")

    # Summary with one example for each scenario
    print(f"\n" + "=" * 50)
    print("SUMMARY - Best Example for Each Scenario")
    print("=" * 50)

    examples = []

    if result1 is not None and not result1.empty:
        best1 = result1.iloc[0]
        examples.append({
            'scenario': 'SCENARIO 1: >60 Customers',
            'agent': best1['agent_id'],
            'date': best1['route_date'],
            'customers': best1['customer_count'],
            'description': f"{best1['customer_count']} customers - no prospects needed"
        })

    if result2 is not None and not result2.empty:
        best2 = result2.iloc[0]
        examples.append({
            'scenario': 'SCENARIO 2: 20-60 + Prospects (any coords)',
            'agent': best2['agent_id'],
            'date': best2['route_date'],
            'customers': best2['customer_count'],
            'description': f"{best2['customer_count']} customers, {best2['total_prospects']} prospects (mixed coords)"
        })

    if result3 is not None and not result3.empty:
        best3 = result3.iloc[0]
        examples.append({
            'scenario': 'SCENARIO 3: 20-60 + Prospects (valid coords)',
            'agent': best3['agent_id'],
            'date': best3['route_date'],
            'customers': best3['customer_count'],
            'description': f"{best3['customer_count']} customers, {best3['prospects_valid_coords']} prospects (all valid coords)"
        })

    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['scenario']}")
        print(f"   Agent: {example['agent']}, Date: {example['date']}")
        print(f"   {example['description']}")

    if examples:
        print(f"\nUSAGE - Update run_specific_agents.py:")
        print("specific_agents = [")
        for example in examples:
            print(f'    ("{example["agent"]}", "{example["date"]}"),  # {example["scenario"].split(":")[0]}')
        print("]")

    db.close()
    return examples

def main():
    """Main function"""
    try:
        examples = find_specific_scenarios()

        if examples:
            print(f"\n" + "=" * 50)
            print("SUCCESS: Found examples for all requested scenarios!")
            print("Use the SQL queries in sql/specific_scenario_queries.sql")
            print("for detailed analysis of each agent.")
        else:
            print(f"\nNo examples found. The database may not have agents")
            print("matching the specific criteria requested.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()