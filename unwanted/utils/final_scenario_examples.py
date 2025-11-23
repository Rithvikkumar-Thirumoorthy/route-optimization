#!/usr/bin/env python3
"""
Final Scenario Examples - Get specific examples for all 3 scenarios
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def get_final_examples():
    """Get final examples for all 3 scenarios"""
    db = DatabaseConnection()
    db.connect()

    print("FINAL SCENARIO EXAMPLES")
    print("=" * 50)

    scenarios = {}

    # SCENARIO 1: More than 60 customers (we know these exist)
    print("\n1. SCENARIO 1: Agent with >60 customers")
    print("-" * 40)

    query1 = """
    SELECT TOP 3
        Code as agent_id,
        RouteDate,
        COUNT(DISTINCT CustNo) as customers
    FROM routedata
    WHERE Code IS NOT NULL AND Code != 'NULL'
    GROUP BY Code, RouteDate
    HAVING COUNT(DISTINCT CustNo) > 60
    ORDER BY COUNT(DISTINCT CustNo) ASC  -- Get smaller examples for easier testing
    """

    result1 = db.execute_query_df(query1)
    if result1 is not None and not result1.empty:
        for _, row in result1.iterrows():
            print(f"   Agent: '{row['agent_id']}', Date: {row['RouteDate']}, Customers: {row['customers']}")
        scenarios['scenario1'] = result1.iloc[0]
    else:
        print("   No examples found")

    # SCENARIO 2 & 3: Look for agents with 20-60 customers in a different range
    print(f"\n2. Looking for agents with 20-60 customers...")
    print("-" * 40)

    # Try broader search for medium-sized agents
    query2 = """
    SELECT TOP 10
        Code as agent_id,
        RouteDate,
        COUNT(DISTINCT CustNo) as customers
    FROM routedata
    WHERE Code IS NOT NULL AND Code != 'NULL'
    GROUP BY Code, RouteDate
    HAVING COUNT(DISTINCT CustNo) BETWEEN 10 AND 59  -- Broader range
    ORDER BY COUNT(DISTINCT CustNo) DESC
    """

    result2 = db.execute_query_df(query2)
    if result2 is not None and not result2.empty:
        print(f"   Found {len(result2)} candidates with 10-59 customers:")
        for _, row in result2.iterrows():
            print(f"     Agent: '{row['agent_id']}', Date: {row['RouteDate']}, Customers: {row['customers']}")

        # Test prospect availability for the best candidate
        best_candidate = result2.iloc[0]
        agent_id = best_candidate['agent_id']
        route_date = best_candidate['RouteDate']

        print(f"\n3. Testing prospect availability for {agent_id} on {route_date}:")
        print("-" * 40)

        # Check prospect availability
        prospect_query = f"""
        SELECT
            COUNT(DISTINCT p.CustNo) as total_prospects,
            COUNT(DISTINCT CASE WHEN p.Latitude IS NOT NULL AND p.Longitude IS NOT NULL
                                AND p.Latitude != 0 AND p.Longitude != 0
                                THEN p.CustNo END) as prospects_valid_coords,
            COUNT(DISTINCT r.barangay_code) as customer_barangay_codes
        FROM routedata r
        LEFT JOIN prospective p ON r.barangay_code = p.barangay_code
        WHERE r.Code = '{agent_id}' AND r.RouteDate = '{route_date}'
        AND r.barangay_code IS NOT NULL AND r.barangay_code != '#' AND r.barangay_code != ''
        """

        prospect_result = db.execute_query_df(prospect_query)
        if prospect_result is not None and not prospect_result.empty:
            prospects = prospect_result.iloc[0]
            customers = best_candidate['customers']
            needed = 60 - customers

            print(f"   Customer analysis:")
            print(f"     Current customers: {customers}")
            print(f"     Prospects needed: {needed}")
            print(f"     Customer barangay codes: {prospects['customer_barangay_codes']}")
            print(f"     Total prospects available: {prospects['total_prospects']}")
            print(f"     Prospects with valid coords: {prospects['prospects_valid_coords']}")

            if prospects['total_prospects'] > 0:
                scenarios['scenario2'] = {
                    'agent_id': agent_id,
                    'RouteDate': route_date,
                    'customers': customers,
                    'total_prospects': prospects['total_prospects'],
                    'prospects_valid_coords': prospects['prospects_valid_coords']
                }
                print(f"     STATUS: GOOD for SCENARIO 2 (prospects with any coords)")

            if prospects['prospects_valid_coords'] > 0:
                scenarios['scenario3'] = {
                    'agent_id': agent_id,
                    'RouteDate': route_date,
                    'customers': customers,
                    'prospects_valid_coords': prospects['prospects_valid_coords']
                }
                print(f"     STATUS: GOOD for SCENARIO 3 (prospects with valid coords)")

    else:
        print("   No candidates found in 10-59 range")

    # If no prospects found, try a different approach
    if 'scenario2' not in scenarios:
        print(f"\n4. Alternative search for prospects...")
        print("-" * 40)

        # Just check if any prospects exist at all
        prospect_check = """
        SELECT TOP 1
            COUNT(DISTINCT CustNo) as total_prospects
        FROM prospective
        WHERE barangay_code IS NOT NULL
        """

        prospect_check_result = db.execute_query_df(prospect_check)
        if prospect_check_result is not None and not prospect_check_result.empty:
            total_prospects = prospect_check_result.iloc[0]['total_prospects']
            print(f"   Total prospects in database: {total_prospects}")

            if total_prospects > 0:
                # Find any agent with matching barangay codes
                match_query = """
                SELECT TOP 3
                    r.Code as agent_id,
                    r.RouteDate,
                    COUNT(DISTINCT r.CustNo) as customers,
                    COUNT(DISTINCT p.CustNo) as prospects
                FROM routedata r
                INNER JOIN prospective p ON r.barangay_code = p.barangay_code
                WHERE r.Code IS NOT NULL AND r.Code != 'NULL'
                AND r.barangay_code IS NOT NULL AND r.barangay_code != '#' AND r.barangay_code != ''
                GROUP BY r.Code, r.RouteDate
                HAVING COUNT(DISTINCT r.CustNo) < 60
                ORDER BY COUNT(DISTINCT p.CustNo) DESC
                """

                match_result = db.execute_query_df(match_query)
                if match_result is not None and not match_result.empty:
                    print(f"   Found agents with prospect matches:")
                    for _, row in match_result.iterrows():
                        print(f"     Agent: '{row['agent_id']}', Date: {row['RouteDate']}")
                        print(f"       Customers: {row['customers']}, Prospects: {row['prospects']}")

                    best_match = match_result.iloc[0]
                    scenarios['scenario2'] = best_match
                    scenarios['scenario3'] = best_match

    db.close()
    return scenarios

def main():
    """Main function"""
    try:
        scenarios = get_final_examples()

        print(f"\n" + "=" * 50)
        print("FINAL SCENARIO EXAMPLES SUMMARY")
        print("=" * 50)

        examples = []

        # Format the results
        if 'scenario1' in scenarios:
            s1 = scenarios['scenario1']
            examples.append({
                'scenario': 'SCENARIO 1: >60 customers',
                'agent_id': s1['agent_id'],
                'route_date': s1['RouteDate'],
                'description': f"{s1['customers']} customers - no prospects needed"
            })

        if 'scenario2' in scenarios:
            s2 = scenarios['scenario2']
            if isinstance(s2, dict) and 'total_prospects' in s2:
                desc = f"{s2['customers']} customers, {s2['total_prospects']} prospects (any coords)"
            else:
                desc = f"{s2['customers']} customers, {s2['prospects']} prospects (any coords)"
            examples.append({
                'scenario': 'SCENARIO 2: 20-60 customers + prospects (any coords)',
                'agent_id': s2['agent_id'],
                'route_date': s2['RouteDate'],
                'description': desc
            })

        if 'scenario3' in scenarios:
            s3 = scenarios['scenario3']
            if isinstance(s3, dict) and 'prospects_valid_coords' in s3:
                desc = f"{s3['customers']} customers, {s3['prospects_valid_coords']} prospects (valid coords)"
            else:
                desc = f"{s3['customers']} customers, {s3['prospects']} prospects (valid coords)"
            examples.append({
                'scenario': 'SCENARIO 3: 20-60 customers + prospects (valid coords)',
                'agent_id': s3['agent_id'],
                'route_date': s3['RouteDate'],
                'description': desc
            })

        # Display results
        for i, example in enumerate(examples, 1):
            print(f"\n{i}. {example['scenario']}")
            print(f"   Agent: '{example['agent_id']}'")
            print(f"   Date: {example['route_date']}")
            print(f"   Details: {example['description']}")

        # Provide SQL templates
        print(f"\n" + "=" * 50)
        print("SQL QUERY TEMPLATES FOR DETAILED ANALYSIS")
        print("=" * 50)

        for example in examples:
            agent_id = example['agent_id']
            route_date = example['route_date']
            scenario_num = example['scenario'].split()[1].replace(':', '')

            print(f"\n-- {example['scenario']}")
            print(f"-- Agent: {agent_id}, Date: {route_date}")
            if scenario_num == "1":
                print(f"""
