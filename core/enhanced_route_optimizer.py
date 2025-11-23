import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt
from itertools import permutations
from database import DatabaseConnection

class EnhancedRouteOptimizer:
    def __init__(self):
        self.db = DatabaseConnection()
        self.db.connect()
        self.used_prospects = set()  # Track used prospects to avoid repetition

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate the great circle distance between two points on Earth"""
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Radius of earth in kilometers
        return c * r

    def get_sales_agents(self):
        """Get all unique sales agents from routedata"""
        query = """
        SELECT DISTINCT SalesManTerritory
        FROM routedata
        WHERE SalesManTerritory IS NOT NULL
        AND SalesManTerritory != ''
        """
        result = self.db.execute_query_df(query)
        return result['SalesManTerritory'].tolist() if result is not None else []

    def get_customer_count_by_date(self, sales_agent):
        """Get customer count for each date for a sales agent"""
        query = """
        SELECT RouteDate, COUNT(DISTINCT CustNo) as customer_count
        FROM routedata
        WHERE SalesManTerritory = ?
        AND RouteDate IS NOT NULL
        GROUP BY RouteDate
        ORDER BY RouteDate
        """
        return self.db.execute_query_df(query, params=[sales_agent])

    def get_customers_for_agent_date(self, sales_agent, route_date):
        """Get customers for a specific sales agent and date"""
        query = """
        SELECT r.CustNo, r.latitude, r.longitude, r.barangay_code, r.custype, r.Name
        FROM routedata r
        WHERE r.SalesManTerritory = ? AND r.RouteDate = ?
        AND r.CustNo IS NOT NULL
        """
        return self.db.execute_query_df(query, params=[sales_agent, route_date])

    def get_used_prospects(self):
        """Get list of prospects that have already been assigned to routes"""
        query = """
        SELECT DISTINCT custno
        FROM routeplan_ai
        WHERE custype = 'prospect'
        """
        result = self.db.execute_query_df(query)
        return set(result['custno'].tolist()) if result is not None and not result.empty else set()

    def get_barangay_prospects_2step(self, customers_with_coords, customers_without_coords, needed_count=15):
        """
        2-step process to get prospects:
        1. Get centroid of customers with coordinates
        2. Find prospects in same barangay based on barangay_code matching barangay_code
        3. Calculate haversine distance from centroid
        4. Select nearest prospects
        """
        if customers_with_coords.empty:
            return pd.DataFrame()

        # Step 1: Calculate centroid of customers with coordinates
        centroid_lat = customers_with_coords['latitude'].mean()
        centroid_lon = customers_with_coords['longitude'].mean()

        print(f"  Centroid calculated: Lat {centroid_lat:.4f}, Lon {centroid_lon:.4f}")

        # Get unique barangay_codes from existing customers (barangay_code)
        existing_barangay_codes = set()
        for _, customer in customers_with_coords.iterrows():
            if pd.notna(customer.get('barangay_code')):
                existing_barangay_codes.add(customer['barangay_code'])

        for _, customer in customers_without_coords.iterrows():
            if pd.notna(customer.get('barangay_code')):
                existing_barangay_codes.add(customer['barangay_code'])

        if not existing_barangay_codes:
            print("  No barangay_codes found in existing customers")
            return pd.DataFrame()

        print(f"  Looking for prospects in barangay_codes: {list(existing_barangay_codes)[:5]}...")

        # Get current used prospects to avoid repetition
        used_prospects = self.get_used_prospects()

        # Step 2: Get prospects from same barangay_codes (barangay_code = barangay_code)
        barangay_code_placeholders = ','.join(['?' for _ in existing_barangay_codes])

        exclusion_condition = ""
        query_params = list(existing_barangay_codes)

        if used_prospects:
            exclusion_placeholders = ','.join(['?' for _ in used_prospects])
            exclusion_condition = f"AND CustNo NOT IN ({exclusion_placeholders})"
            query_params.extend(list(used_prospects))

        query = f"""
        SELECT CustNo, Latitude, Longitude, Barangay, barangay_code, Custype
        FROM prospective
        WHERE Latitude IS NOT NULL
        AND Longitude IS NOT NULL
        AND Latitude != 0
        AND Longitude != 0
        AND barangay_code IN ({barangay_code_placeholders})
        {exclusion_condition}
        """

        prospects = self.db.execute_query_df(query, params=query_params)

        if prospects is None or prospects.empty:
            print("  No prospects found in same barangay_codes")
            print("  Falling back to nearby prospects regardless of barangay_code...")

            # Fallback: Get prospects regardless of barangay_code, based purely on distance
            fallback_query_params = []
            fallback_exclusion_condition = ""

            if used_prospects:
                fallback_exclusion_placeholders = ','.join(['?' for _ in used_prospects])
                fallback_exclusion_condition = f"AND CustNo NOT IN ({fallback_exclusion_placeholders})"
                fallback_query_params.extend(list(used_prospects))

            fallback_query = f"""
            SELECT CustNo, Latitude, Longitude, Barangay, barangay_code, Custype
            FROM prospective
            WHERE Latitude IS NOT NULL
            AND Longitude IS NOT NULL
            AND Latitude != 0
            AND Longitude != 0
            {fallback_exclusion_condition}
            """

            prospects = self.db.execute_query_df(fallback_query, params=fallback_query_params)

            if prospects is None or prospects.empty:
                print("  No prospects found anywhere")
                return pd.DataFrame()

            print(f"  Found {len(prospects)} prospects regardless of barangay_code")

        else:
            print(f"  Found {len(prospects)} prospects in same barangay_codes")

        # Step 3: Calculate haversine distance from centroid
        prospects['distance_from_centroid'] = prospects.apply(
            lambda row: self.haversine_distance(
                centroid_lat, centroid_lon, row['Latitude'], row['Longitude']
            ), axis=1
        )

        # Step 4: Select nearest prospects up to needed count
        nearest_prospects = prospects.nsmallest(needed_count, 'distance_from_centroid')

        print(f"  Selected {len(nearest_prospects)} nearest prospects")
        if not nearest_prospects.empty:
            print(f"  Distance range: {nearest_prospects['distance_from_centroid'].min():.2f} - {nearest_prospects['distance_from_centroid'].max():.2f} km")

        return nearest_prospects

    def classify_customer_type(self, customers_df, prospects_df):
        """Classify customers and prospects with appropriate custype"""
        # Mark existing customers as 'customer'
        customers_df['final_custype'] = 'customer'

        # Mark prospects as 'prospect'
        prospects_df['final_custype'] = 'prospect'

        return customers_df, prospects_df

    def solve_tsp_nearest_neighbor(self, locations_df):
        """Solve TSP using nearest neighbor heuristic for locations with lat/lon"""
        if len(locations_df) <= 1:
            return locations_df

        # Standardize column names - handle both customer (latitude/longitude) and prospect (Latitude/Longitude) formats
        standardized_df = locations_df.copy()

        # If prospects have Latitude/Longitude, rename to latitude/longitude
        if 'Latitude' in standardized_df.columns and 'latitude' not in standardized_df.columns:
            standardized_df['latitude'] = standardized_df['Latitude']
        if 'Longitude' in standardized_df.columns and 'longitude' not in standardized_df.columns:
            standardized_df['longitude'] = standardized_df['Longitude']

        # For prospects that have both, use the lowercase version and fill NaN with uppercase
        if 'Latitude' in standardized_df.columns and 'latitude' in standardized_df.columns:
            standardized_df['latitude'] = standardized_df['latitude'].fillna(standardized_df['Latitude'])
        if 'Longitude' in standardized_df.columns and 'longitude' in standardized_df.columns:
            standardized_df['longitude'] = standardized_df['longitude'].fillna(standardized_df['Longitude'])

        # Filter locations with valid coordinates
        valid_locations = standardized_df[
            (standardized_df['latitude'].notna()) &
            (standardized_df['longitude'].notna()) &
            (standardized_df['latitude'] != 0) &
            (standardized_df['longitude'] != 0)
        ].copy()

        if len(valid_locations) == 0:
            return standardized_df

        # Start from first location
        unvisited = valid_locations.copy()
        route = []
        current_idx = 0
        current_location = unvisited.iloc[current_idx]
        route.append(current_location)
        unvisited = unvisited.drop(unvisited.index[current_idx])

        # Build route using nearest neighbor
        while not unvisited.empty:
            current_lat = current_location['latitude']
            current_lon = current_location['longitude']

            # Find nearest unvisited location
            distances = unvisited.apply(
                lambda row: self.haversine_distance(
                    current_lat, current_lon, row['latitude'], row['longitude']
                ), axis=1
            )

            nearest_idx = distances.idxmin()
            current_location = unvisited.loc[nearest_idx]
            route.append(current_location)
            unvisited = unvisited.drop(nearest_idx)

        # Create result dataframe with stop numbers
        result_df = pd.DataFrame(route)
        result_df['stopno'] = range(1, len(result_df) + 1)

        return result_df

    def process_sales_agent(self, sales_agent):
        """Process all dates for a specific sales agent with enhanced 2-step logic"""
        print(f"Processing sales agent: {sales_agent}")

        # Get customer counts by date
        date_counts = self.get_customer_count_by_date(sales_agent)

        if date_counts is None or date_counts.empty:
            print(f"No data found for sales agent: {sales_agent}")
            return

        results = []

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
                    nearby_prospects = self.get_barangay_prospects_2step(
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
                # Handle data type conversions
                latitude = customer.get('latitude', customer.get('Latitude'))
                longitude = customer.get('longitude', customer.get('Longitude'))
                stopno = customer.get('stopno', 1)

                # Convert to proper types and handle NaN values
                try:
                    latitude = float(latitude) if pd.notna(latitude) else None
                except (ValueError, TypeError):
                    latitude = None

                try:
                    longitude = float(longitude) if pd.notna(longitude) else None
                except (ValueError, TypeError):
                    longitude = None

                try:
                    stopno = int(stopno) if pd.notna(stopno) else 1
                except (ValueError, TypeError):
                    stopno = 1

                # Get custype with proper fallback
                custype_value = customer.get('final_custype')
                if pd.isna(custype_value) or custype_value is None:
                    custype_value = customer.get('custype', 'customer')
                if pd.isna(custype_value) or custype_value is None:
                    custype_value = 'customer'  # Default fallback

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

        # Insert results into routeplan_ai table
        if results:
            self.insert_route_plan(results)
            print(f"Inserted {len(results)} records for {sales_agent}")

    def insert_route_plan(self, route_data):
        """Insert route plan data into routeplan_ai table"""
        insert_query = """
        INSERT INTO routeplan_ai (salesagent, custno, custype, latitude, longitude, stopno, routedate, barangay, barangay_code, is_visited)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        data_tuples = [
            (
                data['salesagent'],
                data['custno'],
                data['custype'],
                data['latitude'],
                data['longitude'],
                data['stopno'],
                data['routedate'],
                data['barangay'],
                data['barangay_code'],
                data['is_visited']
            )
            for data in route_data
        ]

        return self.db.execute_bulk_insert(insert_query, data_tuples)

    def run_pipeline(self):
        """Run the complete enhanced route optimization pipeline"""
        print("Starting Enhanced Route Optimization Pipeline...")

        # Get all sales agents
        sales_agents = self.get_sales_agents()

        if not sales_agents:
            print("No sales agents found!")
            return

        print(f"Found {len(sales_agents)} sales agents")

        # Process each sales agent
        for agent in sales_agents:
            try:
                self.process_sales_agent(agent)
            except Exception as e:
                print(f"Error processing {agent}: {e}")
                continue

        print("Enhanced Pipeline completed!")

    def close(self):
        """Close database connection"""
        self.db.close()