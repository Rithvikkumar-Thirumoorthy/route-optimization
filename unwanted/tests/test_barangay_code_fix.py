#!/usr/bin/env python3
"""
Test the corrected barangay_code matching logic
"""

from enhanced_route_optimizer import EnhancedRouteOptimizer

def test_barangay_code_matching():
    """Test that barangay_code matching works correctly"""
    print("Testing Corrected Barangay Code Matching")
    print("=" * 50)

    optimizer = None
    try:
        optimizer = EnhancedRouteOptimizer()

        # Test 1: Get a sample customer with barangay_code (barangay_code)
        test_query = """
        SELECT TOP 5 CustNo, latitude, longitude, barangay_code, custype, Name
        FROM routedata
        WHERE barangay_code IS NOT NULL
        AND latitude IS NOT NULL
        AND longitude IS NOT NULL
        AND latitude != 0
        AND longitude != 0
        """

        customers = optimizer.db.execute_query_df(test_query)

        if customers is not None and not customers.empty:
            print(f"Found {len(customers)} test customers with barangay_codes")

            # Display sample barangay_codes
            sample_codes = customers['barangay_code'].unique()[:3]
            print(f"Sample barangay_codes from customers: {list(sample_codes)}")

            # Test 2: Check if prospects exist with matching barangay_codes
            if sample_codes is not None and len(sample_codes) > 0:
                test_code = sample_codes[0]
                print(f"\nTesting with barangay_code: {test_code}")

                prospect_query = """
                SELECT COUNT(*) as count
                FROM prospective
                WHERE barangay_code = ?
                AND Latitude IS NOT NULL
                AND Longitude IS NOT NULL
                AND Latitude != 0
                AND Longitude != 0
                """

                result = optimizer.db.execute_query(prospect_query, params=[test_code])
                if result:
                    prospect_count = result[0][0]
                    print(f"Found {prospect_count} prospects with matching barangay_code")

                    if prospect_count > 0:
                        print("SUCCESS: Barangay_code matching appears to be working correctly")
                    else:
                        print("WARNING: No prospects found with this barangay_code - may need different test data")

            # Test 3: Run the actual prospect selection method
            print(f"\nTesting get_barangay_prospects_2step method...")

            customers_with_coords = customers[
                (customers['latitude'].notna()) &
                (customers['longitude'].notna()) &
                (customers['latitude'] != 0) &
                (customers['longitude'] != 0)
            ].copy()

            customers_without_coords = customers[
                (customers['latitude'].isna()) |
                (customers['longitude'].isna()) |
                (customers['latitude'] == 0) |
                (customers['longitude'] == 0)
            ].copy()

            prospects = optimizer.get_barangay_prospects_2step(
                customers_with_coords, customers_without_coords, needed_count=5
            )

            if not prospects.empty:
                print(f"SUCCESS: Successfully found {len(prospects)} prospects using corrected matching")
                print(f"Prospect barangay_codes: {prospects['Barangay_code'].unique()[:3]}")
            else:
                print("WARNING: No prospects found - this could indicate the barangay_codes don't match")

        else:
            print("No test customers found")

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if optimizer:
            optimizer.close()

    print(f"\nBarangay code matching test completed!")

if __name__ == "__main__":
    test_barangay_code_matching()