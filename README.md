# Code of the Sea
## Raspberry Pi Control Panel for Interactive Art Installation

<img width="1439" height="485" alt="Code of the Sea - Control Panel" src="https://github.com/user-attachments/assets/fc4e5a73-d628-48de-a57d-d57067611a71" />


**An art project collaboration between:**
- **Werapol Bejranonda** (Engineer) 
- **Eunji Lee** (Artist)

---

## 🎨 Project Overview

**Code of the Sea** is an interactive art installation that transforms a Raspberry Pi into a comprehensive control system for multimedia art experiences. The project bridges the technical and artistic realms, providing an intuitive web-based interface to control various hardware components including audio broadcasting, LED lighting systems, FM radio, and environmental monitoring.

This technical implementation serves as the backbone for immersive art installations where visitors can interact with and influence the artistic environment through various controls and real-time feedback systems.

## ✨ Features

### 🎵 **Broadcast System**
- **Audio Playback Control**: Play, pause, stop, next/previous track navigation
- **Multi-format Support**: MP3, WAV, OGG audio files
- **Web Interface**: Browser-based control panel for easy operation
- **Exhibition Ready**: Reliable track navigation without service interruptions
- **Auto-loop Capability**: Seamless audio experiences for installations

### 💡 **LED Lighting Control**
- **Dynamic Lighting**: Programmable LED strip control
- **Color Patterns**: Custom lighting sequences and effects
- **Real-time Control**: Immediate response to user interactions
- **Installation Integration**: Synchronized with other system components

### 📻 **FM Radio Integration**
- **Radio Control**: FM radio tuning and playback
- **Station Management**: Save and recall favorite stations
- **Audio Routing**: Integration with main audio system

### 🌡️ **Environmental Monitoring**
- **Hardware Monitoring**: CPU temperature, memory usage
- **System Health**: Real-time system status monitoring
- **Fan Control**: Automated cooling system management

### 🖥️ **Unified Web Interface**
- **Dashboard Mode**: Comprehensive control panel
- **Simple Mode**: Streamlined interface for basic operations  
- **Enhanced Mode**: Advanced controls for technical users
- **Mobile Responsive**: Works on tablets and smartphones

## 🏗️ System Architecture

```
Code of the Sea Control Panel
│
├── 🎵 Broadcast Module (broadcast/)
│   ├── Audio playback engine (mpg123 integration)
│   ├── Playlist management
│   ├── Media file scanning
│   └── Web API endpoints
│
├── 💡 LED Module (led/)
│   ├── Hardware control (GPIO/SPI)
│   ├── Pattern generation
│   ├── Color management
│   └── Effect scheduling
│
├── 📻 Radio Module (radio/)
│   ├── FM radio control
│   ├── Station presets
│   └── Audio routing
│
├── 🌡️ Hardware Module (fan/)
│   ├── Temperature monitoring
│   ├── Fan control
│   └── System metrics
│
├── 🔧 Core System (core/)
│   ├── Configuration management
│   ├── Service orchestration
│   ├── Logging system
│   └── Hardware abstraction
│
└── 🌐 Web Interface (templates/)
    ├── Dashboard UI
    ├── Control interfaces
    └── Status displays
```

## 🔌 Hardware Connections

### **Raspberry Pi GPIO Pinout**

The Code of the Sea system uses the following hardware components connected to specific GPIO pins:

```
┌─────────────────────────────────────┐
│           Raspberry Pi 4            │
│  ┌─────┬──────────┬──────────┬─────┐│
│  │ 3V3 │    1   2 │    5V    │     ││  
│  │ SDA │    3   4 │    5V    │     ││  ← I2C Data (GPIO2)
│  │ SCL │    5   6 │    GND   │     ││  ← I2C Clock (GPIO3)
│  │     │    7   8 │          │     ││
│  │ GND │    9  10 │          │     ││
│  │     │   11  12 │  GPIO18  │ PWM ││  ← Fan Control
│  │     │   13  14 │    GND   │     ││
│  │     │   15  16 │          │     ││
│  │ 3V3 │   17  18 │          │     ││
│  │     │   19  20 │    GND   │     ││
│  └─────┴──────────┴──────────┴─────┘│
└─────────────────────────────────────┘
```

### **Connected Devices**

#### **🌈 VEML7700 Light Sensor** (LED Service)
```
Raspberry Pi  →  VEML7700
Pin 1  (3V3)  →  VIN
Pin 6  (GND)  →  GND  
Pin 3  (SDA)  →  SDA (I2C Data)
Pin 5  (SCL)  →  SCL (I2C Clock)
```
- **Purpose**: Ambient light sensing for automatic LED brightness control
- **Interface**: I2C Bus 1
- **Used by**: LED lighting service for responsive brightness adjustment

