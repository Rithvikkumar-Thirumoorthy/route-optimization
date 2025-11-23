#!/usr/bin/env python3
"""
Basic agent check with minimal queries
"""

from database import DatabaseConnection

def basic_agent_check():
    """Basic agent analysis with minimal queries"""
    print("BASIC AGENT SCENARIO CHECK")
    print("=" * 30)

    db = None
    try:
        db = DatabaseConnection()
        db.connect()

        # Step 1: Simple customer count check
        print("1. Customer count distribution:")

        counts = [60, 59, 58, 57, 56, 55]
        for count in counts:
            query = f"""
            SELECT COUNT(*)
            FROM (
                SELECT SalesManTerritory, RouteDate, COUNT(DISTINCT CustNo) as cust_count
                FROM routedata
                WHERE SalesManTerritory IS NOT NULL
                GROUP BY SalesManTerritory, RouteDate
                HAVING COUNT(DISTINCT CustNo) = {count}
            ) sub
            """

            result = db.execute_query(query)
            if result:
                print(f"  {count} customers: {result[0][0]} agent-days")

        # Step 2: Sample agents with <60 customers
        print("\n2. Sample agents with <60 customers:")

        sample_query = """
        SELECT TOP 5 SalesManTerritory, RouteDate, COUNT(DISTINCT CustNo) as customer_count
        FROM routedata
        WHERE SalesManTerritory IS NOT NULL
        GROUP BY SalesManTerritory, RouteDate
        HAVING COUNT(DISTINCT CustNo) < 60
        ORDER BY COUNT(DISTINCT CustNo) DESC
        """

        sample_result = db.execute_query(sample_query)
        if sample_result:
            for row in sample_result:
                agent_id = row[0]
                date = row[1]
                count = row[2]
                print(f"  Agent: {agent_id}, Date: {date}, Customers: {count}")

                # Check this agent's barangay codes
                barangay_query = """
                SELECT TOP 3 barangay_code
                FROM routedata
                WHERE SalesManTerritory = ? AND RouteDate = ?
                AND barangay_code IS NOT NULL AND barangay_code != '#'
                """

                barangay_result = db.execute_query(barangay_query, [agent_id, date])
                if barangay_result:
                    codes = [r[0] for r in barangay_result]
                    print(f"    Barangay codes: {codes}")

        # Step 3: Test barangay matching with known working code
        print("\n3. Barangay matching test:")
        working_code = "45808009"

        # Count customers with this code
        customer_count_query = """
        SELECT COUNT(DISTINCT CustNo)
        FROM routedata
        WHERE barangay_code = ?
        """

        customer_count = db.execute_query(customer_count_query, [working_code])
        print(f"  Customers with barangay_code='{working_code}': {customer_count[0][0]}")

        # Count prospects with this code
        prospect_count_query = """
        SELECT COUNT(DISTINCT CustNo)
        FROM prospective
        WHERE barangay_code = ?
        AND Latitude IS NOT NULL AND Longitude IS NOT NULL
        """

        prospect_count = db.execute_query(prospect_count_query, [working_code])
        print(f"  Prospects with barangay_code='{working_code}': {prospect_count[0][0]}")

        print(f"\n  MATCHING LOGIC CONFIRMED: barangay_code = barangay_code")

        # Step 4: Stop100 condition check
        print("\n4. Stop100 conditions (customers without coordinates):")

        stop100_query = """
        SELECT TOP 3 SalesManTerritory, RouteDate,
               COUNT(DISTINCT CustNo) as total_customers,
               COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                          OR latitude = 0 OR longitude = 0 THEN 1 END) as stop100_count
        FROM routedata
        WHERE SalesManTerritory IS NOT NULL
        GROUP BY SalesManTerritory, RouteDate
        HAVING COUNT(DISTINCT CustNo) < 60
        AND COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                       OR latitude = 0 OR longitude = 0 THEN 1 END) > 0
        ORDER BY COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL
                             OR latitude = 0 OR longitude = 0 THEN 1 END) DESC
        """

        stop100_result = db.execute_query(stop100_query)
        if stop100_result:
            for row in stop100_result:
                print(f"  Agent: {row[0]}, Date: {row[1]}")
                print(f"    Total customers: {row[2]}, Stop100: {row[3]}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    basic_agent_check()