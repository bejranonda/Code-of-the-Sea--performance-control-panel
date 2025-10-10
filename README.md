# Code of the Sea
> *"Technology becomes invisible when art speaks through it."*

*Raspberry Pi Control Panel for Interactive Art Installation*

**Code of the Sea - Control Panel** transforms a Raspberry Pi into a comprehensive control system for interactive art installations, orchestrating LED lighting, FM radio broadcasting, live audio mixing, and environmental monitoring through a unified Flask web interface.
 
Created through collaboration between engineer and artist, this exhibition-tested system has powered immersive art experiences in Germany and South Korea - proving that technical precision and artistic vision can harmonize in a single, elegant platform. Watch it control lights that dance to sound, mix audience voices into soundscapes, and respond to environmental changes in real-time.

<img width="1462" height="502" alt="image" src="https://github.com/user-attachments/assets/a4d79fc7-3c47-4410-a2a4-a64a531083ca" />

*Control Panel: to config, trigger and monitor all services*

## 📍 Exhibition
### Venue
- **18.10-12.11.2024**: Galerie Markt 21, Weimar, Germany ([@c.keller_weimar](https://www.instagram.com/c.keller_weimar))
- **02.12-14.12.2024**: 예술 공간 [:틈] (Art Space Teum), Seoul, South Korea ([@art.space.tum](https://www.instagram.com/art.space.tum))

### Collaboration
**An art project collaboration between:**
- **Werapol Bejranonda** (Engineer)
- **Eunji Lee** (Artist)

### Thanks
- Supported in **2025** by Kulturstiftung Thüringen ([@kulturstiftung_thueringen](https://www.instagram.com/kulturstiftung_thueringen))
- A huge thank you to *Krittaporn Mahaweerarat* for her suport for technical installation and preparation of the exhibition setup.

---

## 🎨 Project Overview

**Code of the Sea** is an interactive installation exploring how humans might adapt in an age of constant physical and digital migration. Inspired by the horseshoe crab’s protective shell, it imagines future nomads merging clothing, shelter, and technology into one adaptive shell.

The control panel transforms a Raspberry Pi into the **nervous system of this technological organism**, coordinating LEDs, FM radio, live audio, wind, and environmental sensors through a unified Flask web interface. Technology becomes a living, responsive layer—protective, adaptive, and alive.

Exhibited in Germany and South Korea, the system proved exhibition-grade reliable, self-monitoring, and self-healing—an intelligent organism integrating light, sound, and environment into a seamless, resilient whole.

<img width="597" height="319" alt="image" src="https://github.com/user-attachments/assets/fd24e88e-64dc-4f81-89f2-8de3e42079f5" />

*Preparation and validation of the hardware components before the exhibition*

---

## 🧐 If you need to understand more

### ❓ What It Does (Value for different audiences)

> "Inspired by the ancient horseshoe crab (*limule*), whose resilient exoskeleton has ensured its survival for millions of years"

**Code of the Sea** reimagines this natural armor as a technological shell—one that protects, connects, and amplifies interactive art. The system integrates light, sound, communication, and environmental sensing into a unified, adaptive platform for immersive installations.

- **For Artists & Curators:** Exhibition-ready multimedia controller running autonomously 24/7. Orchestrate audio-reactive lights, mix audience voices into soundscapes, tune FM radio, monitor environmental conditions—all through a single web interface.

- **For Exhibition Visitors:** Experience art that breathes and responds. Lights pulse with musical rhythm, your voice becomes part of the sonic landscape, the environment participates—creating immersive spaces where technology dissolves into artistic expression.

- **For Developers & Makers:** Production-ready IoT platform demonstrating professional Raspberry Pi orchestration. Real-time hardware control (I2C sensors, PWM outputs, audio processing), comprehensive monitoring, automatic recovery, modular architecture adaptable for any interactive installation.

### 🎭 The Experience (What people encounter)

> "In a world of constant movement—physical migration, digital nomadism, cultural displacement—this installation embodies **future nomads** who carry their entire environment integrated as a protective technological shell."

The title **"Code of the Sea"** explores how machines interpret human experiences—migration, memory, identity—translating the fluid, boundless nature of existence into discrete signals, like decoding the vast ocean's depths.

**The Installation as Living System:**
- **Light**: Audio-reactive and ambient-responsive luminous environment
- **Sound**: Audience voices mixed into master tracks, becoming part of the soundscape
- **Radio**: Connects to broader electromagnetic spectrum
- **Wind**: Controlled airflow creates breathing patterns, responds to heat and light
- **Environmental Sensing**: Temperature and light monitoring, reacting to gallery space
- **Solar Energy**: Self-sustaining power from 6×2W solar panels, embodying ecological autonomy [*solar panels provide partial energy for the system*]

Together, these create a **robotic, enigmatic form**—a technological organism that protects, responds, and evolves with ecological sustainability, powered by renewable energy like natural organisms drawing sustenance from the sun.

<img width="778" height="459" alt="image" src="https://github.com/user-attachments/assets/c2dfa0e3-0149-48b8-afa1-93447e3a4624" />

*Series of solar panels providing power to the computer (though not sufficient to run the Raspberry Pi)*


### ⚙️ How It Works

> "Think of this system as a **living organism** where each part works independently but contributes to the whole"

#### **🧠 The Brain: Web Control Panel**
- You interact with a simple web interface on your phone or computer—adjusting lights, changing music, tuning the radio. Your command travels instantly to the Raspberry Pi's brain.

#### **💬 The Nervous System: Independent Services**
- Each function (lights, sound, radio, fan) runs as its own "organ"—checking every second for new instructions, making decisions, and updating its status. If one part fails, the others keep working. Like a living body that heals itself.

#### **🎭 Real-Time Response**
1. **You touch a slider** on the web interface
2. **Within 1 second**, your command reaches the service
3. **The service responds immediately** (lights change, music plays, fan speeds up)
4. **Within 15 seconds**, the dashboard updates to confirm the change

#### **🔧 Smart Hardware**
- **Light & Temperature Sensors**: Detect brightness and heat levels automatically
- **FM Radio Module**: Scans and tunes radio frequencies
- **Audio Processing**: Records your voice, mixes it with music, creates soundscapes
- **LED Controllers**: Respond to sound levels, making lights dance to music
- **Fan System**: Creates wind patterns—breathing with the installation, responding to temperature and light
- **Solar Power**: 6 panels (2W each) harvest sunlight → Waveshare Power Manager → USB-C to Raspberry Pi—completely self-sustaining

#### **🛡️ Self-Healing Design**
Three guardian systems watch over everything 24/7:
- **Exhibition Watchdog** checks health every 2 minutes
- **Service Protection** prevents accidental shutdowns every 4 minutes
- **Automatic Recovery** restarts crashed services within 2-3 minutes

If the power goes out, everything remembers its settings and resumes automatically when power returns—like a hibernating animal waking up exactly where it left off.

---

## ✨ Features

### 🎵 **Broadcast Service**
- **Audio Playback Control**: Play, pause, stop, next/previous track navigation
- **Multi-format Support**: MP3, WAV, OGG, M4A, FLAC audio files
- **Playlist Management**: Dynamic file upload, deletion, and organization
- **Web Audio Player**: Browser-based audio preview for current tracks
- **Loop & Random Modes**: Automatic playback modes for exhibitions
- **Volume Control**: Adjustable audio output levels (0-100%)
- **Real-time Status**: Current track, playlist position, playback state

<img width="310" height="417" alt="image" src="https://github.com/user-attachments/assets/e3670e45-bb90-41da-b091-444b91ba7f46" />

*Stereo speakers used to output mixed audio*


### 🎙️ **Mixing Service**
- **Real-time Audio Mixing**: Live microphone recording mixed with master audio tracks
- **Configurable Recording Duration**: 10-300 second recording segments
- **Dual Volume Control**: Independent master audio and microphone volume (0-100%)
- **Auto/Manual Modes**: Continuous auto-mixing or single manual sessions
- **Position-based Mixing**: Sequential audio segments from different master track positions
- **Output Generation**: Mixed audio files saved as timestamped MP3s
- **Status Monitoring**: Real-time recording/mixing status and file counts
- **Enhanced Audio Detection**: Automatic USB microphone detection with PulseAudio support
- **Robust Error Recovery**: Multiple retry attempts with aggressive process cleanup
- **Device Conflict Resolution**: Prevents multiple service instances from accessing audio devices

### 💡 **LED Service**
- **Smart Lighting Control**: VEML7700 light sensor integration with configurable lux ranges
- **Multiple Modes**: Musical LED (audio-reactive), Lux sensor (ambient), Manual LED (direct control)
- **Brightness Control**: Adjustable intensity levels (0-100%) with real-time lux level display
- **Auto-brightness**: Responds to ambient light conditions with configurable min/max lux thresholds
- **Real-time Control**: Immediate response to user interactions and environmental changes
- **Power Management**: On/off control with status monitoring and current light level feedback
- **Musical LED Performance Toggle**: Active/off button to disable LED regardless of audio input
- **Asymmetric Brightness Thresholds**: Different sensitivity for brighter (20) vs darker (30) changes for optimal musical responsiveness

<img width="306" height="320" alt="image" src="https://github.com/user-attachments/assets/c020fee4-96af-475e-a55d-7bfe021e51b6" />

*The LED strip is wirelessly controlled via a Tuya chip.*


### 📻 **Radio Service**
- **FM Radio Control**: TEA5767 module integration for stable radio reception
- **Station Scanning**: Full FM band scan (87-108 MHz) with intelligent signal strength detection
- **Manual Tuning**: Precise frequency control with 0.1 MHz steps and passive frequency stability
- **Station Memory**: Found stations list with signal quality indicators and stereo detection
- **Stable Audio**: Passive frequency mode prevents I2C interference for continuous clear audio
- **Mode Switching**: Fixed frequency (passive), scan, or loop modes with automatic station selection
- **Smart Detection**: Minimum RSSI threshold filtering and stereo preference for optimal stations
- **Loop Mode**: Automatic station cycling with configurable duration and passive frequency setting
- **Enhanced Scan Logic**: Proper mode transitions from scan to fixed/loop based on configuration


<img width="301" height="381" alt="image" src="https://github.com/user-attachments/assets/ecd14ec2-b673-4fa8-8d71-c2bedb859494" />

*FM radio module used as an audio source for mixing*


### 🌀 **Fan Service**
- **Cooling Management**: PWM-controlled fan speed regulation with 5V Grove MOSFET
- **Multiple Modes**:
  - **Fixed**: Constant speed (0-100%)
  - **Cycle**: Sine wave pattern (0→100%→0%) over 2-minute periods
  - **Random**: Random speed changes every 20 seconds
  - **Lux Sensor**: Light-reactive speed control (more light = lower speed) with configurable lux ranges
- **Smart Lux Integration**: VEML7700 sensor with configurable min/max lux values for speed mapping
- **Speed Control**: Variable fan speed (0-100%) with real-time feedback and current lux display
- **Temperature Monitoring**: System temperature awareness for cooling decisions
- **GPIO Integration**: Hardware PWM control via GPIO12 (requires 5V power supply)

<img width="273" height="326" alt="image" src="https://github.com/user-attachments/assets/6f3f720e-2bdd-4dd7-ae26-4d61511f0a9a" />

*PWM-Module regulates the fan speed to control the cooling condition*


### 🌱 **Light Sensor Service**
- **Ambient Light Detection**: VEML7700 high-accuracy light sensor
- **Auto Mode**: Automatic brightness adjustment based on environmental conditions
- **I2C Integration**: Hardware communication via GPIO2/GPIO3
- **Real-time Monitoring**: Continuous light level feedback


<img width="441" height="345" alt="image" src="https://github.com/user-attachments/assets/765c4404-8050-4cb5-a6b3-17243616cedf" />

*The ambient light sensor detects brightness, while the amplifier drives the audio output*


### 🖥️ **Unified Web Interface**
- **Comprehensive Dashboard**: Single-page control for all services
- **Real-time Status**: Live service health monitoring and updates
- **Service Management**: Start, stop, and restart individual services
- **Configuration Management**: Persistent settings for all modules
- **Hardware Monitoring**: CPU, memory, temperature, and uptime tracking
- **Mobile Responsive**: Optimized for tablets and smartphones
- **Exhibition Monitor**: Dedicated monitoring interface for installations

<img width="874" height="914" alt="image" src="https://github.com/user-attachments/assets/a6cc80d9-fe9c-4755-9625-6520aa96af3a" />

*User-Interface: during Performance Mode*

<img width="1484" height="805" alt="image" src="https://github.com/user-attachments/assets/de0df485-1ec9-452e-9f14-19c987b18f3e" />

*Exhibition Monitor: to observe the environment and resources used in the technical parts*


<img width="1476" height="724" alt="image" src="https://github.com/user-attachments/assets/f1d5cb9b-0c4e-462e-b4b8-e51861337363" />

*System Health Monitor: to observe the technical issues in hardware*


<img width="463" height="307" alt="image" src="https://github.com/user-attachments/assets/05a05f41-fbe6-4657-a68b-17f8ae20a86b" />

*LED controlled by sound level detected by microphone*



## 💡 Recommended Lux Configuration

The VEML7700 light sensor enables intelligent control of both LED brightness and fan speed based on ambient light levels. The following configurations provide optimal performance for different environments:

### **LED Service - Lux-to-Brightness Mapping**

**Default Configuration:**
- **Min Lux (100% brightness)**: 20 lux
- **Max Lux (0% brightness)**: 1500 lux

**Recommended Settings by Environment:**

| Environment | Min Lux | Max Lux | Description |
|-------------|---------|---------|-------------|
| **Indoor Office** | 20 lux | 800 lux | Typical office lighting (200-500 lux) |
| **Home Interior** | 10 lux | 400 lux | Living rooms, bedrooms (50-200 lux) |
| **Art Gallery** | 50 lux | 1000 lux | Museum lighting (150-300 lux) |
| **Outdoor Display** | 100 lux | 5000 lux | Variable daylight conditions |
| **Stage/Performance** | 5 lux | 2000 lux | Dramatic lighting changes |

**Typical Lux Values for Reference:**
- 0.1 lux: Moonlight
- 1 lux: Candle at 1 meter
- 10-50 lux: Dimly lit room
- 100-300 lux: Well-lit indoor space
- 500-1000 lux: Bright office lighting
- 1000-5000 lux: Cloudy day outdoors
- 10000+ lux: Direct sunlight

### **Fan Service - Lux-to-Speed Mapping**

**Default Configuration:**
- **Min Lux (100% speed)**: 1 lux
- **Max Lux (0% speed)**: 1000 lux

**Recommended Settings by Use Case:**

| Use Case | Min Lux | Max Lux | Description |
|----------|---------|---------|-------------|
| **Energy Efficient** | 10 lux | 500 lux | Moderate cooling in normal conditions |
| **Performance Cooling** | 1 lux | 300 lux | Aggressive cooling for high-performance systems |
| **Exhibition Space** | 50 lux | 800 lux | Quiet operation during bright gallery hours |
| **Outdoor Installation** | 5 lux | 2000 lux | Full range for day/night cycles |
| **Server Room** | 1 lux | 100 lux | Maximum cooling in low-light environments |

**Configuration Tips:**
1. **Min Lux**: Set to the darkest condition where maximum response is needed
2. **Max Lux**: Set to the brightest condition where minimum response is acceptable
3. **Range Selection**: Wider ranges provide more gradual transitions
4. **Testing**: Monitor actual lux values in your environment using the dashboard

## 🏗️ System Architecture

```
Code of the Sea Control Panel
│
├── 🎵 Broadcast Service (broadcast/)
│   ├── broadcast_menu.py - Main controller and mpg123 integration
│   ├── media/ - Audio file storage directory
│   ├── Web player controls (play, pause, next, previous)
│   ├── File management (upload, delete)
│   └── Status: current_file, playing, playlist, volume
│
├── 🎙️ Mixing Service (mixing/)
│   ├── mixing_menu.py - Audio recording and mixing engine
│   ├── Real-time microphone recording (arecord)
│   ├── FFmpeg audio processing and volume control
│   ├── Position-based master audio segmentation
│   ├── mixing_status.json - Real-time status tracking
│   └── Output: timestamped mixed audio files
│
├── 💡 LED Service (led/)
│   ├── lighting_menu.py - VEML7700 sensor integration with configurable lux ranges
│   ├── led_config.json - Device configuration
│   ├── led_status.json - Current state tracking with lux level
│   ├── Modes: Musical LED, Lux sensor (ambient), Manual LED
│   └── I2C hardware communication (GPIO2/GPIO3)
│
├── 📻 Radio Service (radio/)
│   ├── fm-radio_menu.py - TEA5767 radio module control with passive frequency stability
│   ├── FM band scanning (87-108 MHz) with intelligent station detection
│   ├── Signal strength monitoring with RSSI thresholds
│   ├── Station memory and selection with stereo preference
│   └── I2C communication (GPIO2/GPIO3) with interference prevention
│
├── 🌀 Fan Service (fan/)
│   ├── fan_mic_menu.py - PWM fan control with VEML7700 integration
│   ├── fan_status.json - Speed, mode tracking, and lux level
│   ├── Modes: Fixed, Cycle, Random, Lux Sensor (configurable ranges)
│   ├── GPIO12 PWM control (10Hz frequency)
│   └── Temperature-based speed adjustment with real-time lux display
│
├── 🌱 Light Sensor Service (light_sensor/)
│   ├── Ambient light monitoring (VEML7700)
│   ├── Auto-brightness integration
│   └── I2C sensor communication
│
├── 🔧 Core System
│   ├── unified_app.py - Flask web server and routing
│   ├── service_config.json - Global service configuration
│   ├── Service health monitoring and management
│   ├── Hardware status tracking (CPU, memory, temperature)
│   └── Unified logging and error handling
│
└── 🌐 Web Interface (templates/)
    ├── dashboard.html - Main control interface
    ├── exhibition/dashboard.html - Exhibition monitoring
    ├── Real-time service status updates
    ├── Interactive sliders and controls
    └── Mobile-responsive design
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
│  │     │   11  12 │  GPIO12  │ PWM ││  ← Fan Control
│  │     │   13  14 │    GND   │     ││
│  │     │   15  16 │          │     ││
│  │ 3V3 │   17  18 │          │     ││
│  │     │   19  20 │    GND   │     ││
│  └─────┴──────────┴──────────┴─────┘│
└─────────────────────────────────────┘
```

<img width="373" height="626" alt="image" src="https://github.com/user-attachments/assets/4ae7859f-9abc-4691-b00c-8d888be2b7f1" />

*The Raspberry Pi serves as the central controller for all sensors and actuators*


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
- **Interface**: I2C Bus 1 (Address: 0x10)
- **Used by**: LED Service for responsive brightness adjustment
- **Modes**: Auto-brightness in Lighting LED mode
- **Status Tracking**: Real-time light level monitoring

#### **📻 TEA5767 FM Radio Module** (Radio Service)
```
Module: TEA5767 FM Radio Tuner
I2C Bus: 1
I2C Address: 0x60
Connection: Via I2C (GPIO2/GPIO3)
```
- **Purpose**: FM radio reception and tuning
- **Interface**: I2C communication
- **Used by**: Radio Service for FM broadcast reception
- **Features**: Full band scanning, signal strength detection, stereo detection
- **Range**: 87.0-108.0 MHz with 0.1 MHz precision

#### **🌀 Fan Control System** (Fan Service)
```
Module: Seeed Grove MOSFET (CJQ4435)
Control Pin: GPIO12 (PWM)
PWM Frequency: 10 Hz
Control Range: 0-100% duty cycle
```
- **Purpose**: System cooling and ventilation
- **Control**: PWM-based speed control via fan_mic_menu.py
- **Modes**: Fixed speed, Cycle, Random patterns, Sound-reactive
- **Temperature Integration**: CPU temperature monitoring for automatic speed adjustment
- **Real-time Feedback**: Current and target speed monitoring

#### **🎵 Audio System** (Broadcast & Mixing Services)
```
Broadcast Audio:
  Interface: 3.5mm jack / HDMI / USB
  Player: mpg123
  Media Directory: broadcast/media/
  Supported Formats: MP3, WAV, OGG, M4A, FLAC

Mixing Audio:
  Input: USB microphone (arecord)
  Processing: FFmpeg audio mixing
  Output: Mixed MP3 files in mixing/
  Recording Duration: 10-300 seconds (configurable)
```
- **Broadcast Purpose**: Audio playback for art installations
- **Mixing Purpose**: Real-time audio interaction and recording
- **Control**: Web-based playback controls and volume adjustment
- **Status**: Real-time playback state, file position, mixing progress

#### **💾 USB Audio Device** (Mixing Service)
```
Device: USB microphone or audio interface
Capture Tool: arecord (ALSA)
Sample Rate: 44.1 kHz
Format: WAV (converted to MP3)
```
- **Purpose**: Live audio capture for mixing with master tracks
- **Integration**: Automatic device detection and configuration
- **Processing**: Real-time volume control and audio mixing
- **Output**: Synchronized mixed audio files with timestamps

#### **☀️ Solar Power System** (Power Supply)
```
Solar Panels: 6 panels × 2W each (12W total)
Power Manager: Waveshare Solar Power Manager Module D
Output: 5V/3A via USB-C
Connection: USB-C → Raspberry Pi power input
Battery Management: Integrated charge controller
```
- **Purpose**: Self-sustaining renewable power for off-grid installations
- **Capacity**: 12W solar generation for daylight operation
- **Features**:
  - Automatic battery charging and discharge management
  - Power regulation to stable 5V for Raspberry Pi
  - Integrated over-charge and over-discharge protection
  - Allows 24/7 operation with battery backup
- **Ecological Significance**: Enables completely autonomous art installations powered by sunlight
- **Installation**: Position panels for maximum sun exposure (south-facing in Northern Hemisphere)

### **I2C Device Summary**
| Device | Address | Purpose | GPIO Pins |
|--------|---------|---------|-----------|
| VEML7700 | 0x10 | Light sensor | SDA(2), SCL(3) |
| TEA5767 | 0x60 | FM radio | SDA(2), SCL(3) |

### **PWM Output Summary**
| Device | Pin | Frequency | Purpose |
|--------|-----|-----------|---------|
| Fan MOSFET | GPIO12 | 10 Hz | Cooling control |

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
├── README.md                    # This file - Complete system documentation
├── setup.sh                    # Initial setup script (if exists)
├── run.py                      # Application launcher - Service startup
├── unified_app.py              # Main Flask web application
├── service_config.json         # Global service configuration
├── app_menu.py                 # Menu system integration
│
├── broadcast/                  # Audio broadcast system
│   ├── broadcast_menu.py       # Main controller - mpg123 integration
│   ├── broadcast_status.json   # Current playback status
│   ├── media/                  # Audio files directory (MP3, WAV, OGG, etc.)
│   └── playlist management and web controls
│
├── mixing/                     # Real-time audio mixing system
│   ├── mixing_menu.py          # Audio recording and mixing engine
│   ├── mixing_status.json      # Real-time recording/mixing status
│   ├── mixing_log.txt          # Detailed operation logs
│   ├── Microphone recording (arecord integration)
│   ├── FFmpeg audio processing and volume control
│   └── Output: mixed_audio_YYYYMMDD_HHMMSS.mp3
│
├── led/                        # LED lighting control system
│   ├── lighting_menu.py        # VEML7700 sensor and LED controller
│   ├── led_config.json         # Device configuration and credentials
│   ├── led_status.json         # Current brightness, mode, power state
│   ├── tinytuya.json           # Tuya device integration
│   └── I2C light sensor integration
│
├── radio/                      # FM radio control system
│   ├── fm-radio_menu.py        # TEA5767 radio module controller
│   ├── radio_status.json       # Current frequency, signal, mode
│   ├── FM band scanning (87-108 MHz)
│   ├── Station memory and signal strength monitoring
│   └── I2C radio module communication
│
├── fan/                        # Environmental control system
│   ├── fan_mic_menu.py         # PWM fan control and monitoring
│   ├── fan_status.json         # Speed, mode, temperature tracking
│   ├── GPIO12 PWM control (10Hz frequency)
│   ├── Multiple modes: Fixed, Cycle, Random, Lux (light-reactive)
│   └── CPU temperature monitoring integration
│
├── light_sensor/               # Light sensor service (if separate)
│   ├── Ambient light monitoring
│   ├── VEML7700 sensor integration
│   └── Auto-brightness functionality
│
├── templates/                  # Web interface templates
│   ├── dashboard.html          # Main control dashboard
│   ├── exhibition/
│   │   └── dashboard.html      # Exhibition monitoring interface
│   ├── Real-time status displays
│   ├── Interactive control sliders
│   └── Mobile-responsive design
│
├── logs/                       # System logs and diagnostics
│   ├── wifi_diagnostics_*.json # Network monitoring logs
│   ├── Service-specific log files
│   └── Error tracking and debugging
│
├── scripts/                    # Utility scripts
│   ├── start_wifi_monitor.sh   # Network monitoring
│   └── System maintenance scripts
│
└── static/                     # Web assets (CSS, JS, images)
    ├── CSS styling and responsive design
    ├── JavaScript for interactive controls
    └── Media file serving
```

## 🛠️ Service Management System (v3.0)

**Code of the Sea v3.0** introduces a comprehensive service management system that ensures reliable, single-instance operation of all services with proper startup, shutdown, and monitoring capabilities.

### **🔧 Systemd Service Configuration**

The system uses multiple systemd services for automatic startup and management:

#### **cos-control-panel.service** (Main Application)
- **Description**: Code of the Sea Control Panel - Main Flask web application
- **User**: payas (runs as regular user, not root)
- **Working Directory**: `/home/payas/cos`
- **Command**: `/home/payas/venv/bin/python /home/payas/cos/run.py unified --no-debug`
- **Auto-restart**: Yes (15-second delay)
- **Resource Limits**: 768MB RAM, 70% CPU quota
- **Dependencies**: Waits for network and sound systems, starts after cos-services.service

#### **cos-services.service** (Service Startup)
- **Description**: COS All Services Startup (Optimized) - Starts all individual services
- **Type**: oneshot (runs once then exits)
- **Script**: `/home/payas/cos/scripts/startup_services_optimized.sh`
- **Startup Logic**: Conflict-aware sequential startup with audio system coordination
- **Timeout**: 120 seconds for complete startup sequence
- **Dependencies**: Waits for network and sound systems

#### **Startup Sequence** (startup_services_optimized.sh)
1. **Phase 1**: Non-audio services (Radio, Fan) - 15-second system readiness wait
2. **Audio System Check**: Waits for PulseAudio/ALSA to be ready
3. **Phase 2**: Audio-dependent services (LED primary, then Broadcast)
4. **Phase 3**: Mixing service (starts in disabled mode to prevent conflicts)
5. **Health Check**: Verifies all services started successfully

#### **Service Management Commands**
```bash
# Check service status
sudo systemctl status cos-control-panel
sudo systemctl status cos-services

# Start/stop main services
sudo systemctl start cos-control-panel
sudo systemctl stop cos-control-panel

# View logs
sudo journalctl -u cos-control-panel -f
sudo journalctl -u cos-services -f

# Enable/disable auto-start
sudo systemctl enable cos-control-panel
sudo systemctl disable cos-control-panel
```

### **🎯 Key Features**
- **Single Instance Enforcement**: Prevents duplicate service processes that cause conflicts
- **Automatic Process Cleanup**: Intelligent detection and removal of zombie/stuck processes
- **Centralized Management**: Unified control system for all services
- **Enhanced Error Recovery**: Robust error handling with automatic retry mechanisms
- **PulseAudio Integration**: Improved microphone recording with fallback to ALSA
- **Debug Mode Optimization**: Fixed Flask debug mode to prevent process duplication

### **🔧 Service Management Scripts**

All services now have dedicated management scripts in `/scripts/`:

```bash
# Individual Service Management
./manage_radio_service.sh {start|stop|restart|status}
./manage_led_service.sh {start|stop|restart|status}
./manage_fan_service.sh {start|stop|restart|status}
./manage_broadcast_service.sh {start|stop|restart|status}
./manage_mixing_service.sh {start|stop|restart|status}
./manage_unified_app.sh {start|stop|restart|status}

# Master Service Control
./manage_all_services.sh {start|stop|restart|status} [service_name]
```

### **⚡ Quick Service Commands**

From the main directory (`/home/payas/cos/`):

```bash
# Control all services
./services start           # Start all services
./services stop            # Stop all services
./services restart         # Restart all services
./services status          # Check all service status

# Control individual services
./services start radio     # Start only radio service
./services restart mixing  # Restart only mixing service
./services status led      # Check only LED service status
```

### **🔄 Smart Process Management**

Each service management script implements:

1. **Pre-start Cleanup**: Automatically kills existing instances before starting
2. **PID File Management**: Tracks process IDs with cleanup of stale files
3. **Graceful Shutdown**: SIGTERM followed by SIGKILL if needed
4. **Process Verification**: Confirms successful start/stop operations
5. **Comprehensive Status**: Detailed process state reporting

### **📊 Enhanced Monitoring**

The unified app now provides:
- **Real-time Service Health**: Color-coded status indicators
- **Process Tracking**: Live PID monitoring and restart detection
- **Error Recovery**: Automatic restart on service failures
- **Resource Monitoring**: CPU, memory, and system health tracking

## 🔄 Complete System Workflow

### Service Startup and Management

The Code of the Sea system follows a comprehensive startup and management workflow:

```
1. System Boot
   └── Auto-start main application (if service installed)
   └── Initialize hardware resources (GPIO, I2C, PWM)
   └── Load service configurations from JSON files
   └── Start Flask web server (port 5000)

2. Service Initialization
   ├── Broadcast Service: Load media files, initialize mpg123
   ├── Mixing Service: Detect USB audio devices, setup recording
   ├── LED Service: Connect to VEML7700 sensor, initialize Tuya device
   ├── Radio Service: Initialize TEA5767, perform communication test
   ├── Fan Service: Setup GPIO12 PWM, initialize VEML7700
   └── Light Sensor: VEML7700 I2C initialization

3. Runtime Operation
   ├── Web Interface: Real-time status updates every 15 seconds
   ├── Service Monitoring: Health checks and automatic restart on failure
   ├── Configuration Persistence: Auto-save settings on user changes
   └── Hardware Monitoring: CPU, memory, temperature tracking

4. Service Communication
   ├── Inter-service JSON file communication
   ├── Hardware I2C bus sharing (VEML7700 + TEA5767)
   ├── Independent GPIO control (PWM, LED)
   └── Web API endpoints for real-time control
```

### Monitoring and Diagnostics Workflow

```
Real-time Monitoring Pipeline:
├── Hardware Status Collection (every 15s)
│   ├── CPU usage, temperature, memory
│   ├── Disk space and system uptime
│   └── GPIO and I2C device status

├── Service Health Monitoring (continuous)
│   ├── Process existence and PID tracking
│   ├── Service-specific status files
│   ├── Error count accumulation
│   └── Color-coded health indicators

├── Environmental Monitoring (continuous)
│   ├── VEML7700 lux level readings
│   ├── Automatic brightness/speed adjustments
│   └── Real-time dashboard updates

└── Error Handling and Recovery
    ├── Automatic service restart on failure
    ├── I2C communication retry mechanisms
    ├── Configuration fallback to defaults
    └── Comprehensive logging and alerts
```

## 🎛️ Usage Guide

### Web Interface Access

1. **Main Dashboard** (`http://pi-ip:5000/`) - Complete control panel with all services
2. **Exhibition Monitor** (`http://pi-ip:5000/exhibition/dashboard`) - Monitoring interface for installations
3. **System Logs** (`http://pi-ip:5000/logs`) - Comprehensive logging and debugging

### Service Operation

#### **🎵 Broadcast Service**
- **Playback Control**: Play, pause, stop, next, previous track buttons
- **File Management**: Web-based file upload (drag & drop) and deletion
- **Playlist Navigation**: Visual playlist with current track highlighting
- **Volume Control**: Adjustable output volume (0-100%)
- **Mode Selection**: Loop (sequential) or Random playback
- **Web Audio Player**: Browser preview of current track
- **Status Monitoring**: Real-time track position, playlist info, playback state

#### **🎙️ Mixing Service**
- **Recording Control**: Auto mode (continuous) or Once mode (manual)
- **Duration Settings**: Configurable recording length (10-300 seconds)
- **Volume Mixing**: Independent master audio (0-100%) and microphone (0-100%) levels
- **Real-time Status**: Recording/mixing progress, file counts, current operation
- **Output Files**: Timestamped mixed audio files (mixed_audio_YYYYMMDD_HHMMSS.mp3)
- **Position Tracking**: Sequential master audio segments for varied mixing

#### **💡 LED Service**
- **Mode Selection**: Musical LED (audio-reactive), Lighting LED (ambient), Manual LED (direct)
- **Brightness Control**: Manual brightness adjustment (0-100%) in Manual LED mode
- **Auto-brightness**: VEML7700 sensor integration for ambient light response
- **Power Control**: On/off switching with status feedback
- **Connection Status**: Real-time device communication monitoring
- **Musical LED Advanced Options**:
  - **Performance Toggle**: `musical_led_active` setting ("active" or "off") to disable LED regardless of audio input
  - **Asymmetric Brightness Thresholds**: Separate sensitivity for brighter (20 points) vs darker (30 points) changes
  - **Below Threshold Behavior**: `musical_led_below_threshold` configures LED behavior when audio is quiet
  - **Minimum Brightness**: `musical_led_minimum_brightness` sets lowest LED level when staying on


#### **📻 Radio Service**
- **Tuning Control**: Manual frequency slider (87.0-108.0 MHz, 0.1 MHz steps) with passive stability
- **Station Scanning**: Full FM band scan with intelligent signal strength detection and stereo preference
- **Station Selection**: Click-to-tune from scanned station list with automatic station memory
- **Signal Monitoring**: Real-time signal strength bars and quality indicators
- **Mode Switching**: Fixed frequency (passive) or scan mode with automatic best station selection
- **Stereo Detection**: Visual indicators for stereo broadcasts with quality-based filtering
- **Stable Operation**: Passive frequency mode prevents I2C interference for continuous clear audio
- **Smart Scanning**: Configurable RSSI thresholds and automatic station quality assessment

#### **🌀 Fan Service**
- **Mode Selection**: Fixed, Cycle, Random, Lux Sensor (light-reactive with configurable ranges)
- **Speed Control**: Manual fan speed (0-100%) in Fixed mode with real-time current lux display
- **Auto Modes**:
  - **Cycle**: Sine wave pattern (0→100%→0%) over 2-minute cycles
  - **Random**: Random speed changes every 20 seconds
  - **Lux Sensor**: Light-reactive speed control with configurable min/max lux thresholds (more light = lower speed)
- **Smart Configuration**: Configurable lux ranges for different environments (1-5000 lux range)
- **Hardware Requirements**: 5V power supply for Grove MOSFET module, VEML7700 sensor
- **Temperature Integration**: CPU temperature monitoring for automatic adjustments
- **Real-time Feedback**: Current speed, target speed, mode status, and ambient light level

### System Management

#### **Service Control**
- **Individual Services**: Start, stop, restart each service independently
- **Service Health**: Color-coded status indicators (Healthy, Warning, Error)
- **Process Monitoring**: Real-time PID tracking and service state
- **Configuration Persistence**: Settings saved automatically on change

#### **Hardware Monitoring**
- **CPU Usage**: Real-time processor utilization with progress bars
- **Memory Usage**: RAM utilization tracking
- **CPU Temperature**: Thermal monitoring with color-coded warnings
- **Disk Usage**: Storage utilization monitoring
- **System Uptime**: Hours and minutes since last boot
- **Active Services**: Count of running services

#### **Logging and Diagnostics**
- **Service Logs**: Individual log files for each service
- **Main System Logs**: Unified application logging
- **Error Tracking**: Error count monitoring and reporting
- **WiFi Diagnostics**: Network connectivity monitoring
- **Real-time Updates**: Auto-refreshing status every 15 seconds

## 🛡️ Advanced System Monitoring & Protection

The Code of the Sea system includes a comprehensive multi-layer monitoring and protection system designed for reliable long-term operation in art installations and exhibition environments.

### **🔍 System Monitoring Architecture**

#### **Multi-Layer Monitoring System**
The system employs three coordinated monitoring layers that work together without conflicts:

1. **Exhibition Watchdog** (`core/exhibition_watchdog.py`) - 120-second intervals
2. **Service Protection Manager** (`core/service_protection.py`) - 240-second intervals
3. **Cron-based Monitoring** - 2-3 minute intervals per service

#### **Lock-based Coordination**
- Uses `/tmp/cos_protection.lock` to prevent monitoring conflicts
- Staggered timing ensures comprehensive coverage without resource competition
- Graceful degradation when multiple monitors are active

### **🚨 Exhibition Watchdog System**

The Exhibition Watchdog provides comprehensive system health monitoring optimized for art installations:

#### **Key Features:**
- **Continuous Health Monitoring**: CPU, memory, temperature, disk usage
- **Network Stability Tracking**: WiFi diagnostics with interference detection
- **Hardware Health Checks**: I2C devices (VEML7700, TEA5767), GPIO functionality
- **Automatic Recovery**: Memory leak detection, zombie process cleanup
- **Resource Management**: System cleanup, cache management, log rotation

#### **Thresholds and Actions:**
```
CPU Usage > 90%        → Process analysis and cleanup
Memory Usage > 85%     → Memory leak detection and restart
Temperature > 75°C     → Thermal monitoring and fan control
Disk Usage > 95%       → Cleanup old logs and temporary files
Network Failures > 2   → Network stack recovery procedures
```

#### **Advanced Network Monitoring:**
- **WiFi Signal Analysis**: Real-time signal strength and interference detection
- **Power Management Detection**: Identifies WiFi disconnection causes
- **Gateway Connectivity**: Dynamic gateway detection and testing
- **DNS Resolution Testing**: Comprehensive network stack validation
- **Detailed Diagnostics**: Saves WiFi diagnostics to `/home/payas/cos/logs/` for analysis

### **🔧 Service Protection System**

The Service Protection Manager prevents inappropriate service stops and ensures service persistence:

#### **Protection Features:**
- **Self-Stop Prevention**: Prevents services from entering "Disable" mode inappropriately
- **Config Restoration**: Automatically restores service configurations from "Disable" to working modes
- **Performance Mode Awareness**: Allows proper stops during LED performance modes
- **Automatic Restart**: Restarts crashed or stopped services when appropriate

#### **Service-Specific Protection:**
```
Fan Service      → Restored to "Fixed" mode
Broadcast Service → Restored to "Auto" mode
Mixing Service   → Restored to "Manual" mode
Radio Service    → Restored to "Auto" mode
LED Service      → Restored to "Manual LED" mode
```

#### **Performance Mode Integration:**
- **Musical/Manual LED Mode**: Creates `/tmp/cos_performance_mode_active` flag
- **Service Coordination**: Prevents cron jobs from restarting services during performance
- **Automatic LED Switching**: Switches LED to "Lux sensor" mode when exiting performance
- **Audio Conflict Prevention**: Ensures only LED service uses audio device during performance

### **⏰ Automated Monitoring (Cron Jobs)**

Cron-based monitoring provides immediate service restart capabilities:

```bash
# LED Service monitoring (every 2 minutes)
*/2 * * * * /home/payas/cos/scripts/manage_led_service.sh status >/dev/null 2>&1 || start

# Other services monitoring (every 3 minutes)
*/3 * * * * /home/payas/cos/scripts/manage_fan_service.sh status >/dev/null 2>&1 || start
*/3 * * * * /home/payas/cos/scripts/manage_broadcast_service.sh status >/dev/null 2>&1 || start
*/3 * * * * /home/payas/cos/scripts/manage_mixing_service.sh status >/dev/null 2>&1 || start
*/3 * * * * /home/payas/cos/scripts/manage_radio_service.sh status >/dev/null 2>&1 || start

# Service state backup (every 5 minutes)
*/5 * * * * /home/payas/cos/scripts/periodic_service_backup.sh >/dev/null 2>&1
```

### **🛠️ Service Management Scripts**

Each service has a dedicated management script with comprehensive functionality:

#### **Script Capabilities:**
- **Status Checking**: PID-based process verification with cleanup of stale PID files
- **Safe Starting**: Prevents multiple instances, handles existing processes
- **Clean Stopping**: Graceful termination with SIGTERM/SIGKILL progression
- **Process Cleanup**: Removes zombie processes and cleans up temporary files
- **Logging Integration**: Comprehensive logging of all start/stop operations

#### **Management Script Locations:**
```
scripts/manage_led_service.sh      → LED Service management
scripts/manage_fan_service.sh      → Fan Service management
scripts/manage_broadcast_service.sh → Broadcast Service management
scripts/manage_mixing_service.sh   → Mixing Service management
scripts/manage_radio_service.sh    → Radio Service management
scripts/manage_unified_app.sh      → Main application management
```

### **📊 Service State Persistence**

The system maintains service state across restarts and failures:

#### **State Tracking:**
- **Running Services**: Current active service list
- **Manually Stopped**: User-initiated service stops (preserved across restarts)
- **Service History**: Timestamped record of all service state changes
- **Protection Status**: Per-service protection settings and reasons

#### **State Files:**
```
cos_service_state.json           → Current service state
service_protection.log           → Protection system events
service_events.log              → Detailed service start/stop history
/tmp/cos_protection.lock        → Monitoring coordination lock
/tmp/cos_performance_mode_active → Performance mode flag
```

### **⚠️ Error Prevention & Recovery**

#### **Common Issues Prevented:**
- **Audio Device Conflicts**: Automatic LED mode switching prevents device competition
- **Service Self-Stopping**: Config protection prevents inappropriate "Disable" mode switches
- **Memory Leaks**: Watchdog detects and handles memory leak patterns
- **Network Instability**: Advanced WiFi diagnostics and automatic recovery
- **Hardware Failures**: I2C bus recovery and GPIO reset procedures
- **Process Zombies**: Automated cleanup of stuck and orphaned processes

#### **Recovery Procedures:**
- **Service Restart Limits**: Maximum 3 restarts per hour per service
- **Hardware Reset**: I2C driver reload, GPIO cleanup, PWM reset
- **Network Recovery**: WiFi interface restart, wpa_supplicant reload, DHCP renewal
- **Memory Cleanup**: Cache clearing, temp file removal, log rotation
- **Process Cleanup**: Zombie process elimination, resource release

### **📈 Monitoring Status & Logs**

#### **Real-time Status:**
```bash
# Check service protection status
python3 core/service_protection.py status

# Check exhibition watchdog health
tail -f logs/cos-watchdog.log

# View service events history
tail -f service_events.log

# Check cron monitoring
tail -f /var/log/syslog | grep cos
```

#### **Log Files:**
```
unified_app.log                 → Main application events
service_protection.log          → Protection system activity
logs/cos-watchdog.log          → Exhibition watchdog events
service_events.log             → Service start/stop history
reboot_monitor.log             → System reboot events
logs/wifi_diagnostics_*.json   → WiFi connectivity analysis
```

### **🔄 Performance Mode Service Management**

#### **Performance Mode Behavior:**
When entering LED performance modes (Musical LED, Manual LED):

1. **Service Stopping**: All non-LED services are stopped using management scripts
2. **Flag Creation**: `/tmp/cos_performance_mode_active` prevents cron restarts
3. **Audio Exclusivity**: LED service gets exclusive audio device access
4. **Protection Coordination**: Service protection system recognizes performance mode

#### **Performance Mode Exit:**
When exiting performance mode:

1. **LED Auto-Switch**: LED automatically switches to "Lux sensor" mode
2. **Service Restart**: All stopped services are restarted automatically
3. **Flag Removal**: Performance mode flag is removed, allowing normal monitoring
4. **Audio Conflict Prevention**: "Lux sensor" mode prevents audio device conflicts

#### **Audio Device Management:**
- **Performance Modes**: LED service uses audio input for reactive lighting
- **Normal Operation**: LED in "Lux sensor" mode allows other services audio access
- **Conflict Prevention**: Automatic mode switching ensures clean audio device handoff
- **PulseAudio Integration**: Proper audio device cleanup during mode switches

This comprehensive monitoring system ensures reliable, long-term operation suitable for art installations, exhibitions, and unattended deployments while providing detailed diagnostics and automatic error recovery.

## 🔧 Configuration

### 📁 Playlist File Management

**Playlist File Limit Configuration:**

The broadcast service automatically manages playlist files to prevent storage overflow. By default, only the **5 newest** audio files are kept in the broadcast media directory, with older files automatically deleted.

**To change the playlist file limit:**

1. **Location**: Edit `/home/payas/cos/mixing/mixing_menu.py`
2. **Line**: 664
3. **Change**: Replace `5` with your desired number of files to keep

```python
# Line 664 in mixing/mixing_menu.py
cleanup_old_files(BROADCAST_MEDIA_DIR, 5)  # Change this 5 to your desired limit
```

**How it works:**
- Cleanup happens automatically after each audio mixing operation
- Files are sorted by modification time (newest first)
- Only the specified number of newest files are kept
- Older files are deleted and logged with "Removed old file: filename.mp3"
- The broadcast media directory is located at `/home/payas/cos/broadcast/media/`

**Examples:**
```python
cleanup_old_files(BROADCAST_MEDIA_DIR, 10)  # Keep 10 files
cleanup_old_files(BROADCAST_MEDIA_DIR, 20)  # Keep 20 files
cleanup_old_files(BROADCAST_MEDIA_DIR, 3)   # Keep only 3 files
```

### 💡 **Musical LED Brightness Configuration**

**Advanced Musical LED Settings:**

The Musical LED mode includes several advanced configuration options for fine-tuning the audio-reactive behavior:

#### **Performance Toggle**
```json
"musical_led_active": "active"  // or "off"
```
- **"active"**: LED responds to audio/RMS levels normally
- **"off"**: LED is always turned off, regardless of any audio input (bypasses brightness change thresholds)

#### **Asymmetric Brightness Thresholds**

The system uses different sensitivity thresholds for brighter vs darker changes to optimize musical responsiveness:

**Constants in `led/lighting_menu.py`:**
```python
BRIGHTNESS_MINIMUM_CHANGE_HIGHER = 20  # Minimum change for brighter (increasing)
BRIGHTNESS_MINIMUM_CHANGE_LOWER = 30   # Minimum change for darker (decreasing)
```

**How it works:**
- **Getting Brighter**: LED responds faster to volume increases (20-point threshold)
- **Getting Darker**: LED is more conservative about dimming (30-point threshold)
- **Musical Benefit**: More responsive to loud music moments while preventing quick dimming during brief quiet parts
- **Threshold Bypass**: Max/min brightness (≥95% or ≤5%) always updates immediately, regardless of thresholds

#### **Below Threshold Behavior**
```json
"musical_led_below_threshold": "off",     // or "minimum"
"musical_led_minimum_brightness": "3"     // 0-100 brightness level
```
- **"off"**: Turn LED completely off when audio is below quiet threshold
- **"minimum"**: Keep LED on at minimum brightness level when audio is quiet

#### **RMS Thresholds**
```json
"mic_rms_quiet": "0.002",   // RMS value considered "quiet/emotional" music
"mic_rms_loud": "0.04"      // RMS value considered "loud/energetic" music
```

**Configuration Examples:**

**Responsive Setup** (for dynamic music):
```json
{
  "musical_led_active": "active",
  "musical_led_below_threshold": "off",
  "mic_rms_quiet": "0.001",
  "mic_rms_loud": "0.03"
}
```

**Ambient Setup** (for background music):
```json
{
  "musical_led_active": "active",
  "musical_led_below_threshold": "minimum",
  "musical_led_minimum_brightness": "5",
  "mic_rms_quiet": "0.005",
  "mic_rms_loud": "0.05"
}
```

**Disabled Setup** (LED always off):
```json
{
  "musical_led_active": "off"
}
```

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

The system provides comprehensive RESTful API endpoints:

```bash
# Broadcast Service Controls
POST /broadcast_control/play          # Start playback
POST /broadcast_control/pause         # Pause current track
POST /broadcast_control/stop          # Stop playback
POST /broadcast_control/next          # Next track
POST /broadcast_control/previous      # Previous track
POST /upload_broadcast_file           # Upload audio file
POST /delete_broadcast_file           # Delete audio file
GET  /serve_media/<filename>          # Stream audio file

# Service Management
POST /start_service/<service_name>    # Start individual service
POST /stop_service/<service_name>     # Stop individual service
POST /save_service_config/<service>   # Update service configuration
GET  /service_logs/<service_name>     # Get service-specific logs

# Radio Service
POST /radio_stop_scan                 # Stop FM scan operation
GET  /radio_scan_partial              # Get partial scan results

# System Controls
POST /restart_pi                      # Restart Raspberry Pi
GET  /logs                            # Main system logs
GET  /health/<service_name>           # Individual service health

# Web Interface Routes
GET  /                                # Main dashboard
GET  /exhibition/dashboard            # Exhibition monitoring interface
GET  /dashboard                       # Alternative dashboard route

# Status and Monitoring
GET  /system_status                   # Hardware and system metrics
GET  /service_health                  # All services health status
```

### Configuration Files

Service configurations are managed through JSON files:

```bash
# Global Configuration
service_config.json                   # All service settings

# Service-Specific Status Files
broadcast/broadcast_status.json      # Playback state, playlist
mixing/mixing_status.json            # Recording state, file counts
led/led_status.json                  # Brightness, mode, power
led/led_config.json                  # Device credentials
radio/radio_status.json              # Frequency, signal, stations
fan/fan_status.json                  # Speed, mode, temperature
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

## 🙏 Credits and Attribution

**Code of the Sea** is an original collaborative work by **Werapol Bejranonda** (Engineer) and **Eunji Lee** (Artist).

### Third-Party Open Source Libraries

This project builds upon the following open-source libraries and hardware interfaces:

#### **Core Python Libraries**
- **[Flask](https://flask.palletsprojects.com/)** - Web framework for the control panel (BSD-3-Clause License)
- **[psutil](https://github.com/giampaolo/psutil)** - System and hardware monitoring (BSD-3-Clause License)

#### **Hardware Control Libraries**
- **[TinyTuya](https://github.com/jasonacox/tinytuya)** - Tuya smart device control for LED integration (MIT License)
- **[Adafruit CircuitPython VEML7700](https://github.com/adafruit/Adafruit_CircuitPython_VEML7700)** - Light sensor interface (MIT License)
- **[RPi.GPIO](https://sourceforge.net/projects/raspberry-gpio-python/)** - Raspberry Pi GPIO control (MIT License)
- **[smbus2](https://github.com/kplindegaard/smbus2)** - I2C communication for sensors (MIT License)

#### **Audio Processing**
- **[mpg123](https://www.mpg123.de/)** - Audio playback engine (LGPL 2.1)
- **[FFmpeg](https://ffmpeg.org/)** - Audio mixing and processing (LGPL/GPL)
- **[sounddevice](https://github.com/spatialaudio/python-sounddevice)** - Audio input for musical LED mode (MIT License)

#### **Hardware Components**
- **TEA5767 FM Radio Module** - FM radio tuning
- **VEML7700 Ambient Light Sensor** - Environmental light detection
- **Raspberry Pi** - Computing platform

### Development Tools
- **Python 3** - Primary programming language
- **systemd** - Service management on Linux

All third-party libraries are used in accordance with their respective licenses. We are grateful to the open-source community for providing these excellent tools that make this project possible.

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
- **v2.0** - Major system overhaul with comprehensive service management
- **v2.1.0** - Enhanced persistence & environmental monitoring
- **v2.2.0** - Stability improvements and configuration resilience
- **v3.0.0** - Production-ready exhibition system with enhanced stability
- **v3.1.0** - Performance mode complete fix & service reliability improvements
- **v3.2.0** - Enhanced Musical LED performance mode with intelligent threshold management

### **🚀 v3.2.0 Release Notes**

**Enhanced Musical LED Performance Mode with Intelligent Threshold Management:**

#### **Performance Mode Improvements**
- ✅ **Active Off Button**: The `musical_led_active: "off"` setting now immediately forces LED off regardless of RMS levels, bypassing brightness change thresholds
- ✅ **Intelligent Threshold Bypass**: LED updates immediately when reaching near-maximum (≥95%) or near-minimum (≤5%) brightness to show system limits
- ✅ **Realistic Threshold Values**: Updated from 0%/100% to 5%/95% based on actual RMS and lux sensor brightness calculation ranges
- ✅ **Enhanced Performance Control**: Musical LED off button is now truly responsive during performance mode operation

#### **Technical Enhancements**
- ✅ **Smart Brightness Management**: Brightness threshold bypass logic now considers actual sensor value ranges (RMS: 0.004-0.006, Lux: 1-800)
- ✅ **Improved User Feedback**: Users can now see when LED system reaches its practical brightness limits during musical performances
- ✅ **Configuration Responsiveness**: Musical LED active/off toggle now works instantly without waiting for brightness change thresholds
- ✅ **Optimized Performance**: Reduced unnecessary LED updates while ensuring critical state changes are immediate

#### **Musical LED Mode Features**
- ✅ **Performance Toggle Reliability**: `musical_led_active: "off"` now guarantees LED stays off during musical performances
- ✅ **Threshold Intelligence**: System recognizes when brightness reaches practical limits and updates immediately
- ✅ **Enhanced Musical Responsiveness**: Maintains existing asymmetric threshold system (20 points brighter, 30 points darker) while adding intelligent bypasses
- ✅ **Real-time Feedback**: Users can observe LED reaching maximum brightness during loud music or minimum brightness during quiet passages

**Technical Achievements:**
- 🎭 **Performance Mode Excellence**: Off button now provides immediate, reliable LED control
- 🔧 **Intelligent Threshold System**: Smart bypass logic for maximum user feedback
- 📊 **Realistic Range Management**: Updated thresholds based on actual sensor capabilities
- ⚡ **Instant Response**: Critical brightness changes update immediately regardless of normal thresholds

### **🚀 v3.1.0 Release Notes**

**Performance Mode Complete Fix & Service Reliability:**

#### **Performance Mode Resolution**
- ✅ **Root Cause Fixed**: LED service not starting on system restart was the core issue affecting both modes
- ✅ **Auto Mode Fully Operational**: Microphone input detection working perfectly with real-time RMS values (0.0003-0.01+)
- ✅ **Manual Mode Fully Operational**: Slider controls respond instantly via `/performing/direct_brightness` endpoint
- ✅ **Mode Switching Verified**: Seamless switching between Musical LED (auto) and Manual LED modes confirmed
- ✅ **Configuration Synchronization**: Fixed unified_config.json vs service_config.json discrepancy

#### **Service Management Improvements**
- ✅ **LED Service Restart Scripts**: Enhanced `/scripts/manage_led_service.sh` with proper PID management
- ✅ **Service Status Monitoring**: Real-time status file updates with brightness, RMS values, and connection status
- ✅ **Automatic Recovery**: Service management scripts can detect and restart stuck services
- ✅ **Configuration Consistency**: All services now use unified configuration management

#### **System Reliability**
- ✅ **Service Startup Validation**: Comprehensive analysis of systemd service startup sequence
- ✅ **Configuration File Management**: Proper separation and synchronization of config files
- ✅ **Real-time Monitoring**: Live performance metrics with continuous status updates
- ✅ **Error Recovery**: Enhanced error handling with automatic service recovery

**Technical Achievements:**
- 🎭 **Performance Mode 100% Operational**: Both auto (microphone-reactive) and manual (slider-controlled) modes fully functional
- 🔧 **Service Reliability**: LED service properly managed with automatic restart capabilities
- 📊 **Real-time Monitoring**: Live RMS detection with continuous audio input processing
- 🔄 **Instant Response**: Manual brightness control with immediate LED status updates
- 📚 **Complete Service Documentation**: Updated with comprehensive service management details

### **🚀 v3.0.1 Release Notes** (Previous Release)

**Performance Mode Fixes & Hardware Updates:**

#### **Performance Mode Reliability**
- ✅ **Performance Page Auto Mode Fixed**: Resolved microphone input detection issues - auto mode now properly reacts to sound levels
- ✅ **Performance Page Manual Mode Fixed**: Slider controls now respond correctly to user input
- ✅ **LED Service Startup**: Fixed LED service not running on system startup, enabling both auto and manual performance modes
- ✅ **Mode Recognition**: Enhanced mode detection and switching between Musical LED (auto) and Manual LED modes

#### **Hardware Configuration Updates**
- ✅ **Fan Service Pin Change**: Moved FAN_PIN from GPIO18 to GPIO12 for improved hardware compatibility
- ✅ **Updated Documentation**: All GPIO pin references updated to reflect GPIO12 usage for fan control
- ✅ **Hardware Mapping**: Complete documentation update for new pin assignments

#### **System Service Management**
- ✅ **Systemd Service Review**: Comprehensive analysis of cos-control-panel.service and cos-services.service
- ✅ **Startup Optimization**: Enhanced startup script with conflict-aware service initialization
- ✅ **Service Documentation**: Updated README with complete systemd service information

**Technical Achievements:**
- 🎭 **Performance Mode Operational**: Both auto and manual performance modes fully functional
- 🔧 **Hardware Pin Optimization**: Fan service relocated to GPIO12 for better system integration
- 📚 **Complete Documentation**: Updated README with all recent changes and service details
- ⚡ **Service Reliability**: Enhanced startup sequence and service management

### **🚀 v3.0.0 Release Notes**

**Production-Ready Exhibition System with Enhanced Stability:**

#### **Exhibition Reliability & Performance**
- ✅ **Production-Grade Stability**: Battle-tested system for 24/7 art installations
- ✅ **Enhanced Broadcast Control**: Improved mpg123 startup reliability and audio playback
- ✅ **Exhibition Monitor Integration**: Dedicated monitoring interface for installation oversight
- ✅ **System Health Monitoring**: Comprehensive health checks and automatic recovery mechanisms
- ✅ **Optimized Resource Management**: Improved memory and CPU usage for long-running installations

#### **Audio System Improvements**
- ✅ **Reliable Audio Startup**: Fixed mpg123 initialization issues for consistent audio playback
- ✅ **Enhanced Broadcast Service**: Improved file handling and playlist management
- ✅ **Audio Device Detection**: Better USB microphone and audio interface recognition
- ✅ **Volume Control Stability**: Consistent volume management across all audio services

#### **User Interface & Control**
- ✅ **Responsive Dashboard**: Optimized web interface for tablets and mobile devices
- ✅ **Real-time Status Updates**: Enhanced live monitoring with 15-second refresh intervals
- ✅ **Control Panel Screenshots**: Built-in screenshot capability for documentation
- ✅ **Service Management**: Streamlined start/stop/restart controls for all services

#### **System Monitoring & Diagnostics**
- ✅ **Advanced Metrics Collection**: Comprehensive system and service performance tracking
- ✅ **Exhibition Metrics**: Specialized monitoring for art installation environments
- ✅ **Enhanced Logging**: Detailed logging system for troubleshooting and maintenance
- ✅ **Automatic Health Checks**: Self-monitoring system with proactive issue detection

**Technical Achievements:**
- 🎯 **Exhibition Certified**: Proven reliability for professional art installations
- 🔧 **Zero-Maintenance Operation**: Self-healing system with automatic recovery
- 📊 **Advanced Monitoring**: Complete visibility into system performance and health
- 🎵 **Audio Excellence**: Flawless audio playback and mixing capabilities

### **🔧 v2.2.0 Release Notes**

**Stability Improvements & Configuration Resilience:**

#### **Configuration System Enhancements**
- ✅ **Improved JSON Handling**: Enhanced read_config() function in fan service with race condition protection
- ✅ **File Access Resilience**: Better handling of configuration file access issues and JSON decode errors
- ✅ **Configuration Path Resolution**: Fixed LED and Fan service configuration file path resolution
- ✅ **Robust Service Startup**: Automatic service startup system for exhibition reliability

#### **Service Stability Improvements**
- ✅ **Enhanced Error Recovery**: Comprehensive service error resilience and recovery mechanisms
- ✅ **Process Management**: Improved service process lifecycle management
- ✅ **File System Safety**: Protection against configuration file corruption and access conflicts
- ✅ **Exhibition Reliability**: Bulletproof configuration handling for 24/7 art installations

#### **Technical Improvements**
- ✅ **Race Condition Prevention**: Eliminated configuration file access race conditions
- ✅ **JSON Error Handling**: Robust JSON parsing with fallback mechanisms
- ✅ **Service Dependencies**: Enhanced service dependency management
- ✅ **Automatic Recovery**: Self-healing configuration system for corrupted files

**Technical Achievements:**
- 🛡️ **Zero Configuration Loss**: Complete protection against configuration corruption
- 🔧 **Self-Healing Services**: Automatic recovery from configuration errors
- 🎯 **Exhibition Hardened**: Ultra-reliable operation for critical art installations
- ⚡ **Instant Recovery**: Immediate service restoration after configuration issues

### **✨ v2.1.0 Release Notes**

**Enhanced Persistence & Environmental Monitoring:**

#### **Service Persistence System**
- ✅ **Automatic Service Restoration**: Services automatically restart after system reboot, power outage, or crash
- ✅ **Dashboard Configuration Persistence**: User settings, modes, and configurations persist across restarts
- ✅ **Exhibition-Grade Reliability**: Bulletproof operation for 24/7 art installations without manual intervention
- ✅ **Intelligent State Management**: Comprehensive tracking of service states and configurations
- ✅ **Seamless Recovery**: Services restore to exact previous state including volume levels, modes, and settings

#### **Enhanced Environmental Monitoring**
- ✅ **Extended Lux History**: 5000-entry capacity (increased from 100) for comprehensive light monitoring
- ✅ **Smart History Management**: Automatic file size control with intelligent trimming to prevent storage issues
- ✅ **Threshold-Based Recording**: Only records significant lux changes (>50 lux difference) to reduce noise
- ✅ **Robust LED Service**: Continues lux monitoring even when Tuya LED hardware is unavailable
- ✅ **Real-time Environmental Data**: Continuous light level tracking for responsive art installations

#### **System Reliability Improvements**
- ✅ **Dashboard Mode Control**: Default dashboard interface instead of enhanced mode for cleaner presentation
- ✅ **Persistent Storage Migration**: Moved critical state files from temporary to permanent storage
- ✅ **Enhanced Error Recovery**: Improved handling of hardware communication failures
- ✅ **Version Consistency**: Comprehensive version tracking across all system components

**Technical Achievements:**
- 🌟 **Zero Data Loss**: Complete persistence across unexpected shutdowns
- 📊 **Extended Monitoring**: 50x increase in environmental data capacity
- 🎯 **Exhibition Ready**: Fully autonomous operation for art installations
- 🔄 **Intelligent Recovery**: Smart service restoration with configuration preservation

### **🚀 v2.0 Release Notes**

**Major System Improvements:**

#### **Service Management Revolution**
- ✅ **Complete Service Management System**: Individual scripts for each service with unified control
- ✅ **Single Instance Enforcement**: Prevents duplicate processes and resource conflicts
- ✅ **Intelligent Process Cleanup**: Automatic detection and removal of stuck/zombie processes
- ✅ **Centralized Control**: Master script (`./services`) for managing all services
- ✅ **Enhanced Status Monitoring**: Real-time PID tracking and health indicators

#### **Audio System Enhancements**
- ✅ **Microphone Recording Fixes**: Resolved "device busy" and "No such file or directory" errors
- ✅ **Smart Audio Detection**: Automatic USB microphone discovery with fallback support
- ✅ **PulseAudio Integration**: Improved audio handling with ALSA fallback
- ✅ **Device Conflict Resolution**: Prevents multiple services from accessing audio devices simultaneously
- ✅ **Robust Error Recovery**: Multiple retry attempts with aggressive cleanup on failures

#### **Radio Service Improvements**
- ✅ **Loop Mode Stability**: Fixed endless scan repetition in loop mode
- ✅ **Passive Frequency Setting**: Prevents I2C interference for stable audio output
- ✅ **Enhanced Mode Transitions**: Proper scan-to-fixed/loop mode switching
- ✅ **Configuration Consistency**: Fixed mode selector conflicts between scan and loop modes
- ✅ **Memory Management**: Improved station list persistence and cycling

#### **System Reliability**
- ✅ **Flask Debug Mode Fix**: Eliminated duplicate unified app processes
- ✅ **Enhanced Service Manager**: System-wide process checking with aggressive cleanup
- ✅ **Unified App Management**: Dedicated management script for web interface
- ✅ **Process Tracking**: Comprehensive PID file management with stale cleanup
- ✅ **Fault Tolerance**: Automatic restart capabilities for failed services

#### **Network and Connectivity**
- ✅ **Dual WiFi Support**: WLAN1 primary with WLAN0 backup configuration
- ✅ **Network Priority Management**: Automatic interface priority switching
- ✅ **Enhanced Monitoring**: Improved network status detection and reporting
- ✅ **WiFi Interface Priority**: Configurable primary/backup WiFi interface system

#### **Developer Experience**
- ✅ **Comprehensive Documentation**: Updated README with complete service management guide
- ✅ **Troubleshooting Tools**: Enhanced logging and diagnostic capabilities
- ✅ **Service Scripts**: Standardized start/stop/restart/status operations
- ✅ **Quick Commands**: Convenient `./services` wrapper for common operations

**Technical Achievements:**
- 🔧 **Zero Duplicate Processes**: Eliminated all service instance conflicts
- 🎵 **Reliable Audio Recording**: 100% success rate for microphone operations
- 📻 **Stable Radio Operations**: No more scan loops or frequency corruption
- 🌐 **Network Resilience**: Automatic failover between WiFi interfaces
- 🛠️ **Production Ready**: Robust service management for art installations

---

**Code of the Sea** represents the intersection of technology and art, providing a robust platform for interactive installations while maintaining the flexibility needed for creative expression. The collaboration between engineering precision and artistic vision creates possibilities for unique and engaging art experiences.
