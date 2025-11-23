import pandas as pd
import sys

# Read the CSV file
csv_file = sys.argv[1] if len(sys.argv) > 1 else 'output/ors_prospect_routes_11619_2024-12-02_20251120_105315.csv'
df = pd.read_csv(csv_file)

# Analyze cluster sizes
sizes = df.groupby('RouteCode').size()

print(f'=== CLUSTER SIZE ANALYSIS ===')
print(f'Total routes: {len(sizes)}')
print(f'Total records: {len(df)}')
print(f'Min cluster size: {sizes.min()}')
print(f'Max cluster size: {sizes.max()}')
print(f'Mean cluster size: {sizes.mean():.1f}')

# Check for oversized clusters
print(f'\n=== ROUTES EXCEEDING 60 STORES ===')
oversized = sizes[sizes > 60]
print(f'Count: {len(oversized)}')

if len(oversized) > 0:
    print(f'\nTop 20 oversized routes:')
    print(oversized.sort_values(ascending=False).head(20))
else:
    print('SUCCESS: No routes exceed 60 stores!')

# Check agent-date uniqueness
print(f'\n=== AGENT-DATE UNIQUENESS CHECK ===')
agent_date_routes = df.groupby(['AgentCode', 'RouteDate'])['RouteCode'].nunique()
duplicates = agent_date_routes[agent_date_routes > 1]
print(f'Agent-Date combinations with multiple routes: {len(duplicates)}')
if len(duplicates) > 0:
    print('ERROR: Some agents have multiple routes on same date!')
    print(duplicates.head(10))
else:
    print('SUCCESS: Each (agent, date) has exactly ONE route!')
