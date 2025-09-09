#!/bin/bash
# Complete setup script for Code of the Sea Control Panel

echo "🌊 Code of the Sea Control Panel Setup"
echo "======================================"

# Set script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install it first:"
    echo "   sudo apt update && sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "📋 Installing Python packages..."
    pip install -r requirements.txt
else
    echo "⚠️  requirements.txt not found, installing basic packages..."
    pip install flask psutil
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p broadcast/media
mkdir -p logs
mkdir -p backups

# Set permissions
chmod +x start.sh
chmod +x install-service.sh

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Quick start options:"
echo "  Manual:    ./start.sh"
echo "  Service:   ./install-service.sh"
echo ""
echo "📖 Manual commands (what you were using before):"
echo "  source venv/bin/activate"
echo "  cd ~/cos/"
echo "  python run.py unified"
echo ""