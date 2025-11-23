#!/usr/bin/env python3
"""
Organize Project Files
Moves unwanted files to 'unwanted' folder while keeping essential files
"""

import os
import shutil
from pathlib import Path

def organize_project(auto_confirm=False):
    """Organize project by moving unwanted files to 'unwanted' folder"""

    project_root = Path(r"C:\Simplr projects\Route-optimization")
    unwanted_dir = project_root / "unwanted"

    print("=" * 80)
    print("PROJECT FILE ORGANIZATION")
    print("=" * 80)
    print(f"Project Root: {project_root}")
    print(f"Unwanted Folder: {unwanted_dir}")
    print("=" * 80)

    # Essential files/folders to KEEP (not move)
    keep_items = {
        # Main pipeline files
        'full_pipeline/run_monthly_route_pipeline_hierarchical.py',
        'full_pipeline/run_prospect_only_routes.py',
        'full_pipeline/config.py',
        'full_pipeline/logs',
        'full_pipeline/output',

        # Core dependencies
        'core',
        'core/database.py',
        'core/scalable_route_optimizer.py',
        'core/enhanced_route_optimizer.py',
        'core/route_optimizer.py',

        # Recently created/modified essential files
        'route_optimizer.py',
        'visualize_route_output.py',
        'convert_route_to_monthly_format.py',
        'organize_files.py',

        # Configuration files
        '.env',
        '.gitignore',
        'requirements.txt',
        'README.md',

        # Output files
        'route_optimization_output.csv',
        'route_monthly_plan.csv',
        'route_map.html',
        'route_map_day1.html',

        # Unwanted folder itself
        'unwanted',

        # Version control
        '.git',

        # Python cache
        '__pycache__',
        '.pytest_cache',
    }

    # Folders to organize within 'unwanted'
    category_folders = {
        'tests': 'tests',
        'utils': 'utils',
        'visualization': 'visualization',
        'full_pipeline': 'full_pipeline_old',
    }

    # Create unwanted directory
    unwanted_dir.mkdir(exist_ok=True)
    print(f"\nCreated/verified unwanted directory: {unwanted_dir}")

    # Get all items in project root
    all_items = []
    for item in project_root.iterdir():
        if item.name not in ['.git', '__pycache__', 'unwanted', '.pytest_cache']:
            all_items.append(item)

    print(f"\nFound {len(all_items)} items in project root")

    # Track what we're moving
    files_to_move = []
    folders_to_move = []

    # Analyze what to move
    for item in all_items:
        relative_path = item.relative_to(project_root)
        relative_str = str(relative_path).replace('\\', '/')

        # Check if this item should be kept
        should_keep = False

        for keep_pattern in keep_items:
            # Exact match
            if relative_str == keep_pattern:
                should_keep = True
                break
            # Starts with (for folders)
            if relative_str.startswith(keep_pattern + '/') or keep_pattern.startswith(relative_str + '/'):
                should_keep = True
                break

        if not should_keep:
            if item.is_file():
                files_to_move.append(item)
            else:
                folders_to_move.append(item)

    print(f"\nItems to move:")
    print(f"  Files: {len(files_to_move)}")
    print(f"  Folders: {len(folders_to_move)}")

    # Show what will be moved
    print("\n" + "=" * 80)
    print("FILES TO MOVE:")
    print("=" * 80)
    for f in files_to_move[:20]:  # Show first 20
        print(f"  {f.name}")
    if len(files_to_move) > 20:
        print(f"  ... and {len(files_to_move) - 20} more files")

    print("\n" + "=" * 80)
    print("FOLDERS TO MOVE:")
    print("=" * 80)
    for f in folders_to_move:
        print(f"  {f.name}/")

    # Ask for confirmation
    print("\n" + "=" * 80)
    if not auto_confirm:
        confirm = input("Do you want to proceed with moving these files? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled.")
            return
    else:
        print("Auto-confirm enabled - proceeding with file organization...")

    print("\n" + "=" * 80)
    print("MOVING FILES...")
    print("=" * 80)

    moved_count = 0

    # Move files
    for file_path in files_to_move:
        try:
            # Determine target folder
            target_dir = unwanted_dir

            # If file is in a specific folder, preserve structure
            if file_path.parent != project_root:
                parent_name = file_path.parent.name
                if parent_name in category_folders:
                    target_dir = unwanted_dir / category_folders[parent_name]
                else:
                    target_dir = unwanted_dir / parent_name

            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / file_path.name

            # Move file
            shutil.move(str(file_path), str(target_path))
            print(f"  Moved: {file_path.name} -> unwanted/{target_dir.relative_to(unwanted_dir)}/{file_path.name}")
            moved_count += 1

        except Exception as e:
            print(f"  ERROR moving {file_path.name}: {e}")

    # Move folders
    for folder_path in folders_to_move:
        try:
            # Determine target folder
            folder_name = folder_path.name

            if folder_name in category_folders:
                target_path = unwanted_dir / category_folders[folder_name]
            else:
                target_path = unwanted_dir / folder_name

            # Move folder
            if target_path.exists():
                # If target exists, merge contents
                shutil.copytree(str(folder_path), str(target_path), dirs_exist_ok=True)
                shutil.rmtree(str(folder_path))
                print(f"  Moved: {folder_name}/ -> unwanted/{target_path.relative_to(unwanted_dir)}/")
            else:
                shutil.move(str(folder_path), str(target_path))
                print(f"  Moved: {folder_name}/ -> unwanted/{target_path.relative_to(unwanted_dir)}/")

            moved_count += 1

        except Exception as e:
            print(f"  ERROR moving {folder_name}/: {e}")

    print("\n" + "=" * 80)
    print("ORGANIZATION COMPLETE!")
    print("=" * 80)
    print(f"Total items moved: {moved_count}")
    print(f"All unwanted files are now in: {unwanted_dir}")

    # Show final structure
    print("\n" + "=" * 80)
    print("FINAL PROJECT STRUCTURE:")
    print("=" * 80)

    essential_files = list(project_root.glob('*'))
    for item in sorted(essential_files):
        if item.name not in ['unwanted', '.git', '__pycache__']:
            if item.is_dir():
                print(f"  {item.name}/")
            else:
                print(f"  {item.name}")

    print("\n  unwanted/")
    unwanted_items = list(unwanted_dir.glob('*'))
    for item in sorted(unwanted_items)[:10]:
        if item.is_dir():
            print(f"    {item.name}/")
        else:
            print(f"    {item.name}")
    if len(unwanted_items) > 10:
        print(f"    ... and {len(unwanted_items) - 10} more items")

    print("\n" + "=" * 80)
    print("ESSENTIAL FILES KEPT:")
    print("=" * 80)
    print("  - full_pipeline/run_monthly_route_pipeline_hierarchical.py")
    print("  - full_pipeline/run_prospect_only_routes.py")
    print("  - core/ (database, optimizers)")
    print("  - route_optimizer.py (clustering)")
    print("  - visualize_route_output.py (map visualization)")
    print("  - convert_route_to_monthly_format.py (CSV conversion)")
    print("  - .env (database config)")
    print("  - Output CSVs and HTML maps")
    print("=" * 80)

if __name__ == "__main__":
    import sys

    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv

    if auto_confirm:
        print("Running with auto-confirm enabled")

    organize_project(auto_confirm=auto_confirm)
