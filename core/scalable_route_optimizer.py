#!/usr/bin/env python3
"""
Scalable Route Optimizer - Optimized for 5.8L prospects + 1.8L customers
Includes geographic filtering, caching, and performance optimizations
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt, degrees
from enhanced_route_optimizer import EnhancedRouteOptimizer

class ScalableRouteOptimizer(EnhancedRouteOptimizer):
    def __init__(self, cache_size=1000):
        super().__init__()
        self.prospect_cache = {}
        self.barangay_cache = {}
        self.cache_size = cache_size

    def calculate_bounding_box(self, center_lat, center_lon, radius_km=25):
        """Calculate bounding box for geographic filtering"""
        # Approximate conversion: 1 degree ≈ 111 km
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * cos(radians(center_lat)))

        return {
            'min_lat': center_lat - lat_delta,
            'max_lat': center_lat + lat_delta,
            'min_lon': center_lon - lon_delta,
            'max_lon': center_lon + lon_delta
        }

    def get_prospects_with_bounding_box(self, center_lat, center_lon, customer_barangay_codes, needed_count, radius_km=25):
        """Get prospects using geographic bounding box for performance"""

        # Step 1: Try same barangay first (with bounding box)
        bbox = self.calculate_bounding_box(center_lat, center_lon, radius_km)

        print(f"  Using bounding box: {bbox['min_lat']:.3f} to {bbox['max_lat']:.3f} lat, {bbox['min_lon']:.3f} to {bbox['max_lon']:.3f} lon")

        # Check cache first
        cache_key = f"{center_lat:.3f}_{center_lon:.3f}_{radius_km}"
        if cache_key in self.prospect_cache:
            print(f"  Using cached prospects for area")
            prospects = self.prospect_cache[cache_key]
        else:
            # Same barangay_code prospects within bounding box
            # Match: routedata.barangay_code = prospective.barangay_code
            if customer_barangay_codes:
                barangay_code_list = "', '".join(customer_barangay_codes)

                same_barangay_query = f"""
                SELECT TOP 1000 CustNo, Latitude, Longitude, Barangay, barangay_code, Custype
                FROM prospective
                WHERE Latitude BETWEEN {bbox['min_lat']} AND {bbox['max_lat']}
                AND Longitude BETWEEN {bbox['min_lon']} AND {bbox['max_lon']}
                AND Latitude IS NOT NULL
                AND Longitude IS NOT NULL
                AND Latitude != 0
                AND Longitude != 0
                AND barangay_code IN ('{barangay_code_list}')
                ORDER BY (Latitude - {center_lat})*(Latitude - {center_lat}) + (Longitude - {center_lon})*(Longitude - {center_lon})
                """

                prospects = self.db.execute_query_df(same_barangay_query)

                if prospects is not None and not prospects.empty:
                    print(f"  Found {len(prospects)} prospects in same barangay_code (within {radius_km}km)")
                else:
                    prospects = pd.DataFrame()
            else:
                prospects = pd.DataFrame()

            # Step 2: Fallback to any barangay within bounding box
            if prospects.empty or len(prospects) < needed_count:
                print(f"  Falling back to nearby prospects (any barangay) within {radius_km}km...")

                # Get used prospects to exclude
                used_prospects = self.get_used_prospects()
                exclusion_condition = ""

                if used_prospects:
                    used_list = "', '".join(used_prospects)
                    exclusion_condition = f"AND CustNo NOT IN ('{used_list}')"

                fallback_query = f"""
                SELECT TOP 2000 CustNo, Latitude, Longitude, Barangay, barangay_code, Custype
                FROM prospective
                WHERE Latitude BETWEEN {bbox['min_lat']} AND {bbox['max_lat']}
                AND Longitude BETWEEN {bbox['min_lon']} AND {bbox['max_lon']}
                AND Latitude IS NOT NULL
                AND Longitude IS NOT NULL
                AND Latitude != 0
                AND Longitude != 0
                {exclusion_condition}
                ORDER BY (Latitude - {center_lat})*(Latitude - {center_lat}) + (Longitude - {center_lon})*(Longitude - {center_lon})
                """

                fallback_prospects = self.db.execute_query_df(fallback_query)

                if fallback_prospects is not None and not fallback_prospects.empty:
                    print(f"  Found {len(fallback_prospects)} fallback prospects within {radius_km}km")
                    prospects = pd.concat([prospects, fallback_prospects], ignore_index=True).drop_duplicates(subset=['CustNo'])
                else:
                    print(f"  No prospects found within {radius_km}km, expanding search...")
                    # Try larger radius
                    return self.get_prospects_with_bounding_box(center_lat, center_lon, customer_barangay_codes, needed_count, radius_km * 2)

            # Cache the results
            if len(self.prospect_cache) < self.cache_size:
                self.prospect_cache[cache_key] = prospects

        if prospects.empty:
            print(f"  No prospects found")
            return pd.DataFrame()

        # Step 3: Calculate precise distances and select nearest
        prospects['distance_from_centroid'] = prospects.apply(
            lambda row: self.haversine_distance(
                center_lat, center_lon, row['Latitude'], row['Longitude']
            ), axis=1
        )

        # Select nearest prospects
        nearest_prospects = prospects.nsmallest(needed_count, 'distance_from_centroid')

        print(f"  Selected {len(nearest_prospects)} nearest prospects")
        if not nearest_prospects.empty:
            print(f"  Distance range: {nearest_prospects['distance_from_centroid'].min():.2f} - {nearest_prospects['distance_from_centroid'].max():.2f} km")

        return nearest_prospects

    def get_barangay_prospects_2step_optimized(self, customers_with_coords, customers_without_coords, needed_count=15):
        """Optimized 2-step prospect selection with bounding box filtering"""

        if customers_with_coords.empty:
            return pd.DataFrame()

        # Step 1: Calculate centroid
        centroid_lat = customers_with_coords['latitude'].mean()
        centroid_lon = customers_with_coords['longitude'].mean()

        print(f"  Centroid calculated: Lat {centroid_lat:.4f}, Lon {centroid_lon:.4f}")

        # Get unique barangay_codes from customer barangay_code field
        existing_barangay_codes = set()
        for _, customer in customers_with_coords.iterrows():
            if pd.notna(customer.get('barangay_code')):
                existing_barangay_codes.add(customer['barangay_code'])

        for _, customer in customers_without_coords.iterrows():
            if pd.notna(customer.get('barangay_code')):
                existing_barangay_codes.add(customer['barangay_code'])

        if existing_barangay_codes:
            print(f"  Looking for prospects in barangay_codes: {list(existing_barangay_codes)[:5]}...")
        else:
            existing_barangay_codes = None

        # Step 2: Use optimized prospect selection with bounding box
        return self.get_prospects_with_bounding_box(
            centroid_lat, centroid_lon, existing_barangay_codes, needed_count
        )

    def process_sales_agent_optimized(self, sales_agent):
        """Optimized processing for single sales agent"""
        print(f"Processing sales agent: {sales_agent}")

        # Get customer counts by date
        date_counts = self.get_customer_count_by_date(sales_agent)

        if date_counts is None or date_counts.empty:
            print(f"No data found for sales agent: {sales_agent}")
            return

        results = []
        processed_dates = 0

        for _, row in date_counts.iterrows():
            route_date = row['RouteDate']
            customer_count = row['customer_count']

            print(f"  Processing date: {route_date}, Count: {customer_count}")

            # Skip if count > 60
            if customer_count > 60:
                print(f"    Skipping - count ({customer_count}) > 60")
                continue

            # Get existing customers for this date
            existing_customers = self.get_customers_for_agent_date(sales_agent, route_date)

            if existing_customers is None or existing_customers.empty:
                continue

            # Separate customers with and without coordinates
            customers_with_coords = existing_customers[
                (existing_customers['latitude'].notna()) &
                (existing_customers['longitude'].notna()) &
                (existing_customers['latitude'] != 0) &
                (existing_customers['longitude'] != 0)
            ].copy()

            customers_without_coords = existing_customers[
                (existing_customers['latitude'].isna()) |
                (existing_customers['longitude'].isna()) |
                (existing_customers['latitude'] == 0) |
                (existing_customers['longitude'] == 0)
            ].copy()

            print(f"    Customers with coords: {len(customers_with_coords)}")
            print(f"    Customers without coords: {len(customers_without_coords)}")

            # Get prospects if needed (target 60 total)
            nearby_prospects = pd.DataFrame()
            if customer_count < 60:
                needed_prospects = 60 - customer_count
                print(f"    Need {needed_prospects} prospects to reach 60")

                if not customers_with_coords.empty:
                    nearby_prospects = self.get_barangay_prospects_2step_optimized(
                        customers_with_coords, customers_without_coords, needed_prospects
                    )

            # Classify customer types
            existing_customers, nearby_prospects = self.classify_customer_type(
                existing_customers, nearby_prospects
            )

            # Update the separated dataframes with the classification
            customers_with_coords = existing_customers[
                (existing_customers['latitude'].notna()) &
                (existing_customers['longitude'].notna()) &
                (existing_customers['latitude'] != 0) &
                (existing_customers['longitude'] != 0)
            ].copy()

            customers_without_coords = existing_customers[
                (existing_customers['latitude'].isna()) |
                (existing_customers['longitude'].isna()) |
                (existing_customers['latitude'] == 0) |
                (existing_customers['longitude'] == 0)
            ].copy()

            # Process customers without coordinates - assign stopno = 100
            customers_without_coords['stopno'] = 100

            # Combine customers with coordinates and prospects for TSP
            customers_for_tsp = pd.concat([customers_with_coords, nearby_prospects], ignore_index=True)

            # Run TSP on locations with coordinates
            if not customers_for_tsp.empty:
                optimized_route = self.solve_tsp_nearest_neighbor(customers_for_tsp)
                print(f"    TSP optimized {len(optimized_route)} locations")
            else:
                optimized_route = pd.DataFrame()

            # Combine all results
            final_route = pd.concat([optimized_route, customers_without_coords], ignore_index=True)

            print(f"    Final route: {len(final_route)} total stops")

            # Count by type
            with_coords_count = len(optimized_route) if not optimized_route.empty else 0
            without_coords_count = len(customers_without_coords)
            prospects_count = len(nearby_prospects) if not nearby_prospects.empty else 0

            print(f"      - With coordinates: {with_coords_count}")
            print(f"      - Without coordinates: {without_coords_count}")
            print(f"      - Prospects: {prospects_count}")

            # Prepare data for routeplan_ai table
            for _, customer in final_route.iterrows():
                # Get custype with proper fallback
                custype_value = customer.get('final_custype')
                if pd.isna(custype_value) or custype_value is None:
                    custype_value = customer.get('custype', 'customer')
                if pd.isna(custype_value) or custype_value is None:
                    custype_value = 'customer'  # Default fallback

                # Handle data type conversions
                latitude = customer.get('latitude', customer.get('Latitude'))
                longitude = customer.get('longitude', customer.get('Longitude'))
                stopno = customer.get('stopno', 1)

                try:
                    latitude = float(latitude) if pd.notna(latitude) else None
                    longitude = float(longitude) if pd.notna(longitude) else None
                    stopno = int(stopno) if pd.notna(stopno) else 1
                except (ValueError, TypeError):
                    latitude = longitude = None
                    stopno = 1

                route_data = {
                    'salesagent': str(sales_agent),
                    'custno': str(customer.get('CustNo', '')),
                    'custype': str(custype_value),
                    'latitude': latitude,
                    'longitude': longitude,
                    'stopno': stopno,
                    'routedate': route_date,
                    'barangay': str(customer.get('barangay_code', customer.get('Barangay', ''))),
                    'barangay_code': str(customer.get('barangay_code', customer.get('barangay_code', ''))),
                    'is_visited': 0
                }
                results.append(route_data)

            processed_dates += 1

        # Insert results into routeplan_ai table
        if results:
            self.insert_route_plan(results)
            print(f"Inserted {len(results)} records for {sales_agent} ({processed_dates} dates)")

    def run_optimized_pipeline(self):
        """Run the optimized pipeline for large datasets"""
        print("Starting Optimized Route Optimization Pipeline...")
        print("Optimizations: Geographic filtering, caching, bounding box queries")

        # Get all sales agents
        sales_agents = self.get_sales_agents()

        if not sales_agents:
            print("No sales agents found!")
            return

        print(f"Found {len(sales_agents)} sales agents")

        # Process each sales agent
        processed_count = 0
        for agent in sales_agents:
            try:
                print(f"\n{'='*60}")
                print(f"Processing {processed_count + 1}/{len(sales_agents)}: {agent}")
                print(f"{'='*60}")

                self.process_sales_agent_optimized(agent)
                processed_count += 1

                # Clear cache periodically to manage memory
                if processed_count % 10 == 0:
                    self.prospect_cache.clear()
                    print(f"Cache cleared after {processed_count} agents")

            except Exception as e:
                print(f"Error processing {agent}: {e}")
                continue

        print(f"\nOptimized Pipeline completed!")
        print(f"Processed {processed_count} sales agents successfully")

if __name__ == "__main__":
    optimizer = ScalableRouteOptimizer()
    try:
        optimizer.run_optimized_pipeline()
    finally:
        optimizer.close()