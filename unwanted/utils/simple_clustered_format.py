#!/usr/bin/env python3
"""
Simple clustered format display for distributor 11814 scenarios
Using the previously obtained data
"""

def display_clustered_scenarios():
    """Display scenarios in clustered format"""

    print("=" * 100)
    print("CLUSTERED SCENARIO REPORT - DISTRIBUTOR 11814")
    print("=" * 100)
    print("Total agent-date combinations: 480")
    print()

    # Scenario 1: >60 customers, ALL valid coords (8 agents)
    print("SCENARIO 1: Agent with >60 customers, ALL valid coords")
    print("   Total: 8 agent-date combinations")
    print("-" * 90)

    print("\nSK Family (8 agents):")
    print("   • Agent with >60 (61) customers")
    print("     \"SK-SAT4\" on \"18/09/2025\"")
    print("     (61 valid coords, 0 invalid coords - 100.0%)")

    print("   • Agent with >60 (61) customers")
    print("     \"SK-SAT4\" on \"04/09/2025\"")
    print("     (61 valid coords, 0 invalid coords - 100.0%)")

    print("   • Agent with >60 (63) customers")
    print("     \"SK-SAT5\" on \"22/09/2025\"")
    print("     (63 valid coords, 0 invalid coords - 100.0%)")

    print("   • Agent with >60 (62) customers")
    print("     \"SK-SAT5\" on \"18/09/2025\"")
    print("     (62 valid coords, 0 invalid coords - 100.0%)")

    print("   • Agent with >60 (67) customers")
    print("     \"SK-SAT5\" on \"17/09/2025\"")
    print("     (67 valid coords, 0 invalid coords - 100.0%)")

    print("   • Agent with >60 (67) customers")
    print("     \"SK-SAT5\" on \"08/09/2025\"")
    print("     (67 valid coords, 0 invalid coords - 100.0%)")

    print("   • Agent with >60 (63) customers")
    print("     \"SK-SAT5\" on \"04/09/2025\"")
    print("     (63 valid coords, 0 invalid coords - 100.0%)")

    print("   • Agent with >60 (62) customers")
    print("     \"SK-SAT5\" on \"03/09/2025\"")
    print("     (62 valid coords, 0 invalid coords - 100.0%)")
    print()

    # Scenario 2: >60 customers, MIXED valid/invalid coords (2 agents)
    print("SCENARIO 2: Agent with >60 customers, MIXED valid/invalid coords")
    print("   Total: 2 agent-date combinations")
    print("-" * 90)

    print("\nSK Family (2 agents):")
    print("   • Agent with >60 (61) customers")
    print("     \"SK-SAT4\" on \"25/09/2025\"")
    print("     (49 valid coords, 12 invalid coords - 80.3%)")

    print("   • Agent with >60 (61) customers")
    print("     \"SK-SAT4\" on \"11/09/2025\"")
    print("     (49 valid coords, 12 invalid coords - 80.3%)")
    print()

    # Scenario 3: 30-60 customers, ALL valid coords (63 agents)
    print("SCENARIO 3: Agent with 30-60 customers, ALL valid coords")
    print("   Total: 63 agent-date combinations")
    print("-" * 90)

    print("\nSK Family (63 agents):")
    print("   • Agent with 30-60 (30) customers")
    print("     \"SK-PMS1\" on \"27/09/2025\"")
    print("     (30 valid coords, 0 invalid coords - 100.0%)")

    print("   • Agent with 30-60 (31) customers")
    print("     \"SK-PMS1\" on \"23/09/2025\"")
    print("     (31 valid coords, 0 invalid coords - 100.0%)")

    print("   • Agent with 30-60 customers (multiple dates)")
    print("     \"SK-SAT2\":")
    print("       - 29/09/2025 (47 customers, 100.0% valid)")
    print("       - 27/09/2025 (50 customers, 100.0% valid)")
    print("       - 25/09/2025 (47 customers, 100.0% valid)")

    print("   • Agent with 30-60 customers (multiple dates)")
    print("     \"SK-SAT3\":")
    print("       - 29/09/2025 (55 customers, 100.0% valid)")
    print("       - 26/09/2025 (55 customers, 100.0% valid)")
    print("       - 23/09/2025 (55 customers, 100.0% valid)")

    print("   • Agent with 30-60 customers (multiple dates)")
    print("     \"SK-SAT6\":")
    print("       - 29/09/2025 (58 customers, 100.0% valid)")
    print("       - 26/09/2025 (58 customers, 100.0% valid)")
    print("       - ... and 55 more dates")
    print()

    # Scenario 4: 30-60 customers, MIXED valid/invalid coords (6 agents)
    print("SCENARIO 4: Agent with 30-60 customers, MIXED valid/invalid coords")
    print("   Total: 6 agent-date combinations")
    print("-" * 90)

    print("\nPVM Family (2 agents):")
    print("   • Agent with 30-60 (53) customers")
    print("     \"PVM-KAR01\" on \"22/09/2025\"")
    print("     (2 valid coords, 51 invalid coords - 3.8%)")

    print("   • Agent with 30-60 (34) customers")
    print("     \"PVM-PRE01\" on \"22/09/2025\"")
    print("     (11 valid coords, 23 invalid coords - 32.4%)")

    print("   • Agent with 30-60 (34) customers")
    print("     \"PVM-PRE01\" on \"08/09/2025\"")
    print("     (11 valid coords, 23 invalid coords - 32.4%)")

    print("\nREM Family (3 agents):")
    print("   • Agent with 30-60 (52) customers")
    print("     \"REM-KAS7\" on \"22/09/2025\"")
    print("     (1 valid coords, 51 invalid coords - 1.9%)")

    print("   • Agent with 30-60 (32) customers")
    print("     \"REM-PMS1\" on \"24/09/2025\"")
    print("     (2 valid coords, 30 invalid coords - 6.2%)")

    print("   • Agent with 30-60 (32) customers")
    print("     \"REM-PMS1\" on \"10/09/2025\"")
    print("     (2 valid coords, 30 invalid coords - 6.2%)")
    print()

    # Scenario 5: <60 customers, NO valid coords (401 agents)
    print("SCENARIO 5: Agent with <60 customers, NO valid coords")
    print("   Total: 401 agent-date combinations")
    print("-" * 90)

    print("\nPVM Family (200+ agents):")
    print("   • Agent with <60 (3) customers")
    print("     \"PVM-KAR01\" on \"29/09/2025\"")
    print("     (0 valid coords, 3 invalid coords - 0.0%)")

    print("   • Agent with <60 (9) customers")
    print("     \"PVM-KAR01\" on \"26/09/2025\"")
    print("     (0 valid coords, 9 invalid coords - 0.0%)")

    print("   • Agent with <60 customers (multiple dates)")
    print("     \"PVM-KAR02\":")
    print("       - 27/09/2025 (2 customers, 0.0% valid)")
    print("       - 20/09/2025 (13 customers, 0.0% valid)")
    print("       - 13/09/2025 (5 customers, 0.0% valid)")

    print("\nREM Family (150+ agents):")
    print("   • Agent with <60 customers (multiple dates)")
    print("     \"REM-KAS7\" (multiple dates without coords)")
    print("   • Agent with <60 customers (multiple dates)")
    print("     \"REM-PMS1\" (multiple dates without coords)")

    print("\n   • ... and 241 more agent-date combinations")
    print()

    print("=" * 100)
    print("PROCESSING LISTS BY SCENARIO")
    print("=" * 100)

    # Processing lists
    scenarios = {
        1: {
            "name": "Agent with >60 customers, ALL valid coords",
            "agents": [
                ("SK-SAT4", "2025-09-18"),
                ("SK-SAT4", "2025-09-04"),
                ("SK-SAT5", "2025-09-22"),
                ("SK-SAT5", "2025-09-18"),
                ("SK-SAT5", "2025-09-17"),
                ("SK-SAT5", "2025-09-08"),
                ("SK-SAT5", "2025-09-04"),
                ("SK-SAT5", "2025-09-03")
            ]
        },
        2: {
            "name": "Agent with >60 customers, MIXED valid/invalid coords",
            "agents": [
                ("SK-SAT4", "2025-09-25"),
                ("SK-SAT4", "2025-09-11")
            ]
        },
        4: {
            "name": "Agent with 30-60 customers, MIXED valid/invalid coords",
            "agents": [
                ("PVM-KAR01", "2025-09-22"),
                ("PVM-PRE01", "2025-09-22"),
                ("PVM-PRE01", "2025-09-08"),
                ("REM-KAS7", "2025-09-22"),
                ("REM-PMS1", "2025-09-24"),
                ("REM-PMS1", "2025-09-10")
            ]
        }
    }

    for scenario_num, scenario_data in scenarios.items():
        print(f"\nSCENARIO {scenario_num}: {scenario_data['name']}")
        print(f"Processing list ({len(scenario_data['agents'])} agents):")
        print("```python")
        print("specific_agents = [")

        for agent_id, route_date in scenario_data['agents']:
            print(f"    (\"{agent_id}\", \"{route_date}\"),")

        print("]")
        print("```")
        print()

    # Note about Scenario 3 and 5
    print("NOTE:")
    print("- Scenario 3 (63 agents with 30-60 customers, all valid coords) - Full list available in exported CSV")
    print("- Scenario 5 (401 agents with <60 customers, no valid coords) - Full list available in exported CSV")

    print("\n" + "=" * 100)
    print("CLUSTERED ANALYSIS COMPLETED!")
    print("=" * 100)

if __name__ == "__main__":
    display_clustered_scenarios()