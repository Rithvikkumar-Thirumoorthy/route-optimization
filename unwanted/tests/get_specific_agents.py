#!/usr/bin/env python3
"""
Get specific agent-ids and days for each scenario
"""

from database import DatabaseConnection

def get_specific_agents():
    """Get concrete agent examples for each scenario"""
    print("SPECIFIC AGENT ANALYSIS BY SCENARIO")
    print("=" * 45)
    print("Matching Logic: routedata.barangay_code = prospective.barangay_code")
    print("=" * 45)

    db = None
    try:
        db = DatabaseConnection()
        db.connect()

        # SCENARIO 1: Agents with exactly 60 customers on a particular day
        print("\n1. AGENTS WITH EXACTLY 60 CUSTOMERS ON A PARTICULAR DAY")
        print("-" * 55)

        scenario1_query = """
        SELECT TOP 10
            SalesManTerritory as agent_id,
            RouteDate as day,
            COUNT(DISTINCT CustNo) as customer_count
        FROM routedata
        WHERE SalesManTerritory IS NOT NULL
        GROUP BY SalesManTerritory, RouteDate
        HAVING COUNT(DISTINCT CustNo) = 60
        ORDER BY SalesManTerritory, RouteDate
        """

        print("Agent_ID        Day           Customers")
        print("-" * 40)
        scenario1_result = db.execute_query(scenario1_query)
        if scenario1_result:
            for row in scenario1_result:
                print(f"{row[0]:<14} {row[1]:<12} {row[2]}")
        else:
            print("No agents found with exactly 60 customers")

        # SCENARIO 2: Agents with <60 customers + prospects in same barangay
        print("\n\n2. AGENTS WITH <60 CUSTOMERS + PROSPECTS IN SAME BARANGAY")
        print("-" * 60)

        # First get agents with <60 customers
        agents_under_60_query = """
        SELECT TOP 5
            SalesManTerritory as agent_id,
            RouteDate as day,
            COUNT(DISTINCT CustNo) as customer_count
        FROM routedata
        WHERE SalesManTerritory IS NOT NULL
        GROUP BY SalesManTerritory, RouteDate
        HAVING COUNT(DISTINCT CustNo) < 60
        ORDER BY COUNT(DISTINCT CustNo) DESC
        """

        agents_under_60 = db.execute_query(agents_under_60_query)
        if agents_under_60:
            print("Agent_ID        Day           Customers  Barangay_Code    Prospects_Available")
            print("-" * 75)

            for row in agents_under_60:
                agent_id, day, customer_count = row

                # Get barangay codes for this agent on this day
                barangay_query = """
                SELECT DISTINCT barangay_code
                FROM routedata
                WHERE SalesManTerritory = ? AND RouteDate = ?
                AND barangay_code IS NOT NULL AND barangay_code != '#' AND barangay_code != ''
                """

                barangay_result = db.execute_query(barangay_query, [agent_id, day])
                if barangay_result:
                    for barangay_row in barangay_result[:1]:  # Show first barangay code
                        barangay_code = barangay_row[0]

                        # Check prospects for this barangay code
                        prospects_query = """
                        SELECT COUNT(DISTINCT CustNo)
                        FROM prospective
                        WHERE barangay_code = ?
                        AND Latitude IS NOT NULL AND Longitude IS NOT NULL
                        AND Latitude != 0 AND Longitude != 0
                        """

                        prospects_result = db.execute_query(prospects_query, [barangay_code])
                        prospect_count = prospects_result[0][0] if prospects_result else 0

                        # Only show if prospects are available
                        if prospect_count > 0:
                            print(f"{agent_id:<14} {day:<12} {customer_count:<9} {barangay_code:<15} {prospect_count}")

                            # Show the matching logic in action
                            print(f"  -> MATCH: barangay_code='{barangay_code}' = barangay_code='{barangay_code}'")
                            print(f"  -> Can add {min(60-customer_count, prospect_count)} prospects to reach 60")
                            print()

        # SCENARIO 3: Agents with <60 customers + stop100 conditions
        print("\n3. AGENTS WITH <60 CUSTOMERS + STOP100 CONDITIONS")
        print("-" * 55)

        scenario3_query = """
        SELECT TOP 5
            SalesManTerritory as agent_id,
            RouteDate as day,
            COUNT(DISTINCT CustNo) as customer_count,
            COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                       AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coords,
            COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                       OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_customers
        FROM routedata
        WHERE SalesManTerritory IS NOT NULL
        GROUP BY SalesManTerritory, RouteDate
        HAVING COUNT(DISTINCT CustNo) < 60
        AND COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                       OR latitude = 0 OR longitude = 0 THEN 1 END) > 0
        ORDER BY COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                             OR latitude = 0 OR longitude = 0 THEN 1 END) DESC
        """

        print("Agent_ID        Day           Customers  WithCoords  Stop100")
        print("-" * 55)
        scenario3_result = db.execute_query(scenario3_query)
        if scenario3_result:
            for row in scenario3_result:
                agent_id, day, customers, with_coords, stop100 = row
                print(f"{agent_id:<14} {day:<12} {customers:<9} {with_coords:<9} {stop100}")

                # Show stop100 explanation
                print(f"  -> Stop100: {stop100} customers without coordinates (lat/lon = NULL or 0)")
                print(f"  -> These will get stopno=100 in route optimization")
                print()

        # DETAILED BARANGAY MATCHING DEMONSTRATION
        print("\n4. BARANGAY MATCHING VERIFICATION")
        print("-" * 40)
        print("Demonstrating: routedata.barangay_code = prospective.barangay_code")

        # Show successful matches
        matching_demo_query = """
        SELECT TOP 3
            r.barangay_code,
            COUNT(DISTINCT r.CustNo) as customers,
            COUNT(DISTINCT p.CustNo) as prospects
        FROM routedata r
        INNER JOIN prospective p ON r.barangay_code = p.barangay_code
        WHERE r.barangay_code IS NOT NULL AND r.barangay_code != '#'
        AND p.Latitude IS NOT NULL AND p.Longitude IS NOT NULL
        GROUP BY r.barangay_code
        ORDER BY COUNT(DISTINCT p.CustNo) DESC
        """

        matching_result = db.execute_query(matching_demo_query)
        if matching_result:
            print("\nSuccessful Matches:")
            print("Barangay_Code   Customers   Prospects")
            print("-" * 35)
            for row in matching_result:
                print(f"{row[0]:<14} {row[1]:<9} {row[2]}")

        # Show a specific agent using a working barangay code
        print("\n5. EXAMPLE: AGENT USING WORKING BARANGAY CODE")
        print("-" * 45)

        working_code = "45808009"  # We know this works
        example_agent_query = """
        SELECT TOP 1
            SalesManTerritory,
            RouteDate,
            COUNT(DISTINCT CustNo) as customers
        FROM routedata
        WHERE barangay_code = ?
        GROUP BY SalesManTerritory, RouteDate
        ORDER BY RouteDate DESC
        """

        example_result = db.execute_query(example_agent_query, [working_code])
        if example_result:
            agent, date, customers = example_result[0]

            # Get prospect count
            prospect_count_query = """
            SELECT COUNT(DISTINCT CustNo)
            FROM prospective
            WHERE barangay_code = ?
            AND Latitude IS NOT NULL AND Longitude IS NOT NULL
            """

            prospect_result = db.execute_query(prospect_count_query, [working_code])
            prospect_count = prospect_result[0][0] if prospect_result else 0

            print(f"Agent: {agent}")
            print(f"Date: {date}")
            print(f"Current customers: {customers}")
            print(f"Barangay code: {working_code}")
            print(f"Available prospects: {prospect_count}")
            print(f"Matching: routedata.barangay_code='{working_code}' = prospective.barangay_code='{working_code}'")

            if customers < 60:
                needed = 60 - customers
                can_add = min(needed, prospect_count)
                print(f"Can add {can_add} prospects to reach 60 total stops")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    get_specific_agents()