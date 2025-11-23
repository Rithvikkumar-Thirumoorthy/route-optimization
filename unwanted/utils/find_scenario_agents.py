#!/usr/bin/env python3
"""
Find Real Agents and Days for All Route Optimization Scenarios
READ-ONLY: Only executes SELECT statements to find examples
"""

import sys
import os
import pandas as pd

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

class ScenarioFinder:
    def __init__(self):
        self.db = DatabaseConnection()
        self.db.connect()
        self.scenarios = {}

    def find_scenario_1_exactly_60(self):
        """Find agents with exactly 60 customers"""
        query = """
        SELECT TOP 5
            'SCENARIO_1_EXACTLY_60' as scenario_type,
            Code as agent_id,
            RouteDate as route_date,
            COUNT(DISTINCT CustNo) as customer_count,
            COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                       AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
            COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                       OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count
        FROM routedata
        WHERE Code IS NOT NULL
        GROUP BY Code, RouteDate
        HAVING COUNT(DISTINCT CustNo) = 60
        ORDER BY Code, RouteDate
        """
        return self.db.execute_query_df(query)

    def find_scenario_2_more_than_60(self):
        """Find agents with more than 60 customers"""
        query = """
        SELECT TOP 5
            'SCENARIO_2_MORE_THAN_60' as scenario_type,
            Code as agent_id,
            RouteDate as route_date,
            COUNT(DISTINCT CustNo) as customer_count,
            COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                       AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
            COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                       OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count
        FROM routedata
        WHERE Code IS NOT NULL
        GROUP BY Code, RouteDate
        HAVING COUNT(DISTINCT CustNo) > 60
        ORDER BY COUNT(DISTINCT CustNo) DESC
        """
        return self.db.execute_query_df(query)

    def find_scenario_3_less_than_60(self):
        """Find agents with less than 60 customers"""
        query = """
        SELECT TOP 10
            'SCENARIO_3_LESS_THAN_60' as scenario_type,
            Code as agent_id,
            RouteDate as route_date,
            COUNT(DISTINCT CustNo) as customer_count,
            COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                       AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
            COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                       OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count,
            (60 - COUNT(DISTINCT CustNo)) as prospects_needed
        FROM routedata
        WHERE Code IS NOT NULL
        GROUP BY Code, RouteDate
        HAVING COUNT(DISTINCT CustNo) < 60
        ORDER BY COUNT(DISTINCT CustNo) DESC
        """
        return self.db.execute_query_df(query)

    def find_scenario_4_all_valid_coords(self):
        """Find agents where ALL customers have valid coordinates"""
        query = """
        SELECT TOP 5
            'SCENARIO_4_ALL_VALID_COORDS' as scenario_type,
            Code as agent_id,
            RouteDate as route_date,
            COUNT(DISTINCT CustNo) as customer_count,
            COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                       AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
            COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                       OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count
        FROM routedata
        WHERE Code IS NOT NULL
        GROUP BY Code, RouteDate
        HAVING COUNT(DISTINCT CustNo) < 60
        AND COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                      OR latitude = 0 OR longitude = 0 THEN 1 END) = 0
        ORDER BY COUNT(DISTINCT CustNo) DESC
        """
        return self.db.execute_query_df(query)

    def find_scenario_5_mixed_coordinates(self):
        """Find agents with mixed coordinate quality"""
        query = """
        SELECT TOP 5
            'SCENARIO_5_MIXED_COORDINATES' as scenario_type,
            Code as agent_id,
            RouteDate as route_date,
            COUNT(DISTINCT CustNo) as customer_count,
            COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                       AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
            COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                       OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count,
            CAST(COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                           OR latitude = 0 OR longitude = 0 THEN 1 END) * 100.0 / COUNT(*) AS DECIMAL(5,1)) as stop100_percentage
        FROM routedata
        WHERE Code IS NOT NULL
        GROUP BY Code, RouteDate
        HAVING COUNT(DISTINCT CustNo) < 60
        AND COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                      AND latitude != 0 AND longitude != 0 THEN 1 END) > 0
        AND COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                      OR latitude = 0 OR longitude = 0 THEN 1 END) > 0
        ORDER BY COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                           OR latitude = 0 OR longitude = 0 THEN 1 END) DESC
        """
        return self.db.execute_query_df(query)

    def find_scenario_6_all_invalid_coords(self):
        """Find agents where ALL customers lack coordinates"""
        query = """
        SELECT TOP 3
            'SCENARIO_6_ALL_INVALID_COORDS' as scenario_type,
            Code as agent_id,
            RouteDate as route_date,
            COUNT(DISTINCT CustNo) as customer_count,
            COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                       AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
            COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                       OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count
        FROM routedata
        WHERE Code IS NOT NULL
        GROUP BY Code, RouteDate
        HAVING COUNT(DISTINCT CustNo) < 60
        AND COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                      AND latitude != 0 AND longitude != 0 THEN 1 END) = 0
        ORDER BY COUNT(DISTINCT CustNo) DESC
        """
        return self.db.execute_query_df(query)

    def find_scenario_11_prospects_available(self):
        """Find agents with prospects available in same barangay"""
        query = """
        SELECT TOP 5
            'SCENARIO_11_PROSPECTS_AVAILABLE' as scenario_type,
            r.Code as agent_id,
            r.RouteDate as route_date,
            COUNT(DISTINCT r.CustNo) as customer_count,
            COUNT(DISTINCT r.barangay_code) as unique_barangay_codes,
            COUNT(DISTINCT p.CustNo) as available_prospects,
            (60 - COUNT(DISTINCT r.CustNo)) as prospects_needed,
            CASE
                WHEN COUNT(DISTINCT p.CustNo) >= (60 - COUNT(DISTINCT r.CustNo))
                THEN 'CAN_REACH_60'
                ELSE 'PARTIAL_FILL'
            END as fill_capability
        FROM routedata r
        INNER JOIN prospective p ON r.barangay_code = p.barangay_code
            AND p.Latitude IS NOT NULL
            AND p.Longitude IS NOT NULL
            AND p.Latitude != 0
            AND p.Longitude != 0
        WHERE r.Code IS NOT NULL
        AND r.barangay_code IS NOT NULL
        AND r.barangay_code != '#'
        AND r.barangay_code != ''
        GROUP BY r.Code, r.RouteDate
        HAVING COUNT(DISTINCT r.CustNo) < 60
        AND COUNT(DISTINCT p.CustNo) > 0
        ORDER BY COUNT(DISTINCT p.CustNo) DESC
        """
        return self.db.execute_query_df(query)

    def find_scenario_13_insufficient_prospects(self):
        """Find agents where available prospects < needed count"""
        query = """
        SELECT TOP 5
            'SCENARIO_13_INSUFFICIENT_PROSPECTS' as scenario_type,
            r.Code as agent_id,
            r.RouteDate as route_date,
            COUNT(DISTINCT r.CustNo) as customer_count,
            COUNT(DISTINCT p.CustNo) as available_prospects,
            (60 - COUNT(DISTINCT r.CustNo)) as prospects_needed,
            (COUNT(DISTINCT r.CustNo) + COUNT(DISTINCT p.CustNo)) as max_possible_total
        FROM routedata r
        INNER JOIN prospective p ON r.barangay_code = p.barangay_code
            AND p.Latitude IS NOT NULL
            AND p.Longitude IS NOT NULL
            AND p.Latitude != 0
            AND p.Longitude != 0
        WHERE r.Code IS NOT NULL
        AND r.barangay_code IS NOT NULL
        AND r.barangay_code != '#'
        AND r.barangay_code != ''
        GROUP BY r.Code, r.RouteDate
        HAVING COUNT(DISTINCT r.CustNo) < 60
        AND COUNT(DISTINCT p.CustNo) > 0
        AND COUNT(DISTINCT p.CustNo) < (60 - COUNT(DISTINCT r.CustNo))
        ORDER BY COUNT(DISTINCT p.CustNo) ASC
        """
        return self.db.execute_query_df(query)

    def find_scenario_14_abundant_prospects(self):
        """Find agents with abundant prospects"""
        query = """
        SELECT TOP 5
            'SCENARIO_14_ABUNDANT_PROSPECTS' as scenario_type,
            r.Code as agent_id,
            r.RouteDate as route_date,
            COUNT(DISTINCT r.CustNo) as customer_count,
            COUNT(DISTINCT p.CustNo) as available_prospects,
            (60 - COUNT(DISTINCT r.CustNo)) as prospects_needed,
            (COUNT(DISTINCT p.CustNo) - (60 - COUNT(DISTINCT r.CustNo))) as excess_prospects
        FROM routedata r
        INNER JOIN prospective p ON r.barangay_code = p.barangay_code
            AND p.Latitude IS NOT NULL
            AND p.Longitude IS NOT NULL
            AND p.Latitude != 0
            AND p.Longitude != 0
        WHERE r.Code IS NOT NULL
        AND r.barangay_code IS NOT NULL
        AND r.barangay_code != '#'
        AND r.barangay_code != ''
        GROUP BY r.Code, r.RouteDate
        HAVING COUNT(DISTINCT r.CustNo) < 60
        AND COUNT(DISTINCT p.CustNo) >= (60 - COUNT(DISTINCT r.CustNo))
        ORDER BY (COUNT(DISTINCT p.CustNo) - (60 - COUNT(DISTINCT r.CustNo))) DESC
        """
        return self.db.execute_query_df(query)

    def find_scenario_33_single_customer(self):
        """Find agents with only 1 customer"""
        query = """
        SELECT TOP 3
            'SCENARIO_33_SINGLE_CUSTOMER' as scenario_type,
            Code as agent_id,
            RouteDate as route_date,
            COUNT(DISTINCT CustNo) as customer_count,
            COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                       AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
            COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                       OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count,
            59 as prospects_needed
        FROM routedata
        WHERE Code IS NOT NULL
        GROUP BY Code, RouteDate
        HAVING COUNT(DISTINCT CustNo) = 1
        ORDER BY Code, RouteDate
        """
        return self.db.execute_query_df(query)

    def find_high_value_testing_agents(self):
        """Find the best agents for testing scenarios"""
        query = """
        SELECT TOP 5
            'HIGH_VALUE_TESTING_AGENTS' as scenario_type,
            r.Code as agent_id,
            r.RouteDate as route_date,
            COUNT(DISTINCT r.CustNo) as customer_count,
            COUNT(DISTINCT CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
                                AND r.latitude != 0 AND r.longitude != 0
                                THEN r.CustNo END) as customers_with_coords,
            COUNT(DISTINCT CASE WHEN r.barangay_code IS NOT NULL
                                AND r.barangay_code != '#'
                                AND r.barangay_code != ''
                                THEN r.barangay_code END) as valid_barangay_codes,
            COUNT(DISTINCT p.CustNo) as available_prospects,
            (60 - COUNT(DISTINCT r.CustNo)) as prospects_needed,
            'IDEAL_FOR_TESTING' as recommendation
        FROM routedata r
        INNER JOIN prospective p ON r.barangay_code = p.barangay_code
            AND p.Latitude IS NOT NULL
            AND p.Longitude IS NOT NULL
            AND p.Latitude != 0
            AND p.Longitude != 0
        WHERE r.Code IS NOT NULL
        AND r.barangay_code IS NOT NULL
        AND r.barangay_code != '#'
        AND r.barangay_code != ''
        GROUP BY r.Code, r.RouteDate
        HAVING COUNT(DISTINCT r.CustNo) BETWEEN 40 AND 59
        AND COUNT(DISTINCT CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
                                 AND r.latitude != 0 AND r.longitude != 0
                                 THEN r.CustNo END) >= (COUNT(DISTINCT r.CustNo) * 0.8)
        AND COUNT(DISTINCT p.CustNo) >= (60 - COUNT(DISTINCT r.CustNo))
        ORDER BY COUNT(DISTINCT p.CustNo) DESC
        """
        return self.db.execute_query_df(query)

    def find_known_working_examples(self):
        """Check specific agents mentioned in previous analysis"""
        query = """
        SELECT
            'KNOWN_WORKING_EXAMPLES' as scenario_type,
            agent_data.agent_id,
            agent_data.route_date,
            agent_data.customer_count,
            agent_data.customers_with_coords,
            agent_data.valid_barangay_codes,
            COALESCE(prospect_data.available_prospects, 0) as available_prospects,
            (60 - agent_data.customer_count) as prospects_needed,
            CASE
                WHEN COALESCE(prospect_data.available_prospects, 0) >= (60 - agent_data.customer_count)
                THEN 'CAN_REACH_60'
                ELSE 'PARTIAL_FILL'
            END as fill_capability
        FROM (
            SELECT
                Code as agent_id,
                RouteDate as route_date,
                COUNT(DISTINCT CustNo) as customer_count,
                COUNT(DISTINCT CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                                    AND latitude != 0 AND longitude != 0
                                    THEN CustNo END) as customers_with_coords,
                COUNT(DISTINCT CASE WHEN barangay_code IS NOT NULL
                                    AND barangay_code != '#'
                                    AND barangay_code != ''
                                    THEN barangay_code END) as valid_barangay_codes
            FROM routedata
            WHERE Code IN ('914', '10551', 'SK-PMS2', 'D305', 'SK-SAT5', 'MVP-SAT2', 'OL-07', 'SMDLZ-1')
            GROUP BY Code, RouteDate
        ) agent_data
        LEFT JOIN (
            SELECT
                r.Code as agent_id,
                r.RouteDate as route_date,
                COUNT(DISTINCT p.CustNo) as available_prospects
            FROM routedata r
            INNER JOIN prospective p ON r.barangay_code = p.barangay_code
                AND p.Latitude IS NOT NULL
                AND p.Longitude IS NOT NULL
                AND p.Latitude != 0
                AND p.Longitude != 0
            WHERE r.Code IN ('914', '10551', 'SK-PMS2', 'D305', 'SK-SAT5', 'MVP-SAT2', 'OL-07', 'SMDLZ-1')
            AND r.barangay_code IS NOT NULL
            AND r.barangay_code != '#'
            AND r.barangay_code != ''
            GROUP BY r.Code, r.RouteDate
        ) prospect_data ON agent_data.agent_id = prospect_data.agent_id
                        AND agent_data.route_date = prospect_data.route_date
        ORDER BY agent_data.agent_id, agent_data.route_date
        """
        return self.db.execute_query_df(query)

    def get_scenario_distribution_summary(self):
        """Get overall distribution of scenarios"""
        query = """
        SELECT
            'SCENARIO_DISTRIBUTION_SUMMARY' as analysis_type,
            SUM(CASE WHEN customer_count = 60 THEN 1 ELSE 0 END) as exactly_60_agents,
            SUM(CASE WHEN customer_count > 60 THEN 1 ELSE 0 END) as more_than_60_agents,
            SUM(CASE WHEN customer_count < 60 THEN 1 ELSE 0 END) as less_than_60_agents,
            SUM(CASE WHEN customer_count < 60 AND stop100_count = 0 THEN 1 ELSE 0 END) as all_valid_coords_agents,
            SUM(CASE WHEN customer_count < 60 AND stop100_count > 0 AND with_coords > 0 THEN 1 ELSE 0 END) as mixed_coords_agents,
            SUM(CASE WHEN customer_count < 60 AND with_coords = 0 THEN 1 ELSE 0 END) as all_stop100_agents,
            COUNT(*) as total_agent_days
        FROM (
            SELECT
                Code,
                RouteDate,
                COUNT(DISTINCT CustNo) as customer_count,
                COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                           AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coords,
                COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                           OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count
            FROM routedata
            WHERE Code IS NOT NULL
            GROUP BY Code, RouteDate
        ) agent_summary
        """
        return self.db.execute_query_df(query)

    def run_all_scenarios(self):
        """Run all scenario finding queries"""
        print("Finding Real Agents and Days for All Route Optimization Scenarios")
        print("=" * 80)

        scenarios_to_find = [
            ("Scenario 1: Exactly 60 Customers", self.find_scenario_1_exactly_60),
            ("Scenario 2: More than 60 Customers", self.find_scenario_2_more_than_60),
            ("Scenario 3: Less than 60 Customers", self.find_scenario_3_less_than_60),
            ("Scenario 4: All Valid Coordinates", self.find_scenario_4_all_valid_coords),
            ("Scenario 5: Mixed Coordinates", self.find_scenario_5_mixed_coordinates),
            ("Scenario 6: All Invalid Coordinates", self.find_scenario_6_all_invalid_coords),
            ("Scenario 11: Prospects Available", self.find_scenario_11_prospects_available),
            ("Scenario 13: Insufficient Prospects", self.find_scenario_13_insufficient_prospects),
            ("Scenario 14: Abundant Prospects", self.find_scenario_14_abundant_prospects),
            ("Scenario 33: Single Customer", self.find_scenario_33_single_customer),
            ("High Value Testing Agents", self.find_high_value_testing_agents),
            ("Known Working Examples", self.find_known_working_examples),
        ]

        all_results = []

        for scenario_name, scenario_func in scenarios_to_find:
            print(f"\n=== {scenario_name} ===")
            print("-" * 60)

            try:
                result = scenario_func()
                if result is not None and not result.empty:
                    print(f"Found {len(result)} examples:")
                    for idx, row in result.iterrows():
                        if 'agent_id' in row and 'route_date' in row:
                            print(f"  - Agent: {row['agent_id']}, Date: {row['route_date']}, Customers: {row.get('customer_count', 'N/A')}")
                            if 'available_prospects' in row:
                                print(f"    Available Prospects: {row['available_prospects']}, Needed: {row.get('prospects_needed', 'N/A')}")
                            if 'with_coordinates' in row and 'stop100_count' in row:
                                print(f"    With Coords: {row['with_coordinates']}, Stop100: {row['stop100_count']}")

                    all_results.append((scenario_name, result))
                else:
                    print("  No examples found")
            except Exception as e:
                print(f"  Error: {e}")

        # Get overall summary
        print(f"\n=== Overall Scenario Distribution ===")
        print("-" * 60)
        try:
            summary = self.get_scenario_distribution_summary()
            if summary is not None and not summary.empty:
                row = summary.iloc[0]
                print(f"Total Agent-Days: {row['total_agent_days']:,}")
                print(f"Exactly 60 customers: {row['exactly_60_agents']:,}")
                print(f"More than 60 customers: {row['more_than_60_agents']:,}")
                print(f"Less than 60 customers: {row['less_than_60_agents']:,}")
                print(f"All valid coordinates: {row['all_valid_coords_agents']:,}")
                print(f"Mixed coordinates: {row['mixed_coords_agents']:,}")
                print(f"All Stop100: {row['all_stop100_agents']:,}")
        except Exception as e:
            print(f"Error getting summary: {e}")

        return all_results

    def close(self):
        """Close database connection"""
        self.db.close()

def main():
    """Main function"""
    finder = ScenarioFinder()
    try:
        results = finder.run_all_scenarios()

        print(f"\n=== Summary ===")
        print("=" * 80)
        print(f"Found examples for {len(results)} different scenario types")
        print("These agents and dates can be used for testing specific pipeline scenarios")
        print("\nRecommended Testing Agents:")

        # Extract high-value testing agents
        for scenario_name, data in results:
            if "High Value" in scenario_name and not data.empty:
                print("\nBest agents for comprehensive testing:")
                for idx, row in data.head(3).iterrows():
                    print(f"  *** Agent: {row['agent_id']}, Date: {row['route_date']} ***")
                    print(f"     Customers: {row['customer_count']}, With Coords: {row['customers_with_coords']}")
                    print(f"     Available Prospects: {row['available_prospects']}, Needed: {row['prospects_needed']}")
                break

    finally:
        finder.close()

if __name__ == "__main__":
    main()