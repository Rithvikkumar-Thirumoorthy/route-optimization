#!/usr/bin/env python3
"""
Run hierarchical pipeline for specific distributor or specific agent
Usage:
  - All agents in distributor: python run_specific_agent.py --distributor 11814
  - Specific agent: python run_specific_agent.py --distributor 11814 --agent SK-SAT6
"""

import sys
import os
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_monthly_route_pipeline_hierarchical import HierarchicalMonthlyRoutePipelineProcessor
from core.database import DatabaseConnection

class SpecificAgentProcessor(HierarchicalMonthlyRoutePipelineProcessor):
    def __init__(self, target_distributor_id, target_agent_id=None, batch_size=50, max_workers=1, start_lat=None, start_lon=None):
        super().__init__(batch_size, max_workers, start_lat, start_lon)
        self.target_distributor_id = target_distributor_id
        self.target_agent_id = target_agent_id

    def get_distributors_hierarchy(self, db):
        """Override to filter for specific distributor and optionally specific agent"""
        try:
            if self.target_agent_id:
                # Single agent mode
                self.logger.info(f'Building hierarchy for DistributorID: {self.target_distributor_id}, Agent: {self.target_agent_id}')

                # Get dates for this specific agent (chronological)
                dates_query = f"""
                SELECT
                    RouteDate,
                    COUNT(DISTINCT CustNo) as customer_count,
                    COUNT(*) as total_records
                FROM MonthlyRoutePlan_temp
                WHERE DistributorID = '{self.target_distributor_id}'
                    AND AgentID = '{self.target_agent_id}'
                    AND RouteDate IS NOT NULL
                    AND CustNo IS NOT NULL
                GROUP BY RouteDate
                ORDER BY RouteDate ASC
                """
                dates_df = db.execute_query_df(dates_query)

                if dates_df is None or dates_df.empty:
                    self.logger.error(f'No dates found for DistributorID: {self.target_distributor_id}, Agent: {self.target_agent_id}')
                    return {}

                hierarchy = {self.target_distributor_id: {self.target_agent_id: dates_df.to_dict('records')}}

                # Log summary
                total_combinations = len(dates_df)
                self.logger.info(f'Found {total_combinations} date combinations for Agent {self.target_agent_id}')

                # Show date range
                if total_combinations > 0:
                    first_date = dates_df['RouteDate'].min()
                    last_date = dates_df['RouteDate'].max()
                    self.logger.info(f'Date range: {first_date} to {last_date}')

                    # Show sample dates
                    self.logger.info("Dates to be processed:")
                    for _, row in dates_df.iterrows():
                        self.logger.info(f"  {row['RouteDate']}: {row['customer_count']} customers")

            else:
                # All agents for distributor mode
                self.logger.info(f'Building hierarchy for all agents in DistributorID: {self.target_distributor_id}')

                # Get all agents for this distributor
                agents_query = f"""
                SELECT DISTINCT AgentID
                FROM MonthlyRoutePlan_temp
                WHERE DistributorID = '{self.target_distributor_id}'
                    AND AgentID IS NOT NULL
                ORDER BY AgentID
                """
                agents_df = db.execute_query_df(agents_query)

                if agents_df is None or agents_df.empty:
                    self.logger.error(f'No agents found for DistributorID: {self.target_distributor_id}')
                    return {}

                hierarchy = {self.target_distributor_id: {}}

                for _, agent_row in agents_df.iterrows():
                    agent_id = agent_row['AgentID']

                    # Get dates for this agent (chronological)
                    dates_query = f"""
                    SELECT
                        RouteDate,
                        COUNT(DISTINCT CustNo) as customer_count,
                        COUNT(*) as total_records
                    FROM MonthlyRoutePlan_temp
                    WHERE DistributorID = '{self.target_distributor_id}'
                        AND AgentID = '{agent_id}'
                        AND RouteDate IS NOT NULL
                        AND CustNo IS NOT NULL
                    GROUP BY RouteDate
                    ORDER BY RouteDate ASC
                    """
                    dates_df = db.execute_query_df(dates_query)

                    if dates_df is not None and not dates_df.empty:
                        hierarchy[self.target_distributor_id][agent_id] = dates_df.to_dict('records')
                        self.logger.info(f'  Agent {agent_id}: {len(dates_df)} dates found')
                    else:
                        self.logger.warning(f'  Agent {agent_id}: No valid dates found')

                # Log distributor summary
                total_agents = len(hierarchy[self.target_distributor_id])
                total_combinations = sum(len(dates) for dates in hierarchy[self.target_distributor_id].values())
                self.logger.info(f'DistributorID {self.target_distributor_id}: {total_agents} agents, {total_combinations} date combinations')

            return hierarchy

        except Exception as e:
            self.logger.error(f'Error building hierarchy for {self.target_distributor_id}: {e}')
            return {}

