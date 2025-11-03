#!/bin/bash

echo "========================================"
echo "  Starting Python Music Analyzer Server"
echo "========================================"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if Flask is installed
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Error: Flask is not installed!"
    echo "Please run: pip install -r requirements.txt"
    exit 1
fi

echo "Starting Flask server..."
echo "Server will be available at: http://localhost:5000"
echo "Press Ctrl+C to stop"
echo ""

python3 api.py

