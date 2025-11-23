#!/usr/bin/env python3
"""
Quick Specific Scenarios - Fast lookup for the 3 scenarios
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def quick_scenario_check():
    """Quick check for specific scenarios"""
    db = DatabaseConnection()
    db.connect()

    print("Quick Specific Scenario Check")
    print("=" * 40)

    # First, get a sample of agents to check
    print("\n1. Getting sample agents...")
    sample_query = """
    SELECT TOP 20
        Code as agent_id,
        RouteDate,
        COUNT(DISTINCT CustNo) as customers
    FROM routedata
    WHERE Code IS NOT NULL
    GROUP BY Code, RouteDate
    ORDER BY COUNT(DISTINCT CustNo) DESC
    """

    sample_result = db.execute_query_df(sample_query)
    if sample_result is not None and not sample_result.empty:
        print(f"Found {len(sample_result)} agent-date combinations")

        # Categorize the sample
        scenario1 = sample_result[sample_result['customers'] > 60]
        scenario2_3 = sample_result[(sample_result['customers'] >= 20) & (sample_result['customers'] <= 60)]

        print(f"\n2. Scenario breakdown from sample:")
        print(f"   SCENARIO 1 (>60 customers): {len(scenario1)} examples")
        print(f"   SCENARIOS 2&3 (20-60 customers): {len(scenario2_3)} examples")

        # Show SCENARIO 1 examples
        if not scenario1.empty:
            print(f"\n   SCENARIO 1 Examples:")
            for _, row in scenario1.head(3).iterrows():
                print(f"     Agent: {row['agent_id']}, Date: {row['RouteDate']}, Customers: {row['customers']}")

        # Show SCENARIO 2&3 candidates
        if not scenario2_3.empty:
            print(f"\n   SCENARIOS 2&3 Candidates:")
            for _, row in scenario2_3.head(5).iterrows():
                print(f"     Agent: {row['agent_id']}, Date: {row['RouteDate']}, Customers: {row['customers']}")

        # Quick prospect check for one promising agent
        if not scenario2_3.empty:
            test_agent = scenario2_3.iloc[0]
            agent_id = test_agent['agent_id']
            route_date = test_agent['RouteDate']

            print(f"\n3. Quick prospect check for {agent_id} on {route_date}:")

            # Check if this agent has prospects
            prospect_check = f"""
            SELECT COUNT(DISTINCT p.CustNo) as prospect_count
            FROM routedata r
            INNER JOIN prospective p ON r.barangay_code = p.barangay_code
            WHERE r.Code = '{agent_id}' AND r.RouteDate = '{route_date}'
            AND r.barangay_code IS NOT NULL AND r.barangay_code != '#' AND r.barangay_code != ''
            """

            prospect_result = db.execute_query_df(prospect_check)
            if prospect_result is not None and not prospect_result.empty:
                prospect_count = prospect_result.iloc[0]['prospect_count']
                needed = 60 - test_agent['customers']
                print(f"     Prospects available: {prospect_count}")
                print(f"     Prospects needed: {needed}")

                if prospect_count > 0:
                    print(f"     Status: GOOD CANDIDATE for scenarios 2&3")
                else:
                    print(f"     Status: No prospects found")

    else:
        print("No agent data found")

    db.close()

def main():
    """Main function"""
    try:
        quick_scenario_check()

        print(f"\n" + "=" * 40)
        print("RECOMMENDATIONS:")
        print("=" * 40)
        print("1. Use agents with >60 customers for SCENARIO 1")
        print("2. Use agents with 20-60 customers for SCENARIOS 2&3")
        print("3. Check prospect availability using the detailed SQL queries")
        print("4. Update run_specific_agents.py with chosen examples")

        print(f"\nSQL FILES AVAILABLE:")
        print("- sql/specific_scenario_queries.sql (detailed queries)")
        print("- Use these to analyze specific agents in detail")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()