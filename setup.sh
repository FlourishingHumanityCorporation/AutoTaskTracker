#!/bin/bash

# AutoTaskTracker Setup Script
echo "🚀 AutoTaskTracker Setup"
echo "========================"

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install memos if not already installed
if ! command -v memos &> /dev/null; then
    echo "Installing memos..."
    pip install memos
fi

# Initialize memos
echo "Initializing memos..."
memos init

# Create config directory
mkdir -p ~/.autotasktracker

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start AutoTaskTracker:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Start all services: python autotasktracker.py start"
echo "  3. Open http://localhost:8502 in your browser"
echo ""
echo "For more information, see the README.md file."