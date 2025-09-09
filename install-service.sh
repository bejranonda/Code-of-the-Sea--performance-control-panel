#!/bin/bash
# Install Code of the Sea Control Panel as a systemd service

echo "🚀 Installing Code of the Sea Control Panel Service..."

# Copy service file to systemd directory
sudo cp /home/payas/cos-control-panel.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable cos-control-panel.service

# Start the service
sudo systemctl start cos-control-panel.service

echo "✅ Service installed successfully!"
echo ""
echo "📋 Useful commands:"
echo "  Status:   sudo systemctl status cos-control-panel"
echo "  Stop:     sudo systemctl stop cos-control-panel"
echo "  Start:    sudo systemctl start cos-control-panel"
echo "  Restart:  sudo systemctl restart cos-control-panel"
echo "  Logs:     sudo journalctl -u cos-control-panel -f"
echo "  Disable:  sudo systemctl disable cos-control-panel"
echo ""
echo "🌐 Access your control panel at: http://$(hostname -I | awk '{print $1}'):5000"