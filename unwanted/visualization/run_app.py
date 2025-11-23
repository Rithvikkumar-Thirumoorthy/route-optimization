#!/usr/bin/env python3
"""
Runner script for the Route Visualizer Streamlit app
"""

import subprocess
import sys
import os

def install_requirements():
    """Install required packages"""
    print("Installing visualization requirements...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("Requirements installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")
        return False

def run_streamlit_app():
    """Run the Streamlit app"""
    print("Starting Route Visualization App...")
    print("The app will open in your default browser.")
    print("Press Ctrl+C to stop the app.")

    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "route_visualizer.py",
            "--server.address", "localhost",
            "--server.port", "8501"
        ])
    except KeyboardInterrupt:
        print("\nApp stopped by user.")
    except Exception as e:
        print(f"Error running app: {e}")

def main():
    """Main function"""
    print("Route Optimization Visualizer")
    print("=" * 35)

    # Check if we're in the right directory
    if not os.path.exists("route_visualizer.py"):
        print("Error: route_visualizer.py not found!")
        print("Please run this script from the visualization folder.")
        return

    # Ask user if they want to install requirements
    install = input("Install/update requirements? (y/n): ").lower().strip()
    if install in ['y', 'yes']:
        if not install_requirements():
            return

    print("\nStarting the visualization app...")
    run_streamlit_app()

if __name__ == "__main__":
    main()