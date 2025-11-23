#!/usr/bin/env python3
"""
Simple agent analysis broken into faster queries
"""

from database import DatabaseConnection

def simple_agent_analysis():
    """Analyze agents with simpler, faster queries"""
    print("AGENT SCENARIO ANALYSIS (Optimized)")
    print("=" * 45)
    print("Matching Logic: routedata.barangay_code = prospective.barangay_code")
    print("=" * 45)

    db = None
    try:
        db = DatabaseConnection()
        db.connect()

        # Scenario 1: Agents with exactly 60 customers
        print("\n1. AGENTS WITH EXACTLY 60 CUSTOMERS")
        print("-" * 40)

        scenario1_query = """
        SELECT TOP 10
            SalesManTerritory as agent_id,
            RouteDate,
            COUNT(DISTINCT CustNo) as customer_count
        FROM routedata
        WHERE SalesManTerritory IS NOT NULL
        GROUP BY SalesManTerritory, RouteDate
        HAVING COUNT(DISTINCT CustNo) = 60
        ORDER BY SalesManTerritory, RouteDate
        """

        scenario1_result = db.execute_query(scenario1_query)
        if scenario1_result:
            print(f"Found {len(scenario1_result)} agent-day combinations with exactly 60 customers:")
            for row in scenario1_result:
                print(f"  Agent: {row[0]}, Date: {row[1]}, Customers: {row[2]}")
        else:
            print("No agents found with exactly 60 customers")

        # Scenario 2: Agents with <60 customers (simple version)
        print("\n\n2. AGENTS WITH <60 CUSTOMERS")
        print("-" * 35)

        scenario2_query = """
        SELECT TOP 15
            SalesManTerritory as agent_id,
            RouteDate,
            COUNT(DISTINCT CustNo) as customer_count,
            COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                       AND latitude != 0 AND longitude != 0 THEN 1 END) as with_coords,
            COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                       OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count
        FROM routedata
        WHERE SalesManTerritory IS NOT NULL
        GROUP BY SalesManTerritory, RouteDate
        HAVING COUNT(DISTINCT CustNo) < 60
        ORDER BY COUNT(DISTINCT CustNo) DESC
        """

        scenario2_result = db.execute_query(scenario2_query)
        if scenario2_result:
            print(f"Found agents with <60 customers:")
            print("Agent_ID          Date         Customers  WithCoords  Stop100")
            print("-" * 65)
            for row in scenario2_result:
                print(f"{row[0]:<15} {row[1]:<12} {row[2]:<9} {row[3]:<9} {row[4]}")
        else:
            print("No agents found with <60 customers")

        # Get a sample agent for detailed analysis
        if scenario2_result:
            sample_agent = scenario2_result[0][0]
            sample_date = scenario2_result[0][1]

            print(f"\n\n3. DETAILED ANALYSIS: {sample_agent} on {sample_date}")
            print("-" * 50)

            # Get barangay codes for this agent
            barangay_query = """
            SELECT DISTINCT barangay_code
            FROM routedata
            WHERE SalesManTerritory = ? AND RouteDate = ?
            AND barangay_code IS NOT NULL AND barangay_code != '#' AND barangay_code != ''
            """

            barangay_result = db.execute_query(barangay_query, [sample_agent, sample_date])
            if barangay_result:
                print(f"Barangay codes for this agent:")
                for row in barangay_result[:5]:  # Show first 5
                    barangay_code = row[0]
                    print(f"  barangay_code: '{barangay_code}'")

                    # Check matching prospects
                    prospect_query = """
                    SELECT COUNT(*)
                    FROM prospective
                    WHERE barangay_code = ?
                    AND Latitude IS NOT NULL AND Longitude IS NOT NULL
                    AND Latitude != 0 AND Longitude != 0
                    """

                    prospect_count = db.execute_query(prospect_query, [barangay_code])
                    if prospect_count:
                        print(f"    -> Matching prospects: {prospect_count[0][0]}")

        # Scenario 3: Show barangay matching verification
        print("\n\n4. BARANGAY MATCHING VERIFICATION")
        print("-" * 40)
        print("Confirming: routedata.barangay_code = prospective.barangay_code")

        verification_query = """
        SELECT TOP 5
            r.barangay_code,
            COUNT(DISTINCT r.CustNo) as customers,
            COUNT(DISTINCT p.CustNo) as prospects
        FROM routedata r
        LEFT JOIN prospective p ON r.barangay_code = p.barangay_code
        WHERE r.barangay_code IS NOT NULL AND r.barangay_code != '#' AND r.barangay_code != ''
        AND p.Latitude IS NOT NULL AND p.Longitude IS NOT NULL
        GROUP BY r.barangay_code
        HAVING COUNT(DISTINCT p.CustNo) > 0
        ORDER BY COUNT(DISTINCT p.CustNo) DESC
        """

        verification_result = db.execute_query(verification_query)
        if verification_result:
            print("Verified matches:")
            print("Barangay_Code    Customers  Prospects")
            print("-" * 40)
            for row in verification_result:
                print(f"{row[0]:<15} {row[1]:<9} {row[2]}")
        else:
            print("No verified matches found")

        # Summary counts
        print("\n\n5. SUMMARY COUNTS")
        print("-" * 20)

        # Count agents by customer ranges
        summary_queries = [
            ("Exactly 60 customers", "COUNT(DISTINCT CustNo) = 60"),
            ("More than 60 customers", "COUNT(DISTINCT CustNo) > 60"),
            ("50-59 customers", "COUNT(DISTINCT CustNo) BETWEEN 50 AND 59"),
            ("40-49 customers", "COUNT(DISTINCT CustNo) BETWEEN 40 AND 49"),
            ("Less than 40 customers", "COUNT(DISTINCT CustNo) < 40")
        ]

        for description, condition in summary_queries:
            count_query = f"""
            SELECT COUNT(*)
            FROM (
                SELECT SalesManTerritory, RouteDate
                FROM routedata
                WHERE SalesManTerritory IS NOT NULL
                GROUP BY SalesManTerritory, RouteDate
                HAVING {condition}
            ) sub
            """

            count_result = db.execute_query(count_query)
            if count_result:
                print(f"{description}: {count_result[0][0]} agent-days")

    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    simple_agent_analysis()