#!/usr/bin/env python3
"""
Check barangay_code data in both tables to understand the matching issue
"""

from database import DatabaseConnection

def check_barangay_codes():
    """Check barangay_code data in both routedata and prospective tables"""
    print("Checking Barangay Code Data")
    print("=" * 40)

    db = None
    try:
        db = DatabaseConnection()
        db.connect()

        # Check routedata barangay_codes (barangay_code)
        print("1. Routedata barangay_code (barangay_codes):")
        routedata_query = """
        SELECT TOP 10 barangay_code, COUNT(*) as count
        FROM routedata
        WHERE barangay_code IS NOT NULL
        GROUP BY barangay_code
        ORDER BY count DESC
        """

        routedata_result = db.execute_query_df(routedata_query)
        if routedata_result is not None and not routedata_result.empty:
            print(routedata_result.to_string(index=False))
        else:
            print("No barangay_code data found in routedata")

        print("\n" + "="*40)

        # Check prospective barangay_codes
        print("2. Prospective barangay_code:")
        prospective_query = """
        SELECT TOP 10 barangay_code, COUNT(*) as count
        FROM prospective
        WHERE barangay_code IS NOT NULL
        AND Latitude IS NOT NULL
        AND Longitude IS NOT NULL
        AND Latitude != 0
        AND Longitude != 0
        GROUP BY barangay_code
        ORDER BY count DESC
        """

        prospective_result = db.execute_query_df(prospective_query)
        if prospective_result is not None and not prospective_result.empty:
            print(prospective_result.to_string(index=False))
        else:
            print("No barangay_code data found in prospective")

        print("\n" + "="*40)

        # Check for any overlap
        print("3. Checking for overlapping barangay_codes:")
        overlap_query = """
        SELECT r.barangay_code as routedata_code, COUNT(DISTINCT r.CustNo) as customer_count,
               COUNT(DISTINCT p.CustNo) as prospect_count
        FROM routedata r
        LEFT JOIN prospective p ON r.barangay_code = p.barangay_code
        WHERE r.barangay_code IS NOT NULL
        AND p.Latitude IS NOT NULL AND p.Longitude IS NOT NULL
        AND p.Latitude != 0 AND p.Longitude != 0
        GROUP BY r.barangay_code
        HAVING COUNT(DISTINCT p.CustNo) > 0
        ORDER BY prospect_count DESC
        """

        overlap_result = db.execute_query_df(overlap_query)
        if overlap_result is not None and not overlap_result.empty:
            print(f"Found {len(overlap_result)} barangay_codes with both customers and prospects:")
            print(overlap_result.head().to_string(index=False))
        else:
            print("No overlapping barangay_codes found!")
            print("This explains why no prospects are being matched.")

        print("\n" + "="*40)

        # Check data types and formats
        print("4. Sample data format comparison:")

        sample_routedata = """
        SELECT TOP 5 barangay_code
        FROM routedata
        WHERE barangay_code IS NOT NULL
        """

        sample_prospective = """
        SELECT TOP 5 barangay_code
        FROM prospective
        WHERE barangay_code IS NOT NULL
        """

        print("Routedata barangay_code samples:")
        rd_samples = db.execute_query_df(sample_routedata)
        if rd_samples is not None:
            for code in rd_samples['barangay_code']:
                print(f"  '{code}' (type: {type(code)}, len: {len(str(code))})")

        print("\nProspective barangay_code samples:")
        p_samples = db.execute_query_df(sample_prospective)
        if p_samples is not None:
            for code in p_samples['barangay_code']:
                print(f"  '{code}' (type: {type(code)}, len: {len(str(code))})")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    check_barangay_codes()