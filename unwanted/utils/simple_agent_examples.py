#!/usr/bin/env python3
"""
Simple Agent Examples - Get basic agent examples quickly
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def get_simple_examples():
    """Get simple agent examples"""
    db = DatabaseConnection()
    db.connect()

    print("Finding Simple Agent Examples...")
    print("=" * 40)

    # Just get some basic agent data
    print("\n1. Sample agents and their customer counts:")
    query = """
    SELECT TOP 10
        Code as agent_id,
        RouteDate,
        COUNT(DISTINCT CustNo) as customers
    FROM routedata
    WHERE Code IS NOT NULL
    GROUP BY Code, RouteDate
    ORDER BY Code, RouteDate
    """

    result = db.execute_query_df(query)
    if result is not None and not result.empty:
        for _, row in result.iterrows():
            print(f"   Agent: {row['agent_id']}, Date: {row['RouteDate']}, Customers: {row['customers']}")

        # Categorize the results
        exactly_60 = result[result['customers'] == 60]
        more_than_60 = result[result['customers'] > 60]
        less_than_60 = result[result['customers'] < 60]

        print(f"\nFrom this sample:")
        print(f"   Exactly 60 customers: {len(exactly_60)} agents")
        print(f"   More than 60 customers: {len(more_than_60)} agents")
        print(f"   Less than 60 customers: {len(less_than_60)} agents")

        if not less_than_60.empty:
            print(f"\nAgents needing optimization (< 60 customers):")
            for _, row in less_than_60.head(3).iterrows():
                prospects_needed = 60 - row['customers']
                print(f"   Agent: {row['agent_id']}, Date: {row['RouteDate']}")
                print(f"     Has: {row['customers']} customers, Needs: {prospects_needed} prospects")

        if not exactly_60.empty:
            print(f"\nAgents with exactly 60 customers:")
            for _, row in exactly_60.head(2).iterrows():
                print(f"   Agent: {row['agent_id']}, Date: {row['RouteDate']}")

        if not more_than_60.empty:
            print(f"\nAgents with more than 60 customers:")
            for _, row in more_than_60.head(2).iterrows():
                print(f"   Agent: {row['agent_id']}, Date: {row['RouteDate']} - {row['customers']} customers")

    else:
        print("   No data found")

    db.close()

def main():
    """Main function"""
    try:
        get_simple_examples()

        print(f"\n" + "=" * 40)
        print("USAGE:")
        print("=" * 40)
        print("Use these agents with run_specific_agents.py:")
        print("1. Edit run_specific_agents.py")
        print("2. Update the specific_agents list with agents from above")
        print("3. Run: python core/run_specific_agents.py")

        print(f"\nExample scenarios covered:")
        print("• Agents needing prospects (< 60 customers)")
        print("• Agents with perfect count (= 60 customers)")
        print("• Agents with excess customers (> 60 customers)")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()