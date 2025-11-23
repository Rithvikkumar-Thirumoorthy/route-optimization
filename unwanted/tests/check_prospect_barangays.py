#!/usr/bin/env python3
"""
Check what barangay codes are available in prospective table
"""

from database import DatabaseConnection

def check_prospect_barangays():
    """Check barangay codes in prospective table"""
    db = DatabaseConnection()
    connection = db.connect()

    if not connection:
        print("Failed to connect to database")
        return

    try:
        # Check barangay codes in prospective table
        query = """
        SELECT TOP 20
            Barangay_code,
            COUNT(*) as prospect_count
        FROM prospective
        WHERE Active = 1
        AND Latitude IS NOT NULL
        AND Longitude IS NOT NULL
        AND Latitude != 0
        AND Longitude != 0
        AND Barangay_code IS NOT NULL
        AND Barangay_code != ''
        GROUP BY Barangay_code
        ORDER BY prospect_count DESC
        """

        result = db.execute_query_df(query)

        if result is not None and not result.empty:
            print("Top barangay codes in prospective table:")
            print(result)

            # Now check if any routedata has matching barangay_code
            top_barangays = result['Barangay_code'].tolist()[:10]

            match_query = """
            SELECT DISTINCT
                r.SalesManTerritory,
                r.RouteDate,
                r.barangay_code,
                COUNT(*) as customer_count
            FROM routedata r
            WHERE r.barangay_code IN ({})
            AND r.SalesManTerritory IS NOT NULL
            AND r.RouteDate IS NOT NULL
            GROUP BY r.SalesManTerritory, r.RouteDate, r.barangay_code
            HAVING COUNT(*) BETWEEN 20 AND 50
            ORDER BY customer_count DESC
            """.format(','.join(['?' for _ in top_barangays]))

            matches = db.execute_query_df(match_query, top_barangays)

            if matches is not None and not matches.empty:
                print(f"\nSales agents with customers in these barangays:")
                print(matches.head(10))
            else:
                print("\nNo sales agents found with customers in these barangays")

        else:
            print("No barangay codes found in prospective table")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_prospect_barangays()