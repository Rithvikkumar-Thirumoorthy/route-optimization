import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt
from itertools import permutations
from database import DatabaseConnection

class RouteOptimizer:
    def __init__(self):
        self.db = DatabaseConnection()
        self.db.connect()

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

    def get_nearby_prospects(self, existing_customers, target_count=60):
        """Get nearby prospects to fill up to target count"""
        if existing_customers.empty:
            return pd.DataFrame()

        # Calculate center point of existing customers
        avg_lat = existing_customers['latitude'].mean()
        avg_lon = existing_customers['longitude'].mean()

        # Get prospects within reasonable distance
        query = """
        SELECT CustNo, Latitude, Longitude, Barangay, Barangay_code, Custype
        FROM prospective
        WHERE Active = 1
        AND Latitude IS NOT NULL
        AND Longitude IS NOT NULL
        AND CustNo NOT IN ({})
        """.format(','.join(['?' for _ in existing_customers['CustNo']]))

        prospects = self.db.execute_query_df(query, params=existing_customers['CustNo'].tolist())

        if prospects.empty:
            return pd.DataFrame()

        # Calculate distances and sort by nearest
        prospects['distance'] = prospects.apply(
            lambda row: self.haversine_distance(avg_lat, avg_lon, row['Latitude'], row['Longitude']),
            axis=1
        )

        # Get the number needed to reach target count
        needed_count = target_count - len(existing_customers)
        return prospects.nsmallest(needed_count, 'distance')

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

        # Filter locations with valid coordinates
        valid_locations = locations_df[
            (locations_df['latitude'].notna()) &
            (locations_df['longitude'].notna()) &
            (locations_df['latitude'] != 0) &
            (locations_df['longitude'] != 0)
        ].copy()

        if len(valid_locations) == 0:
            return locations_df

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
        """Process all dates for a specific sales agent"""
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

            # Get nearby prospects if needed
            nearby_prospects = pd.DataFrame()
            if customer_count < 60:
                nearby_prospects = self.get_nearby_prospects(existing_customers, 60)

            # Classify customer types
            existing_customers, nearby_prospects = self.classify_customer_type(
                existing_customers, nearby_prospects
            )

            # Separate locations with and without coordinates
            all_customers = pd.concat([existing_customers, nearby_prospects], ignore_index=True)

            # Locations without coordinates get stopno = 100
            no_coords = all_customers[
                (all_customers['latitude'].isna()) |
                (all_customers['longitude'].isna()) |
                (all_customers['latitude'] == 0) |
                (all_customers['longitude'] == 0)
            ].copy()
            no_coords['stopno'] = 100

            # Locations with coordinates get optimized route
            with_coords = all_customers[
                (all_customers['latitude'].notna()) &
                (all_customers['longitude'].notna()) &
                (all_customers['latitude'] != 0) &
                (all_customers['longitude'] != 0)
            ].copy()

            if not with_coords.empty:
                optimized_route = self.solve_tsp_nearest_neighbor(with_coords)
            else:
                optimized_route = pd.DataFrame()

            # Combine results
            final_route = pd.concat([optimized_route, no_coords], ignore_index=True)

            # Prepare data for routeplan_ai table
            for _, customer in final_route.iterrows():
                route_data = {
                    'salesagent': sales_agent,
                    'custno': customer.get('CustNo'),
                    'custype': customer.get('final_custype', customer.get('custype')),
                    'latitude': customer.get('latitude', customer.get('Latitude')),
                    'longitude': customer.get('longitude', customer.get('Longitude')),
                    'stopno': customer.get('stopno', 1),
                    'routedate': route_date,
                    'barangay': customer.get('barangay_code', customer.get('Barangay')),
                    'barangay_code': customer.get('barangay_code', customer.get('Barangay_code')),
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
        """Run the complete route optimization pipeline"""
        print("Starting Route Optimization Pipeline...")

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

        print("Pipeline completed!")

    def close(self):
        """Close database connection"""
        self.db.close()