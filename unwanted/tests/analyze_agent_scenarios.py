#!/usr/bin/env python3
"""
Analyze sales agents and their days based on multiple scenarios:
1. Agents with exactly 60 customers
2. Agents with <60 customers that have prospects in same barangay (barangay_code = barangay_code)
3. Agents with <60 customers with stop100 conditions (no coordinates)
"""

from database import DatabaseConnection
import pandas as pd

def analyze_agent_scenarios():
    """Analyze agents based on different customer count scenarios"""
    print("AGENT SCENARIO ANALYSIS")
    print("=" * 50)
    print("Matching Logic: routedata.barangay_code = prospective.barangay_code")
    print("=" * 50)

    db = None
    try:
        db = DatabaseConnection()
        db.connect()

        # Scenario 1: Agents with exactly 60 customers
        print("\n1. SCENARIO 1: Agents with exactly 60 customers")
        print("-" * 45)

        scenario1_query = """
        SELECT
            SalesManTerritory as agent_id,
            RouteDate,
            COUNT(DISTINCT CustNo) as customer_count,
            COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                       AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
            COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                       OR latitude = 0 OR longitude = 0 THEN 1 END) as without_coordinates
        FROM routedata
        WHERE SalesManTerritory IS NOT NULL
        GROUP BY SalesManTerritory, RouteDate
        HAVING COUNT(DISTINCT CustNo) = 60
        ORDER BY SalesManTerritory, RouteDate
        """

        scenario1_result = db.execute_query_df(scenario1_query)
        if scenario1_result is not None and not scenario1_result.empty:
            print(f"Found {len(scenario1_result)} agent-day combinations with exactly 60 customers:")
            print(scenario1_result.head(10).to_string(index=False))

            # Show sample agent details
            sample_agent = scenario1_result.iloc[0]
            print(f"\nSample Agent Details:")
            print(f"Agent: {sample_agent['agent_id']}, Date: {sample_agent['RouteDate']}")
            print(f"With coordinates: {sample_agent['with_coordinates']}, Without: {sample_agent['without_coordinates']}")
        else:
            print("No agents found with exactly 60 customers")

        # Scenario 2: Agents with <60 customers that have prospects in same barangay
        print("\n\n2. SCENARIO 2: Agents with <60 customers + prospects in same barangay")
        print("-" * 65)

        scenario2_query = """
        WITH agent_data AS (
            SELECT
                r.SalesManTerritory as agent_id,
                r.RouteDate,
                COUNT(DISTINCT r.CustNo) as customer_count,
                COUNT(CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
                           AND r.latitude != 0 AND r.longitude != 0 THEN 1 END) as with_coordinates,
                COUNT(CASE WHEN r.latitude IS NULL OR r.longitude IS NULL
                           OR r.latitude = 0 OR r.longitude = 0 THEN 1 END) as without_coordinates,
                STRING_AGG(DISTINCT r.barangay_code, ',') as barangay_codes
            FROM routedata r
            WHERE r.SalesManTerritory IS NOT NULL
            GROUP BY r.SalesManTerritory, r.RouteDate
            HAVING COUNT(DISTINCT r.CustNo) < 60
        ),
        prospect_counts AS (
            SELECT
                ad.agent_id,
                ad.RouteDate,
                ad.customer_count,
                ad.with_coordinates,
                ad.without_coordinates,
                ad.barangay_codes,
                COUNT(DISTINCT p.CustNo) as available_prospects
            FROM agent_data ad
            CROSS APPLY STRING_SPLIT(ad.barangay_codes, ',') as bc
            LEFT JOIN prospective p ON bc.value = p.barangay_code
                AND p.Latitude IS NOT NULL AND p.Longitude IS NOT NULL
                AND p.Latitude != 0 AND p.Longitude != 0
            GROUP BY ad.agent_id, ad.RouteDate, ad.customer_count, ad.with_coordinates, ad.without_coordinates, ad.barangay_codes
        )
        SELECT TOP 15 *
        FROM prospect_counts
        WHERE available_prospects > 0
        ORDER BY available_prospects DESC, customer_count ASC
        """

        scenario2_result = db.execute_query_df(scenario2_query)
        if scenario2_result is not None and not scenario2_result.empty:
            print(f"Found {len(scenario2_result)} agent-day combinations with <60 customers + available prospects:")
            print(scenario2_result.to_string(index=False))

            # Show detailed analysis for top agent
            top_agent = scenario2_result.iloc[0]
            print(f"\nDetailed Analysis - Top Agent:")
            print(f"Agent: {top_agent['agent_id']}, Date: {top_agent['RouteDate']}")
            print(f"Current customers: {top_agent['customer_count']}")
            print(f"Available prospects in same barangay: {top_agent['available_prospects']}")
            print(f"Barangay codes: {top_agent['barangay_codes'][:100]}...")

            # Show the barangay matching
            print(f"\nBarangay Matching Verification:")
            barangay_codes = top_agent['barangay_codes'].split(',')[:3]  # First 3 codes
            for code in barangay_codes:
                if code and code != '#':
                    prospect_count = db.execute_query(
                        "SELECT COUNT(*) FROM prospective WHERE barangay_code = ? AND Latitude IS NOT NULL AND Longitude IS NOT NULL",
                        [code.strip()]
                    )
                    print(f"  barangay_code='{code.strip()}' -> barangay_code matches: {prospect_count[0][0]} prospects")

        else:
            print("No agents found with <60 customers and available prospects")

        # Scenario 3: Agents with <60 customers and stop100 conditions
        print("\n\n3. SCENARIO 3: Agents with <60 customers + stop100 conditions")
        print("-" * 60)

        scenario3_query = """
        SELECT
            SalesManTerritory as agent_id,
            RouteDate,
            COUNT(DISTINCT CustNo) as customer_count,
            COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                       AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
            COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                       OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_customers,
            CAST(COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                       OR latitude = 0 OR longitude = 0 THEN 1 END) * 100.0 / COUNT(*) AS DECIMAL(5,1)) as stop100_percentage
        FROM routedata
        WHERE SalesManTerritory IS NOT NULL
        GROUP BY SalesManTerritory, RouteDate
        HAVING COUNT(DISTINCT CustNo) < 60
        AND COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                       OR latitude = 0 OR longitude = 0 THEN 1 END) > 0
        ORDER BY stop100_customers DESC, customer_count ASC
        """

        scenario3_result = db.execute_query_df(scenario3_query)
        if scenario3_result is not None and not scenario3_result.empty:
            print(f"Found {len(scenario3_result)} agent-day combinations with <60 customers + stop100 conditions:")
            print(scenario3_result.head(15).to_string(index=False))

            # Show sample stop100 analysis
            sample_stop100 = scenario3_result.iloc[0]
            print(f"\nSample Stop100 Analysis:")
            print(f"Agent: {sample_stop100['agent_id']}, Date: {sample_stop100['RouteDate']}")
            print(f"Total customers: {sample_stop100['customer_count']}")
            print(f"Stop100 customers (no coordinates): {sample_stop100['stop100_customers']}")
            print(f"Stop100 percentage: {sample_stop100['stop100_percentage']}%")

        else:
            print("No agents found with <60 customers and stop100 conditions")

        # Summary statistics
        print("\n\n4. SUMMARY STATISTICS")
        print("-" * 25)

        summary_query = """
        SELECT
            CASE
                WHEN COUNT(DISTINCT CustNo) = 60 THEN 'Exactly 60 customers'
                WHEN COUNT(DISTINCT CustNo) > 60 THEN 'More than 60 customers'
                ELSE 'Less than 60 customers'
            END as scenario,
            COUNT(*) as agent_day_count,
            AVG(CAST(COUNT(DISTINCT CustNo) AS FLOAT)) as avg_customers,
            MIN(COUNT(DISTINCT CustNo)) as min_customers,
            MAX(COUNT(DISTINCT CustNo)) as max_customers
        FROM routedata
        WHERE SalesManTerritory IS NOT NULL
        GROUP BY SalesManTerritory, RouteDate
        GROUP BY
            CASE
                WHEN COUNT(DISTINCT CustNo) = 60 THEN 'Exactly 60 customers'
                WHEN COUNT(DISTINCT CustNo) > 60 THEN 'More than 60 customers'
                ELSE 'Less than 60 customers'
            END
        ORDER BY scenario
        """

        summary_result = db.execute_query_df(summary_query)
        if summary_result is not None and not summary_result.empty:
            print("Distribution of agent-day scenarios:")
            print(summary_result.to_string(index=False))

        # Barangay matching verification
        print("\n\n5. BARANGAY MATCHING VERIFICATION")
        print("-" * 40)
        print("Confirming: routedata.barangay_code = prospective.barangay_code")

        matching_query = """
        SELECT TOP 10
            r.barangay_code as routedata_barangay_code,
            COUNT(DISTINCT r.CustNo) as customers_with_this_code,
            COUNT(DISTINCT p.CustNo) as prospects_with_this_code
        FROM routedata r
        LEFT JOIN prospective p ON r.barangay_code = p.barangay_code
            AND p.Latitude IS NOT NULL AND p.Longitude IS NOT NULL
            AND p.Latitude != 0 AND p.Longitude != 0
        WHERE r.barangay_code IS NOT NULL
        AND r.barangay_code != '#'
        AND r.barangay_code != ''
        GROUP BY r.barangay_code
        HAVING COUNT(DISTINCT p.CustNo) > 0
        ORDER BY COUNT(DISTINCT p.CustNo) DESC
        """

        matching_result = db.execute_query_df(matching_query)
        if matching_result is not None and not matching_result.empty:
            print("Verified barangay code matches:")
            print(matching_result.to_string(index=False))
            print(f"\nMatching logic confirmed: routedata.barangay_code = prospective.barangay_code")
        else:
            print("No barangay code matches found")

    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    analyze_agent_scenarios()