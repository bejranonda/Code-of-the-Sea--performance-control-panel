#!/bin/bash
# Optimized startup script for Code of the Sea Control Panel

# Set script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🌊 Starting Code of the Sea Control Panel..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if required packages are installed
python -c "import flask, psutil" 2>/dev/null || {
    echo "📦 Installing missing dependencies..."
    pip install -r requirements.txt
}

# Start the application
echo "🚀 Launching application..."
python run.py unified