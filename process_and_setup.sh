#!/bin/bash
# Master script: Process videos and setup frontend

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "CCTV Video Processing & Frontend Setup"
echo "=========================================="
echo ""

# Step 1: Process videos
echo "Step 1: Processing videos..."
echo "----------------------------------------"
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

source venv/bin/activate

if [ ! -f "offline_processor/process_videos.py" ]; then
    echo "❌ offline_processor/process_videos.py not found!"
    exit 1
fi

python offline_processor/process_videos.py

if [ $? -ne 0 ]; then
    echo "❌ Video processing failed!"
    exit 1
fi

echo ""
echo "✓ Video processing complete"
echo ""

# Step 2: Copy files to frontend
echo "Step 2: Copying files to frontend..."
echo "----------------------------------------"
cd frontend
bash copy-data.sh

if [ $? -ne 0 ]; then
    echo "❌ File copy failed!"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. cd frontend"
echo "  2. npm install"
echo "  3. npm run dev"
echo ""

