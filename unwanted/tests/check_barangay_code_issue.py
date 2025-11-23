#!/usr/bin/env python3
"""
Check barangay_code issue in routeplan_ai table
"""

from database import DatabaseConnection

def check_barangay_code_issue():
    """Check the barangay_code values in routeplan_ai table"""
    print("CHECKING BARANGAY_CODE ISSUE IN ROUTEPLAN")
    print("=" * 45)

    db = None
    try:
        db = DatabaseConnection()
        db.connect()

        # Check recent insertions for our agents
        print("1. Checking barangay_code values for our test agents:")

        check_query = """
        SELECT TOP 20
            salesagent,
            routedate,
            custno,
            custype,
            barangay,
            barangay_code,
            CASE
                WHEN barangay_code IS NULL THEN 'NULL'
                WHEN barangay_code = 'nan' THEN 'NAN_STRING'
                WHEN barangay_code = '' THEN 'EMPTY'
                ELSE 'HAS_VALUE'
            END as barangay_code_status
        FROM routeplan_ai
        WHERE salesagent IN ('914', 'SK-PMS2')
        ORDER BY salesagent, custype, custno
        """

        results = db.execute_query(check_query)
        if results:
            print("salesagent | custype   | custno     | barangay_code | status")
            print("-" * 65)
            for row in results:
                agent, date, custno, custype, barangay, barangay_code, status = row
                print(f"{agent:<9} | {custype:<8} | {custno:<9} | {str(barangay_code):<12} | {status}")

        # Check prospects specifically
        print("\n2. Checking prospect entries specifically:")

        prospect_query = """
        SELECT
            salesagent,
            custno,
            barangay_code,
            custype,
            CASE
                WHEN barangay_code IS NULL THEN 'NULL'
                WHEN barangay_code = 'nan' THEN 'NAN_STRING'
                WHEN barangay_code = '' THEN 'EMPTY'
                ELSE 'HAS_VALUE'
            END as status
        FROM routeplan_ai
        WHERE salesagent IN ('914', 'SK-PMS2')
        AND custype = 'prospect'
        ORDER BY salesagent, custno
        """

        prospect_results = db.execute_query(prospect_query)
        if prospect_results:
            print("agent | custno     | barangay_code | status")
            print("-" * 40)
            for row in prospect_results:
                agent, custno, barangay_code, custype, status = row
                print(f"{agent:<5} | {custno:<9} | {str(barangay_code):<12} | {status}")
        else:
            print("No prospect entries found")

        # Check source data for comparison
        print("\n3. Checking source prospect data:")

        # Get some prospect IDs from routeplan_ai
        if prospect_results:
            sample_prospect_ids = [row[1] for row in prospect_results[:3]]  # First 3 prospect custno

            for prospect_id in sample_prospect_ids:
                source_query = """
                SELECT CustNo, barangay_code, Barangay
                FROM prospective
                WHERE CustNo = ?
                """

                source_data = db.execute_query(source_query, [prospect_id])
                if source_data:
                    custno, barangay_code, barangay = source_data[0]
                    print(f"  Prospect {custno}: barangay_code='{barangay_code}', Barangay='{barangay}'")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if db:
            db.close()

if __name__ == "__main__":
    check_barangay_code_issue()