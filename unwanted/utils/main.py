#!/usr/bin/env python3
"""
Route Optimization Pipeline
Main entry point for the route optimization system
"""

from route_optimizer import RouteOptimizer
import sys

def main():
    """Main function to run the route optimization pipeline"""
    print("=" * 50)
    print("Route Optimization Pipeline")
    print("=" * 50)

    optimizer = None
    try:
        # Initialize the route optimizer
        optimizer = RouteOptimizer()

        # Run the complete pipeline
        optimizer.run_pipeline()

    except Exception as e:
        print(f"Error running pipeline: {e}")
        sys.exit(1)
    finally:
        # Clean up
        if optimizer:
            optimizer.close()

    print("=" * 50)
    print("Pipeline execution completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()