# Installation Guide
## Code of the Sea - Complete Setup Instructions

This guide will walk you through setting up the Code of the Sea control panel on a Raspberry Pi for art installation use.

## 🔧 Hardware Requirements

### Minimum Requirements
- **Raspberry Pi 3B+ or newer** (Pi 4 recommended)
- **MicroSD Card**: 32GB Class 10 or better
- **Power Supply**: Official Pi power adapter (5V 3A for Pi 4)
- **Audio Output**: Speakers, headphones, or USB audio interface
- **Network Connection**: WiFi or Ethernet

### Optional Hardware
- **LED Strips**: WS2812/WS2812B addressable LEDs
- **FM Radio Module**: For radio functionality
- **Cooling Fan**: For extended operation
- **Temperature Sensors**: For environmental monitoring
- **External Audio Interface**: For professional audio quality

## 💿 SD Card Preparation

### 1. Flash Raspberry Pi OS
```bash
# Download Raspberry Pi Imager
# Flash Raspberry Pi OS (64-bit recommended)
# Enable SSH in imager settings if needed
```

### 2. Initial Pi Setup
```bash
# Boot Pi and connect to network
# Update system
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install -y git python3-pip python3-venv mpg123 alsa-utils
```

## 📥 Project Installation

### Method 1: Automatic Setup (Recommended)

```bash
# Clone the repository
cd ~
git clone https://github.com/your-username/code-of-the-sea.git
cd code-of-the-sea

# Run automated setup
chmod +x setup.sh
./setup.sh

# Install as system service
sudo ./install-service.sh
```

### Method 2: Manual Setup

```bash
# 1. Clone repository
cd ~
git clone https://github.com/your-username/code-of-the-sea.git
cd code-of-the-sea

# 2. Create virtual environment
python3 -m venv ~/venv
source ~/venv/bin/activate

# 3. Install Python dependencies
pip install flask psutil

# 4. Install system audio packages
sudo apt install -y mpg123 alsa-utils

# 5. Test installation
python run.py unified
```

## 🎵 Audio System Configuration

### 1. Configure Audio Output
```bash
# List available audio devices
aplay -l

# Test audio output
speaker-test -t wav -c 2

# Set default audio device (if needed)
sudo raspi-config
# Navigate to Advanced Options > Audio
```

### 2. Audio Permissions
```bash
# Add user to audio group
sudo usermod -a -G audio $USER

# Reboot to apply changes
sudo reboot
```

## 💡 LED System Setup (Optional)

### 1. Enable SPI Interface
```bash
sudo raspi-config
# Interface Options > SPI > Enable
```

### 2. GPIO Permissions
```bash
# Add user to gpio group  
sudo usermod -a -G gpio $USER

# Install GPIO libraries (if not already installed)
pip install RPi.GPIO
```

### 3. Connect LED Strip
- **Data Pin**: GPIO 18 (Pin 12)
- **Power**: 5V (external power recommended for >10 LEDs)
- **Ground**: Common ground with Pi

## 🌐 Network Configuration

### WiFi Setup
```bash
sudo raspi-config
# System Options > Wireless LAN
# Enter SSID and password
```

### Static IP (Recommended for installations)
```bash
# Edit dhcpcd configuration
sudo nano /etc/dhcpcd.conf

# Add at bottom:
interface wlan0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1
```

## 🔧 Service Installation

### Install as System Service
```bash
cd ~/code-of-the-sea
sudo ./install-service.sh
```

### Service Management
```bash
# Check service status
sudo systemctl status cos-control-panel

# Start service
sudo systemctl start cos-control-panel

# Stop service
sudo systemctl stop cos-control-panel

# Restart service
sudo systemctl restart cos-control-panel

# Enable auto-start on boot
sudo systemctl enable cos-control-panel

# Disable auto-start
sudo systemctl disable cos-control-panel

# View service logs
sudo journalctl -u cos-control-panel -f
```

## 🎨 Exhibition Configuration

### 1. Prepare Media Files
```bash
# Copy your audio files to media directory
cp /path/to/your/audio/* ~/code-of-the-sea/broadcast/media/

# Supported formats: MP3, WAV, OGG
# Files will be automatically detected by the system
```

