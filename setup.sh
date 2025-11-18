#!/bin/bash
# Setup script for Hierarchical Route Pipeline (Linux/Mac)
# This script automates the initial setup process

set -e  # Exit on error

echo "================================================================================"
echo "          HIERARCHICAL ROUTE PIPELINE - SETUP SCRIPT"
echo "================================================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "[1/5] Python found:"
python3 --version
echo ""

# Create virtual environment
echo "[2/5] Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists, skipping..."
else
    python3 -m venv venv
    echo "Virtual environment created successfully"
fi
echo ""

# Activate virtual environment and install dependencies
echo "[3/5] Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "Dependencies installed successfully"
echo ""

# Create .env file if it doesn't exist
echo "[4/5] Setting up configuration..."
if [ -f ".env" ]; then
    echo ".env file already exists, skipping..."
else
    cp .env.example .env
    echo ".env file created from template"
    echo "IMPORTANT: Please edit .env file with your database credentials"
fi
echo ""

# Create logs directory
echo "[5/5] Creating directories..."
mkdir -p logs
echo "Directories created"
echo ""

# Make setup scripts executable
chmod +x setup.sh
chmod +x run_pipeline.py

echo "================================================================================"
echo "                         SETUP COMPLETE!"
echo "================================================================================"
echo ""
echo "Next steps:"
echo "  1. Edit the .env file with your database credentials:"
echo "     nano .env  (or use your preferred editor)"
echo "  2. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo "  3. Test configuration:"
echo "     python run_pipeline.py --validate-config"
echo "  4. Run the pipeline in test mode:"
echo "     python run_pipeline.py --test-mode"
echo ""
echo "For more information, see README.md and docs/QUICKSTART.md"
echo "================================================================================"
