#!/usr/bin/env python3
"""
Comprehensive Agent Finder - Find diverse agents for all scenarios
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def find_diverse_agents():
    """Find agents representing different scenarios"""
    db = DatabaseConnection()
    db.connect()

    print("Finding Diverse Agent Examples for All Scenarios...")
    print("=" * 60)

    all_scenarios = {}

    # 1. Get a broader sample
    print("\n1. Getting broader agent sample...")
    broad_query = """
    SELECT
        Code as agent_id,
        RouteDate,
        COUNT(DISTINCT CustNo) as customers,
        COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                   AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coords,
        COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                   OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100,
        COUNT(DISTINCT CASE WHEN barangay_code IS NOT NULL
                            AND barangay_code != '#'
                            AND barangay_code != ''
                            THEN barangay_code END) as valid_barangay_codes
    FROM routedata
    WHERE Code IS NOT NULL
    GROUP BY Code, RouteDate
    ORDER BY NEWID()  -- Random order
    OFFSET 0 ROWS FETCH NEXT 50 ROWS ONLY
    """

    broad_result = db.execute_query_df(broad_query)
    if broad_result is not None and not broad_result.empty:
        print(f"   Found {len(broad_result)} diverse agent-date combinations")

        # Categorize scenarios
        scenarios = {
            'exactly_60': broad_result[broad_result['customers'] == 60],
            'more_than_60': broad_result[broad_result['customers'] > 60],
            'less_than_60': broad_result[broad_result['customers'] < 60],
            'all_valid_coords': broad_result[(broad_result['customers'] < 60) & (broad_result['stop100'] == 0)],
            'mixed_coords': broad_result[(broad_result['customers'] < 60) & (broad_result['with_coords'] > 0) & (broad_result['stop100'] > 0)],
            'all_stop100': broad_result[(broad_result['customers'] < 60) & (broad_result['with_coords'] == 0)],
            'single_customer': broad_result[broad_result['customers'] == 1],
            'few_customers': broad_result[(broad_result['customers'] >= 2) & (broad_result['customers'] <= 10)],
            'medium_customers': broad_result[(broad_result['customers'] >= 40) & (broad_result['customers'] <= 59)],
        }

        print(f"\n2. Scenario Distribution:")
        print("-" * 40)
        for scenario_name, data in scenarios.items():
            count = len(data)
            if count > 0:
                print(f"   {scenario_name.replace('_', ' ').title()}: {count} examples")
                all_scenarios[scenario_name] = data

        # Show specific examples for each scenario
        print(f"\n3. Specific Examples by Scenario:")
        print("-" * 40)

        for scenario_name, data in all_scenarios.items():
            if not data.empty:
                print(f"\n   {scenario_name.replace('_', ' ').upper()}:")
                for _, row in data.head(3).iterrows():
                    coords_info = f"Coords: {row['with_coords']}, Stop100: {row['stop100']}"
                    barangay_info = f"Barangay codes: {row['valid_barangay_codes']}"
                    print(f"     Agent: {row['agent_id']}, Date: {row['RouteDate']}, Customers: {row['customers']}")
                    print(f"       {coords_info}, {barangay_info}")

    # 3. Check for prospect availability for promising agents
    print(f"\n4. Checking prospect availability for optimization candidates:")
    print("-" * 40)

    if 'medium_customers' in all_scenarios and not all_scenarios['medium_customers'].empty:
        # Check a few medium customer agents for prospect availability
        sample_agents = all_scenarios['medium_customers'].head(3)

        for _, agent_row in sample_agents.iterrows():
            agent_id = agent_row['agent_id']
            route_date = agent_row['RouteDate']

            prospect_query = f"""
            SELECT COUNT(DISTINCT p.CustNo) as available_prospects
            FROM routedata r
            INNER JOIN prospective p ON r.barangay_code = p.barangay_code
                AND p.Latitude IS NOT NULL AND p.Longitude IS NOT NULL
                AND p.Latitude != 0 AND p.Longitude != 0
            WHERE r.Code = '{agent_id}' AND r.RouteDate = '{route_date}'
            AND r.barangay_code IS NOT NULL AND r.barangay_code != '#' AND r.barangay_code != ''
            """

            prospect_result = db.execute_query_df(prospect_query)
            if prospect_result is not None and not prospect_result.empty:
                prospects = prospect_result.iloc[0]['available_prospects']
                customers = agent_row['customers']
                needed = 60 - customers
                can_reach_60 = "YES" if prospects >= needed else "PARTIAL"

                print(f"   Agent: {agent_id}, Date: {route_date}")
                print(f"     Customers: {customers}, Prospects available: {prospects}, Needed: {needed}")
                print(f"     Can reach 60: {can_reach_60}")

    db.close()
    return all_scenarios

def main():
    """Main function"""
    try:
        scenarios = find_diverse_agents()

        print(f"\n" + "=" * 60)
        print("COMPREHENSIVE SCENARIO EXAMPLES FOUND")
        print("=" * 60)

        # Recommend best examples for each type of testing
        recommendations = []

        if 'few_customers' in scenarios and not scenarios['few_customers'].empty:
            agent = scenarios['few_customers'].iloc[0]
            recommendations.append({
                'type': 'HIGH_PROSPECT_NEED',
                'agent': agent['agent_id'],
                'date': agent['RouteDate'],
                'customers': agent['customers'],
                'description': f"Agent with {agent['customers']} customers - needs {60-agent['customers']} prospects"
            })

        if 'medium_customers' in scenarios and not scenarios['medium_customers'].empty:
            agent = scenarios['medium_customers'].iloc[0]
            recommendations.append({
                'type': 'MODERATE_PROSPECT_NEED',
                'agent': agent['agent_id'],
                'date': agent['RouteDate'],
                'customers': agent['customers'],
                'description': f"Agent with {agent['customers']} customers - needs {60-agent['customers']} prospects"
            })

        if 'mixed_coords' in scenarios and not scenarios['mixed_coords'].empty:
            agent = scenarios['mixed_coords'].iloc[0]
            recommendations.append({
                'type': 'MIXED_COORDINATES',
                'agent': agent['agent_id'],
                'date': agent['RouteDate'],
                'customers': agent['customers'],
                'description': f"Mixed coord quality: {agent['with_coords']} with coords, {agent['stop100']} Stop100"
            })

        if 'exactly_60' in scenarios and not scenarios['exactly_60'].empty:
            agent = scenarios['exactly_60'].iloc[0]
            recommendations.append({
                'type': 'EXACTLY_60_CUSTOMERS',
                'agent': agent['agent_id'],
                'date': agent['RouteDate'],
                'customers': agent['customers'],
                'description': "Perfect count - no prospects needed"
            })

        if 'more_than_60' in scenarios and not scenarios['more_than_60'].empty:
            agent = scenarios['more_than_60'].iloc[0]
            recommendations.append({
                'type': 'EXCESS_CUSTOMERS',
                'agent': agent['agent_id'],
                'date': agent['RouteDate'],
                'customers': agent['customers'],
                'description': f"Excess customers - {agent['customers']} total"
            })

        print(f"\nTOP RECOMMENDATIONS FOR TESTING:")
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec['type']}:")
            print(f"   Agent: {rec['agent']}, Date: {rec['date']}")
            print(f"   {rec['description']}")

        print(f"\nTO USE THESE AGENTS:")
        print("1. Edit core/run_specific_agents.py")
        print("2. Update the specific_agents list:")
        print("   specific_agents = [")
        for rec in recommendations[:3]:  # Show top 3
            print(f'     ("{rec["agent"]}", "{rec["date"]}"),')
        print("   ]")
        print("3. Run: python core/run_specific_agents.py")

        print(f"\nSCENARIOS COVERED:")
        for scenario_name, data in scenarios.items():
            if not data.empty:
                print(f"• {scenario_name.replace('_', ' ').title()}: {len(data)} examples")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()