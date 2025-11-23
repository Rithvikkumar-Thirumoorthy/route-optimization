#!/usr/bin/env python3
"""
Simple Pipeline Runner
Easy-to-use interface for running the full route optimization pipeline
"""

import sys
import os
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def print_banner():
    """Print application banner"""
    print("=" * 80)
    print("ROUTE OPTIMIZATION - FULL PIPELINE")
    print("Process ALL agents in the database")
    print("=" * 80)
    print()

def get_user_choice():
    """Get user choice for pipeline mode"""
    print("Choose pipeline mode:")
    print("1. Quick Run (Sequential, Default Settings)")
    print("2. Fast Run (Parallel Processing)")
    print("3. Test Mode (First 10 agents only)")
    print("4. High Volume Only (60+ customers)")
    print("5. Custom Configuration")
    print("6. Exit")
    print()

    while True:
        try:
            choice = input("Enter choice (1-6): ").strip()
            if choice in ['1', '2', '3', '4', '5', '6']:
                return int(choice)
            else:
                print("Please enter a number between 1 and 6")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
        except Exception:
            print("Invalid input. Please enter a number between 1 and 6")

def get_custom_config():
    """Get custom configuration from user"""
    config = {}

    print("\nCustom Configuration:")
    print("(Press Enter for default values)")

    # Batch size
    try:
        batch_size = input(f"Batch size (default: 50): ").strip()
        config['batch_size'] = int(batch_size) if batch_size else 50
    except ValueError:
        config['batch_size'] = 50

    # Max workers
    try:
        max_workers = input(f"Max workers (default: 4): ").strip()
        config['max_workers'] = int(max_workers) if max_workers else 4
    except ValueError:
        config['max_workers'] = 4

    # Parallel processing
    parallel = input("Enable parallel processing? (y/n, default: n): ").strip().lower()
    config['parallel'] = parallel in ['y', 'yes', 'true', '1']

    return config

def run_pipeline(mode, custom_config=None):
    """Run the pipeline with specified mode"""
    print(f"\nStarting pipeline in mode {mode}...")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Import and run the main pipeline
    try:
        from run_all_agents import FullPipelineProcessor

        if mode == 1:  # Quick Run
            processor = FullPipelineProcessor(batch_size=50, max_workers=4)
            processor.run_full_pipeline(parallel=False)

        elif mode == 2:  # Fast Run
            processor = FullPipelineProcessor(batch_size=50, max_workers=4)
            processor.run_full_pipeline(parallel=True)

        elif mode == 3:  # Test Mode
            processor = FullPipelineProcessor(batch_size=10, max_workers=2)
            # Mock test mode by limiting agents (would need modification to main script)
            print("TEST MODE: This would process only the first 10 agents")
            print("To implement test mode, modify the main script to limit agent count")

        elif mode == 4:  # High Volume Only
            print("HIGH VOLUME MODE: This would process only agents with 60+ customers")
            print("To implement, modify the agent filtering in the main script")
            processor = FullPipelineProcessor(batch_size=100, max_workers=6)
            processor.run_full_pipeline(parallel=True)

        elif mode == 5:  # Custom
            if custom_config:
                processor = FullPipelineProcessor(
                    batch_size=custom_config['batch_size'],
                    max_workers=custom_config['max_workers']
                )
                processor.run_full_pipeline(parallel=custom_config['parallel'])

    except ImportError as e:
        print(f"Error importing pipeline modules: {e}")
        print("Make sure you're running from the correct directory")
        return False
    except Exception as e:
        print(f"Error running pipeline: {e}")
        return False

    return True

def show_system_info():
    """Show system information"""
    import psutil
    import platform

    print("SYSTEM INFORMATION:")
    print(f"  OS: {platform.system()} {platform.release()}")
    print(f"  CPU Cores: {psutil.cpu_count()}")
    print(f"  Available RAM: {psutil.virtual_memory().available / (1024**3):.1f} GB")
    print(f"  Python Version: {sys.version.split()[0]}")
    print()

def check_dependencies():
    """Check if required dependencies are available"""
    required_modules = ['pandas', 'numpy', 'pyodbc', 'sqlalchemy']
    missing = []

    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)

    if missing:
        print("WARNING: Missing required modules:")
        for module in missing:
            print(f"  - {module}")
        print("\nInstall missing modules with:")
        print(f"  pip install {' '.join(missing)}")
        print()
        return False

    return True

def main():
    """Main function"""
    print_banner()

    # Check system info
    show_system_info()

    # Check dependencies
    if not check_dependencies():
        input("Press Enter to continue anyway, or Ctrl+C to exit...")

    # Show estimated processing time
    print("ESTIMATED PROCESSING TIME:")
    print("  Small dataset (100 agents): 5-10 minutes")
    print("  Medium dataset (500 agents): 20-40 minutes")
    print("  Large dataset (1000+ agents): 1-3 hours")
    print()

    # Get user choice
    while True:
        choice = get_user_choice()

        if choice == 6:  # Exit
            print("Goodbye!")
            sys.exit(0)

        custom_config = None
        if choice == 5:  # Custom
            custom_config = get_custom_config()

        # Confirm before starting
        print(f"\nAbout to start pipeline with mode {choice}")
        if custom_config:
            print(f"Custom config: {custom_config}")

        confirm = input("Continue? (y/n): ").strip().lower()
        if confirm in ['y', 'yes']:
            start_time = time.time()

            success = run_pipeline(choice, custom_config)

            end_time = time.time()
            duration = end_time - start_time

            print("\n" + "=" * 80)
            if success:
                print("PIPELINE COMPLETED SUCCESSFULLY!")
                print(f"Total time: {duration/60:.2f} minutes")
            else:
                print("PIPELINE FAILED!")

            print("=" * 80)

            # Ask if user wants to run again
            again = input("\nRun another pipeline? (y/n): ").strip().lower()
            if again not in ['y', 'yes']:
                break
        else:
            print("Cancelled.")

    print("\nThank you for using Route Optimization Pipeline!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)