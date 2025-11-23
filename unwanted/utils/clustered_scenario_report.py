#!/usr/bin/env python3
"""
Generate clustered scenario report for distributor 11814
Group agents by patterns and present in readable format
"""

import sys
import os
import pandas as pd
from datetime import datetime
from collections import defaultdict

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

class ClusteredScenarioReporter:
    def __init__(self):
        self.db = None
        self.distributor_id = '11814'

    def connect_database(self):
        """Connect to database"""
        try:
            self.db = DatabaseConnection()
            self.db.connect()
            return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False

    def get_agent_data(self):
        """Get agent data with clustering information"""
        query = f"""
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
        WHERE distributorID = '{self.distributor_id}'
            AND Code IS NOT NULL
            AND RouteDate IS NOT NULL
            AND CustNo IS NOT NULL
        GROUP BY Code, RouteDate
        HAVING COUNT(DISTINCT CustNo) >= 1
        ORDER BY Code, RouteDate DESC
        """

        try:
            result = self.db.execute_query_df(query)
            if result is not None and not result.empty:
                # Add calculated fields
                result['coord_percentage'] = (result['valid_coord_customers'] / result['total_customers'] * 100).round(1)

                # Add scenario classification
                result['scenario'] = result.apply(self.classify_scenario, axis=1)
                result['scenario_name'] = result['scenario'].map(self.get_scenario_name)

                # Format date for display
                result['formatted_date'] = pd.to_datetime(result['route_date']).dt.strftime('%d/%m/%Y')

                return result
            else:
                return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching agent data: {e}")
            return pd.DataFrame()

    def classify_scenario(self, row):
        """Classify agent into scenario"""
        total = row['total_customers']
        valid = row['valid_coord_customers']
        invalid = row['invalid_coord_customers']

        if total > 60 and invalid == 0 and valid > 0:
            return 1
        elif total > 60 and valid > 0 and invalid > 0:
            return 2
        elif 30 <= total <= 60 and invalid == 0 and valid > 0:
            return 3
        elif 30 <= total <= 60 and valid > 0 and invalid > 0:
            return 4
        elif total < 60 and valid == 0:
            return 5
        else:
            return 0

    def get_scenario_name(self, scenario):
        """Get scenario description"""
        scenarios = {
            1: "Agent with >60 customers, ALL valid coords",
            2: "Agent with >60 customers, MIXED valid/invalid coords",
            3: "Agent with 30-60 customers, ALL valid coords",
            4: "Agent with 30-60 customers, MIXED valid/invalid coords",
            5: "Agent with <60 customers, NO valid coords",
            0: "Other scenarios"
        }
        return scenarios.get(scenario, "Unknown")

    def cluster_agents_by_pattern(self, df):
        """Cluster agents by common patterns"""
        clustered = defaultdict(list)

        for _, row in df.iterrows():
            agent_id = row['agent_id']
            scenario = row['scenario']

            # Group by agent prefix and scenario
            agent_prefix = agent_id.split('-')[0] if '-' in agent_id else agent_id
            key = f"{agent_prefix}_scenario_{scenario}"

            clustered[key].append({
                'agent_id': agent_id,
                'route_date': row['formatted_date'],
                'total_customers': row['total_customers'],
                'valid_coords': row['valid_coord_customers'],
                'invalid_coords': row['invalid_coord_customers'],
                'coord_percentage': row['coord_percentage'],
                'scenario': scenario,
                'scenario_name': row['scenario_name']
            })

        return dict(clustered)

    def print_clustered_report(self, clustered_data):
        """Print clustered scenario report"""
        print("=" * 100)
        print(f"CLUSTERED SCENARIO REPORT - DISTRIBUTOR {self.distributor_id}")
        print("=" * 100)

        # Group by scenario first
        scenarios = defaultdict(list)
        for cluster_key, agents in clustered_data.items():
            scenario_num = agents[0]['scenario']
            scenarios[scenario_num].append((cluster_key, agents))

        total_agents = sum(len(agents) for agents in clustered_data.values())
        print(f"Total agent-date combinations: {total_agents}")
        print()

        for scenario_num in sorted(scenarios.keys()):
            if scenario_num == 0:
                continue

            scenario_agents = scenarios[scenario_num]
            scenario_name = scenario_agents[0][1][0]['scenario_name']
            total_scenario_count = sum(len(agents) for _, agents in scenario_agents)

            print(f"SCENARIO {scenario_num}: {scenario_name}")
            print(f"   Total: {total_scenario_count} agent-date combinations")
            print("-" * 90)

            # Group by agent family
            for cluster_key, agents in sorted(scenario_agents, key=lambda x: x[0]):
                agent_family = cluster_key.replace(f'_scenario_{scenario_num}', '')

                print(f"\n{agent_family.upper()} Family ({len(agents)} agents):")

                # Group agents by same agent_id for cleaner display
                agent_groups = defaultdict(list)
                for agent in agents:
                    agent_groups[agent['agent_id']].append(agent)

                for agent_id, agent_dates in sorted(agent_groups.items()):
                    if len(agent_dates) == 1:
                        agent = agent_dates[0]
                        print(f"   • Agent with {self.format_customer_count(agent['total_customers'])} customers")
                        print(f"     \"{agent_id}\" on \"{agent['route_date']}\"")
                        print(f"     ({agent['valid_coords']} valid coords, {agent['invalid_coords']} invalid coords - {agent['coord_percentage']}%)")
                    else:
                        # Multiple dates for same agent
                        print(f"   • Agent with {self.format_customer_count(agent_dates[0]['total_customers'])} customers (multiple dates)")
                        print(f"     \"{agent_id}\":")
                        for agent in sorted(agent_dates, key=lambda x: x['route_date']):
                            print(f"       - {agent['route_date']} ({agent['total_customers']} customers, {agent['coord_percentage']}% valid)")

            print()

    def format_customer_count(self, count):
        """Format customer count description"""
        if count > 60:
            return f">60 ({count})"
        elif count >= 30:
            return f"30-60 ({count})"
        else:
            return f"<60 ({count})"

    def generate_processing_lists(self, clustered_data):
        """Generate processing lists for each scenario"""
        print("=" * 100)
        print("PROCESSING LISTS BY SCENARIO")
        print("=" * 100)

        scenarios = defaultdict(list)
        for cluster_key, agents in clustered_data.items():
            scenario_num = agents[0]['scenario']
            scenarios[scenario_num].extend(agents)

        for scenario_num in sorted(scenarios.keys()):
            if scenario_num == 0:
                continue

            agents = scenarios[scenario_num]
            scenario_name = agents[0]['scenario_name']

            print(f"\nSCENARIO {scenario_num}: {scenario_name}")
            print(f"Processing list ({len(agents)} agents):")
            print("```python")
            print("specific_agents = [")

            for agent in sorted(agents, key=lambda x: (x['agent_id'], x['route_date'])):
                # Convert date back to SQL format
                date_parts = agent['route_date'].split('/')
                sql_date = f"{date_parts[2]}-{date_parts[1].zfill(2)}-{date_parts[0].zfill(2)}"
                print(f"    (\"{agent['agent_id']}\", \"{sql_date}\"),  # {agent['total_customers']} customers, {agent['coord_percentage']}% valid")

            print("]")
            print("```")
            print()

    def export_clustered_report(self, clustered_data):
        """Export clustered report to files"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Export detailed CSV
        all_data = []
        for cluster_key, agents in clustered_data.items():
            agent_family = cluster_key.split('_scenario_')[0]
            for agent in agents:
                # Convert date back to SQL format
                date_parts = agent['route_date'].split('/')
                sql_date = f"{date_parts[2]}-{date_parts[1].zfill(2)}-{date_parts[0].zfill(2)}"

                all_data.append({
                    'scenario': agent['scenario'],
                    'scenario_name': agent['scenario_name'],
                    'agent_family': agent_family.upper(),
                    'agent_id': agent['agent_id'],
                    'route_date': sql_date,
                    'formatted_date': agent['route_date'],
                    'total_customers': agent['total_customers'],
                    'valid_coords': agent['valid_coords'],
                    'invalid_coords': agent['invalid_coords'],
                    'coord_percentage': agent['coord_percentage'],
                    'distributor_id': self.distributor_id
                })

        if all_data:
            df = pd.DataFrame(all_data)
            csv_file = f'clustered_distributor_{self.distributor_id}_report_{timestamp}.csv'
            df.to_csv(csv_file, index=False)
            print(f"Detailed report exported to: {csv_file}")

            # Export processing lists by scenario
            txt_file = f'processing_lists_{self.distributor_id}_{timestamp}.txt'
            with open(txt_file, 'w') as f:
                scenarios = defaultdict(list)
                for item in all_data:
                    scenarios[item['scenario']].append(item)

                for scenario_num in sorted(scenarios.keys()):
                    if scenario_num == 0:
                        continue

                    agents = scenarios[scenario_num]
                    f.write(f"SCENARIO {scenario_num}: {agents[0]['scenario_name']}\n")
                    f.write("=" * 80 + "\n")
                    f.write("specific_agents = [\n")

                    for agent in sorted(agents, key=lambda x: (x['agent_id'], x['route_date'])):
                        f.write(f"    (\"{agent['agent_id']}\", \"{agent['route_date']}\"),  # {agent['total_customers']} customers, {agent['coord_percentage']}% valid\n")

                    f.write("]\n\n")

            print(f"Processing lists exported to: {txt_file}")
            return csv_file, txt_file

        return None, None

    def run_clustered_analysis(self):
        """Run the complete clustered analysis"""
        print("Starting clustered scenario analysis...")

        if not self.connect_database():
            return False

        try:
            # Get agent data
            df = self.get_agent_data()

            if df.empty:
                print("No data found for analysis")
                return False

            # Filter only scenarios we care about
            df = df[df['scenario'] > 0]

            # Cluster agents by patterns
            clustered_data = self.cluster_agents_by_pattern(df)

            # Print clustered report
            self.print_clustered_report(clustered_data)

            # Generate processing lists
            self.generate_processing_lists(clustered_data)

            # Export reports
            csv_file, txt_file = self.export_clustered_report(clustered_data)

            print("=" * 100)
            print("CLUSTERED ANALYSIS COMPLETED!")
            if csv_file:
                print(f"Detailed report: {csv_file}")
            if txt_file:
                print(f"Processing lists: {txt_file}")
            print("=" * 100)

            return True

        except Exception as e:
            print(f"Error during clustered analysis: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            if self.db:
                self.db.connection.close()

def main():
    """Main function"""
    print("CLUSTERED SCENARIO REPORTER")
    print(f"Distributor ID: 11814")
    print("=" * 50)

    reporter = ClusteredScenarioReporter()
    reporter.run_clustered_analysis()

if __name__ == "__main__":
    main()