#!/bin/bash
# Installation script for Code of the Sea Exhibition System

set -e  # Exit on any error

echo "🌊 Installing Code of the Sea Exhibition System..."
echo "=================================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ This script should not be run as root"
   exit 1
fi

# Check if we're in the right directory
if [[ ! -f "unified_app.py" ]]; then
    echo "❌ Please run this script from the /home/payas/cos directory"
    exit 1
fi

echo "📁 Current directory: $(pwd)"
echo "👤 Current user: $(whoami)"

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    i2c-tools \
    cron \
    curl \
    unattended-upgrades

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip3 install --user \
    flask \
    psutil \
    tinytuya \
    requests

# Create necessary directories
echo "📁 Creating directories..."
sudo mkdir -p /var/log
mkdir -p /home/payas/cos/logs
mkdir -p /home/payas/cos/tmp

# Set up log rotation
echo "📜 Setting up log rotation..."
sudo tee /etc/logrotate.d/cos-exhibition > /dev/null << 'EOF'
/var/log/cos-*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 payas payas
}

/home/payas/cos/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 payas payas
}
EOF

# Install systemd service
echo "⚙️  Installing systemd service..."
sudo cp scripts/cos-exhibition.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable I2C
echo "🔌 Enabling I2C interface..."
if ! grep -q "dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
fi

# Add user to required groups
echo "👥 Adding user to required groups..."
sudo usermod -a -G gpio,i2c,audio payas

# Set up unattended upgrades for security
echo "🔒 Configuring automatic security updates..."
sudo dpkg-reconfigure -plow unattended-upgrades

# Create device config if it doesn't exist
if [[ ! -f "config/devices.json" ]]; then
    echo "⚠️  Device configuration not found, creating from example..."
    mkdir -p config
    cp config/devices.example.json config/devices.json
    echo "🔧 Please edit config/devices.json with your actual device credentials"
    echo "💡 Run 'python3 -m tinytuya wizard' to get Tuya device credentials"
fi

# Test the installation
echo "🧪 Testing installation..."
python3 -c "
import sys
sys.path.insert(0, 'core')
try:
    from exhibition_watchdog import ExhibitionWatchdog
    from device_config import DeviceConfig
    print('✅ Core modules import successfully')
except Exception as e:
    print(f'❌ Module import failed: {e}')
    sys.exit(1)
"

# Enable and start the service
echo "🚀 Enabling exhibition service..."
sudo systemctl enable cos-exhibition.service

# Install maintenance cron job
echo "⏰ Installing maintenance schedule..."
(crontab -l 2>/dev/null || echo "") | grep -v "cos/scripts/daily_maintenance.py" | {
    cat
    echo "0 6 * * * /usr/bin/python3 /home/payas/cos/scripts/daily_maintenance.py >> /var/log/cos-maintenance.log 2>&1"
} | crontab -

echo ""
echo "✅ Installation completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit config/devices.json with your actual device credentials"
echo "2. Run: sudo systemctl start cos-exhibition.service"
echo "3. Check status: sudo systemctl status cos-exhibition.service"
echo "4. View logs: sudo journalctl -u cos-exhibition -f"
echo "5. Access web interface: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "Exhibition monitoring:"
echo "- Dashboard: http://$(hostname -I | awk '{print $1}'):5000/exhibition/dashboard"
echo "- Health API: http://$(hostname -I | awk '{print $1}'):5000/exhibition/health"
echo ""
echo "Maintenance:"
echo "- Daily maintenance runs automatically at 6:00 AM"
echo "- Manual run: python3 scripts/daily_maintenance.py"
echo ""
echo "🌊 Code of the Sea is ready for exhibition deployment!"