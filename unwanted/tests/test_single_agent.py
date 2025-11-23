#!/usr/bin/env python3
"""
Test Single Sales Agent - Enhanced Route Optimization
Use this to test one specific sales agent
"""

from enhanced_route_optimizer import EnhancedRouteOptimizer

def test_single_agent():
    """Test enhanced optimization with a single sales agent"""

    # Configure the test
    TEST_AGENT = "D201"          # Change this to test different agents
    TEST_DATE = "2025-09-24"     # Change this to test different dates

    print(f"Testing Enhanced Route Optimization")
    print(f"Agent: {TEST_AGENT} on {TEST_DATE}")
    print("=" * 50)

    optimizer = None
    try:
        optimizer = EnhancedRouteOptimizer()

        # Clear existing test data
        clear_query = """
        DELETE FROM routeplan_ai
        WHERE salesagent = ? AND routedate = ?
        """
        optimizer.db.execute_query(clear_query, [TEST_AGENT, TEST_DATE])
        print(f"Cleared existing data for {TEST_AGENT}")

        # Process the specific agent
        print(f"Processing {TEST_AGENT}...")
        optimizer.process_sales_agent(TEST_AGENT)

        # Verify results
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

        result = optimizer.db.execute_query_df(verify_query, [TEST_AGENT, TEST_DATE])

        if result is not None and not result.empty:
            print(f"\nResults for {TEST_AGENT}:")
            print(result.to_string(index=False))

            total_count = result['count'].sum()
            print(f"\nTotal optimized stops: {total_count}")

            if total_count <= 60:
                print("✓ Route optimization completed successfully!")
            else:
                print("ⓘ Agent had >60 customers, no prospects added")
        else:
            print(f"No results found for {TEST_AGENT}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if optimizer:
            optimizer.close()

if __name__ == "__main__":
    test_single_agent()