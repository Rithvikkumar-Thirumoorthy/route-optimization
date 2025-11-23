#!/usr/bin/env python3
"""
Detailed Analysis of Scenario 5 - Agents with <60 customers but no valid coords
Show specific days and agents
"""

import sys
import os
import pandas as pd

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def analyze_scenario5_details():
    """Analyze Scenario 5 in detail - show specific days and agents"""
    print("DETAILED ANALYSIS - SCENARIO 5: AGENTS WITH <60 CUSTOMERS BUT NO VALID COORDS")
    print("=" * 80)

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
            CustNo
        FROM routedata
        WHERE distributorid = '{distributor_id}'
        """

        df = db.execute_query_df(main_query)

        if df is None or df.empty:
            print(f"No data found for distributor {distributor_id}")
            return

        print(f"SUCCESS: Found {len(df)} total records")

        # Analyze by agent and day for Scenario 5
        print(f"\nFiltering for Scenario 5 agents...")

        scenario5_data = []

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

            # Scenario 5: <60 customers with no valid coords
            if total_customers < 60 and valid_count == 0:
                scenario5_data.append({
                    'agent': agent,
                    'day': day,
                    'total_customers': total_customers,
                    'valid_coords': valid_count,
                    'invalid_coords': total_customers - valid_count
                })

        scenario5_df = pd.DataFrame(scenario5_data)

        if scenario5_df.empty:
            print("No agents found in Scenario 5")
            return

        print(f"\nFound {len(scenario5_df)} agent-day combinations in Scenario 5")

        # Sort by agent and then by day
        scenario5_df = scenario5_df.sort_values(['agent', 'day'])

        print(f"\n" + "=" * 80)
        print("SCENARIO 5 - DETAILED BREAKDOWN BY AGENT AND DAY")
        print("=" * 80)

        current_agent = None
        agent_total = 0
        agent_days = []

        for _, row in scenario5_df.iterrows():
            agent = row['agent']
            day = row['day']
            total = row['total_customers']

            # Group by agent
            if current_agent != agent:
                if current_agent is not None:
                    print(f"    AGENT TOTAL: {agent_total} customers across {len(agent_days)} days")
                    print(f"    DAYS: {', '.join(sorted([str(d) for d in agent_days]))}")
                    print()

                current_agent = agent
                agent_total = 0
                agent_days = []
                print(f"Agent: {agent}")

            print(f"  {day}: {total} customers (0 valid coords)")
            agent_total += total
            agent_days.append(str(day))

        # Print last agent summary
        if current_agent is not None:
            print(f"    AGENT TOTAL: {agent_total} customers across {len(agent_days)} days")
            print(f"    DAYS: {', '.join(sorted(agent_days))}")

        # Summary statistics
        print(f"\n" + "=" * 80)
        print("SCENARIO 5 - SUMMARY STATISTICS")
        print("=" * 80)

        total_customers_s5 = scenario5_df['total_customers'].sum()
        unique_agents_s5 = scenario5_df['agent'].nunique()
        unique_days_s5 = scenario5_df['day'].nunique()

        print(f"Total Agent-Day Combinations: {len(scenario5_df)}")
        print(f"Total Customers with No Valid Coords: {total_customers_s5}")
        print(f"Unique Agents: {unique_agents_s5}")
        print(f"Unique Days: {unique_days_s5}")

        # Top agents by customer count
        print(f"\nTop 10 Agents by Total Customers (No Valid Coords):")
        agent_totals = scenario5_df.groupby('agent')['total_customers'].sum().sort_values(ascending=False)
        for i, (agent, total) in enumerate(agent_totals.head(10).items(), 1):
            days_count = len(scenario5_df[scenario5_df['agent'] == agent])
            print(f"  {i:2d}. {agent}: {total} customers across {days_count} days")

        # Date range analysis
        print(f"\nDate Range Analysis:")
        date_stats = scenario5_df.groupby('day').agg({
            'agent': 'count',
            'total_customers': 'sum'
        }).sort_index()

        print(f"  Date Range: {scenario5_df['day'].min()} to {scenario5_df['day'].max()}")
        print(f"  Days with Scenario 5 issues: {len(date_stats)}")

        print(f"\nDaily Breakdown (Top 10 days by affected agents):")
        date_stats_sorted = date_stats.sort_values('agent', ascending=False).head(10)
        for day, row in date_stats_sorted.iterrows():
            print(f"  {day}: {row['agent']} agents, {row['total_customers']} customers")

        print(f"\n" + "=" * 80)
        print("ANALYSIS COMPLETED!")
        print("=" * 80)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    analyze_scenario5_details()