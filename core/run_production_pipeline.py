#!/usr/bin/env python3
"""
PRODUCTION PIPELINE: Scalable Route Optimization for 5.8L Prospects
This is the main file to run for production with large datasets
"""

from scalable_route_optimizer import ScalableRouteOptimizer
import sys
import time

def main():
    """Run the production-ready scalable route optimization pipeline"""
    print("="*70)
    print("PRODUCTION ROUTE OPTIMIZATION PIPELINE")
    print("Optimized for Large Datasets (5.8L prospects + 1.8L customers)")
    print("="*70)

    start_time = time.time()
    optimizer = None

    try:
        print("\nInitializing scalable optimizer...")
        print("Features enabled:")
        print("  - Geographic bounding box filtering")
        print("  - Distance-based SQL ordering")
        print("  - Result set limiting (TOP 1000-2000)")
        print("  - Memory-efficient caching")
        print("  - Fallback prospect selection")
        print("  - TSP route optimization")

        # Initialize the scalable optimizer
        optimizer = ScalableRouteOptimizer(cache_size=500)

        print(f"\nStarting pipeline execution...")
        print(f"Target: Process all sales agents with <60 customers")
        print(f"Goal: Add prospects to reach exactly 60 optimized stops per route")

        # Run the optimized pipeline
        optimizer.run_optimized_pipeline()

        # Calculate total execution time
        end_time = time.time()
        total_time = end_time - start_time
        minutes = int(total_time // 60)
        seconds = int(total_time % 60)

        print(f"\n" + "="*70)
        print(f"PIPELINE EXECUTION COMPLETED!")
        print(f"Total execution time: {minutes}m {seconds}s")
        print(f"="*70)

        # Show final statistics
        print(f"\nFinal Results Summary:")

        # Count total records inserted
        total_query = "SELECT COUNT(*) as total FROM routeplan_ai"
        total_result = optimizer.db.execute_query(total_query)
        if total_result:
            total_routes = total_result[0][0]
            print(f"  Total optimized routes: {total_routes:,}")

        # Count by customer type
        type_query = """
        SELECT custype, COUNT(*) as count
        FROM routeplan_ai
        GROUP BY custype
        ORDER BY custype
        """
        type_result = optimizer.db.execute_query_df(type_query)
        if type_result is not None and not type_result.empty:
            print(f"  Route composition:")
            for _, row in type_result.iterrows():
                custype = row['custype']
                count = row['count']
                print(f"    {custype}: {count:,}")

        # Count agents processed
        agent_query = "SELECT COUNT(DISTINCT salesagent) as agents FROM routeplan_ai"
        agent_result = optimizer.db.execute_query(agent_query)
        if agent_result:
            agent_count = agent_result[0][0]
            print(f"  Sales agents processed: {agent_count:,}")

        print(f"\n✓ All optimized routes saved to 'routeplan_ai' table")
        print(f"✓ Ready for field deployment!")

    except KeyboardInterrupt:
        print(f"\n\nPipeline interrupted by user")
        print(f"Partial results may be available in 'routeplan_ai' table")
        sys.exit(1)

    except Exception as e:
        print(f"\nERROR: Pipeline execution failed")
        print(f"Error details: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # Clean up
        if optimizer:
            print(f"\nCleaning up database connections...")
            optimizer.close()

    print(f"\nProduction pipeline completed successfully!")

if __name__ == "__main__":
    main()