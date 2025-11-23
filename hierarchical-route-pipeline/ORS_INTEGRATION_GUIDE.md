# ORS Integration Guide

This guide explains how to test and use the OpenRouteService (ORS) API integration for accurate road-based distance calculations.

## Overview

The pipeline now supports **two distance calculation modes**:

1. **ORS Matrix API** (Recommended) - Uses actual road network distances
2. **Haversine Distance** (Fallback) - Uses straight-line distance

## Quick Start

### 1. Make Sure ORS is Running

Your ORS service should be running at `http://localhost:8080`

Check if it's running:
```bash
curl http://localhost:8080/ors/health
```

If using Docker:
```bash
docker ps | grep ors
```

### 2. Run the Test Suite

```bash
cd hierarchical-route-pipeline
python test_ors_integration.py
```

The test suite will verify:
- ✓ ORS API connection
- ✓ Distance matrix calculation
- ✓ ORS vs Haversine comparison
- ✓ Caching performance
- ✓ Fallback mechanism

### 3. Review Test Results

**Expected Output (Success):**
```
==============================================================================
                         ORS INTEGRATION TEST SUITE
==============================================================================

TEST 1: ORS API Connection
✓ ORS API is working!
  Distance matrix shape: 2x2
  Point 0 → Point 1: 12.34 km

TEST 2: Distance Matrix Calculation
✓ Matrix retrieved successfully in 0.52s
  Matrix shape: (5, 5)

... (additional tests)

==============================================================================
                        🎉 ALL TESTS PASSED! 🎉
==============================================================================
```

## Configuration

### Environment Variables (.env)

```env
# ORS Configuration
ORS_MATRIX_ENDPOINT=http://localhost:8080/ors/v2/matrix/driving-car
ORS_ENABLED=True
ORS_TIMEOUT=30
```

### Config Options (config.py)

```python
ORS_CONFIG = {
    'enabled': True,                    # Enable/disable ORS
    'matrix_endpoint': 'http://...',    # ORS endpoint URL
    'timeout': 30,                      # Request timeout (seconds)
    'use_cache': True,                  # Cache API responses
    'fallback_to_haversine': True,      # Use Haversine if ORS fails
}
```

## How It Works

### Distance Matrix Structure

For a route with **N customers** and **1 distributor starting point**:

```
Matrix Size: (N+1) × (N+1)

       [0]    [1]    [2]    [3]    ... [N]
[0]    0.0    d01    d02    d03    ... d0N   ← Distributor (start)
[1]    d10    0.0    d12    d13    ... d1N   ← Customer 1
[2]    d20    d21    0.0    d23    ... d2N   ← Customer 2
[3]    d30    d31    d32    0.0    ... d3N   ← Customer 3
...
[N]    dN0    dN1    dN2    dN3    ... 0.0   ← Customer N
```

- **Index [0]**: Distributor/starting location
- **Indices [1..N]**: Customer locations
- **d_ij**: Road distance from location i to location j (in km)

### TSP Optimization Flow

```
1. Build location list: [distributor, customer1, customer2, ..., customerN]
2. Call ORS Matrix API → Get (N+1)×(N+1) distance matrix
3. Find nearest customer to distributor (row 0, columns 1..N)
4. Use nearest-neighbor algorithm with matrix for route optimization
5. Return optimized route with stop numbers
```

### Caching Mechanism

- **Cache Key**: MD5 hash of location coordinates
- **Thread-Safe**: Uses locks for parallel processing
- **Automatic**: Transparent caching, no manual management needed
- **Performance**: ~10-100x faster for repeated queries

## Performance Comparison

### Example: 50-Customer Route

| Method | API Calls | Total Requests | Time |
|--------|-----------|----------------|------|
| **Haversine** | None | 0 | ~0.05s |
| **ORS (No Cache)** | 1 | 1 matrix call | ~0.5s |
| **ORS (Cached)** | 0 | 0 | ~0.001s |

### Distance Accuracy

```
Example: Manila City Hall → Quezon City Hall

Haversine:  8.24 km (straight-line) ❌
ORS:       12.34 km (road network) ✓ More accurate!

Difference: +49.8% (ORS accounts for actual roads)
```

## Troubleshooting

### Test Fails: "Cannot connect to ORS API"

**Problem**: ORS service not running

**Solutions**:
```bash
# Check if ORS is running
curl http://localhost:8080/ors/health

# If using Docker, start ORS
docker start ors-app

# Check ORS logs
docker logs ors-app
```

### Test Fails: "ORS API returned HTTP 400"

**Problem**: Invalid request format

**Check**:
- Coordinates are in valid range (lat: -90 to 90, lon: -180 to 180)
- Locations are in [longitude, latitude] order (ORS format)
- No null or NaN values in coordinates

### Pipeline Uses Haversine Instead of ORS

**Problem**: ORS disabled or fallback triggered

**Check**:
1. Verify `ORS_ENABLED=True` in .env
2. Check ORS service is accessible
3. Review logs for "falling back to Haversine" warnings
4. Run test suite to diagnose issue

### Slow Performance

**Problem**: Cache not working or too many unique routes

**Solutions**:
- Verify `use_cache: True` in config.py
- Check cache hit rate in logs
- Consider increasing ORS timeout if network is slow
- Use parallel processing: `--parallel --max-workers 4`

## Running the Pipeline with ORS

### Basic Usage

```bash
# Use ORS for all distance calculations (default)
python run_pipeline.py

# Parallel processing with ORS (RECOMMENDED)
python run_pipeline.py --parallel --max-workers 4
```

### Disable ORS Temporarily

```bash
# Option 1: Set in .env
ORS_ENABLED=False

# Option 2: Edit config.py
ORS_CONFIG['enabled'] = False
```

### Monitor ORS Usage

Check logs for ORS-related messages:
```
INFO - Calling ORS Matrix API for 51 locations...
INFO - ORS Matrix API success: (51, 51) matrix retrieved
INFO - ORS Matrix cache hit for 51 locations
```

## Advanced Configuration

### Custom ORS Profile

To use a different routing profile (e.g., truck, bike):

```env
# In .env
ORS_MATRIX_ENDPOINT=http://localhost:8080/ors/v2/matrix/driving-hgv
```

Available profiles:
- `driving-car` (default) - Standard car routing
- `driving-hgv` - Heavy goods vehicle
- `foot-walking` - Pedestrian routing
- `cycling-regular` - Bicycle routing

### Increase Timeout for Large Matrices

For routes with 100+ customers:

```env
# In .env
ORS_TIMEOUT=60
```

### Disable Caching

For testing or if caching causes issues:

```python
# In config.py
ORS_CONFIG['use_cache'] = False
```

## Support

If you encounter issues:

1. Run the test suite: `python test_ors_integration.py`
2. Check ORS service health: `curl http://localhost:8080/ors/health`
3. Review pipeline logs in `logs/` directory
4. Verify .env configuration matches your ORS setup

## Benefits of ORS Integration

✅ **Accuracy**: Real road distances vs straight-line
✅ **Efficiency**: Single API call for entire route
✅ **Reliability**: Automatic fallback to Haversine
✅ **Performance**: Built-in caching for repeated queries
✅ **Flexibility**: Easy to enable/disable via configuration

## Next Steps

After successful testing:

1. ✓ ORS integration tested and working
2. → Run pipeline on test data: `python run_pipeline.py --test-mode`
3. → Run full pipeline: `python run_pipeline.py --parallel --max-workers 4`
4. → Monitor performance and adjust settings as needed
