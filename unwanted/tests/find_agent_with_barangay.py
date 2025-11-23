#!/usr/bin/env python3
"""
Find a sales agent with customers that have valid barangay data (barangay_code)
"""

from database import DatabaseConnection

def find_agent_with_barangay():
    """Find sales agent with customers having valid barangay data"""
    db = DatabaseConnection()
    connection = db.connect()

    if not connection:
        print("Failed to connect to database")
        return

    try:
        # Find agents with customers having valid barangay_code (barangay) data
        query = """
        SELECT TOP 10
            r.SalesManTerritory,
            r.RouteDate,
            COUNT(*) as total_customers,
            COUNT(CASE WHEN r.barangay_code IS NOT NULL AND r.barangay_code != '' THEN 1 END) as customers_with_barangay,
            SUM(CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
                     AND r.latitude != 0 AND r.longitude != 0 THEN 1 ELSE 0 END) as customers_with_coords
        FROM routedata r
        WHERE r.SalesManTerritory IS NOT NULL
        AND r.RouteDate IS NOT NULL
        GROUP BY r.SalesManTerritory, r.RouteDate
        HAVING COUNT(*) BETWEEN 35 AND 55
        AND COUNT(CASE WHEN r.barangay_code IS NOT NULL AND r.barangay_code != '' THEN 1 END) > 10
        AND SUM(CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
                     AND r.latitude != 0 AND r.longitude != 0 THEN 1 ELSE 0 END) > 10
        ORDER BY customers_with_barangay DESC
        """

        result = db.execute_query_df(query)

        if result is not None and not result.empty:
            print("Sales agents with customers having valid barangay data:")
            print("Agent\t\tDate\t\tTotal\tWith Barangay\tWith Coords")
            print("-" * 65)
            for _, row in result.iterrows():
                print(f"{row['SalesManTerritory']:<15}\t{row['RouteDate']}\t{row['total_customers']}\t{row['customers_with_barangay']}\t\t{row['customers_with_coords']}")

            # Get detailed info for the first agent
            best_agent = result.iloc[0]['SalesManTerritory']
            best_date = result.iloc[0]['RouteDate']

            print(f"\nDetailed info for {best_agent} on {best_date}:")

            # Show barangay distribution
            barangay_query = """
            SELECT barangay_code, COUNT(*) as count
            FROM routedata
            WHERE SalesManTerritory = ? AND RouteDate = ?
            AND barangay_code IS NOT NULL AND barangay_code != ''
            GROUP BY barangay_code
            ORDER BY count DESC
            """

            barangays = db.execute_query_df(barangay_query, [best_agent, best_date])

            if barangays is not None and not barangays.empty:
                print(f"Found {len(barangays)} unique barangays:")
                print(barangays.head(10))

                # Check if we have prospects in these barangays
                barangay_list = barangays['barangay_code'].tolist()[:5]  # Check top 5 barangays

                prospect_query = """
                SELECT Barangay_code, COUNT(*) as prospect_count
                FROM prospective
                WHERE Active = 1
                AND Latitude IS NOT NULL
                AND Longitude IS NOT NULL
                AND Latitude != 0
                AND Longitude != 0
                AND Barangay_code IN ({})
                GROUP BY Barangay_code
                ORDER BY prospect_count DESC
                """.format(','.join(['?' for _ in barangay_list]))

                prospects = db.execute_query_df(prospect_query, barangay_list)

                if prospects is not None and not prospects.empty:
                    print(f"\nProspects available in these barangays:")
                    print(prospects)
                else:
                    print("\nNo prospects found in these barangays")

        else:
            print("No sales agents found with valid barangay data")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    find_agent_with_barangay()