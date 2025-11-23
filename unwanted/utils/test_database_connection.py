#!/usr/bin/env python3
"""
Test Database Connection - Verify the pandas warning fix
"""

import sys
import os
import warnings

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def test_connection():
    """Test database connection and pandas compatibility"""
    print("Testing Database Connection and Pandas Compatibility")
    print("=" * 60)

    # Capture warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        db = DatabaseConnection()

        # Test connection
        print("1. Testing database connection...")
        connection = db.connect()

        if not connection:
            print("ERROR: Database connection failed")
            return False

        print("SUCCESS: Database connection successful")

        # Test simple query
        print("\n2. Testing simple query...")
        try:
            simple_query = "SELECT TOP 1 'test' as message"
            result = db.execute_query_df(simple_query)

            if result is not None and not result.empty:
                print("SUCCESS: Simple query successful")
                print(f"   Result: {result.iloc[0]['message']}")
            else:
                print("ERROR: Simple query failed")
                return False

        except Exception as e:
            print(f"ERROR: Simple query error: {e}")
            return False

        # Test query with real data
        print("\n3. Testing query with real data...")
        try:
            count_query = """
            SELECT TOP 3
                Code as agent_id,
                RouteDate,
                COUNT(DISTINCT CustNo) as customer_count
            FROM routedata
            WHERE Code IS NOT NULL
            GROUP BY Code, RouteDate
            ORDER BY Code, RouteDate
            """
            result = db.execute_query_df(count_query)

            if result is not None and not result.empty:
                print("SUCCESS: Real data query successful")
                print(f"   Found {len(result)} agent-date combinations")
                for idx, row in result.iterrows():
                    print(f"   - Agent: {row['agent_id']}, Date: {row['RouteDate']}, Customers: {row['customer_count']}")
            else:
                print("ERROR: Real data query returned no results")

        except Exception as e:
            print(f"ERROR: Real data query error: {e}")
            return False

        # Check for warnings
        print("\n4. Checking for pandas warnings...")
        pandas_warnings = [warning for warning in w
                          if 'pandas only supports SQLAlchemy' in str(warning.message)]

        if pandas_warnings:
            print("WARNING: Pandas warnings still present:")
            for warning in pandas_warnings:
                print(f"   - {warning.message}")
        else:
            print("SUCCESS: No pandas warnings detected")

        # Close connection
        db.close()
        print("\nSUCCESS: Database connection closed successfully")

        return True

def main():
    """Main function"""
    try:
        success = test_connection()

        if success:
            print(f"\nSUCCESS: All tests passed!")
            print("The database connection is working properly with pandas.")
            print("You can now run the scenario finder without warnings.")
        else:
            print(f"\nERROR: Tests failed!")
            print("There may be database connectivity issues.")

    except Exception as e:
        print(f"\nERROR: Test script error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()