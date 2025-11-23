
#!/usr/bin/env python3
"""
Find a sales agent with customers that have valid coordinates
"""

from database import DatabaseConnection

def find_agent_with_coordinates():
    """Find sales agent with customers having valid coordinates"""
    db = DatabaseConnection()
    connection = db.connect()

    if not connection:
        print("Failed to connect to database")
        return

    try:
        # Find agents with customers having valid coordinates
        query = """
        SELECT TOP 5
            r.SalesManTerritory,
            r.RouteDate,
            COUNT(*) as total_customers,
            SUM(CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
                     AND r.latitude != 0 AND r.longitude != 0 THEN 1 ELSE 0 END) as customers_with_coords
        FROM routedata r
        WHERE r.SalesManTerritory IS NOT NULL
        AND r.RouteDate IS NOT NULL
        GROUP BY r.SalesManTerritory, r.RouteDate
        HAVING COUNT(*) <= 60
        AND SUM(CASE WHEN r.latitude IS NOT NULL AND r.longitude IS NOT NULL
                     AND r.latitude != 0 AND r.longitude != 0 THEN 1 ELSE 0 END) > 5
        ORDER BY customers_with_coords DESC
        """

        result = db.execute_query(query)

        if result:
            print("Sales agents with customers having valid coordinates:")
            print("Agent\t\tDate\t\tTotal\tWith Coords")
            print("-" * 50)
            for row in result:
                print(f"{row[0]:<15}\t{row[1]}\t{row[2]}\t{row[3]}")

            # Get detailed info for the first agent
            best_agent = result[0][0]
            best_date = result[0][1]

            print(f"\nDetailed info for {best_agent} on {best_date}:")

            detail_query = """
            SELECT CustNo, latitude, longitude, Name, custype
            FROM routedata
            WHERE SalesManTerritory = ? AND RouteDate = ?
            AND latitude IS NOT NULL AND longitude IS NOT NULL
            AND latitude != 0 AND longitude != 0
            """

            details = db.execute_query(detail_query, [best_agent, best_date])

            if details:
                print(f"Found {len(details)} customers with valid coordinates:")
                for i, detail in enumerate(details[:10]):  # Show first 10
                    print(f"{i+1}. {detail[0]} - Lat: {detail[1]}, Lon: {detail[2]} - {detail[3]}")
        else:
            print("No sales agents found with customers having valid coordinates")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    find_agent_with_coordinates()