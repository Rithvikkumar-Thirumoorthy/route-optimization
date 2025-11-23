#!/usr/bin/env python3
"""
Find valid barangay_codes that are not # symbols
"""

from database import DatabaseConnection

def find_valid_codes():
    """Find valid barangay_codes in routedata"""
    print("Finding Valid Barangay Codes")
    print("=" * 35)

    db = None
    try:
        db = DatabaseConnection()
        db.connect()

        # Find non-# barangay codes in routedata
        print("1. Looking for non-# barangay codes in routedata:")

        valid_query = """
        SELECT TOP 10 barangay_code, COUNT(*) as count
        FROM routedata
        WHERE barangay_code IS NOT NULL
        AND barangay_code != '#'
        AND barangay_code != ''
        GROUP BY barangay_code
        ORDER BY count DESC
        """

        valid_result = db.execute_query(valid_query)
        if valid_result:
            print("Valid barangay codes found in routedata:")
            for row in valid_result:
                print(f"  {row[0]} (count: {row[1]})")

            # Test with the first valid code
            if len(valid_result) > 0:
                test_code = valid_result[0][0]
                print(f"\n2. Testing prospects with code: {test_code}")

                prospect_match = db.execute_query(
                    "SELECT COUNT(*) FROM prospective WHERE barangay_code = ? AND Latitude IS NOT NULL AND Longitude IS NOT NULL",
                    [test_code]
                )
                print(f"Matching prospects: {prospect_match[0][0]}")

                if prospect_match[0][0] > 0:
                    print("SUCCESS: Found matching prospects!")

                    # Get sample prospect data
                    sample_prospects = db.execute_query(
                        "SELECT TOP 3 CustNo, Latitude, Longitude, barangay_code FROM prospective WHERE barangay_code = ? AND Latitude IS NOT NULL",
                        [test_code]
                    )
                    print("Sample matching prospects:")
                    for row in sample_prospects:
                        print(f"  CustNo: {row[0]}, Lat: {row[1]}, Lon: {row[2]}, Code: {row[3]}")

        else:
            print("No valid barangay codes found (all are # symbols)")

        print("\n3. Summary of barangay code distribution in routedata:")
        distribution_query = """
        SELECT
            CASE
                WHEN barangay_code = '#' THEN 'Hash symbol'
                WHEN barangay_code IS NULL THEN 'NULL'
                WHEN barangay_code = '' THEN 'Empty string'
                ELSE 'Valid code'
            END as code_type,
            COUNT(*) as count
        FROM routedata
        GROUP BY
            CASE
                WHEN barangay_code = '#' THEN 'Hash symbol'
                WHEN barangay_code IS NULL THEN 'NULL'
                WHEN barangay_code = '' THEN 'Empty string'
                ELSE 'Valid code'
            END
        ORDER BY count DESC
        """

        distribution = db.execute_query(distribution_query)
        if distribution:
            for row in distribution:
                print(f"  {row[0]}: {row[1]:,}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    find_valid_codes()