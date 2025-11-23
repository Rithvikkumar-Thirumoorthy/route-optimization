import sys
import os

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, current_dir)
sys.path.insert(0, src_dir)

import database

db = database.DatabaseConnection()
db.connect()

# 1. Get DistributorID for 'Mindanao MVP'
query1 = """
SELECT DistributorID, DistributorName
FROM Distributor
WHERE DistributorName = 'Mindanao MVP'
"""
result1 = db.execute_query_df(query1)
print('Distributor info for Mindanao MVP:')
print(result1)
print()

if not result1.empty:
    dist_id = result1.iloc[0]['DistributorID']
    print(f'DistributorID: {dist_id}')
    print()

    # 2. Check what nodetree territories map to this DistributorID
    query2 = f"""
    SELECT DISTINCT nt.SalesManTerritory, nt.DistributorID
    FROM nodetree nt
    WHERE nt.DistributorID = '{dist_id}'
    ORDER BY nt.SalesManTerritory
    """
    result2 = db.execute_query_df(query2)
    print(f'NodeTree territories for DistributorID {dist_id}:')
    print(result2)
    print()

    # 3. For each territory, check what RD values use it
    territories = result2['SalesManTerritory'].tolist()
    print(f'Checking which RD values use these territories...')

    for territory in territories:
        query3 = f"""
        SELECT DISTINCT RD, COUNT(*) as StoreCount
        FROM prospective
        WHERE barangay_code IN (
            SELECT DISTINCT barangay_code
            FROM prospective p
            INNER JOIN salesagent sa ON sa.nodetreevalue = '{territory}'
            WHERE p.RD IN ('Mindanao MVP', 'Everlink Dist', 'Everlink Dist. Group')
        )
        AND RD IN ('Mindanao MVP', 'Everlink Dist', 'Everlink Dist. Group')
        GROUP BY RD
        """
        result3 = db.execute_query_df(query3)
        print(f'\n  Territory: {territory}')
        print(result3)

db.close()