#### **📻 TEA5767 FM Radio Module**
```
Module: TEA5767 FM Radio Tuner
I2C Bus: 1
I2C Address: 0x60
Connection: Via I2C (GPIO2/GPIO3)
```
- **Purpose**: FM radio reception and tuning
- **Interface**: I2C communication
- **Used by**: Radio service for FM broadcast reception

#### **🌀 Fan Control System**
```
Module: Seeed Grove MOSFET (CJQ4435)
Control Pin: GPIO18 (PWM)
PWM Frequency: 10 Hz
```
- **Purpose**: System cooling and ventilation
- **Control**: PWM-based speed control
- **Algorithm**: Located in `fan_mic_option.py`
- **Temperature Sensor**: None (algorithmic control only)

#### **🎵 Audio Output**
```
Audio Interface: 3.5mm jack / HDMI / USB
Player: mpg123
Media Directory: broadcast/media/
Supported Formats: MP3, WAV, OGG
```
- **Purpose**: Audio broadcast for art installation
- **Control**: Web-based playback controls (play, pause, next, previous)
- **Exhibition Ready**: Reliable track navigation without service interruptions

### **I2C Device Summary**
| Device | Address | Purpose | GPIO Pins |
|--------|---------|---------|-----------|
| VEML7700 | 0x10 | Light sensor | SDA(2), SCL(3) |
| TEA5767 | 0x60 | FM radio | SDA(2), SCL(3) |

### **PWM Output Summary**
| Device | Pin | Frequency | Purpose |
|--------|-----|-----------|---------|
| Fan MOSFET | GPIO18 | 10 Hz | Cooling control |

## 🚀 Quick Start

### Prerequisites
- Raspberry Pi 4 (recommended) or Pi 3B+
- MicroSD card (32GB+ recommended)
- Audio output (speakers, headphones, or audio interface)
- Optional: LED strips, FM radio module, cooling fan

### Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/code-of-the-sea.git
   cd code-of-the-sea
   ```

2. **Run Setup Script**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. **Install as System Service**
   ```bash
   sudo ./install-service.sh
   ```

4. **Access the Control Panel**
   - Open your browser to `http://your-pi-ip:5000`
   - Default URL: `http://192.168.1.XXX:5000`

## 📁 Project Structure

```
code-of-the-sea/
│
├── README.md                    # This file
├── setup.sh                    # Initial setup script
├── install-service.sh           # System service installer
├── run.py                      # Application launcher
├── unified_app.py              # Main Flask application
├── cos-control-panel.service   # Systemd service configuration
│
├── broadcast/                  # Audio broadcast system
│   ├── broadcast_menu.py       # Main broadcast controller
│   ├── media/                  # Audio files directory
│   └── README.md              # Broadcast system docs
│
├── led/                       # LED lighting control
│   ├── lighting_menu.py       # LED controller
│   ├── lighting.py           # Hardware interface
│   └── led_config.json       # LED configuration
│
├── radio/                     # FM radio module
│   ├── fm-radio_menu.py      # Radio controller
│   └── radio_config.json     # Radio settings
│
├── fan/                       # Environmental control
│   ├── fan_mic_menu.py       # Fan and monitoring
│   └── fan_status.json       # System metrics
│
├── core/                      # Core system modules
│   ├── config_manager.py     # Configuration management
│   ├── service_manager.py    # Service orchestration
│   ├── hardware_monitor.py   # Hardware monitoring
│   └── logging_setup.py      # Logging configuration
│
├── templates/                 # Web interface templates
│   ├── dashboard.html        # Main dashboard
│   ├── simple.html          # Simplified interface
│   └── enhanced.html         # Advanced controls
│
└── media_samples/            # Example media files (not in repo)
```

## 🎛️ Usage Guide

### Web Interface

1. **Dashboard Mode** - Complete control panel with all features
2. **Simple Mode** - Basic controls for easy operation
3. **Enhanced Mode** - Advanced technical controls

### Broadcast System

- **Start Playback**: Click play button or use API endpoint
- **Track Navigation**: Use next/previous buttons
- **File Management**: Upload files to `broadcast/media/` directory
- **Status Monitoring**: Real-time playback status and playlist info

### LED Control

- **Pattern Selection**: Choose from predefined lighting patterns
- **Color Control**: RGB color picker and presets
- **Brightness**: Adjustable intensity levels
- **Timing**: Configure pattern speeds and transitions

### System Monitoring

