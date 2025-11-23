"""
Scenario Tracker Module

Tracks and exports route optimization scenarios without modifying core pipeline logic.

Scenarios:
1. Customer + Prospects with valid coordinates
2. Customer + Prospects in same barangay without coordinates
3. Customer only (no prospects due to missing coords or barangay)
"""

import pandas as pd
import os
from datetime import datetime
from typing import Optional, List, Dict


class ScenarioTracker:
    """Tracks different scenario data and exports to CSV"""

    def __init__(self, output_dir: str = "scenario_outputs"):
        """
        Initialize the scenario tracker

        Args:
            output_dir: Directory to save CSV files
        """
        self.output_dir = output_dir
        self.scenario_data = {
            'scenario_1': [],  # Customer + Prospects with valid coordinates
            'scenario_2': [],  # Customer + Prospects in same barangay without coordinates
            'scenario_3': []   # Customer only (no prospects)
        }

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    def add_scenario_data(self,
                         scenario_type: str,
                         distributor_id: str,
                         agent_id: str,
                         date: str,
                         data_df: pd.DataFrame):
        """
        Add data for a specific scenario

        Args:
            scenario_type: 'scenario_1', 'scenario_2', or 'scenario_3'
            distributor_id: Distributor ID
            agent_id: Agent ID
            date: Date string
            data_df: DataFrame containing the route data with columns:
                    - CustNo
                    - latitude (optional)
                    - longitude (optional)
                    - barangay_code (optional)
                    - StopNo (optional)
        """
        if scenario_type not in self.scenario_data:
            raise ValueError(f"Invalid scenario_type: {scenario_type}")

        if data_df is None or data_df.empty:
            return

        # Create a copy to avoid modifying original
        df_copy = data_df.copy()

        # Add identifier columns
        df_copy['DistributorID'] = distributor_id
        df_copy['AgentID'] = agent_id
        df_copy['Date'] = date
        df_copy['Scenario'] = scenario_type

        # Ensure we have the required columns, add NaN if missing
        required_cols = ['DistributorID', 'AgentID', 'Date', 'CustNo',
                        'latitude', 'longitude', 'barangay_code', 'StopNo']

        for col in required_cols:
            if col not in df_copy.columns:
                df_copy[col] = None

        # Map source_table to custype if not already present
        if 'custype' not in df_copy.columns and 'source_table' in df_copy.columns:
            df_copy['custype'] = df_copy['source_table']
        elif 'custype' not in df_copy.columns:
            df_copy['custype'] = None

        # Add sequence number (order within this specific combination)
        df_copy['Sequence'] = range(1, len(df_copy) + 1)

        # Select only the columns we want in the output
        output_cols = ['DistributorID', 'AgentID', 'Date', 'CustNo',
                      'latitude', 'longitude', 'barangay_code',
                      'StopNo', 'Sequence', 'custype', 'Scenario']

        df_output = df_copy[output_cols]

        # Append to scenario data
        self.scenario_data[scenario_type].append(df_output)

    def export_to_csv(self, timestamp: bool = True):
        """
        Export all scenario data to separate CSV files

        Args:
            timestamp: Whether to include timestamp in filename
        """
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S") if timestamp else ""

        results = {}

        for scenario_type, data_list in self.scenario_data.items():
            if not data_list:
                print(f"No data collected for {scenario_type}")
                continue

            # Combine all dataframes for this scenario
            combined_df = pd.concat(data_list, ignore_index=True)

            # Generate filename
            scenario_name = self._get_scenario_name(scenario_type)
            filename = f"{scenario_type}_{scenario_name}"
            if timestamp_str:
                filename += f"_{timestamp_str}"
            filename += ".csv"

            filepath = os.path.join(self.output_dir, filename)

            # Export to CSV
            combined_df.to_csv(filepath, index=False)

            results[scenario_type] = {
                'filepath': filepath,
                'record_count': len(combined_df),
                'unique_combinations': combined_df[['DistributorID', 'AgentID', 'Date']].drop_duplicates().shape[0]
            }

            print(f"Exported {scenario_type}: {len(combined_df)} records to {filepath}")

        return results

    def _get_scenario_name(self, scenario_type: str) -> str:
        """Get descriptive name for scenario type"""
        names = {
            'scenario_1': 'customers_prospects_with_coords',
            'scenario_2': 'customers_prospects_same_barangay_no_coords',
            'scenario_3': 'customers_only_no_prospects'
        }
        return names.get(scenario_type, 'unknown')

    def get_summary_stats(self) -> Dict:
        """
        Get summary statistics for all scenarios

        Returns:
            Dictionary with summary statistics
        """
        summary = {}

        for scenario_type, data_list in self.scenario_data.items():
            if not data_list:
                summary[scenario_type] = {
                    'record_count': 0,
                    'combination_count': 0
                }
                continue

            combined_df = pd.concat(data_list, ignore_index=True)

            summary[scenario_type] = {
                'record_count': len(combined_df),
                'combination_count': combined_df[['DistributorID', 'AgentID', 'Date']].drop_duplicates().shape[0],
                'unique_customers': combined_df['CustNo'].nunique(),
                'unique_distributors': combined_df['DistributorID'].nunique(),
                'unique_agents': combined_df['AgentID'].nunique(),
                'unique_dates': combined_df['Date'].nunique()
            }

        return summary

    def print_summary(self):
        """Print summary statistics"""
        print("\n" + "=" * 80)
        print(" " * 25 + "SCENARIO TRACKING SUMMARY")
        print("=" * 80)

        summary = self.get_summary_stats()

        for scenario_type, stats in summary.items():
            scenario_name = self._get_scenario_name(scenario_type)
            print(f"\n{scenario_type.upper()}: {scenario_name}")
            print("-" * 80)
            print(f"  Total Records:        {stats['record_count']}")
            print(f"  Unique Combinations:  {stats.get('combination_count', 0)}")
            print(f"  Unique Customers:     {stats.get('unique_customers', 0)}")
            print(f"  Unique Distributors:  {stats.get('unique_distributors', 0)}")
            print(f"  Unique Agents:        {stats.get('unique_agents', 0)}")
            print(f"  Unique Dates:         {stats.get('unique_dates', 0)}")

        print("=" * 80 + "\n")
