#!/usr/bin/env python3
"""
Export clustered scenario data to CSV for distributor 11814
"""

import pandas as pd
from datetime import datetime

def create_clustered_csv():
    """Create CSV with all scenario data in clustered format"""

    # All scenario data based on our analysis
    data = []

    # SCENARIO 1: Agent with >60 customers, ALL valid coords (8 agents)
    scenario_1_agents = [
        ("SK-SAT4", "2025-09-18", 61, 61, 0, 100.0),
        ("SK-SAT4", "2025-09-04", 61, 61, 0, 100.0),
        ("SK-SAT5", "2025-09-22", 63, 63, 0, 100.0),
        ("SK-SAT5", "2025-09-18", 62, 62, 0, 100.0),
        ("SK-SAT5", "2025-09-17", 67, 67, 0, 100.0),
        ("SK-SAT5", "2025-09-08", 67, 67, 0, 100.0),
        ("SK-SAT5", "2025-09-04", 63, 63, 0, 100.0),
        ("SK-SAT5", "2025-09-03", 62, 62, 0, 100.0),
    ]

    for agent_id, route_date, total, valid, invalid, percentage in scenario_1_agents:
        agent_family = agent_id.split('-')[0]
        formatted_date = datetime.strptime(route_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        data.append({
            'scenario': 1,
            'scenario_name': 'Agent with >60 customers, ALL valid coords',
            'agent_family': agent_family,
            'agent_id': agent_id,
            'route_date': route_date,
            'formatted_date': formatted_date,
            'total_customers': total,
            'valid_coord_customers': valid,
            'invalid_coord_customers': invalid,
            'coord_percentage': percentage,
            'customer_range': f'>60 ({total})',
            'description': f'Agent with >60 ({total}) customers "{agent_id}" on "{formatted_date}"',
            'coord_status': f'({valid} valid coords, {invalid} invalid coords - {percentage}%)',
            'distributor_id': '11814',
            'priority': 'High - Perfect for optimization'
        })

    # SCENARIO 2: Agent with >60 customers, MIXED valid/invalid coords (2 agents)
    scenario_2_agents = [
        ("SK-SAT4", "2025-09-25", 61, 49, 12, 80.3),
        ("SK-SAT4", "2025-09-11", 61, 49, 12, 80.3),
    ]

    for agent_id, route_date, total, valid, invalid, percentage in scenario_2_agents:
        agent_family = agent_id.split('-')[0]
        formatted_date = datetime.strptime(route_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        data.append({
            'scenario': 2,
            'scenario_name': 'Agent with >60 customers, MIXED valid/invalid coords',
            'agent_family': agent_family,
            'agent_id': agent_id,
            'route_date': route_date,
            'formatted_date': formatted_date,
            'total_customers': total,
            'valid_coord_customers': valid,
            'invalid_coord_customers': invalid,
            'coord_percentage': percentage,
            'customer_range': f'>60 ({total})',
            'description': f'Agent with >60 ({total}) customers "{agent_id}" on "{formatted_date}"',
            'coord_status': f'({valid} valid coords, {invalid} invalid coords - {percentage}%)',
            'distributor_id': '11814',
            'priority': 'High - Good for optimization with some fixes needed'
        })

    # SCENARIO 3: Agent with 30-60 customers, ALL valid coords (sample of main ones)
    scenario_3_agents = [
        ("SK-PMS1", "2025-09-27", 30, 30, 0, 100.0),
        ("SK-PMS1", "2025-09-23", 31, 31, 0, 100.0),
        ("SK-PMS1", "2025-09-20", 30, 30, 0, 100.0),
        ("SK-SAT2", "2025-09-29", 47, 47, 0, 100.0),
        ("SK-SAT2", "2025-09-27", 50, 50, 0, 100.0),
        ("SK-SAT2", "2025-09-25", 47, 47, 0, 100.0),
        ("SK-SAT3", "2025-09-29", 55, 55, 0, 100.0),
        ("SK-SAT3", "2025-09-26", 55, 55, 0, 100.0),
        ("SK-SAT3", "2025-09-23", 55, 55, 0, 100.0),
        ("SK-SAT6", "2025-09-29", 58, 58, 0, 100.0),
        ("SK-SAT6", "2025-09-26", 58, 58, 0, 100.0),
        ("SK-SAT6", "2025-09-23", 58, 58, 0, 100.0),
    ]

    for agent_id, route_date, total, valid, invalid, percentage in scenario_3_agents:
        agent_family = agent_id.split('-')[0]
        formatted_date = datetime.strptime(route_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        data.append({
            'scenario': 3,
            'scenario_name': 'Agent with 30-60 customers, ALL valid coords',
            'agent_family': agent_family,
            'agent_id': agent_id,
            'route_date': route_date,
            'formatted_date': formatted_date,
            'total_customers': total,
            'valid_coord_customers': valid,
            'invalid_coord_customers': invalid,
            'coord_percentage': percentage,
            'customer_range': f'30-60 ({total})',
            'description': f'Agent with 30-60 ({total}) customers "{agent_id}" on "{formatted_date}"',
            'coord_status': f'({valid} valid coords, {invalid} invalid coords - {percentage}%)',
            'distributor_id': '11814',
            'priority': 'Medium - Good for optimization'
        })

    # SCENARIO 4: Agent with 30-60 customers, MIXED valid/invalid coords (6 agents)
    scenario_4_agents = [
        ("PVM-KAR01", "2025-09-22", 53, 2, 51, 3.8),
        ("PVM-PRE01", "2025-09-22", 34, 11, 23, 32.4),
        ("PVM-PRE01", "2025-09-08", 34, 11, 23, 32.4),
        ("REM-KAS7", "2025-09-22", 52, 1, 51, 1.9),
        ("REM-PMS1", "2025-09-24", 32, 2, 30, 6.2),
        ("REM-PMS1", "2025-09-10", 32, 2, 30, 6.2),
    ]

    for agent_id, route_date, total, valid, invalid, percentage in scenario_4_agents:
        agent_family = agent_id.split('-')[0]
        formatted_date = datetime.strptime(route_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        data.append({
            'scenario': 4,
            'scenario_name': 'Agent with 30-60 customers, MIXED valid/invalid coords',
            'agent_family': agent_family,
            'agent_id': agent_id,
            'route_date': route_date,
            'formatted_date': formatted_date,
            'total_customers': total,
            'valid_coord_customers': valid,
            'invalid_coord_customers': invalid,
            'coord_percentage': percentage,
            'customer_range': f'30-60 ({total})',
            'description': f'Agent with 30-60 ({total}) customers "{agent_id}" on "{formatted_date}"',
            'coord_status': f'({valid} valid coords, {invalid} invalid coords - {percentage}%)',
            'distributor_id': '11814',
            'priority': 'Medium - Needs coordinate fixing before optimization'
        })

    # SCENARIO 5: Agent with <60 customers, NO valid coords (sample of main ones)
    scenario_5_agents = [
        ("PVM-KAR01", "2025-09-29", 3, 0, 3, 0.0),
        ("PVM-KAR01", "2025-09-26", 9, 0, 9, 0.0),
        ("PVM-KAR01", "2025-09-19", 8, 0, 8, 0.0),
        ("PVM-KAR02", "2025-09-27", 2, 0, 2, 0.0),
        ("PVM-KAR02", "2025-09-20", 13, 0, 13, 0.0),
        ("PVM-KAR02", "2025-09-13", 5, 0, 5, 0.0),
        ("REM-KAS7", "2025-09-25", 15, 0, 15, 0.0),
        ("REM-KAS7", "2025-09-20", 8, 0, 8, 0.0),
        ("REM-PMS1", "2025-09-22", 12, 0, 12, 0.0),
        ("REM-PMS1", "2025-09-18", 7, 0, 7, 0.0),
    ]

    for agent_id, route_date, total, valid, invalid, percentage in scenario_5_agents:
        agent_family = agent_id.split('-')[0]
        formatted_date = datetime.strptime(route_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        data.append({
            'scenario': 5,
            'scenario_name': 'Agent with <60 customers, NO valid coords',
            'agent_family': agent_family,
            'agent_id': agent_id,
            'route_date': route_date,
            'formatted_date': formatted_date,
            'total_customers': total,
            'valid_coord_customers': valid,
            'invalid_coord_customers': invalid,
            'coord_percentage': percentage,
            'customer_range': f'<60 ({total})',
            'description': f'Agent with <60 ({total}) customers "{agent_id}" on "{formatted_date}"',
            'coord_status': f'({valid} valid coords, {invalid} invalid coords - {percentage}%)',
            'distributor_id': '11814',
            'priority': 'Low - Needs coordinate data before optimization'
        })

    # Create DataFrame and save to CSV
    df = pd.DataFrame(data)

    # Sort by scenario, agent_family, agent_id, route_date
    df = df.sort_values(['scenario', 'agent_family', 'agent_id', 'route_date'])

    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'distributor_11814_clustered_scenarios_{timestamp}.csv'

    # Save to CSV
    df.to_csv(filename, index=False)

    print(f"Clustered scenario data exported to: {filename}")
    print(f"Total records: {len(df)}")
    print("\nScenario breakdown:")
    scenario_counts = df.groupby(['scenario', 'scenario_name']).size().reset_index(name='count')
    for _, row in scenario_counts.iterrows():
        print(f"  Scenario {row['scenario']}: {row['count']} agents - {row['scenario_name']}")

    print(f"\nAgent family breakdown:")
    family_counts = df.groupby('agent_family').size().reset_index(name='count')
    for _, row in family_counts.iterrows():
        print(f"  {row['agent_family']} Family: {row['count']} agents")

    print(f"\nColumns in CSV:")
    for col in df.columns:
        print(f"  - {col}")

    return filename

if __name__ == "__main__":
    create_clustered_csv()