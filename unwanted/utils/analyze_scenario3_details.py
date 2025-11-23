#!/usr/bin/env python3
"""
Detailed Analysis of Scenario 3 - Agents with 30-60 customers with valid coords only
Show specific days and agents
"""

import sys
import os
import pandas as pd

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def analyze_scenario3_details():
    """Analyze Scenario 3 in detail - show specific days and agents"""
    print("DETAILED ANALYSIS - SCENARIO 3: AGENTS WITH 30-60 CUSTOMERS AND VALID COORDS ONLY")
    print("=" * 85)

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

        # Analyze by agent and day for Scenario 3
        print(f"\nFiltering for Scenario 3 agents...")

        scenario3_data = []

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

            # Scenario 3: 30-60 customers with ALL valid coords (no invalid coords)
            if 30 <= total_customers <= 60 and valid_count == total_customers and invalid_count == 0:
                scenario3_data.append({
                    'agent': agent,
                    'day': day,
                    'total_customers': total_customers,
                    'valid_coords': valid_count,
                    'invalid_coords': invalid_count
                })

        scenario3_df = pd.DataFrame(scenario3_data)

        if scenario3_df.empty:
            print("No agents found in Scenario 3")
            return

        print(f"\nFound {len(scenario3_df)} agent-day combinations in Scenario 3")

        # Sort by agent and then by day
        scenario3_df = scenario3_df.sort_values(['agent', 'day'])

        print(f"\n" + "=" * 85)
        print("SCENARIO 3 - DETAILED BREAKDOWN BY AGENT AND DAY")
        print("=" * 85)

        current_agent = None
        agent_total = 0
        agent_days = []

        for _, row in scenario3_df.iterrows():
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

            print(f"  {day}: {total} customers (all valid coords)")
            agent_total += total
            agent_days.append(str(day))

        # Print last agent summary
        if current_agent is not None:
            print(f"    AGENT TOTAL: {agent_total} customers across {len(agent_days)} days")
            print(f"    DAYS: {', '.join(sorted(agent_days))}")

        # Summary statistics
        print(f"\n" + "=" * 85)
        print("SCENARIO 3 - SUMMARY STATISTICS")
        print("=" * 85)

        total_customers_s3 = scenario3_df['total_customers'].sum()
        unique_agents_s3 = scenario3_df['agent'].nunique()
        unique_days_s3 = scenario3_df['day'].nunique()

        print(f"Total Agent-Day Combinations: {len(scenario3_df)}")
        print(f"Total Customers with All Valid Coords: {total_customers_s3}")
        print(f"Unique Agents: {unique_agents_s3}")
        print(f"Unique Days: {unique_days_s3}")

        # Top agents by customer count
        print(f"\nTop 10 Agents by Total Customers (All Valid Coords):")
        agent_totals = scenario3_df.groupby('agent')['total_customers'].sum().sort_values(ascending=False)
        for i, (agent, total) in enumerate(agent_totals.head(10).items(), 1):
            days_count = len(scenario3_df[scenario3_df['agent'] == agent])
            avg_customers = total / days_count
            print(f"  {i:2d}. {agent}: {total} customers across {days_count} days (avg: {avg_customers:.1f})")

        # Date range analysis
        print(f"\nDate Range Analysis:")
        date_stats = scenario3_df.groupby('day').agg({
            'agent': 'count',
            'total_customers': 'sum'
        }).sort_index()

        print(f"  Date Range: {scenario3_df['day'].min()} to {scenario3_df['day'].max()}")
        print(f"  Days with Scenario 3 agents: {len(date_stats)}")

        print(f"\nDaily Breakdown (Top 15 days by total customers):")
        date_stats_sorted = date_stats.sort_values('total_customers', ascending=False).head(15)
        for day, row in date_stats_sorted.iterrows():
            print(f"  {day}: {row['agent']} agents, {row['total_customers']} customers")

        # Customer count distribution
        print(f"\nCustomer Count Distribution:")
        customer_dist = scenario3_df['total_customers'].value_counts().sort_index()
        print("Customers per day distribution:")
        for count, frequency in customer_dist.items():
            print(f"  {count} customers: {frequency} agent-days")

        # Perfect agents (consistent performance)
        print(f"\nConsistent Performance Analysis:")
        agent_consistency = scenario3_df.groupby('agent').agg({
            'total_customers': ['count', 'mean', 'std', 'min', 'max']
        }).round(1)
        agent_consistency.columns = ['Days', 'Avg_Customers', 'Std_Dev', 'Min', 'Max']

        # Find agents with low standard deviation (consistent)
        consistent_agents = agent_consistency[agent_consistency['Std_Dev'] <= 5].sort_values('Days', ascending=False)

        if not consistent_agents.empty:
            print("Most consistent agents (std dev <= 5):")
            print(consistent_agents.head(10).to_string())

        print(f"\n" + "=" * 85)
        print("ANALYSIS COMPLETED!")
        print("=" * 85)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    analyze_scenario3_details()