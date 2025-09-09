# Raspberry Pi Control Panel - Refactored

A comprehensive refactoring of the original Raspberry Pi control system with improved architecture, unified service management, and multiple interface options.

## 🚀 Quick Start

### Recommended Way (Unified Application)
```bash
python run.py unified
```

### List All Options
```bash
python run.py --list
```

## 📋 What's New

### ✨ Key Improvements
- **Unified Architecture**: All three original apps consolidated into a single, modular system
- **Service Management**: Centralized service lifecycle management with health monitoring
- **Configuration System**: Unified configuration management across all services
- **Error Handling**: Comprehensive logging and error recovery
- **Hardware Monitoring**: Real-time system health and performance metrics
- **Multiple UI Modes**: Choose between different interface styles

### 🏗️ Architecture Overview

```
cos/
├── core/                          # Core refactored modules
│   ├── service_manager.py         # Unified service lifecycle management
│   ├── config_manager.py          # Configuration management
│   ├── hardware_monitor.py        # Hardware monitoring utilities
│   └── logging_setup.py           # Centralized logging system
├── templates/                     # External HTML templates
│   ├── dashboard.html             # Advanced dashboard (from app_menu.py)
│   ├── simple_control.html        # Basic control panel (from app.py)
│   └── enhanced_control.html      # Themed interface (from app_option.py)
├── unified_app.py                 # Main refactored application
├── run.py                         # Smart startup script
└── [legacy files preserved]       # Original apps still available
```

## 🎯 Available Applications

### 1. **Unified Application** (Recommended)
- **File**: `unified_app.py`
- **Features**: 
  - Multiple UI modes in one app
  - Unified service management
  - Advanced hardware monitoring
  - Service health checks
  - API endpoints

**Usage**: `python run.py unified`

### 2. **Legacy Applications** (Preserved)
Original applications are preserved for compatibility:

- **Simple**: `python run.py legacy-simple` (original `app.py`)
- **Enhanced**: `python run.py legacy-enhanced` (original `app_option.py`) 
- **Dashboard**: `python run.py legacy-dashboard` (original `app_menu.py`)

## 🎨 UI Modes

The unified application supports multiple interface modes:

### Dashboard Mode (Default)
- Full hardware monitoring
- Service health indicators
- Advanced controls and configuration
- Real-time status updates

### Simple Mode  
- Basic start/stop controls
- Lightweight interface
- Minimal resource usage

### Enhanced Mode
- "Code of the Sea" themed interface
- Advanced fan controls
- Styled UI elements

**Switch modes**: Add `/mode/<mode_name>` to URL or use the mode selector in the interface.

## 🔧 Configuration

### Unified Configuration System
- **File**: `unified_config.json`
- **Features**:
  - Single source of truth for all service configurations
  - Type conversion and validation
  - Automatic defaults for new services
  - Metadata tracking

### Service Configurations
Each service maintains its configuration within the unified system:

```json
{
  "LED Service": {
    "mode": "Manual LED",
    "brightness": 50,
    "status_file": "led/led_status.json"
  },
  "Radio Service": {
    "mode": "Fixed",
    "frequency": 101.1,
    "direction": "Up"
  },
  "Fan Service": {
    "mode": "Fixed",
    "speed": 50
  }
}
```

## 🖥️ Hardware Monitoring

### Comprehensive System Metrics
- **CPU**: Usage percentage, load averages, core count
- **Memory**: Usage, available, total (with GB conversions)
- **Disk**: Usage, free space, total capacity  
- **Network**: I/O counters, bandwidth usage
- **Temperature**: CPU temperature (Raspberry Pi specific)
- **Uptime**: System uptime with formatted display

### Service Health Monitoring
- Process status tracking
- Status file freshness checks
- Error count monitoring
- Automatic cleanup of dead processes

## 📊 Logging & Debugging

### Unified Logging System
- **Main Log**: `logs/unified_app.log`
- **Service Logs**: `logs/[service_name].log`
- **Features**:
  - Timestamped entries
  - Log level filtering
  - Exception tracking with stack traces
  - Performance metrics
  - User action auditing

### Log Management
- Web-based log viewing
- Individual service log access
- Log clearing functionality
- Automatic log rotation (configurable)

## 🔌 API Endpoints

### System Status
```
GET /api/status
```
Returns comprehensive system status including hardware, services, and health metrics.

### Service Health
```
GET /health/<service_name>
```
Returns detailed health information for a specific service.

### Configuration Management
```
POST /save/<service_name>
```
Update service configuration with form data.

## 🛠️ Development

### Adding New Services
1. Add service definition to `SERVICES` dict in `unified_app.py`
2. Create service script in appropriate directory
3. Add configuration defaults to `ConfigManager`
4. Update templates if needed

### Custom UI Modes
1. Create new template in `templates/`
2. Add mode definition to `APP_MODES` in `unified_app.py`
3. Implement any mode-specific logic

### Extending Hardware Monitoring
Add new metrics to `HardwareMonitor` class in `core/hardware_monitor.py`.

## 📦 Dependencies

### Required Python Packages
- `flask`: Web framework
- `psutil`: System monitoring

### Install Dependencies
```bash
pip install flask psutil
```

### System Requirements
- Python 3.6+
- Raspberry Pi OS (or compatible Linux)
- GPIO access (for hardware control)

## 🔧 Troubleshooting

### Common Issues

**Permission Denied for GPIO**
```bash
# Add user to gpio group
sudo usermod -a -G gpio $USER
# Re-login or reboot
```

**Missing Dependencies**
```bash
# Install required packages
pip install flask psutil
```

**Service Won't Start**
- Check logs in web interface or `logs/` directory
- Verify service script paths in configuration
- Ensure working directories are correct

**Template Not Found**
- Verify `templates/` directory exists
- Check template file permissions
- Ensure Flask can access template files

### Debug Mode
Run with debug information:
```bash
python run.py unified --no-debug  # Disable debug mode
python run.py unified --port 8080  # Use different port
```

## 🔄 Migration Guide

### From Original Apps

**If using `app.py`**:
- Switch to: `python run.py unified`
- Set mode to "simple" for similar interface

**If using `app_option.py`**:  
- Switch to: `python run.py unified`
- Set mode to "enhanced" for Code of the Sea theme

**If using `app_menu.py`**:
- Switch to: `python run.py unified` 
- Default dashboard mode provides same functionality

### Configuration Migration
Original config files are automatically imported into the unified system.

## 🤝 Contributing

### Code Style
- Follow existing patterns in core modules
- Add comprehensive error handling
- Include logging for all operations
- Write docstrings for public methods

### Testing
- Test all service operations
- Verify hardware monitoring on actual Raspberry Pi
- Check UI modes in different browsers
- Validate configuration management

## 📝 License

This refactored version maintains the same license as the original project.

## 🎉 Acknowledgments

Built upon the original Raspberry Pi control system, this refactored version preserves all original functionality while providing a more maintainable and extensible architecture.