- **Hardware Status**: CPU temperature, memory usage
- **Service Health**: Individual module status monitoring
- **Error Logging**: Comprehensive system logs

## 🔧 Configuration

### Device Configuration (Secure Setup)

**🔐 Important**: Device credentials are stored separately from code for security.

1. **Copy Configuration Template**
   ```bash
   cp config/devices.example.json config/devices.json
   ```

2. **Update Device Credentials**
   Edit `config/devices.json` with your actual device information:
   ```json
   {
     "led": {
       "tuya_controller": {
         "device_id": "your_device_id_from_tinytuya_wizard",
         "device_ip": "192.168.1.XXX",
         "device_key": "your_device_key_from_tinytuya_wizard"
       }
     },
     "fan": {
       "grove_mosfet": {
         "fan_pwm_pin": 18,
         "pwm_frequency": 10
       }
     }
   }
   ```

3. **Security Note**: The `config/devices.json` file is automatically excluded from git commits to protect your credentials.

### Main Application Configuration
Edit `unified_config.json` for global settings:

```json
{
    "mode": "dashboard",
    "debug": false,
    "auto_start_services": ["broadcast", "led"]
}
```

### Module-Specific Configuration
Each module has its own configuration file in the respective directory.

## 🎨 Art Installation Setup

### For Exhibition Use

1. **Prepare Media Files**
   ```bash
   # Copy your audio files to the media directory
   cp /path/to/your/audio/* broadcast/media/
   ```

2. **Configure for Kiosk Mode**
   ```bash
   # Edit unified_config.json
   {
       "mode": "simple",
       "auto_start": true,
       "kiosk_mode": true
   }
   ```

3. **Install as Service**
   ```bash
   sudo ./install-service.sh
   ```

4. **Auto-start on Boot**
   - Service automatically starts when Pi boots
   - Accessible via web browser immediately
   - Fault-tolerant with automatic restart

### Hardware Integration

- **Audio**: Connect speakers or audio interface
- **LEDs**: Connect WS2812 LED strips to GPIO pin 18
- **Sensors**: Optional temperature/humidity sensors
- **Display**: Connect monitor for local display (optional)

## 🛠️ Development

### Adding New Modules

1. Create module directory in project root
2. Implement module menu class following existing patterns
3. Add configuration files
4. Register in `run.py` and `unified_app.py`
5. Create web interface templates

### API Endpoints

The system provides RESTful API endpoints for all controls:

```bash
# Broadcast controls
POST /broadcast_control/play
POST /broadcast_control/pause  
POST /broadcast_control/next
GET  /broadcast_status

# LED controls
POST /led_control/pattern/<pattern_name>
POST /led_control/color
GET  /led_status

# System status
GET  /system_status
GET  /service_health
```

## 🔍 Troubleshooting

### Common Issues

**Service Won't Start**
```bash
# Check service status
sudo systemctl status cos-control-panel

# View logs
sudo journalctl -u cos-control-panel -f

# Manual start for debugging
cd /home/payas/cos
python run.py unified
```

**Audio Not Playing**
```bash
# Check audio system
aplay -l

# Test audio output
speaker-test -t wav

# Check mpg123 installation
which mpg123
```

**LED Not Working**
```bash
# Check GPIO permissions
sudo usermod -a -G gpio $USER

# Test LED connection
python -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(18, GPIO.OUT)"
```

## 📜 License

This project is open-source and available under the MIT License. See LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests, report issues, or suggest improvements.

### Development Setup
```bash
# Clone repository
git clone https://github.com/your-username/code-of-the-sea.git

# Install dependencies
cd code-of-the-sea
python -m venv venv
source venv/bin/activate
pip install flask psutil

# Run in development mode
python run.py unified
```

## 📞 Support

For technical support or artistic collaboration inquiries:

- **Technical Issues**: Create an issue on GitHub
- **Art Project Inquiries**: Contact the collaborative team
- **Installation Support**: See troubleshooting section above

## 🎯 Roadmap

### Planned Features
- [ ] Mobile app for remote control
- [ ] Advanced scheduling system
- [ ] Multi-device synchronization
- [ ] Cloud-based configuration backup
- [ ] Extended hardware module support
- [ ] Advanced audio effects processing
- [ ] Integration with external art installations

### Version History
- **v1.0** - Initial release with core functionality
- **v1.1** - Enhanced broadcast system with reliable track navigation
- **v1.2** - Improved LED control and web interface

---

**Code of the Sea** represents the intersection of technology and art, providing a robust platform for interactive installations while maintaining the flexibility needed for creative expression. The collaboration between engineering precision and artistic vision creates possibilities for unique and engaging art experiences.