def main():
    parser = argparse.ArgumentParser(description="Run hierarchical pipeline for specific distributor or agent")
    parser.add_argument("--distributor", "-d", required=True, help="DistributorID (e.g., 11814)")
    parser.add_argument("--agent", "-a", required=False, default=None, help="AgentID (e.g., SK-SAT6) - optional, if omitted processes all agents in distributor")
    parser.add_argument("--batch-size", "-b", type=int, default=50, help="Batch size for processing")
    parser.add_argument("--parallel", action="store_true", help="Enable parallel processing")
    parser.add_argument("--test-mode", action="store_true", help="Process only first 3 dates")
    parser.add_argument("--start-lat", type=float, default=14.663813, help="Starting latitude for TSP (default: 14.663813)")
    parser.add_argument("--start-lon", type=float, default=121.122687, help="Starting longitude for TSP (default: 121.122687)")

    args = parser.parse_args()

    print("=" * 80)
    if args.agent:
        print("HIERARCHICAL PIPELINE - SPECIFIC AGENT")
    else:
        print("HIERARCHICAL PIPELINE - ALL AGENTS IN DISTRIBUTOR")
    print("=" * 80)
    print(f"DistributorID: {args.distributor}")
    print(f"Agent: {args.agent if args.agent else 'ALL'}")
    print(f"Batch Size: {args.batch_size}")
    print(f"Parallel: {'Enabled' if args.parallel else 'Disabled'}")
    print(f"Test Mode: {'Enabled (first 3 dates only)' if args.test_mode else 'Disabled'}")
    print(f"Starting Location: ({args.start_lat}, {args.start_lon})")
    print("=" * 80)

    try:
        # Initialize processor for specific agent
        processor = SpecificAgentProcessor(
            args.distributor,
            args.agent,
            batch_size=args.batch_size,
            max_workers=1 if not args.parallel else 4,
            start_lat=args.start_lat,
            start_lon=args.start_lon
        )

        # Modify for test mode if needed
        if args.test_mode:
            # Override to limit to first 3 dates
            original_get_hierarchy = processor.get_distributors_hierarchy

            def limited_get_hierarchy(db):
                hierarchy = original_get_hierarchy(db)
                if hierarchy and args.distributor in hierarchy:
                    if args.agent:
                        # Single agent mode - limit that agent's dates
                        if args.agent in hierarchy[args.distributor]:
                            dates_list = hierarchy[args.distributor][args.agent]
                            hierarchy[args.distributor][args.agent] = dates_list[:3]  # Only first 3 dates
                            processor.logger.info(f"TEST MODE: Limited to {len(hierarchy[args.distributor][args.agent])} dates")
                    else:
                        # All agents mode - limit each agent to first 3 dates
                        for agent_id, dates_list in hierarchy[args.distributor].items():
                            hierarchy[args.distributor][agent_id] = dates_list[:3]
                        processor.logger.info(f"TEST MODE: Limited each agent to 3 dates")
                return hierarchy

            processor.get_distributors_hierarchy = limited_get_hierarchy

        # Run the pipeline
        processor.run_hierarchical_pipeline(parallel=args.parallel)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()