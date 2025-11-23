#!/usr/bin/env python3
"""
Find agents matching specific scenarios for distributor ID '11814'
Scenarios:
1. Agent with >60 customers but all with valid coords
2. Agent with >60 customers but mixed valid/invalid coords
3. Agent with 30-60 customers but all with valid coords
4. Agent with 30-60 customers but mixed valid/invalid coords
5. Agent with <60 customers but no valid coords
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

class ScenarioFinder:
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

    def get_distributor_agents(self):
        """Get all agents for the specific distributor"""
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
            END) as invalid_coord_customers,
            MIN(RouteDate) as earliest_date,
            MAX(RouteDate) as latest_date
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
                print(f"Found {len(result)} agent-date combinations for distributor {self.distributor_id}")
                return result
            else:
                print(f"No agent data found for distributor {self.distributor_id}")
                return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching agent data: {e}")
            return pd.DataFrame()

    def categorize_scenarios(self, agents_df):
        """Categorize agents into the 5 scenarios"""
        scenarios = {
            1: {"name": "Agent with >60 customers, ALL valid coords", "agents": []},
            2: {"name": "Agent with >60 customers, MIXED valid/invalid coords", "agents": []},
            3: {"name": "Agent with 30-60 customers, ALL valid coords", "agents": []},
            4: {"name": "Agent with 30-60 customers, MIXED valid/invalid coords", "agents": []},
            5: {"name": "Agent with <60 customers, NO valid coords", "agents": []}
        }

        for _, agent in agents_df.iterrows():
            agent_id = agent['agent_id']
            route_date = agent['route_date']
            total = agent['total_customers']
            valid = agent['valid_coord_customers']
            invalid = agent['invalid_coord_customers']

            agent_info = {
                'agent_id': agent_id,
                'route_date': route_date,
                'total_customers': total,
                'valid_coord_customers': valid,
                'invalid_coord_customers': invalid,
                'coord_percentage': (valid / total * 100) if total > 0 else 0
            }

            # Scenario 1: >60 customers, ALL valid coords
            if total > 60 and invalid == 0 and valid > 0:
                scenarios[1]["agents"].append(agent_info)

            # Scenario 2: >60 customers, MIXED valid/invalid coords
            elif total > 60 and valid > 0 and invalid > 0:
                scenarios[2]["agents"].append(agent_info)

            # Scenario 3: 30-60 customers, ALL valid coords
            elif 30 <= total <= 60 and invalid == 0 and valid > 0:
                scenarios[3]["agents"].append(agent_info)

            # Scenario 4: 30-60 customers, MIXED valid/invalid coords
            elif 30 <= total <= 60 and valid > 0 and invalid > 0:
                scenarios[4]["agents"].append(agent_info)

            # Scenario 5: <60 customers, NO valid coords
            elif total < 60 and valid == 0:
                scenarios[5]["agents"].append(agent_info)

        return scenarios

    def get_sample_customer_data(self, agent_id, route_date, limit=5):
        """Get sample customer data for an agent"""
        query = f"""
        SELECT TOP {limit}
            CustNo,
            Name,
            latitude,
            longitude,
            barangay_code,
            custype,
            address1,
            CASE
                WHEN latitude IS NOT NULL
                AND longitude IS NOT NULL
                AND latitude != 0
                AND longitude != 0
                THEN 'Valid'
                ELSE 'Invalid'
            END as coord_status
        FROM routedata
        WHERE distributorID = '{self.distributor_id}'
            AND Code = '{agent_id}'
            AND RouteDate = '{route_date}'
            AND CustNo IS NOT NULL
        ORDER BY
            CASE
                WHEN latitude IS NOT NULL
                AND longitude IS NOT NULL
                AND latitude != 0
                AND longitude != 0
                THEN 0 ELSE 1
            END,
            CustNo
        """

        try:
            result = self.db.execute_query_df(query)
            return result if result is not None else pd.DataFrame()
        except Exception as e:
            print(f"Error fetching sample data for {agent_id}: {e}")
            return pd.DataFrame()

    def print_scenario_analysis(self, scenarios):
        """Print detailed scenario analysis"""
        print("=" * 100)
        print(f"SCENARIO ANALYSIS FOR DISTRIBUTOR {self.distributor_id}")
        print("=" * 100)

        total_agents = sum(len(scenario["agents"]) for scenario in scenarios.values())
        print(f"Total agent-date combinations found: {total_agents}")
        print()

        for scenario_num, scenario_data in scenarios.items():
            agents = scenario_data["agents"]
            count = len(agents)

            print(f"SCENARIO {scenario_num}: {scenario_data['name']}")
            print(f"Count: {count} agent-date combinations")
            print("-" * 80)

            if count > 0:
                # Show summary statistics
                total_customers = [a['total_customers'] for a in agents]
                valid_coords = [a['valid_coord_customers'] for a in agents]

                print(f"Customer count range: {min(total_customers)} - {max(total_customers)}")
                print(f"Average customers: {sum(total_customers)/len(total_customers):.1f}")
                print(f"Average valid coords: {sum(valid_coords)/len(valid_coords):.1f}")
                print()

                # Show top examples
                print("Top Examples:")
                for i, agent in enumerate(agents[:5]):  # Show first 5
                    print(f"  {i+1}. Agent: {agent['agent_id']}, Date: {agent['route_date']}")
                    print(f"     Customers: {agent['total_customers']} "
                          f"(Valid coords: {agent['valid_coord_customers']}, "
                          f"Invalid coords: {agent['invalid_coord_customers']})")
                    print(f"     Coord percentage: {agent['coord_percentage']:.1f}%")

                if count > 5:
                    print(f"     ... and {count - 5} more")
                print()

                # Show sample customer data for first agent
                if agents:
                    sample_agent = agents[0]
                    print(f"Sample customer data for {sample_agent['agent_id']} on {sample_agent['route_date']}:")
                    sample_data = self.get_sample_customer_data(
                        sample_agent['agent_id'],
                        sample_agent['route_date']
                    )
                    if not sample_data.empty:
                        print(sample_data.to_string(index=False))
                    else:
                        print("  No sample data available")
            else:
                print("No agents found for this scenario")

            print()

    def export_scenarios_to_csv(self, scenarios, filename=None):
        """Export scenario results to CSV"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'distributor_{self.distributor_id}_scenarios_{timestamp}.csv'

        all_data = []
        for scenario_num, scenario_data in scenarios.items():
            for agent in scenario_data["agents"]:
                row = {
                    'scenario': scenario_num,
                    'scenario_name': scenario_data['name'],
                    'agent_id': agent['agent_id'],
                    'route_date': agent['route_date'],
                    'total_customers': agent['total_customers'],
                    'valid_coord_customers': agent['valid_coord_customers'],
                    'invalid_coord_customers': agent['invalid_coord_customers'],
                    'coord_percentage': round(agent['coord_percentage'], 1),
                    'distributor_id': self.distributor_id
                }
                all_data.append(row)

        if all_data:
            df = pd.DataFrame(all_data)
            df.to_csv(filename, index=False)
            print(f"Results exported to: {filename}")
            return filename
        else:
            print("No data to export")
            return None

    def generate_processing_commands(self, scenarios):
        """Generate commands to process specific scenarios"""
        print("=" * 100)
        print("PROCESSING COMMANDS")
        print("=" * 100)

        for scenario_num, scenario_data in scenarios.items():
            agents = scenario_data["agents"]
            if agents:
                print(f"\nSCENARIO {scenario_num} - {len(agents)} agents:")
                print("Agent-date combinations to process:")

                for agent in agents[:10]:  # Show first 10
                    print(f"  ('{agent['agent_id']}', '{agent['route_date']}'),")

                if len(agents) > 10:
                    print(f"  ... and {len(agents) - 10} more")

    def run_analysis(self):
        """Run the complete scenario analysis"""
        print("Starting scenario analysis...")

        if not self.connect_database():
            return False

        try:
            # Get all agents for the distributor
            agents_df = self.get_distributor_agents()

            if agents_df.empty:
                print("No data found for analysis")
                return False

            # Categorize into scenarios
            scenarios = self.categorize_scenarios(agents_df)

            # Print analysis
            self.print_scenario_analysis(scenarios)

            # Generate processing commands
            self.generate_processing_commands(scenarios)

            # Export to CSV
            csv_file = self.export_scenarios_to_csv(scenarios)

            print("=" * 100)
            print("ANALYSIS COMPLETED!")
            if csv_file:
                print(f"Results saved to: {csv_file}")
            print("=" * 100)

            return scenarios

        except Exception as e:
            print(f"Error during analysis: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            if self.db:
                self.db.connection.close()

def main():
    """Main function"""
    print("=" * 100)
    print("DISTRIBUTOR SCENARIO FINDER")
    print(f"Distributor ID: 11814")
    print("=" * 100)

    finder = ScenarioFinder()
    scenarios = finder.run_analysis()

    if scenarios:
        print("\nScenario Summary:")
        for scenario_num, scenario_data in scenarios.items():
            count = len(scenario_data["agents"])
            print(f"  Scenario {scenario_num}: {count} agents - {scenario_data['name']}")

if __name__ == "__main__":
    main()