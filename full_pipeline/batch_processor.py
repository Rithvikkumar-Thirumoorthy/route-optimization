#!/usr/bin/env python3
"""
Batch Processing Utilities for Full Pipeline
Handle chunked processing and parallel execution
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import logging
import time
from multiprocessing import Pool, cpu_count
import queue
import threading

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseConnection

class BatchConfig:
    """Configuration for batch processing"""
    def __init__(self):
        self.batch_size = 50
        self.max_workers = min(4, cpu_count())
        self.timeout_per_agent = 300  # 5 minutes per agent
        self.retry_count = 3
        self.parallel_enabled = True
        self.log_level = logging.INFO

class BatchMonitor:
    """Monitor batch processing progress"""
    def __init__(self, total_items):
        self.total_items = total_items
        self.processed = 0
        self.success = 0
        self.errors = 0
        self.skipped = 0
        self.start_time = time.time()
        self.lock = threading.Lock()

    def update(self, result_status):
        """Update progress counters"""
        with self.lock:
            self.processed += 1
            if result_status == "success":
                self.success += 1
            elif result_status == "error":
                self.errors += 1
            elif result_status == "skipped":
                self.skipped += 1

    def get_progress(self):
        """Get current progress"""
        with self.lock:
            elapsed = time.time() - self.start_time
            rate = self.processed / elapsed if elapsed > 0 else 0
            remaining_time = (self.total_items - self.processed) / rate if rate > 0 else 0

            return {
                'processed': self.processed,
                'total': self.total_items,
                'success': self.success,
                'errors': self.errors,
                'skipped': self.skipped,
                'elapsed_time': elapsed,
                'remaining_time': remaining_time,
                'rate': rate,
                'percentage': (self.processed / self.total_items) * 100
            }

    def print_progress(self, logger):
        """Print current progress"""
        progress = self.get_progress()
        logger.info(f"Progress: {progress['processed']}/{progress['total']} "
                   f"({progress['percentage']:.1f}%) | "
                   f"Success: {progress['success']} | "
                   f"Errors: {progress['errors']} | "
                   f"Rate: {progress['rate']:.2f}/sec | "
                   f"ETA: {progress['remaining_time']/60:.1f} min")

class AgentFilter:
    """Filter agents based on various criteria"""

    @staticmethod
    def filter_by_customer_count(agents_df, min_customers=5, max_customers=None):
        """Filter agents by customer count"""
        filtered = agents_df[agents_df['customer_count'] >= min_customers]
        if max_customers:
            filtered = filtered[filtered['customer_count'] <= max_customers]
        return filtered

    @staticmethod
    def filter_by_date_range(agents_df, start_date=None, end_date=None):
        """Filter agents by date range"""
        if start_date:
            agents_df = agents_df[agents_df['route_date'] >= start_date]
        if end_date:
            agents_df = agents_df[agents_df['route_date'] <= end_date]
        return agents_df

    @staticmethod
    def filter_by_agents(agents_df, agent_list):
        """Filter by specific agent IDs"""
        if agent_list:
            agents_df = agents_df[agents_df['agent_id'].isin(agent_list)]
        return agents_df

    @staticmethod
    def exclude_processed(agents_df, db):
        """Exclude already processed agents"""
        try:
            processed_query = """
            SELECT DISTINCT salesagent, routedate
            FROM routeplan_ai
            """
            processed_df = db.execute_query_df(processed_query)

            if processed_df is not None and not processed_df.empty:
                # Create a key for comparison
                agents_df['key'] = agents_df['agent_id'] + '_' + agents_df['route_date'].astype(str)
                processed_df['key'] = processed_df['salesagent'] + '_' + processed_df['routedate'].astype(str)

                # Filter out processed ones
                unprocessed = agents_df[~agents_df['key'].isin(processed_df['key'])]
                unprocessed = unprocessed.drop('key', axis=1)

                return unprocessed
            else:
                return agents_df

        except Exception as e:
            logging.warning(f"Could not check processed agents: {e}")
            return agents_df

class BatchValidator:
    """Validate batch processing results"""

    @staticmethod
    def validate_agent_data(agent_data):
        """Validate agent data before processing"""
        required_fields = ['agent_id', 'route_date', 'customer_count']

        for field in required_fields:
            if field not in agent_data or pd.isna(agent_data[field]):
                return False, f"Missing required field: {field}"

        if agent_data['customer_count'] < 1:
            return False, "Customer count must be at least 1"

        return True, "Valid"

    @staticmethod
    def validate_results(results):
        """Validate processing results"""
        if not results:
            return False, "No results to validate"

        valid_statuses = ['success', 'error', 'skipped', 'no_data', 'no_results']

        for result in results:
            if 'status' not in result:
                return False, "Result missing status field"

            if result['status'] not in valid_statuses:
                return False, f"Invalid status: {result['status']}"

        return True, "Valid results"

class BatchReporter:
    """Generate reports for batch processing"""

    def __init__(self, output_dir="full_pipeline/reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_summary_report(self, results, config, monitor):
        """Generate summary report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = os.path.join(self.output_dir, f"pipeline_summary_{timestamp}.txt")

        progress = monitor.get_progress()

        # Count results by status
        status_counts = {}
        for result in results:
            status = result.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

        # Generate report content
        report_content = f"""
ROUTE OPTIMIZATION PIPELINE SUMMARY
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'=' * 60}

CONFIGURATION:
  Batch Size: {config.batch_size}
  Max Workers: {config.max_workers}
  Parallel Processing: {'Enabled' if config.parallel_enabled else 'Disabled'}
  Timeout per Agent: {config.timeout_per_agent}s
  Retry Count: {config.retry_count}

PROCESSING SUMMARY:
  Total Agents: {progress['total']}
  Processed: {progress['processed']}
  Success Rate: {(progress['success']/progress['total']*100):.1f}%

RESULTS BY STATUS:
"""

        for status, count in status_counts.items():
            percentage = (count / progress['total']) * 100
            report_content += f"  {status.title()}: {count} ({percentage:.1f}%)\n"

        report_content += f"""
PERFORMANCE:
  Total Time: {progress['elapsed_time']/60:.2f} minutes
  Average Time per Agent: {progress['elapsed_time']/progress['total']:.2f} seconds
  Processing Rate: {progress['rate']:.2f} agents/second

ERRORS:
"""

        # Add error details
        error_results = [r for r in results if r.get('status') == 'error']
        if error_results:
            for result in error_results[:10]:  # Show first 10 errors
                report_content += f"  {result['agent']} ({result['date']}): {result.get('error', 'Unknown error')}\n"
            if len(error_results) > 10:
                report_content += f"  ... and {len(error_results) - 10} more errors\n"
        else:
            report_content += "  No errors encountered\n"

        # Write report
        with open(report_file, 'w') as f:
            f.write(report_content)

        return report_file

    def generate_detailed_report(self, results):
        """Generate detailed CSV report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = os.path.join(self.output_dir, f"pipeline_details_{timestamp}.csv")

        # Convert results to DataFrame
        df = pd.DataFrame(results)

        # Add additional columns
        df['timestamp'] = datetime.now()
        df['processing_success'] = df['status'] == 'success'

        # Save to CSV
        df.to_csv(csv_file, index=False)

        return csv_file

def create_agent_batches(agents_df, batch_size=50):
    """Split agents into batches for processing"""
    batches = []
    for i in range(0, len(agents_df), batch_size):
        batch = agents_df[i:i + batch_size].copy()
        batches.append(batch)

    return batches

def get_optimal_batch_size(total_agents, max_workers=4):
    """Calculate optimal batch size based on system resources"""
    # Base batch size on available CPU cores and total agents
    base_batch_size = max(10, total_agents // (max_workers * 4))

    # Cap at reasonable limits
    optimal_size = min(max(base_batch_size, 20), 100)

    return optimal_size

def estimate_processing_time(total_agents, avg_time_per_agent=30):
    """Estimate total processing time"""
    total_seconds = total_agents * avg_time_per_agent

    return {
        'total_seconds': total_seconds,
        'minutes': total_seconds / 60,
        'hours': total_seconds / 3600,
        'estimated_completion': datetime.now() + pd.Timedelta(seconds=total_seconds)
    }

if __name__ == "__main__":
    # Example usage
    print("Batch Processing Utilities")
    print("This module provides utilities for batch processing of route optimization.")
    print("Import and use the classes in your main pipeline script.")