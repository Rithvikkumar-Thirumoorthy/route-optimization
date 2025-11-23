#!/usr/bin/env python3
"""
Test Specific Agents - Verify the agents exist and check their data
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def test_agents():
    """Test the specific agents to verify they exist"""
    db = DatabaseConnection()
    db.connect()

    agents_to_test = [
        ("SK-SAT8", "2025-09-04"),
        ("D304", "2025-09-16"),
        ("WesZamVan 3", "2025-09-01")
    ]

    print("Testing Specific Agents")
    print("=" * 40)

    for agent_id, route_date in agents_to_test:
        print(f"\nTesting Agent: {agent_id}, Date: {route_date}")
        print("-" * 30)

        # Test 1: Check if agent exists
        count_query = f"""
        SELECT COUNT(DISTINCT CustNo) as customer_count
        FROM routedata
        WHERE Code = '{agent_id}' AND RouteDate = '{route_date}'
        """

        result = db.execute_query_df(count_query)
        if result is not None and not result.empty:
            customer_count = result.iloc[0]['customer_count']
            print(f"   Customer count: {customer_count}")

            if customer_count > 0:
                # Test 2: Get sample customer data
                sample_query = f"""
                SELECT TOP 3 CustNo, latitude, longitude, barangay_code, custype, Name
                FROM routedata
                WHERE Code = '{agent_id}' AND RouteDate = '{route_date}'
                """

                sample_result = db.execute_query_df(sample_query)
                if sample_result is not None and not sample_result.empty:
                    print(f"   Sample customers:")
                    for _, row in sample_result.iterrows():
                        print(f"     {row['CustNo']}: coords=({row['latitude']}, {row['longitude']}), barangay={row['barangay_code']}")

                # Test 3: Check coordinate distribution
                coord_query = f"""
                SELECT
                    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                               AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coords,
                    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                               OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100
                FROM routedata
                WHERE Code = '{agent_id}' AND RouteDate = '{route_date}'
                """

                coord_result = db.execute_query_df(coord_query)
                if coord_result is not None and not coord_result.empty:
                    coord_row = coord_result.iloc[0]
                    print(f"   Coordinates: {coord_row['with_coords']} valid, {coord_row['stop100']} Stop100")

                # Test 4: Check barangay codes
                barangay_query = f"""
                SELECT COUNT(DISTINCT barangay_code) as unique_barangay_codes
                FROM routedata
                WHERE Code = '{agent_id}' AND RouteDate = '{route_date}'
                AND barangay_code IS NOT NULL AND barangay_code != '#' AND barangay_code != ''
                """

                barangay_result = db.execute_query_df(barangay_query)
                if barangay_result is not None and not barangay_result.empty:
                    barangay_count = barangay_result.iloc[0]['unique_barangay_codes']
                    print(f"   Valid barangay codes: {barangay_count}")

                    # Test 5: Check for prospects if <60 customers
                    if customer_count < 60:
                        prospect_query = f"""
                        SELECT COUNT(DISTINCT p.CustNo) as prospect_count
                        FROM routedata r
                        INNER JOIN prospective p ON r.barangay_code = p.barangay_code
                        WHERE r.Code = '{agent_id}' AND r.RouteDate = '{route_date}'
                        AND r.barangay_code IS NOT NULL AND r.barangay_code != '#' AND r.barangay_code != ''
                        """

                        prospect_result = db.execute_query_df(prospect_query)
                        if prospect_result is not None and not prospect_result.empty:
                            prospect_count = prospect_result.iloc[0]['prospect_count']
                            needed = 60 - customer_count
                            print(f"   Prospects available: {prospect_count}")
                            print(f"   Prospects needed: {needed}")
                            status = "CAN REACH 60" if prospect_count >= needed else "PARTIAL FILL"
                            print(f"   Status: {status}")

                print(f"   Result: AGENT EXISTS ✓")
            else:
                print(f"   Result: NO CUSTOMERS FOUND ✗")
        else:
            print(f"   Result: QUERY FAILED ✗")

    db.close()

def main():
    """Main function"""
    try:
        test_agents()
        print(f"\n" + "=" * 40)
        print("Agent verification complete")
        print("If all agents exist, the pipeline should work")
        print("Check for database parameter format issues")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()