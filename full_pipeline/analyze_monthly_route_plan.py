#!/usr/bin/env python3
"""
MonthlyRoutePlan_temp Analysis Script
Analyzes route data and identifies reasons for routes with < 60 customers
"""

import sys
import os
import pandas as pd
from datetime import datetime
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.database import DatabaseConnection
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running from the project root directory")
    sys.exit(1)


class MonthlyRoutePlanAnalyzer:
    def __init__(self):
        """Initialize analyzer"""
        self.setup_logging()
        self.results = {}

    def setup_logging(self):
        """Setup logging configuration"""
        log_filename = f"route_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_path = os.path.join(os.path.dirname(__file__), 'logs', log_filename)

        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def run_analysis(self):
        """Run complete analysis"""
        self.logger.info("=" * 80)
        self.logger.info("STARTING MONTHLYROUTEPLAN_TEMP ANALYSIS")
        self.logger.info("=" * 80)

        db = None
        try:
            # Connect to database
            db = DatabaseConnection()
            db.connect()
            self.logger.info("Database connected successfully")

            # Run all analyses
            self.analyze_overall_stats(db)
            self.analyze_route_size_distribution(db)
            self.analyze_routes_below_60(db)
            self.analyze_why_no_prospects(db)
            self.analyze_custype_distribution(db)
            self.analyze_barangay_coverage(db)
            self.analyze_prospect_availability(db)
            self.analyze_small_route_agents(db)
            self.analyze_coordinate_coverage(db)
            self.analyze_prospect_exhaustion(db)

            # Generate summary report
            self.generate_summary_report()

            # Export to CSV
            self.export_results()

        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            import traceback
            traceback.print_exc()

        finally:
            if db:
                db.close()

    def analyze_overall_stats(self, db):
        """Analyze overall statistics"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("1. OVERALL STATISTICS")
        self.logger.info("=" * 80)

        query = """
        SELECT
            'Total Records' as Metric,
            COUNT(*) as Value
        FROM MonthlyRoutePlan_temp
        UNION ALL
        SELECT
            'Unique Distributors',
            COUNT(DISTINCT DistributorID)
        FROM MonthlyRoutePlan_temp
        UNION ALL
        SELECT
            'Unique Agents',
            COUNT(DISTINCT AgentID)
        FROM MonthlyRoutePlan_temp
        UNION ALL
        SELECT
            'Unique Dates',
            COUNT(DISTINCT RouteDate)
        FROM MonthlyRoutePlan_temp
        UNION ALL
        SELECT
            'Unique Routes (Distributor-Agent-Date)',
            COUNT(DISTINCT CONCAT(DistributorID, '-', AgentID, '-', CONVERT(VARCHAR, RouteDate, 23)))
        FROM MonthlyRoutePlan_temp
        """

        df = db.execute_query_df(query)
        self.results['overall_stats'] = df

        if df is not None and not df.empty:
            for _, row in df.iterrows():
                self.logger.info(f"  {row['Metric']:<50} {row['Value']:>10,}")
        else:
            self.logger.warning("No data found")

    def analyze_route_size_distribution(self, db):
        """Analyze route size distribution"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("2. ROUTE SIZE DISTRIBUTION")
        self.logger.info("=" * 80)

        query = """
        SELECT
            CASE
                WHEN customer_count >= 60 THEN '60+ (Target Met)'
                WHEN customer_count >= 50 THEN '50-59'
                WHEN customer_count >= 40 THEN '40-49'
                WHEN customer_count >= 30 THEN '30-39'
                WHEN customer_count >= 20 THEN '20-29'
                WHEN customer_count >= 10 THEN '10-19'
                WHEN customer_count >= 5 THEN '5-9'
                ELSE '1-4 (Very Small)'
            END as RouteSize,
            COUNT(*) as RouteCount,
            CAST(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() AS DECIMAL(5,2)) as Percentage
        FROM (
            SELECT
                DistributorID,
                AgentID,
                RouteDate,
                COUNT(*) as customer_count
            FROM MonthlyRoutePlan_temp
            GROUP BY DistributorID, AgentID, RouteDate
        ) route_counts
        GROUP BY
            CASE
                WHEN customer_count >= 60 THEN '60+ (Target Met)'
                WHEN customer_count >= 50 THEN '50-59'
                WHEN customer_count >= 40 THEN '40-49'
                WHEN customer_count >= 30 THEN '30-39'
                WHEN customer_count >= 20 THEN '20-29'
                WHEN customer_count >= 10 THEN '10-19'
                WHEN customer_count >= 5 THEN '5-9'
                ELSE '1-4 (Very Small)'
            END
        ORDER BY
            CASE
                WHEN CASE
                    WHEN customer_count >= 60 THEN '60+ (Target Met)'
                    WHEN customer_count >= 50 THEN '50-59'
                    WHEN customer_count >= 40 THEN '40-49'
                    WHEN customer_count >= 30 THEN '30-39'
                    WHEN customer_count >= 20 THEN '20-29'
                    WHEN customer_count >= 10 THEN '10-19'
                    WHEN customer_count >= 5 THEN '5-9'
                    ELSE '1-4 (Very Small)'
                END = '60+ (Target Met)' THEN 1
                WHEN CASE
                    WHEN customer_count >= 60 THEN '60+ (Target Met)'
                    WHEN customer_count >= 50 THEN '50-59'
                    WHEN customer_count >= 40 THEN '40-49'
                    WHEN customer_count >= 30 THEN '30-39'
                    WHEN customer_count >= 20 THEN '20-29'
                    WHEN customer_count >= 10 THEN '10-19'
                    WHEN customer_count >= 5 THEN '5-9'
                    ELSE '1-4 (Very Small)'
                END = '50-59' THEN 2
                WHEN CASE
                    WHEN customer_count >= 60 THEN '60+ (Target Met)'
                    WHEN customer_count >= 50 THEN '50-59'
                    WHEN customer_count >= 40 THEN '40-49'
                    WHEN customer_count >= 30 THEN '30-39'
                    WHEN customer_count >= 20 THEN '20-29'
                    WHEN customer_count >= 10 THEN '10-19'
                    WHEN customer_count >= 5 THEN '5-9'
                    ELSE '1-4 (Very Small)'
                END = '40-49' THEN 3
                WHEN CASE
                    WHEN customer_count >= 60 THEN '60+ (Target Met)'
                    WHEN customer_count >= 50 THEN '50-59'
                    WHEN customer_count >= 40 THEN '40-49'
                    WHEN customer_count >= 30 THEN '30-39'
                    WHEN customer_count >= 20 THEN '20-29'
                    WHEN customer_count >= 10 THEN '10-19'
                    WHEN customer_count >= 5 THEN '5-9'
                    ELSE '1-4 (Very Small)'
                END = '30-39' THEN 4
                WHEN CASE
                    WHEN customer_count >= 60 THEN '60+ (Target Met)'
                    WHEN customer_count >= 50 THEN '50-59'
                    WHEN customer_count >= 40 THEN '40-49'
                    WHEN customer_count >= 30 THEN '30-39'
                    WHEN customer_count >= 20 THEN '20-29'
                    WHEN customer_count >= 10 THEN '10-19'
                    WHEN customer_count >= 5 THEN '5-9'
                    ELSE '1-4 (Very Small)'
                END = '20-29' THEN 5
                WHEN CASE
                    WHEN customer_count >= 60 THEN '60+ (Target Met)'
                    WHEN customer_count >= 50 THEN '50-59'
                    WHEN customer_count >= 40 THEN '40-49'
                    WHEN customer_count >= 30 THEN '30-39'
                    WHEN customer_count >= 20 THEN '20-29'
                    WHEN customer_count >= 10 THEN '10-19'
                    WHEN customer_count >= 5 THEN '5-9'
                    ELSE '1-4 (Very Small)'
                END = '10-19' THEN 6
                WHEN CASE
                    WHEN customer_count >= 60 THEN '60+ (Target Met)'
                    WHEN customer_count >= 50 THEN '50-59'
                    WHEN customer_count >= 40 THEN '40-49'
                    WHEN customer_count >= 30 THEN '30-39'
                    WHEN customer_count >= 20 THEN '20-29'
                    WHEN customer_count >= 10 THEN '10-19'
                    WHEN customer_count >= 5 THEN '5-9'
                    ELSE '1-4 (Very Small)'
                END = '5-9' THEN 7
                ELSE 8
            END
        """

        df = db.execute_query_df(query)
        self.results['route_size_distribution'] = df

        if df is not None and not df.empty:
            self.logger.info(f"{'Route Size':<20} {'Count':>10} {'Percentage':>12}")
            self.logger.info("-" * 45)
            for _, row in df.iterrows():
                self.logger.info(f"{row['RouteSize']:<20} {row['RouteCount']:>10,} {row['Percentage']:>11.2f}%")
        else:
            self.logger.warning("No data found")

    def analyze_routes_below_60(self, db):
        """Analyze routes with < 60 customers"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("3. ROUTES WITH < 60 CUSTOMERS (Sample - Top 20)")
        self.logger.info("=" * 80)

        query = """
        SELECT TOP 20
            DistributorID,
            AgentID,
            CONVERT(VARCHAR, RouteDate, 23) as RouteDate,
            COUNT(*) as CustomerCount,
            60 - COUNT(*) as ProspectsNeeded,
            COUNT(CASE WHEN custype = 'customer' THEN 1 END) as Customers,
            COUNT(CASE WHEN custype = 'prospect' THEN 1 END) as Prospects
        FROM MonthlyRoutePlan_temp
        GROUP BY DistributorID, AgentID, RouteDate
        HAVING COUNT(*) < 60
        ORDER BY COUNT(*) ASC
        """

        df = db.execute_query_df(query)
        self.results['routes_below_60'] = df

        if df is not None and not df.empty:
            self.logger.info(f"{'Distributor':<12} {'Agent':<12} {'Date':<12} {'Total':>6} {'Need':>6} {'Cust':>6} {'Prosp':>6}")
            self.logger.info("-" * 74)
            for _, row in df.iterrows():
                self.logger.info(
                    f"{row['DistributorID']:<12} {row['AgentID']:<12} {row['RouteDate']:<12} "
                    f"{row['CustomerCount']:>6} {row['ProspectsNeeded']:>6} "
                    f"{row['Customers']:>6} {row['Prospects']:>6}"
                )
        else:
            self.logger.info("All routes have 60+ customers!")

    def analyze_why_no_prospects(self, db):
        """Analyze why prospects weren't added to routes with 0 prospects"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("3B. WHY PROSPECTS WEREN'T ADDED (Sample - Top 10 routes)")
        self.logger.info("=" * 80)

        query = """
        SELECT TOP 10
            m.DistributorID,
            m.AgentID,
            CONVERT(VARCHAR, m.RouteDate, 23) as RouteDate,
            COUNT(*) as CustomerCount,
            COUNT(CASE WHEN custype = 'prospect' THEN 1 END) as ProspectCount,

            -- Check 1: Customers with valid barangay codes
            COUNT(CASE WHEN c.address3 IS NOT NULL AND c.address3 != '' THEN 1 END) as CustomersWithBarangay,

            -- Check 2: Get barangay codes
            (SELECT TOP 1 c2.address3
             FROM MonthlyRoutePlan_temp m2
             INNER JOIN customer c2 ON m2.CustNo = c2.CustNo
             WHERE m2.DistributorID = m.DistributorID
               AND m2.AgentID = m.AgentID
               AND m2.RouteDate = m.RouteDate
               AND c2.address3 IS NOT NULL
               AND c2.address3 != '') as SampleBarangay,

            -- Check 3: Prospects available in those barangays
            (SELECT COUNT(*)
             FROM prospective p
             WHERE p.barangay_code IN (
                 SELECT DISTINCT c3.address3
                 FROM MonthlyRoutePlan_temp m3
                 INNER JOIN customer c3 ON m3.CustNo = c3.CustNo
                 WHERE m3.DistributorID = m.DistributorID
                   AND m3.AgentID = m.AgentID
                   AND m3.RouteDate = m.RouteDate
                   AND c3.address3 IS NOT NULL
                   AND c3.address3 != ''
             )
             AND p.Latitude IS NOT NULL
             AND p.Longitude IS NOT NULL
             AND p.Latitude != 0
             AND p.Longitude != 0) as TotalProspectsInBarangays,

            -- Check 4: Available prospects (not visited)
            (SELECT COUNT(*)
             FROM prospective p
             WHERE p.barangay_code IN (
                 SELECT DISTINCT c3.address3
                 FROM MonthlyRoutePlan_temp m3
                 INNER JOIN customer c3 ON m3.CustNo = c3.CustNo
                 WHERE m3.DistributorID = m.DistributorID
                   AND m3.AgentID = m.AgentID
                   AND m3.RouteDate = m.RouteDate
                   AND c3.address3 IS NOT NULL
                   AND c3.address3 != ''
             )
             AND p.Latitude IS NOT NULL
             AND p.Longitude IS NOT NULL
             AND p.Latitude != 0
             AND p.Longitude != 0
             AND NOT EXISTS (SELECT 1 FROM custvisit WHERE CustID = p.CustNo)) as AvailableProspects

        FROM MonthlyRoutePlan_temp m
        LEFT JOIN customer c ON m.CustNo = c.CustNo
        WHERE custype = 'customer' OR custype IS NULL
        GROUP BY m.DistributorID, m.AgentID, m.RouteDate
        HAVING COUNT(*) < 60 AND COUNT(CASE WHEN custype = 'prospect' THEN 1 END) = 0
        ORDER BY COUNT(*) ASC
        """

        df = db.execute_query_df(query)
        self.results['why_no_prospects'] = df

        if df is not None and not df.empty:
            self.logger.info(f"{'Dist':<6} {'Agent':<10} {'Date':<12} {'Cust':>5} {'HasBar':>7} {'TotPros':>8} {'AvailPros':>10} {'Reason'}")
            self.logger.info("-" * 90)

            for _, row in df.iterrows():
                reason = self.determine_no_prospect_reason(row)
                self.logger.info(
                    f"{row['DistributorID']:<6} {row['AgentID']:<10} {row['RouteDate']:<12} "
                    f"{row['CustomerCount']:>5} {row['CustomersWithBarangay']:>7} "
                    f"{row['TotalProspectsInBarangays']:>8} {row['AvailableProspects']:>10} {reason}"
                )

            # Summary of reasons
            self.logger.info("\n" + "-" * 90)
            self.logger.info("REASON CODES:")
            self.logger.info("  [NO_BAR]   - Customers missing barangay codes")
            self.logger.info("  [NO_PROS]  - No prospects exist in those barangays")
            self.logger.info("  [VISITED]  - All prospects already visited")
            self.logger.info("  [COORDS]   - Prospects missing valid coordinates")
            self.logger.info("  [ALREADY]  - Prospects already in MonthlyRoutePlan_temp")
        else:
            self.logger.info("All routes with < 60 customers have prospects added!")

    def determine_no_prospect_reason(self, row):
        """Determine the reason why no prospects were added"""
        if row['CustomersWithBarangay'] == 0:
            return "[NO_BAR] No barangay codes"
        elif row['TotalProspectsInBarangays'] == 0:
            return "[NO_PROS] No prospects in barangay"
        elif row['AvailableProspects'] == 0:
            return "[VISITED] All prospects visited"
        else:
            return "[ALREADY] Prospects already in plan"

    def analyze_custype_distribution(self, db):
        """Analyze custype distribution"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("4. CUSTYPE DISTRIBUTION (Customer vs Prospect)")
        self.logger.info("=" * 80)

        query = """
        SELECT
            ISNULL(custype, 'NULL') as custype,
            COUNT(*) as RecordCount,
            CAST(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() AS DECIMAL(5,2)) as Percentage
        FROM MonthlyRoutePlan_temp
        GROUP BY custype
        """

        df = db.execute_query_df(query)
        self.results['custype_distribution'] = df

        if df is not None and not df.empty:
            self.logger.info(f"{'Custype':<15} {'Count':>12} {'Percentage':>12}")
            self.logger.info("-" * 42)
            for _, row in df.iterrows():
                self.logger.info(f"{row['custype']:<15} {row['RecordCount']:>12,} {row['Percentage']:>11.2f}%")
        else:
            self.logger.warning("No data found")

    def analyze_barangay_coverage(self, db):
        """Analyze barangay code coverage"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("5. BARANGAY CODE COVERAGE ISSUES")
        self.logger.info("=" * 80)

        query = """
        SELECT
            COUNT(*) as TotalCustomerRecords,
            COUNT(CASE WHEN c.address3 IS NULL OR c.address3 = '' THEN 1 END) as MissingBarangayCode,
            CAST(COUNT(CASE WHEN c.address3 IS NULL OR c.address3 = '' THEN 1 END) * 100.0 / COUNT(*) AS DECIMAL(5,2)) as PctMissing
        FROM MonthlyRoutePlan_temp m
        LEFT JOIN customer c ON m.CustNo = c.CustNo
        WHERE m.custype = 'customer' OR m.custype IS NULL
        """

        df = db.execute_query_df(query)
        self.results['barangay_coverage'] = df

        if df is not None and not df.empty:
            row = df.iloc[0]
            total = int(row['TotalCustomerRecords'])
            missing = int(row['MissingBarangayCode'])
            pct = float(row['PctMissing'])

            self.logger.info(f"  Total Customer Records: {total:,}")
            self.logger.info(f"  Missing Barangay Code: {missing:,} ({pct:.2f}%)")

            if missing > 0:
                self.logger.warning(f"  [!] {missing:,} customers have NULL/empty barangay codes!")
                self.logger.warning("      This prevents prospect matching for those routes.")
        else:
            self.logger.warning("No data found")

    def analyze_prospect_availability(self, db):
        """Analyze prospect availability by barangay"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("6. PROSPECT AVAILABILITY BY BARANGAY (Top 10)")
        self.logger.info("=" * 80)

        query = """
        SELECT TOP 10
            c.address3 as BarangayCode,
            COUNT(DISTINCT m.AgentID) as AgentsUsingThisBarangay,
            (SELECT COUNT(*) FROM prospective WHERE barangay_code = c.address3
             AND Latitude IS NOT NULL AND Longitude IS NOT NULL
             AND Latitude != 0 AND Longitude != 0) as ProspectsWithCoords,
            (SELECT COUNT(*) FROM prospective p
             WHERE p.barangay_code = c.address3
             AND EXISTS (SELECT 1 FROM custvisit WHERE CustID = p.CustNo)) as ProspectsAlreadyVisited,
            (SELECT COUNT(*) FROM prospective p
             WHERE p.barangay_code = c.address3
             AND NOT EXISTS (SELECT 1 FROM custvisit WHERE CustID = p.CustNo)
             AND p.Latitude IS NOT NULL AND p.Longitude IS NOT NULL
             AND p.Latitude != 0 AND p.Longitude != 0) as ProspectsAvailable
        FROM MonthlyRoutePlan_temp m
        INNER JOIN customer c ON m.CustNo = c.CustNo
        WHERE c.address3 IS NOT NULL AND c.address3 != ''
        GROUP BY c.address3
        ORDER BY COUNT(DISTINCT m.AgentID) DESC
        """

        df = db.execute_query_df(query)
        self.results['prospect_availability'] = df

        if df is not None and not df.empty:
            self.logger.info(f"{'Barangay':<15} {'Agents':>7} {'Total':>7} {'Visited':>8} {'Available':>10}")
            self.logger.info("-" * 60)
            for _, row in df.iterrows():
                self.logger.info(
                    f"{row['BarangayCode']:<15} {row['AgentsUsingThisBarangay']:>7} "
                    f"{row['ProspectsWithCoords']:>7} {row['ProspectsAlreadyVisited']:>8} "
                    f"{row['ProspectsAvailable']:>10}"
                )
                if row['ProspectsAvailable'] == 0 and row['AgentsUsingThisBarangay'] > 0:
                    self.logger.warning(f"      [!] No prospects available in barangay {row['BarangayCode']}!")
        else:
            self.logger.warning("No barangay data found")

    def analyze_small_route_agents(self, db):
        """Analyze agents with consistently small routes"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("7. AGENTS WITH CONSISTENTLY SMALL ROUTES (Avg < 60)")
        self.logger.info("=" * 80)

        query = """
        SELECT TOP 20
            DistributorID,
            AgentID,
            COUNT(DISTINCT RouteDate) as TotalDates,
            CAST(AVG(CAST(customer_count AS FLOAT)) AS DECIMAL(5,1)) as AvgCustomersPerRoute,
            MIN(customer_count) as MinCustomers,
            MAX(customer_count) as MaxCustomers
        FROM (
            SELECT
                DistributorID,
                AgentID,
                RouteDate,
                COUNT(*) as customer_count
            FROM MonthlyRoutePlan_temp
            GROUP BY DistributorID, AgentID, RouteDate
        ) route_stats
        GROUP BY DistributorID, AgentID
        HAVING AVG(CAST(customer_count AS FLOAT)) < 60
        ORDER BY AVG(CAST(customer_count AS FLOAT)) ASC
        """

        df = db.execute_query_df(query)
        self.results['small_route_agents'] = df

        if df is not None and not df.empty:
            self.logger.info(f"{'Distributor':<12} {'Agent':<12} {'Dates':>6} {'Avg':>6} {'Min':>5} {'Max':>5}")
            self.logger.info("-" * 60)
            for _, row in df.iterrows():
                self.logger.info(
                    f"{row['DistributorID']:<12} {row['AgentID']:<12} {row['TotalDates']:>6} "
                    f"{row['AvgCustomersPerRoute']:>6.1f} {row['MinCustomers']:>5} {row['MaxCustomers']:>5}"
                )
        else:
            self.logger.info("All agents have average routes >= 60 customers!")

    def analyze_coordinate_coverage(self, db):
        """Analyze coordinate coverage issues"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("8. COORDINATE COVERAGE (Routes with customers missing coordinates)")
        self.logger.info("=" * 80)

        query = """
        SELECT TOP 10
            DistributorID,
            AgentID,
            CONVERT(VARCHAR, RouteDate, 23) as RouteDate,
            COUNT(*) as TotalCustomers,
            COUNT(c.Latitude) as CustomersWithCoords,
            COUNT(*) - COUNT(c.Latitude) as CustomersWithoutCoords,
            CAST((COUNT(*) - COUNT(c.Latitude)) * 100.0 / COUNT(*) AS DECIMAL(5,2)) as PctWithoutCoords
        FROM MonthlyRoutePlan_temp m
        LEFT JOIN customer c ON m.CustNo = c.CustNo
        GROUP BY DistributorID, AgentID, RouteDate
        HAVING COUNT(*) - COUNT(c.Latitude) > 0
        ORDER BY CAST((COUNT(*) - COUNT(c.Latitude)) * 100.0 / COUNT(*) AS DECIMAL(5,2)) DESC
        """

        df = db.execute_query_df(query)
        self.results['coordinate_coverage'] = df

        if df is not None and not df.empty:
            self.logger.info(f"{'Distributor':<12} {'Agent':<12} {'Date':<12} {'Total':>6} {'W/Coords':>9} {'Missing':>8} {'%':>6}")
            self.logger.info("-" * 78)
            for _, row in df.iterrows():
                self.logger.info(
                    f"{row['DistributorID']:<12} {row['AgentID']:<12} {row['RouteDate']:<12} "
                    f"{row['TotalCustomers']:>6} {row['CustomersWithCoords']:>9} "
                    f"{row['CustomersWithoutCoords']:>8} {row['PctWithoutCoords']:>5.1f}%"
                )
        else:
            self.logger.info("All customers have coordinates!")

    def analyze_prospect_exhaustion(self, db):
        """Analyze barangays with no prospects left"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("9. PROSPECT EXHAUSTION (Barangays with no available prospects)")
        self.logger.info("=" * 80)

        query = """
        SELECT TOP 15
            c.address3 as BarangayCode,
            COUNT(DISTINCT CONCAT(m.AgentID, '-', CONVERT(VARCHAR, m.RouteDate, 23))) as RoutesAffected,
            (SELECT COUNT(*) FROM prospective WHERE barangay_code = c.address3) as TotalProspects,
            (SELECT COUNT(*) FROM prospective p
             WHERE p.barangay_code = c.address3
             AND EXISTS (SELECT 1 FROM custvisit WHERE CustID = p.CustNo)) as VisitedProspects,
            (SELECT COUNT(*) FROM prospective p
             WHERE p.barangay_code = c.address3
             AND NOT EXISTS (SELECT 1 FROM custvisit WHERE CustID = p.CustNo)
             AND p.Latitude IS NOT NULL
             AND p.Longitude IS NOT NULL
             AND p.Latitude != 0
             AND p.Longitude != 0) as AvailableProspects
        FROM MonthlyRoutePlan_temp m
        INNER JOIN customer c ON m.CustNo = c.CustNo
        WHERE c.address3 IS NOT NULL AND c.address3 != ''
        GROUP BY c.address3
        HAVING (SELECT COUNT(*) FROM prospective p
                WHERE p.barangay_code = c.address3
                AND NOT EXISTS (SELECT 1 FROM custvisit WHERE CustID = p.CustNo)
                AND p.Latitude IS NOT NULL
                AND p.Longitude IS NOT NULL
                AND p.Latitude != 0
                AND p.Longitude != 0) = 0
        ORDER BY COUNT(DISTINCT CONCAT(m.AgentID, '-', CONVERT(VARCHAR, m.RouteDate, 23))) DESC
        """

        df = db.execute_query_df(query)
        self.results['prospect_exhaustion'] = df

        if df is not None and not df.empty:
            self.logger.info(f"{'Barangay':<15} {'Routes':>8} {'Total':>7} {'Visited':>8} {'Available':>10}")
            self.logger.info("-" * 60)
            for _, row in df.iterrows():
                self.logger.info(
                    f"{row['BarangayCode']:<15} {row['RoutesAffected']:>8} "
                    f"{row['TotalProspects']:>7} {row['VisitedProspects']:>8} "
                    f"{row['AvailableProspects']:>10}"
                )
            self.logger.warning(f"\n  [!] Found {len(df)} barangays with ZERO available prospects!")
            self.logger.warning("      These barangays cannot add prospects to reach 60.")
        else:
            self.logger.info("All barangays have available prospects!")

    def generate_summary_report(self):
        """Generate summary report with key findings"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("SUMMARY & KEY FINDINGS")
        self.logger.info("=" * 80)

        # Overall stats summary
        if 'overall_stats' in self.results and not self.results['overall_stats'].empty:
            stats = self.results['overall_stats']
            self.logger.info("\n[DATABASE OVERVIEW]")
            for _, row in stats.iterrows():
                self.logger.info(f"   - {row['Metric']}: {row['Value']:,}")

        # Route size issues
        if 'route_size_distribution' in self.results and not self.results['route_size_distribution'].empty:
            dist = self.results['route_size_distribution']
            below_60 = dist[~dist['RouteSize'].str.contains('60+')]['RouteCount'].sum()
            total = dist['RouteCount'].sum()
            pct = (below_60 / total * 100) if total > 0 else 0

            self.logger.info(f"\n[TARGET ACHIEVEMENT]")
            self.logger.info(f"   - Routes below 60 customers: {below_60:,} ({pct:.1f}%)")

        # Main reasons for < 60
        self.logger.info("\n[MAIN REASONS FOR ROUTES < 60 CUSTOMERS]")

        # Reason 1: Small territories
        if 'small_route_agents' in self.results and not self.results['small_route_agents'].empty:
            count = len(self.results['small_route_agents'])
            self.logger.info(f"   1. Small Agent Territories: {count} agents with avg < 60 customers")

        # Reason 2: Missing barangay codes
        if 'barangay_coverage' in self.results and not self.results['barangay_coverage'].empty:
            missing = int(self.results['barangay_coverage'].iloc[0]['MissingBarangayCode'])
            if missing > 0:
                self.logger.info(f"   2. Missing Barangay Codes: {missing:,} customer records")

        # Reason 3: Prospect exhaustion
        if 'prospect_exhaustion' in self.results and not self.results['prospect_exhaustion'].empty:
            barangays = len(self.results['prospect_exhaustion'])
            routes = int(self.results['prospect_exhaustion']['RoutesAffected'].sum())
            self.logger.info(f"   3. Prospect Exhaustion: {barangays} barangays, {routes} routes affected")

        # Reason 4: Coordinate issues
        if 'coordinate_coverage' in self.results and not self.results['coordinate_coverage'].empty:
            routes = len(self.results['coordinate_coverage'])
            self.logger.info(f"   4. Missing Coordinates: {routes} routes have customers without coordinates")

        self.logger.info("\n[RECOMMENDATIONS]")
        self.logger.info("   - Add more prospects to exhausted barangays")
        self.logger.info("   - Fix missing barangay codes in customer data")
        self.logger.info("   - Add coordinates for customers missing lat/lon")
        self.logger.info("   - Consider lowering 60-customer target for small territories")
        self.logger.info("   - Review prospect visit data (custvisit) for accuracy")

    def export_results(self):
        """Export results to CSV files"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("EXPORTING RESULTS")
        self.logger.info("=" * 80)

        export_dir = os.path.join(os.path.dirname(__file__), 'analysis_results')
        os.makedirs(export_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        for name, df in self.results.items():
            if df is not None and not df.empty:
                filename = f"{name}_{timestamp}.csv"
                filepath = os.path.join(export_dir, filename)
                df.to_csv(filepath, index=False)
                self.logger.info(f"  [OK] Exported: {filename}")

        self.logger.info(f"\nAll results exported to: {export_dir}")


def main():
    """Main function"""
    print("=" * 80)
    print("MONTHLYROUTEPLAN_TEMP ANALYSIS")
    print("=" * 80)
    print("This script analyzes route data and identifies reasons for routes < 60 customers")
    print("=" * 80)

    analyzer = MonthlyRoutePlanAnalyzer()
    analyzer.run_analysis()

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE!")
    print("Check the logs and analysis_results folders for detailed output")
    print("=" * 80)


if __name__ == "__main__":
    main()
