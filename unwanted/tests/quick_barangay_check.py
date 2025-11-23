#!/usr/bin/env python3
"""
Quick check of barangay_code data
"""

from database import DatabaseConnection

def quick_check():
    """Quick check of barangay_code data"""
    print("Quick Barangay Code Check")
    print("=" * 30)

    db = None
    try:
        db = DatabaseConnection()
        db.connect()

        # Simple count check
        print("1. Row counts:")

        routedata_count = db.execute_query("SELECT COUNT(*) FROM routedata WHERE barangay_code IS NOT NULL")
        print(f"Routedata with barangay_code: {routedata_count[0][0]:,}")

        prospective_count = db.execute_query("SELECT COUNT(*) FROM prospective WHERE barangay_code IS NOT NULL")
        print(f"Prospective with barangay_code: {prospective_count[0][0]:,}")

        # Quick sample
        print("\n2. Sample barangay_codes:")

        sample_rd = db.execute_query("SELECT TOP 3 barangay_code FROM routedata WHERE barangay_code IS NOT NULL")
        print("Routedata barangay_code samples:")
        for row in sample_rd:
            print(f"  {row[0]}")

        sample_p = db.execute_query("SELECT TOP 3 barangay_code FROM prospective WHERE barangay_code IS NOT NULL")
        print("Prospective barangay_code samples:")
        for row in sample_p:
            print(f"  {row[0]}")

        # Quick match test
        print("\n3. Quick match test:")
        test_code = sample_rd[0][0]  # Get first routedata barangay_code
        print(f"Testing with code: {test_code}")

        match_count = db.execute_query("SELECT COUNT(*) FROM prospective WHERE barangay_code = ?", [test_code])
        print(f"Matching prospects: {match_count[0][0]}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    quick_check()