#!/usr/bin/env python3
"""
Quick Scenario Examples - Find key agent examples for different scenarios
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def get_key_scenarios():
    """Get key scenario examples quickly"""
    db = DatabaseConnection()
    db.connect()

    scenarios = {}

    print("Finding Key Scenario Examples...")
    print("=" * 50)

    # Scenario 1: Exactly 60 customers
    print("\n1. Agents with exactly 60 customers:")
    query1 = """
    SELECT TOP 3 Code as agent_id, RouteDate, COUNT(DISTINCT CustNo) as customers
    FROM routedata WHERE Code IS NOT NULL
    GROUP BY Code, RouteDate HAVING COUNT(DISTINCT CustNo) = 60
    ORDER BY Code, RouteDate
    """
    result1 = db.execute_query_df(query1)
    if result1 is not None and not result1.empty:
        for _, row in result1.iterrows():
            print(f"   Agent: {row['agent_id']}, Date: {row['RouteDate']}, Customers: {row['customers']}")
        scenarios['exactly_60'] = result1
    else:
        print("   No examples found")

    # Scenario 2: More than 60 customers
    print("\n2. Agents with more than 60 customers:")
    query2 = """
    SELECT TOP 3 Code as agent_id, RouteDate, COUNT(DISTINCT CustNo) as customers
    FROM routedata WHERE Code IS NOT NULL
    GROUP BY Code, RouteDate HAVING COUNT(DISTINCT CustNo) > 60
    ORDER BY COUNT(DISTINCT CustNo) DESC
    """
    result2 = db.execute_query_df(query2)
    if result2 is not None and not result2.empty:
        for _, row in result2.iterrows():
            print(f"   Agent: {row['agent_id']}, Date: {row['RouteDate']}, Customers: {row['customers']}")
        scenarios['more_than_60'] = result2
    else:
        print("   No examples found")

    # Scenario 3: Less than 60 customers with good coordinates
    print("\n3. Agents with <60 customers (good for optimization):")
    query3 = """
    SELECT TOP 5
        Code as agent_id,
        RouteDate,
        COUNT(DISTINCT CustNo) as customers,
        COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                   AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coords,
        COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                   OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100
    FROM routedata WHERE Code IS NOT NULL
    GROUP BY Code, RouteDate
    HAVING COUNT(DISTINCT CustNo) < 60
    AND COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
              AND latitude != 0 AND longitude != 0 THEN 1 END) > 0
    ORDER BY COUNT(DISTINCT CustNo) DESC
    """
    result3 = db.execute_query_df(query3)
    if result3 is not None and not result3.empty:
        for _, row in result3.iterrows():
            print(f"   Agent: {row['agent_id']}, Date: {row['RouteDate']}, Customers: {row['customers']}, With Coords: {row['with_coords']}, Stop100: {row['stop100']}")
        scenarios['less_than_60'] = result3
    else:
        print("   No examples found")

    # Scenario 4: Agents with prospects available
    print("\n4. Agents with prospects available in same barangay:")
    query4 = """
    SELECT TOP 3
        r.Code as agent_id,
        r.RouteDate,
        COUNT(DISTINCT r.CustNo) as customers,
        COUNT(DISTINCT p.CustNo) as prospects,
        (60 - COUNT(DISTINCT r.CustNo)) as needed
    FROM routedata r
    INNER JOIN prospective p ON r.barangay_code = p.barangay_code
        AND p.Latitude IS NOT NULL AND p.Longitude IS NOT NULL
        AND p.Latitude != 0 AND p.Longitude != 0
    WHERE r.Code IS NOT NULL
    AND r.barangay_code IS NOT NULL AND r.barangay_code != '#' AND r.barangay_code != ''
    GROUP BY r.Code, r.RouteDate
    HAVING COUNT(DISTINCT r.CustNo) < 60 AND COUNT(DISTINCT p.CustNo) > 0
    ORDER BY COUNT(DISTINCT p.CustNo) DESC
    """
    result4 = db.execute_query_df(query4)
    if result4 is not None and not result4.empty:
        for _, row in result4.iterrows():
            print(f"   Agent: {row['agent_id']}, Date: {row['RouteDate']}, Customers: {row['customers']}, Prospects: {row['prospects']}, Needed: {row['needed']}")
        scenarios['with_prospects'] = result4
    else:
        print("   No examples found")

    # Scenario 5: Check specific known agents
    print("\n5. Known working agents from previous analysis:")
    query5 = """
    SELECT Code as agent_id, RouteDate, COUNT(DISTINCT CustNo) as customers
    FROM routedata
    WHERE Code IN ('914', '10551', 'SK-PMS2', 'D305', 'SK-SAT5', 'OL-07', 'SMDLZ-1')
    GROUP BY Code, RouteDate
    ORDER BY Code, RouteDate
    """
    result5 = db.execute_query_df(query5)
    if result5 is not None and not result5.empty:
        for _, row in result5.iterrows():
            print(f"   Agent: {row['agent_id']}, Date: {row['RouteDate']}, Customers: {row['customers']}")
        scenarios['known_agents'] = result5
    else:
        print("   No examples found")

    # Overall statistics
    print("\n6. Overall database statistics:")
    query6 = """
    SELECT
        COUNT(DISTINCT Code) as total_agents,
        COUNT(DISTINCT CONCAT(Code, '-', RouteDate)) as total_agent_days,
        SUM(CASE WHEN customer_count = 60 THEN 1 ELSE 0 END) as exactly_60,
        SUM(CASE WHEN customer_count > 60 THEN 1 ELSE 0 END) as more_than_60,
        SUM(CASE WHEN customer_count < 60 THEN 1 ELSE 0 END) as less_than_60
    FROM (
        SELECT Code, RouteDate, COUNT(DISTINCT CustNo) as customer_count
        FROM routedata WHERE Code IS NOT NULL
        GROUP BY Code, RouteDate
    ) summary
    """
    result6 = db.execute_query_df(query6)
    if result6 is not None and not result6.empty:
        row = result6.iloc[0]
        print(f"   Total agents: {row['total_agents']}")
        print(f"   Total agent-days: {row['total_agent_days']}")
        print(f"   Exactly 60 customers: {row['exactly_60']}")
        print(f"   More than 60 customers: {row['more_than_60']}")
        print(f"   Less than 60 customers: {row['less_than_60']}")

    db.close()
    return scenarios

def main():
    """Main function"""
    try:
        scenarios = get_key_scenarios()

        print(f"\n" + "=" * 50)
        print("SUMMARY - Key Testing Agents:")
        print("=" * 50)

        # Extract best examples for testing
        if 'less_than_60' in scenarios and not scenarios['less_than_60'].empty:
            best_agents = scenarios['less_than_60'].head(3)
            print("\nRecommended agents for pipeline testing:")
            for _, row in best_agents.iterrows():
                print(f"  Agent: {row['agent_id']}, Date: {row['RouteDate']}")
                print(f"    Customers: {row['customers']}, With Coords: {row['with_coords']}, Stop100: {row['stop100']}")
                print(f"    Prospects needed: {60 - row['customers']}")

        if 'with_prospects' in scenarios and not scenarios['with_prospects'].empty:
            prospect_agents = scenarios['with_prospects'].head(2)
            print(f"\nAgents with confirmed prospect availability:")
            for _, row in prospect_agents.iterrows():
                print(f"  Agent: {row['agent_id']}, Date: {row['RouteDate']}")
                print(f"    Can add {row['prospects']} prospects (need {row['needed']})")

        print(f"\nThese agents can be used with run_specific_agents.py for testing!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()