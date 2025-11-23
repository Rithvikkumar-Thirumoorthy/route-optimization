#!/usr/bin/env python3
"""
Debug barangay_code matching issue
"""

from database import DatabaseConnection

def debug_matching():
    """Debug why barangay codes don't match"""
    print("Debugging Barangay Code Matching")
    print("=" * 40)

    db = None
    try:
        db = DatabaseConnection()
        db.connect()

        # Check if the specific code exists in prospective
        test_code = "042108023"
        print(f"1. Checking if '{test_code}' exists in prospective table:")

        exact_match = db.execute_query(
            "SELECT COUNT(*) FROM prospective WHERE barangay_code = ?",
            [test_code]
        )
        print(f"Exact matches: {exact_match[0][0]}")

        # Check similar codes
        similar_match = db.execute_query(
            "SELECT COUNT(*) FROM prospective WHERE barangay_code LIKE ?",
            [f"%{test_code}%"]
        )
        print(f"Similar matches (LIKE): {similar_match[0][0]}")

        # Check the actual barangay codes that start with 042
        print(f"\n2. Barangay codes in prospective starting with '042':")
        prefix_query = """
        SELECT TOP 10 barangay_code, COUNT(*) as count
        FROM prospective
        WHERE barangay_code LIKE '042%'
        GROUP BY barangay_code
        ORDER BY count DESC
        """

        prefix_result = db.execute_query(prefix_query)
        if prefix_result:
            for row in prefix_result:
                print(f"  {row[0]} (count: {row[1]})")
        else:
            print("  No codes starting with '042' found")

        # Check what codes are in the prospective table that might match routedata
        print(f"\n3. Looking for overlap between tables:")
        overlap_query = """
        SELECT p.barangay_code, COUNT(DISTINCT p.CustNo) as prospect_count
        FROM prospective p
        WHERE p.barangay_code IN (
            SELECT DISTINCT barangay_code
            FROM routedata
            WHERE barangay_code IS NOT NULL
            AND barangay_code != '#'
            AND barangay_code != ''
        )
        AND p.Latitude IS NOT NULL
        AND p.Longitude IS NOT NULL
        AND p.Latitude != 0
        AND p.Longitude != 0
        GROUP BY p.barangay_code
        ORDER BY prospect_count DESC
        """

        overlap_result = db.execute_query(overlap_query)
        if overlap_result:
            print("Found overlapping barangay codes:")
            for row in overlap_result[:10]:  # Top 10
                print(f"  {row[0]}: {row[1]} prospects")

            # Test with first overlapping code
            if len(overlap_result) > 0:
                working_code = overlap_result[0][0]
                print(f"\n4. Testing with working code: {working_code}")

                # Get customers with this code
                customers_query = """
                SELECT TOP 3 CustNo, latitude, longitude, barangay_code
                FROM routedata
                WHERE barangay_code = ?
                AND latitude IS NOT NULL
                AND longitude IS NOT NULL
                """

                customers = db.execute_query(customers_query, [working_code])
                print(f"Customers with this code: {len(customers)}")

                # Get prospects with this code
                prospects_query = """
                SELECT TOP 3 CustNo, Latitude, Longitude, barangay_code
                FROM prospective
                WHERE barangay_code = ?
                AND Latitude IS NOT NULL
                AND Longitude IS NOT NULL
                """

                prospects = db.execute_query(prospects_query, [working_code])
                print(f"Prospects with this code: {len(prospects)}")

                if len(customers) > 0 and len(prospects) > 0:
                    print("SUCCESS: Found working barangay code match!")
                    print("The barangay_code matching logic should work with this data.")

        else:
            print("No overlapping barangay codes found between tables")
            print("This indicates a data mismatch between routedata.barangay_code and prospective.barangay_code")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    debug_matching()