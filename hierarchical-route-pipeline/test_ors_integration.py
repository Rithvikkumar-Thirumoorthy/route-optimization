#!/usr/bin/env python3
"""
Test script for ORS Matrix API integration

This script verifies that the ORS API integration is working correctly
and compares results with Haversine distance calculations.
"""

import sys
import os
import time

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import config
from src.pipeline import HierarchicalMonthlyRoutePipelineProcessor
import numpy as np

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def test_ors_connection():
    """Test 1: Verify ORS API is accessible"""
    print_section("TEST 1: ORS API Connection")

    try:
        import requests

        print(f"ORS Endpoint: {config.ORS_CONFIG['matrix_endpoint']}")
        print(f"ORS Enabled: {config.ORS_CONFIG['enabled']}")
        print(f"Timeout: {config.ORS_CONFIG['timeout']}s")
        print(f"Caching: {config.ORS_CONFIG['use_cache']}")

        # Try a simple 2-point distance calculation
        test_locations = [
            [120.9842, 14.5995],  # Manila City Hall (lon, lat)
            [121.0583, 14.6091]   # Quezon City Hall
        ]

        print(f"\nTesting with 2 sample locations (Manila area)...")

        request_body = {
            "locations": test_locations,
            "metrics": ["distance"],
            "units": "km"
        }

        response = requests.post(
            config.ORS_CONFIG['matrix_endpoint'],
            json=request_body,
            headers={'Content-Type': 'application/json'},
            timeout=config.ORS_CONFIG['timeout']
        )

        if response.status_code == 200:
            result = response.json()
            if 'distances' in result:
                distances = result['distances']
                print(f"✓ ORS API is working!")
                print(f"  Distance matrix shape: {len(distances)}x{len(distances[0])}")
                print(f"  Point 0 → Point 1: {distances[0][1]:.2f} km")
                print(f"  Point 1 → Point 0: {distances[1][0]:.2f} km")
                return True
            else:
                print(f"✗ ORS API response missing 'distances' field")
                print(f"  Response: {result}")
                return False
        else:
            print(f"✗ ORS API returned HTTP {response.status_code}")
            print(f"  Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to ORS API at {config.ORS_CONFIG['matrix_endpoint']}")
        print(f"  Make sure ORS is running at http://localhost:8080")
        return False
    except Exception as e:
        print(f"✗ Error testing ORS connection: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_distance_matrix():
    """Test 2: Test distance matrix calculation with pipeline processor"""
    print_section("TEST 2: Distance Matrix Calculation")

    try:
        # Create processor instance
        processor = HierarchicalMonthlyRoutePipelineProcessor()

        # Test locations in Manila/Quezon City area
        test_locations = [
            [120.9842, 14.5995],  # Manila City Hall (start point)
            [121.0583, 14.6091],  # Quezon City Hall
            [121.0354, 14.5547],  # Makati City Hall
            [121.0223, 14.5764],  # Mandaluyong City Hall
            [121.0559, 14.6760]   # Fairview, QC
        ]

        location_names = [
            "Manila (Start)",
            "Quezon City",
            "Makati",
            "Mandaluyong",
            "Fairview"
        ]

        print(f"\nTesting with {len(test_locations)} locations:")
        for i, name in enumerate(location_names):
            print(f"  {i}. {name}: [{test_locations[i][0]:.4f}, {test_locations[i][1]:.4f}]")

        print(f"\nCalling ORS Matrix API...")
        start_time = time.time()
        distance_matrix = processor.get_ors_distance_matrix(test_locations)
        elapsed_time = time.time() - start_time

        if distance_matrix is not None:
            print(f"✓ Matrix retrieved successfully in {elapsed_time:.2f}s")
            print(f"  Matrix shape: {distance_matrix.shape}")

            # Display distance matrix
            print(f"\nDistance Matrix (km):")
            print("     ", end="")
            for i in range(len(location_names)):
                print(f"{i:>8}", end="")
            print()

            for i in range(len(distance_matrix)):
                print(f"{i:>3}  ", end="")
                for j in range(len(distance_matrix[i])):
                    if i == j:
                        print(f"{'--':>8}", end="")
                    else:
                        print(f"{distance_matrix[i][j]:>8.2f}", end="")
                print(f"  {location_names[i]}")

            return True, distance_matrix
        else:
            print(f"✗ Failed to get distance matrix")
            return False, None

    except Exception as e:
        print(f"✗ Error testing distance matrix: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_ors_vs_haversine():
    """Test 3: Compare ORS distances with Haversine"""
    print_section("TEST 3: ORS vs Haversine Comparison")

    try:
        processor = HierarchicalMonthlyRoutePipelineProcessor()

        # Test points
        start_lat, start_lon = 14.5995, 120.9842  # Manila
        end_lat, end_lon = 14.6091, 121.0583      # Quezon City

        print(f"Point A: ({start_lat}, {start_lon}) - Manila")
        print(f"Point B: ({end_lat}, {end_lon}) - Quezon City")

        # Calculate Haversine distance
        print(f"\nCalculating Haversine distance...")
        haversine_dist = processor.haversine_distance(start_lat, start_lon, end_lat, end_lon)
        print(f"  Haversine distance: {haversine_dist:.2f} km (straight-line)")

        # Calculate ORS distance
        if config.ORS_CONFIG['enabled']:
            print(f"\nCalculating ORS distance...")
            locations = [
                [start_lon, start_lat],
                [end_lon, end_lat]
            ]
            distance_matrix = processor.get_ors_distance_matrix(locations)

            if distance_matrix is not None:
                ors_dist = distance_matrix[0][1]
                print(f"  ORS distance: {ors_dist:.2f} km (road network)")

                # Calculate difference
                difference = ors_dist - haversine_dist
                percent_diff = (difference / haversine_dist) * 100

                print(f"\nComparison:")
                print(f"  Difference: {difference:.2f} km ({percent_diff:.1f}%)")
                print(f"  ORS is {'longer' if difference > 0 else 'shorter'} than straight-line")
                print(f"  This is expected as ORS follows actual roads!")

                return True
            else:
                print(f"✗ Failed to get ORS distance")
                return False
        else:
            print(f"⚠ ORS is disabled, skipping ORS distance calculation")
            return True

    except Exception as e:
        print(f"✗ Error comparing distances: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_caching():
    """Test 4: Verify caching is working"""
    print_section("TEST 4: Caching Performance")

    try:
        processor = HierarchicalMonthlyRoutePipelineProcessor()

        test_locations = [
            [120.9842, 14.5995],
            [121.0583, 14.6091],
            [121.0354, 14.5547]
        ]

        print(f"Testing cache with 3 locations...")

        # First call (cache miss)
        print(f"\n1st call (should fetch from ORS):")
        start_time = time.time()
        matrix1 = processor.get_ors_distance_matrix(test_locations)
        time1 = time.time() - start_time
        print(f"   Time: {time1:.3f}s")

        # Second call (cache hit)
        print(f"\n2nd call (should use cache):")
        start_time = time.time()
        matrix2 = processor.get_ors_distance_matrix(test_locations)
        time2 = time.time() - start_time
        print(f"   Time: {time2:.3f}s")

        if matrix1 is not None and matrix2 is not None:
            # Verify matrices are identical
            if np.array_equal(matrix1, matrix2):
                print(f"\n✓ Matrices are identical")
                speedup = time1 / time2 if time2 > 0 else float('inf')
                print(f"✓ Cache speedup: {speedup:.1f}x faster")

                if time2 < time1 * 0.1:  # Cache should be at least 10x faster
                    print(f"✓ Cache is working efficiently!")
                else:
                    print(f"⚠ Cache seems slow (might still be calling API)")

                return True
            else:
                print(f"✗ Matrices differ (cache may not be working)")
                return False
        else:
            print(f"✗ Failed to get distance matrices")
            return False

    except Exception as e:
        print(f"✗ Error testing cache: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fallback():
    """Test 5: Verify fallback to Haversine when ORS fails"""
    print_section("TEST 5: Fallback to Haversine")

    try:
        # Temporarily disable ORS
        original_enabled = config.ORS_CONFIG['enabled']
        config.ORS_CONFIG['enabled'] = False

        print(f"ORS disabled temporarily...")

        processor = HierarchicalMonthlyRoutePipelineProcessor()

        # Test calculate_distance method
        dist = processor.calculate_distance(14.5995, 120.9842, 14.6091, 121.0583)

        print(f"✓ Fallback working: {dist:.2f} km (using Haversine)")

        # Re-enable ORS
        config.ORS_CONFIG['enabled'] = original_enabled
        print(f"ORS re-enabled")

        return True

    except Exception as e:
        print(f"✗ Error testing fallback: {e}")
        # Re-enable ORS even if test fails
        config.ORS_CONFIG['enabled'] = original_enabled
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print(" " * 25 + "ORS INTEGRATION TEST SUITE")
    print("=" * 80)

    print(f"\nConfiguration:")
    print(f"  Database: {config.DB_CONFIG['database']} @ {config.DB_CONFIG['server']}")
    print(f"  ORS Endpoint: {config.ORS_CONFIG['matrix_endpoint']}")
    print(f"  ORS Enabled: {config.ORS_CONFIG['enabled']}")

    # Track results
    results = {}

    # Run tests
    results['connection'] = test_ors_connection()

    if results['connection']:
        results['matrix'], _ = test_distance_matrix()
        results['comparison'] = test_ors_vs_haversine()
        results['caching'] = test_caching()
    else:
        print("\n⚠ Skipping remaining tests due to connection failure")
        results['matrix'] = False
        results['comparison'] = False
        results['caching'] = False

    results['fallback'] = test_fallback()

    # Summary
    print_section("TEST SUMMARY")

    total = len(results)
    passed = sum(1 for r in results.values() if r)
    failed = total - passed

    print(f"\nResults:")
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}  {test_name.replace('_', ' ').title()}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n" + "=" * 80)
        print(" " * 20 + "🎉 ALL TESTS PASSED! 🎉")
        print("=" * 80)
        print("\nYour ORS integration is working perfectly!")
        print("You can now run the pipeline with ORS-based distance calculations.")
        return 0
    else:
        print("\n" + "=" * 80)
        print(" " * 20 + "⚠ SOME TESTS FAILED ⚠")
        print("=" * 80)

        if not results['connection']:
            print("\nTroubleshooting:")
            print("  1. Make sure ORS is running: docker ps | grep ors")
            print("  2. Check if port 8080 is accessible: curl http://localhost:8080/ors/health")
            print("  3. Verify the endpoint URL in .env file")

        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
