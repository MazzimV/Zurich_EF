#!/bin/bash
# Start Alice Service

cd "$(dirname "$0")"

# Use graph-generation's venv since it has all the dependencies
source ../graph-generation/venv/bin/activate

echo "Starting Alice Service on port 8004..."
python main.py