### 2. Configure for Exhibition
```bash
# Edit main configuration
nano ~/code-of-the-sea/unified_config.json

# Example exhibition configuration:
{
    "mode": "simple",
    "auto_start": true,
    "debug": false,
    "exhibition_mode": true,
    "hardware": {
        "audio_output": "auto",
        "led_enabled": true,
        "led_pin": 18
    }
}
```

### 3. Kiosk Mode Setup (Optional)
```bash
# Install chromium for kiosk mode
sudo apt install -y chromium-browser unclutter

# Create kiosk startup script
nano ~/kiosk.sh

#!/bin/bash
export DISPLAY=:0
chromium-browser --noerrdialogs --disable-infobars --kiosk http://localhost:5000

# Make executable
chmod +x ~/kiosk.sh

# Add to autostart
echo "@/home/pi/kiosk.sh" >> ~/.config/lxsession/LXDE-pi/autostart
```

## 🔍 Testing Installation

### 1. Test Audio System
```bash
# Test system directly
cd ~/code-of-the-sea
python run.py unified

# Should see:
# * Running on http://0.0.0.0:5000
# Access via browser at Pi's IP address
```

### 2. Test Web Interface
- Open browser to `http://your-pi-ip:5000`
- Test broadcast controls (play/pause/next/previous)
- Check system status indicators
- Verify audio playback

### 3. Test Service Installation
```bash
# Stop manual test
Ctrl+C

# Start service
sudo systemctl start cos-control-panel

# Check status
sudo systemctl status cos-control-panel

# Should show: Active (running)
```

## 🛠️ Troubleshooting

### Audio Issues
```bash
# No audio output
sudo apt install -y pulseaudio
pulseaudio --start

# Permission denied errors
sudo usermod -a -G audio $USER
sudo reboot

# Test mpg123 directly
mpg123 /path/to/test.mp3
```

### Service Issues
```bash
# Service won't start - check Python path
which python3
# Update service file if needed

# Permission errors
sudo chown -R pi:pi ~/code-of-the-sea
chmod +x ~/code-of-the-sea/run.py

# View detailed logs
sudo journalctl -u cos-control-panel -f --no-pager
```

### Web Interface Issues
```bash
# Cannot access web interface
# Check firewall
sudo ufw status

# Check service is listening
sudo netstat -tlnp | grep 5000

# Test locally
curl http://localhost:5000
```

### LED Issues
```bash
# LEDs not working
# Check GPIO permissions
ls -l /dev/gpiomem

# Check SPI enabled
ls /dev/spi*

# Test GPIO access
python3 -c "import RPi.GPIO as GPIO; print('GPIO OK')"
```

## 📊 Performance Optimization

### For Art Installations
```bash
# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable cups
sudo systemctl disable avahi-daemon

# Optimize for audio
echo "vm.swappiness=1" | sudo tee -a /etc/sysctl.conf

# Set CPU governor for performance
echo 'GOVERNOR="performance"' | sudo tee -a /etc/default/cpufrequtils
```

### Memory Management
```bash
# Increase GPU memory split for audio
sudo raspi-config
# Advanced Options > Memory Split > 128
```

## 🔄 Updates and Maintenance

### Updating the System
```bash
# Update code
cd ~/code-of-the-sea
git pull origin main

# Restart service
sudo systemctl restart cos-control-panel
```

### Backup Configuration
```bash
# Backup configuration files
tar -czf cos-backup-$(date +%Y%m%d).tar.gz \
    ~/code-of-the-sea/*.json \
    ~/code-of-the-sea/broadcast/media/ \
    /etc/systemd/system/cos-control-panel.service
```

## 🎯 Production Checklist

Before deploying for an art installation:

- [ ] Audio system tested and working
- [ ] All media files uploaded and tested
- [ ] Web interface accessible from all devices
- [ ] Service auto-starts on boot
- [ ] Network configuration stable
- [ ] LED system functioning (if used)
- [ ] Backup configuration created
- [ ] Documentation available on-site
- [ ] Emergency restart procedures documented
- [ ] Contact information available

## 📞 Support

For installation support:
1. Check troubleshooting section above
2. Review system logs: `sudo journalctl -u cos-control-panel -f`
3. Test components individually
4. Create issue on GitHub with log output

---

This installation guide ensures a smooth setup process for the Code of the Sea art installation system.