#!/usr/bin/env python3
"""
Hierarchical Route Pipeline - Main Entry Point

This script runs the hierarchical monthly route optimization pipeline.
It processes routes in a hierarchical manner: Distributor → Agent → Date.

Starting Location Priority:
    1. CLI arguments (--start-lat/--start-lon) - HIGHEST PRIORITY
    2. Distributor table (fetches location per distributor from DB)
    3. Config defaults (fallback if not in DB)

Usage:
    # Basic usage (uses distributor locations from DB)
    python run_pipeline.py

    # Filter by specific distributor
    python run_pipeline.py --distributor-id "DIST001"

    # Override starting location for ALL distributors
    python run_pipeline.py --start-lat 14.5995 --start-lon 120.9842

    # Custom configuration
    python run_pipeline.py --batch-size 100 --max-workers 8 --max-distance-km 10

    # Parallel processing (RECOMMENDED - 3-4x faster!)
    python run_pipeline.py --parallel --max-workers 4

    # Test mode (process first 10 combinations only)
    python run_pipeline.py --test-mode
"""

import sys
import os
import argparse
from datetime import datetime

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import configuration and pipeline modules
import config
from src.pipeline import HierarchicalMonthlyRoutePipelineProcessor

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Hierarchical Monthly Route Optimization Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run for all data (uses distributor locations from database)
  python run_pipeline.py

  # Filter by specific distributor
  python run_pipeline.py --distributor-id "DIST001"

  # Override starting location for ALL distributors
  python run_pipeline.py --start-lat 14.5995 --start-lon 120.9842

  # Custom batch size and workers
  python run_pipeline.py --batch-size 100 --max-workers 8

  # Parallel processing (RECOMMENDED - 3-4x faster!)
  python run_pipeline.py --parallel --max-workers 4

  # Test mode (process only first 10 combinations)
  python run_pipeline.py --test-mode

  # All options combined with parallel processing
  python run_pipeline.py --parallel --distributor-id "DIST001" --start-lat 14.5995 \\
      --start-lon 120.9842 --batch-size 50 --max-workers 4 \\
      --max-distance-km 10.0 --test-mode

Starting Location Priority:
  1. CLI arguments (--start-lat/--start-lon) - overrides everything
  2. Distributor table - fetches location per distributor from database
  3. Config defaults - fallback if distributor location not in database
        """
    )

    # Pipeline configuration
    parser.add_argument(
        '--batch-size',
        type=int,
        default=config.BATCH_SIZE,
        help=f'Batch size for processing (default: {config.BATCH_SIZE})'
    )

    parser.add_argument(
        '--max-workers',
        type=int,
        default=config.MAX_WORKERS,
        help=f'Maximum number of parallel workers (default: {config.MAX_WORKERS})'
    )

    # TSP configuration
    parser.add_argument(
        '--start-lat',
        type=float,
        default=None,
        help='Starting latitude for TSP optimization (overrides distributor location if specified)'
    )

    parser.add_argument(
        '--start-lon',
        type=float,
        default=None,
        help='Starting longitude for TSP optimization (overrides distributor location if specified)'
    )

    # Filtering
    parser.add_argument(
        '--distributor-id',
        type=str,
        default=config.DISTRIBUTOR_ID_FILTER,
        help='Filter by specific distributor ID (optional)'
    )

    # Prospect search
    parser.add_argument(
        '--max-distance-km',
        type=float,
        default=config.MAX_DISTANCE_KM,
        help=f'Maximum distance for prospect search in km (default: {config.MAX_DISTANCE_KM})'
    )

    # Parallel processing
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Enable parallel agent processing (RECOMMENDED - 3-4x faster!)'
    )

    # Test mode
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Run in test mode (process only first 10 combinations)'
    )

    # Validation only
    parser.add_argument(
        '--validate-config',
        action='store_true',
        help='Validate configuration and exit'
    )

    return parser.parse_args()

def print_banner():
    """Print startup banner"""
    print("=" * 80)
    print(" " * 15 + "HIERARCHICAL ROUTE OPTIMIZATION PIPELINE")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

def print_configuration(args):
    """Print pipeline configuration"""
    print("\nCONFIGURATION:")
    print("-" * 80)
    print(f"  Processing Mode:       {'PARALLEL (agents processed concurrently)' if args.parallel else 'SEQUENTIAL (agents processed one at a time)'}")
    print(f"  Batch Size:            {args.batch_size}")
    print(f"  Max Workers:           {args.max_workers}{' (concurrent agents)' if args.parallel else ' (unused in sequential mode)'}")

    # Improved starting location display
    if args.start_lat and args.start_lon:
        print(f"  Starting Location:     User-specified ({args.start_lat}, {args.start_lon})")
        print(f"                         [Overrides distributor locations from DB]")
    else:
        print(f"  Starting Location:     Auto (from distributors table)")
        print(f"                         [Fallback: config defaults if not in DB]")

    print(f"  Distributor Filter:    {args.distributor_id if args.distributor_id else 'None (process all)'}")
    print(f"  Max Distance (km):     {args.max_distance_km}")
    print(f"  Test Mode:             {'Yes (first 10 only)' if args.test_mode else 'No (process all)'}")
    if args.parallel:
        print(f"\n  💡 TIP: Parallel mode enabled - expect 3-4x faster processing!")
    else:
        print(f"\n  💡 TIP: Use --parallel --max-workers 4 for 3-4x faster processing!")
    print("-" * 80)
    print()

def main():
    """Main execution function"""
    # Parse arguments
    args = parse_arguments()

    # Print banner
    print_banner()

    # Validate configuration if requested
    if args.validate_config:
        print("\nValidating configuration...")
        try:
            config.validate_config()
            config.print_config()
            print("\n✓ Configuration is valid")
            return 0
        except Exception as e:
            print(f"\n✗ Configuration error: {e}")
            return 1

    # Print configuration
    print_configuration(args)

    # Validate configuration
    try:
        config.validate_config()
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        print("Please check your .env file and config.py")
        return 1

    # Update config with command line arguments
    config.MAX_DISTANCE_KM = args.max_distance_km

    # Create processor instance
    print("Initializing pipeline processor...")
    processor = HierarchicalMonthlyRoutePipelineProcessor(
        batch_size=args.batch_size,
        max_workers=args.max_workers,
        start_lat=args.start_lat,
        start_lon=args.start_lon,
        distributor_id=args.distributor_id
    )

    # Run pipeline
    try:
        print("Starting pipeline execution...\n")
        processor.run_hierarchical_pipeline(parallel=args.parallel)

        print("\n" + "=" * 80)
        print(" " * 25 + "PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Check the logs directory for detailed execution logs")
        print("=" * 80)

        return 0

    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print(" " * 25 + "PIPELINE INTERRUPTED BY USER")
        print("=" * 80)
        return 130

    except Exception as e:
        print("\n\n" + "=" * 80)
        print(" " * 25 + "PIPELINE FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print("\nCheck the logs directory for detailed error information")
        print("=" * 80)

        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
