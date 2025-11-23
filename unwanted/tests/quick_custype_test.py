#!/usr/bin/env python3
"""
Quick test to verify custype is now properly set
"""

from enhanced_route_optimizer import EnhancedRouteOptimizer

def quick_custype_test():
    """Quick test of custype classification"""
    print("Quick custype test")
    print("=" * 30)

    optimizer = None
    try:
        optimizer = EnhancedRouteOptimizer()

        # Test with our debug data
        test_agent = "DEBUG-TEST"
        test_date = "2025-12-01"

        # Check what we have in the database from the previous debug test
        verify_query = """
        SELECT
            custype,
            COUNT(*) as count,
            MIN(stopno) as min_stop,
            MAX(stopno) as max_stop
        FROM routeplan_ai
        WHERE salesagent = ? AND routedate = ?
        GROUP BY custype
        ORDER BY custype
        """

        result = optimizer.db.execute_query_df(verify_query, [test_agent, test_date])

        if result is not None and not result.empty:
            print("Current DEBUG-TEST data:")
            print(result.to_string(index=False))
        else:
            print("No DEBUG-TEST data found")

        # Check latest D201 data
        print("\nChecking latest D201 data:")
        d201_query = """
        SELECT TOP 1
            salesagent,
            routedate,
            COUNT(*) as total_records,
            COUNT(CASE WHEN custype = 'customer' THEN 1 END) as customers,
            COUNT(CASE WHEN custype = 'prospect' THEN 1 END) as prospects,
            COUNT(CASE WHEN custype IS NULL THEN 1 END) as null_types
        FROM routeplan_ai
        WHERE salesagent = 'D201'
        GROUP BY salesagent, routedate
        ORDER BY routedate DESC
        """

        d201_result = optimizer.db.execute_query_df(d201_query)

        if d201_result is not None and not d201_result.empty:
            print("Latest D201 data:")
            print(d201_result.to_string(index=False))

            # Check if any custype values are properly set
            sample_query = """
            SELECT TOP 10 custno, custype, stopno
            FROM routeplan_ai
            WHERE salesagent = 'D201'
            ORDER BY routedate DESC, stopno
            """
            sample_result = optimizer.db.execute_query_df(sample_query)
            print("\nSample D201 records:")
            print(sample_result.to_string(index=False))
        else:
            print("No D201 data found")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if optimizer:
            optimizer.close()

if __name__ == "__main__":
    quick_custype_test()