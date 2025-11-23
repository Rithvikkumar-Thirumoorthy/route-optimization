#!/usr/bin/env python3
"""
Analyze RouteData Table - Distributor ID 11814
"""

import sys
import os
import pandas as pd

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

def analyze_routedata():
    """Analyze routedata table for distributor ID 11814"""
    print("ANALYZING ROUTEDATA TABLE - DISTRIBUTOR ID 11814")
    print("=" * 60)

    distributor_id = "11814"

    db = None

    try:
        # Connect to database
        db = DatabaseConnection()
        db.connect()
        print("Database connection successful!")

        # Main query
        print(f"\nQuerying routedata for distributor ID {distributor_id}...")
        main_query = f"""
        SELECT *
        FROM routedata
        WHERE distributorid = '{distributor_id}'
        """

        routedata_df = db.execute_query_df(main_query)

        if routedata_df is None or routedata_df.empty:
            print(f"No data found for distributor ID {distributor_id}")
            return

        total_records = len(routedata_df)
        print(f"SUCCESS: Found {total_records} records")

        # Basic statistics
        print(f"\n" + "="*60)
        print("BASIC STATISTICS")
        print("="*60)
        print(f"Total Records: {total_records}")

        # Show columns
        print(f"\nColumn Information:")
        for col in routedata_df.columns:
            print(f"  - {col}")

        # Show first few records
        print(f"\nFirst 5 Records:")
        print(routedata_df.head().to_string())

        # Analysis by key fields if they exist
        if 'salesagent' in routedata_df.columns:
            print(f"\n" + "="*60)
            print("SALES AGENT ANALYSIS")
            print("="*60)
            agent_stats = routedata_df['salesagent'].value_counts()
            print("Records per Sales Agent:")
            for agent, count in agent_stats.items():
                print(f"  Agent {agent}: {count} records")

        if 'routedate' in routedata_df.columns:
            print(f"\n" + "="*60)
            print("DATE ANALYSIS")
            print("="*60)
            date_stats = routedata_df['routedate'].value_counts().sort_index()
            print("Records per Date:")
            for date, count in date_stats.items():
                print(f"  {date}: {count} records")

            # Date range
            if len(date_stats) > 0:
                min_date = date_stats.index.min()
                max_date = date_stats.index.max()
                print(f"\nDate Range: {min_date} to {max_date}")

        if 'custype' in routedata_df.columns:
            print(f"\n" + "="*60)
            print("CUSTOMER TYPE ANALYSIS")
            print("="*60)
            custype_stats = routedata_df['custype'].value_counts()
            print("Records per Customer Type:")
            for custype, count in custype_stats.items():
                print(f"  {custype}: {count} records")

        if 'barangay_code' in routedata_df.columns:
            print(f"\n" + "="*60)
            print("BARANGAY ANALYSIS")
            print("="*60)
            barangay_stats = routedata_df['barangay_code'].value_counts()
            print("Records per Barangay:")
            for barangay, count in barangay_stats.head(10).items():
                print(f"  Barangay {barangay}: {count} records")

            if len(barangay_stats) > 10:
                print(f"  ... and {len(barangay_stats) - 10} more barangays")

        # Geographic analysis if coordinates exist
        if 'latitude' in routedata_df.columns and 'longitude' in routedata_df.columns:
            print(f"\n" + "="*60)
            print("GEOGRAPHIC ANALYSIS")
            print("="*60)

            # Remove null/zero coordinates
            valid_coords = routedata_df[
                (routedata_df['latitude'].notna()) &
                (routedata_df['longitude'].notna()) &
                (routedata_df['latitude'] != 0) &
                (routedata_df['longitude'] != 0)
            ]

            if not valid_coords.empty:
                print(f"Valid Coordinates: {len(valid_coords)}/{total_records} records")
                print(f"Latitude Range: {valid_coords['latitude'].min():.4f} to {valid_coords['latitude'].max():.4f}")
                print(f"Longitude Range: {valid_coords['longitude'].min():.4f} to {valid_coords['longitude'].max():.4f}")

                # Center point
                center_lat = valid_coords['latitude'].mean()
                center_lon = valid_coords['longitude'].mean()
                print(f"Geographic Center: ({center_lat:.4f}, {center_lon:.4f})")
            else:
                print("No valid coordinates found")

        # Stop number analysis if exists
        if 'stopno' in routedata_df.columns:
            print(f"\n" + "="*60)
            print("STOP NUMBER ANALYSIS")
            print("="*60)
            stopno_stats = routedata_df['stopno'].describe()
            print("Stop Number Statistics:")
            print(f"  Min: {stopno_stats['min']}")
            print(f"  Max: {stopno_stats['max']}")
            print(f"  Mean: {stopno_stats['mean']:.1f}")
            print(f"  Count: {stopno_stats['count']}")

        # Sample data
        print(f"\n" + "="*60)
        print("SAMPLE DATA")
        print("="*60)
        print(routedata_df.sample(min(5, len(routedata_df))).to_string())

        print(f"\n" + "="*60)
        print("ANALYSIS COMPLETED!")
        print("="*60)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    analyze_routedata()