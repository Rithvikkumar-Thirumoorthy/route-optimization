#!/usr/bin/env python3
"""
Finish organizing remaining files
"""

import os
import shutil

def finish_organization():
    """Move remaining loose files to appropriate folders"""
    print("FINISHING FILE ORGANIZATION")
    print("=" * 35)

    # Additional files to move to tests/
    additional_test_files = [
        'check_barangay_codes.py',
        'check_prospect_barangays.py',
        'debug_prospects.py',
        'final_working_test.py',
        'find_agent_with_barangay.py',
        'find_agent_with_coords.py',
        'quick_custype_test.py',
        'test_enhanced_logic.py',
        'test_fallback_prospects.py',
        'test_final_prospect_demo.py',
        'test_real_agent.py',
        'test_tsp.py',
        'test_tsp_with_coords.py',
        'test_with_prospects.py',
        'test_with_simulated_data.py'
    ]

    # Additional files to move to core/
    additional_core_files = [
        'route_optimizer.py',
        'run_enhanced_pipeline.py'
    ]

    # Additional files to move to utils/
    additional_util_files = [
        'main.py',
        'create_table.py'
    ]

    moved_count = 0

    print("Moving additional test files to tests/:")
    for file in additional_test_files:
        if os.path.exists(file):
            try:
                destination = os.path.join('tests', file)
                shutil.move(file, destination)
                print(f"  Moved: {file}")
                moved_count += 1
            except Exception as e:
                print(f"  Error moving {file}: {e}")

    print("\nMoving additional core files to core/:")
    for file in additional_core_files:
        if os.path.exists(file):
            try:
                destination = os.path.join('core', file)
                shutil.move(file, destination)
                print(f"  Moved: {file}")
                moved_count += 1
            except Exception as e:
                print(f"  Error moving {file}: {e}")

    print("\nMoving additional util files to utils/:")
    for file in additional_util_files:
        if os.path.exists(file):
            try:
                destination = os.path.join('utils', file)
                shutil.move(file, destination)
                print(f"  Moved: {file}")
                moved_count += 1
            except Exception as e:
                print(f"  Error moving {file}: {e}")

    # Clean up old testing folder if it exists
    if os.path.exists('testing scripts'):
        try:
            # Move any files from old testing folder to tests/
            for file in os.listdir('testing scripts'):
                old_path = os.path.join('testing scripts', file)
                new_path = os.path.join('tests', file)
                if os.path.isfile(old_path):
                    shutil.move(old_path, new_path)
                    print(f"  Moved from old folder: {file}")
                    moved_count += 1

            # Remove empty old folder
            shutil.rmtree('testing scripts')
            print("  Removed old 'testing scripts' folder")
        except Exception as e:
            print(f"  Error cleaning old folder: {e}")

    print(f"\nAdditional files moved: {moved_count}")

    # Show final structure
    print(f"\nFinal Project Structure:")
    for folder in ['core', 'sql', 'tests', 'utils']:
        if os.path.exists(folder):
            files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
            print(f"  {folder}/ ({len(files)} files)")

    # List remaining root files
    root_files = [f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('.')]
    print(f"  root/ ({len(root_files)} files): {root_files}")

    print(f"\nProject organization completed!")

if __name__ == "__main__":
    finish_organization()