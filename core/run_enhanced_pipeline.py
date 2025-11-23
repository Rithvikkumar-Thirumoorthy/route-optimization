#!/usr/bin/env python3
"""
Enhanced Route Optimization Pipeline - Main Entry Point
Run this file to process all sales agents with prospect addition
"""

from enhanced_route_optimizer import EnhancedRouteOptimizer
import sys

def main():
    """Run the complete enhanced route optimization pipeline"""
    print("=" * 60)
    print("Enhanced Route Optimization Pipeline")
    print("Features: 2-step prospect selection + TSP optimization")
    print("=" * 60)

    optimizer = None
    try:
        # Initialize the enhanced route optimizer
        optimizer = EnhancedRouteOptimizer()

        print("Starting pipeline...")
        print("- Processing all sales agents")
        print("- Adding prospects to reach 60 customers per route")
        print("- Running TSP optimization")
        print("- Inserting results into routeplan_ai table")
        print()

        # Run the complete pipeline
        optimizer.run_pipeline()

        print("=" * 60)
        print("Pipeline completed successfully!")
        print("Check the 'routeplan_ai' table for optimized routes")
        print("=" * 60)

    except Exception as e:
        print(f"Error running pipeline: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up
        if optimizer:
            optimizer.close()

if __name__ == "__main__":
    main()