SELECT CustNo, latitude, longitude, barangay_code, custype, Name
FROM routedata
WHERE Code = '{agent_id}' AND RouteDate = '{route_date}'
ORDER BY CustNo;""")
            else:
                print(f"""
-- Customers
SELECT 'CUSTOMER' as type, CustNo, latitude, longitude, barangay_code, custype, Name
FROM routedata
WHERE Code = '{agent_id}' AND RouteDate = '{route_date}'

UNION ALL

-- Available prospects
SELECT 'PROSPECT' as type, CustNo, Latitude as latitude, Longitude as longitude,
       barangay_code, 'prospect' as custype, OutletName as Name
FROM prospective p
WHERE barangay_code IN (
    SELECT DISTINCT barangay_code FROM routedata
    WHERE Code = '{agent_id}' AND RouteDate = '{route_date}'
    AND barangay_code IS NOT NULL AND barangay_code != '#' AND barangay_code != ''
)
ORDER BY type, CustNo;""")

        # Update instruction
        if examples:
            print(f"\n" + "=" * 50)
            print("TO USE THESE EXAMPLES:")
            print("=" * 50)
            print("1. Update core/run_specific_agents.py:")
            print("\nspecific_agents = [")
            for example in examples:
                print(f"    ('{example['agent_id']}', '{example['route_date']}'),  # {example['scenario'].split(':')[0]}")
            print("]")
            print("\n2. Run: python core/run_specific_agents.py")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()