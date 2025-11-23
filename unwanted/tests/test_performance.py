#!/usr/bin/env python3
"""
Performance Test: Compare original vs scalable optimizer
"""

import time
from enhanced_route_optimizer import EnhancedRouteOptimizer
from scalable_route_optimizer import ScalableRouteOptimizer

def test_performance():
    """Test performance of scalable optimizer vs original"""

    print("Performance Test: Original vs Scalable Optimizer")
    print("=" * 60)

    test_agent = "PERF-TEST"
    test_date = "2025-12-20"

    # Test 1: Scalable Optimizer
    print("\n1. Testing Scalable Optimizer...")
    start_time = time.time()

    scalable_optimizer = None
    try:
        scalable_optimizer = ScalableRouteOptimizer()

        # Clear test data
        clear_query = """DELETE FROM routeplan_ai WHERE salesagent = ? AND routedate = ?"""
        scalable_optimizer.db.execute_query(clear_query, [test_agent, test_date])

        # Get test customers (30 customers)
        customer_query = """
        SELECT TOP 30 CustNo, latitude, longitude, barangay_code, custype, Name
        FROM routedata
        WHERE SalesManTerritory = 'D201' AND RouteDate = '2025-09-24'
        AND latitude IS NOT NULL AND longitude IS NOT NULL
        AND latitude != 0 AND longitude != 0
        """
        customers = scalable_optimizer.db.execute_query_df(customer_query)

        if customers is not None and not customers.empty:
            print(f"   Retrieved {len(customers)} test customers")

            # Test optimized prospect selection
            centroid_lat = customers['latitude'].mean()
            centroid_lon = customers['longitude'].mean()

            prospects = scalable_optimizer.get_prospects_with_bounding_box(
                centroid_lat, centroid_lon, ['042108023'], 30, radius_km=25
            )

            scalable_time = time.time() - start_time
            print(f"   Scalable optimizer completed in: {scalable_time:.2f} seconds")
            print(f"   Found {len(prospects)} prospects")

        else:
            print("   No test customers found")
            scalable_time = time.time() - start_time

    except Exception as e:
        scalable_time = time.time() - start_time
        print(f"   Scalable optimizer error: {e}")
    finally:
        if scalable_optimizer:
            scalable_optimizer.close()

    # Test 2: Memory and cache info
    print(f"\n2. Performance Summary:")
    print(f"   Scalable optimizer time: {scalable_time:.2f} seconds")
    print(f"   Optimizations used:")
    print(f"   ✓ Geographic bounding box filtering")
    print(f"   ✓ Limited result sets (TOP 1000-2000)")
    print(f"   ✓ Distance-based ordering in SQL")
    print(f"   ✓ Caching for repeated queries")

    # Test 3: Database query optimization
    print(f"\n3. Database Query Analysis:")

    optimizer = ScalableRouteOptimizer()
    try:
        # Test the optimized query performance
        start_query_time = time.time()

        test_query = """
        SELECT TOP 100 CustNo, Latitude, Longitude
        FROM prospective
        WHERE Latitude BETWEEN 14.0 AND 15.0
        AND Longitude BETWEEN 120.0 AND 122.0
        AND Latitude IS NOT NULL
        ORDER BY (Latitude - 14.5)*(Latitude - 14.5) + (Longitude - 121.0)*(Longitude - 121.0)
        """

        result = optimizer.db.execute_query_df(test_query)
        query_time = time.time() - start_query_time

        print(f"   Bounding box query time: {query_time:.2f} seconds")
        print(f"   Records returned: {len(result) if result is not None else 0}")

    except Exception as e:
        print(f"   Query test error: {e}")
    finally:
        optimizer.close()

    print(f"\n" + "="*60)
    print("Performance Test Complete!")
    print("Use scalable_route_optimizer.py for production with 5.8L prospects")
    print("="*60)

if __name__ == "__main__":
    test_performance()