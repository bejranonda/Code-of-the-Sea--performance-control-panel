#!/bin/bash
# Install WiFi Priority Service

SERVICE_FILE="/home/payas/cos/scripts/wifi-priority.service"
SYSTEM_SERVICE_DIR="/etc/systemd/system"
SERVICE_NAME="wifi-priority"

echo "Installing WiFi Priority Service..."

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root or with sudo"
    echo "Usage: sudo $0"
    exit 1
fi

# Copy service file to systemd directory
echo "Copying service file to $SYSTEM_SERVICE_DIR/"
cp "$SERVICE_FILE" "$SYSTEM_SERVICE_DIR/$SERVICE_NAME.service"

# Set proper permissions
chmod 644 "$SYSTEM_SERVICE_DIR/$SERVICE_NAME.service"

# Reload systemd daemon
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable service to start on boot
echo "Enabling service to start on boot..."
systemctl enable "$SERVICE_NAME.service"

# Start the service
echo "Starting WiFi Priority service..."
systemctl start "$SERVICE_NAME.service"

# Check status
echo "Service status:"
systemctl status "$SERVICE_NAME.service" --no-pager -l

echo ""
echo "WiFi Priority Service installation complete!"
echo ""
echo "Commands to manage the service:"
echo "  sudo systemctl status wifi-priority     # Check service status"
echo "  sudo systemctl start wifi-priority      # Start service"
echo "  sudo systemctl stop wifi-priority       # Stop service"
echo "  sudo systemctl restart wifi-priority    # Restart service"
echo "  sudo journalctl -u wifi-priority -f     # View live logs"
echo ""
echo "Manual WiFi priority check:"
echo "  /home/payas/cos/scripts/wifi_interface_priority.sh status"