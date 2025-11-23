#!/usr/bin/env python3
"""
Analyze Agent Scenarios for Distributor 11814
Categorize agents by customer count and coordinate validity
"""

import sys
import os
import pandas as pd

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def analyze_agent_scenarios():
    """Analyze agent scenarios for distributor 11814"""
    print("ANALYZING AGENT SCENARIOS - DISTRIBUTOR 11814")
    print("=" * 70)

    distributor_id = "11814"

    db = None

    try:
        # Connect to database
        db = DatabaseConnection()
        db.connect()
        print("Database connection successful!")

        # Get all data for distributor 11814
        print(f"\nGetting all data for distributor {distributor_id}...")
        main_query = f"""
        SELECT
            Code as agent,
            RouteDate as day,
            latitude,
            longitude,
            CustNo,
            barangay_code
        FROM routedata
        WHERE distributorid = '{distributor_id}'
        """

        df = db.execute_query_df(main_query)

        if df is None or df.empty:
            print(f"No data found for distributor {distributor_id}")
            return

        print(f"SUCCESS: Found {len(df)} total records")

        # Analyze by agent and day
        print(f"\nAnalyzing agents by day...")

        # Group by agent and day
        agent_day_stats = []

        for (agent, day), group in df.groupby(['agent', 'day']):
            total_customers = len(group)

            # Check coordinate validity
            valid_coords = group[
                (group['latitude'].notna()) &
                (group['longitude'].notna()) &
                (group['latitude'] != 0) &
                (group['longitude'] != 0)
            ]

            valid_count = len(valid_coords)
            invalid_count = total_customers - valid_count

            agent_day_stats.append({
                'agent': agent,
                'day': day,
                'total_customers': total_customers,
                'valid_coords': valid_count,
                'invalid_coords': invalid_count,
                'has_valid_coords': valid_count > 0,
                'has_invalid_coords': invalid_count > 0
            })

        agent_df = pd.DataFrame(agent_day_stats)

        # Categorize according to scenarios
        print(f"\n" + "=" * 70)
        print("SCENARIO ANALYSIS")
        print("=" * 70)

        scenarios = {
            1: [],  # >60 with valid coords only
            2: [],  # >60 with valid and invalid coords
            3: [],  # 30-60 with valid coords only
            4: [],  # 30-60 with valid and invalid coords
            5: []   # <60 with no valid coords
        }

        for _, row in agent_df.iterrows():
            agent = row['agent']
            day = row['day']
            total = row['total_customers']
            valid = row['valid_coords']
            invalid = row['invalid_coords']
            has_valid = row['has_valid_coords']
            has_invalid = row['has_invalid_coords']

            scenario_info = {
                'agent': agent,
                'day': day,
                'total_customers': total,
                'valid_coords': valid,
                'invalid_coords': invalid
            }

            if total > 60:
                if has_valid and not has_invalid:
                    scenarios[1].append(scenario_info)
                elif has_valid and has_invalid:
                    scenarios[2].append(scenario_info)
            elif 30 <= total <= 60:
                if has_valid and not has_invalid:
                    scenarios[3].append(scenario_info)
                elif has_valid and has_invalid:
                    scenarios[4].append(scenario_info)
            elif total < 60 and not has_valid:
                scenarios[5].append(scenario_info)

        # Display results
        scenario_descriptions = {
            1: "Agents with >60 customers but with valid coords only",
            2: "Agents with >60 customers but with valid and invalid coords",
            3: "Agents with 30-60 customers and valid coords only",
            4: "Agents with 30-60 customers and valid and invalid coords",
            5: "Agents with <60 customers but no valid coords"
        }

        for scenario_num in range(1, 6):
            print(f"\nScenario {scenario_num}: {scenario_descriptions[scenario_num]}")
            print("-" * 60)

            scenario_data = scenarios[scenario_num]

            if scenario_data:
                print(f"Found {len(scenario_data)} agent-day combinations:")

                # Sort by total customers descending
                scenario_data.sort(key=lambda x: x['total_customers'], reverse=True)

                for item in scenario_data[:10]:  # Show top 10
                    agent = item['agent']
                    day = item['day']
                    total = item['total_customers']
                    valid = item['valid_coords']
                    invalid = item['invalid_coords']

                    print(f"  Agent: {agent}, Day: {day}, Total: {total}, Valid: {valid}, Invalid: {invalid}")

                if len(scenario_data) > 10:
                    print(f"  ... and {len(scenario_data) - 10} more combinations")

                # Summary stats for this scenario
                total_customers = sum(item['total_customers'] for item in scenario_data)
                total_valid = sum(item['valid_coords'] for item in scenario_data)
                total_invalid = sum(item['invalid_coords'] for item in scenario_data)

                print(f"  TOTALS: {total_customers} customers, {total_valid} valid coords, {total_invalid} invalid coords")
            else:
                print("  No agents found matching this scenario")

        # Overall statistics
        print(f"\n" + "=" * 70)
        print("OVERALL STATISTICS")
        print("=" * 70)

        total_agent_days = len(agent_df)
        unique_agents = agent_df['agent'].nunique()
        unique_days = agent_df['day'].nunique()

        print(f"Total Agent-Day Combinations: {total_agent_days}")
        print(f"Unique Agents: {unique_agents}")
        print(f"Unique Days: {unique_days}")

        # Agent summary
        print(f"\nAgent Summary:")
        agent_summary = agent_df.groupby('agent').agg({
            'total_customers': 'sum',
            'valid_coords': 'sum',
            'invalid_coords': 'sum',
            'day': 'count'
        }).sort_values('total_customers', ascending=False)

        agent_summary.columns = ['Total_Customers', 'Valid_Coords', 'Invalid_Coords', 'Days_Active']

        print(agent_summary.head(15).to_string())

        print(f"\n" + "=" * 70)
        print("ANALYSIS COMPLETED!")
        print("=" * 70)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    analyze_agent_scenarios()