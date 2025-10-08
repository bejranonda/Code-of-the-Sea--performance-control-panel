# Code of the Sea v2.1.0 Release Notes

## Enhanced Persistence & Environmental Monitoring

**Release Date:** September 17, 2025
**Release Type:** Minor Update (Non-breaking)
**Upgrade Required:** No

---

## 🌟 What's New in v2.1.0

### Service Persistence System
Building on v2.0's rock-solid service management foundation, v2.1.0 introduces comprehensive persistence that ensures your art installation never misses a beat.

#### ✅ **Automatic Service Restoration**
- Services automatically restart after system reboot, power outage, or unexpected crash
- Zero manual intervention required for exhibition environments
- Maintains exact service states including volume levels, frequencies, and modes

#### ✅ **Dashboard Configuration Persistence**
- User settings, modes, and all configurations persist across restarts
- Dashboard preference (dashboard vs enhanced mode) remembered permanently
- Service-specific settings (lux ranges, volumes, modes) automatically restored

#### ✅ **Exhibition-Grade Reliability**
- Bulletproof operation for 24/7 art installations
- Intelligent state management across all system components
- Seamless recovery from any type of system interruption

### Enhanced Environmental Monitoring

#### ✅ **Extended Lux History (5000 entries)**
- **50x increase** from previous 100-entry limit to 5000 entries
- Comprehensive light monitoring for long-term installations
- Perfect for analyzing environmental patterns over days/weeks

#### ✅ **Smart History Management**
- Automatic file size control with intelligent trimming
- Prevents storage issues while maintaining valuable data
- Configurable thresholds (currently 1MB with 2500-entry safety margin)

#### ✅ **Threshold-Based Recording**
- Only records significant lux changes (>50 lux difference)
- Reduces noise and focuses on meaningful environmental shifts
- Eliminates redundant data while preserving important trends

#### ✅ **Robust LED Service**
- Continues comprehensive lux monitoring even when Tuya LED hardware is unavailable
- No functionality loss during hardware communication issues
- Maintains environmental awareness for other light-reactive services

### System Reliability Improvements

#### ✅ **Enhanced User Experience**
- Default dashboard interface instead of enhanced mode for cleaner presentation
- Streamlined UI for exhibition environments
- Consistent version tracking across all system components

#### ✅ **Storage Architecture**
- Migrated critical state files from temporary (/tmp) to permanent storage
- Prevents data loss during system restarts
- Improved filesystem resilience

---

## 🚀 Technical Achievements

| Feature | Before v2.1.0 | After v2.1.0 | Improvement |
|---------|---------------|--------------|-------------|
| **Service Persistence** | Manual restart required | Automatic restoration | 100% autonomous |
| **Lux History Capacity** | 100 entries | 5000 entries | **50x increase** |
| **Configuration Persistence** | Lost on restart | Fully persistent | **Zero data loss** |
| **Storage Reliability** | Temporary files | Permanent storage | **Production ready** |
| **Environmental Monitoring** | Basic tracking | Comprehensive history | **Exhibition grade** |

---

## 🎯 Perfect for Art Installations

This release specifically targets the unique needs of interactive art installations:

- **Zero Downtime**: Services automatically recover from any interruption
- **Long-term Data**: 5000-entry environmental history for extended exhibitions
- **Unattended Operation**: No manual intervention needed for months of operation
- **Power Resilience**: Complete recovery from power outages and brownouts
- **Data Integrity**: All configurations and environmental data preserved

---

## 🔄 Upgrade Instructions

### From v2.0.x to v2.1.0

This is a **non-breaking update** with automatic migration:

1. **Pull latest code:**
   ```bash
   git pull origin main
   ```

2. **The system will automatically:**
   - Migrate state files to permanent storage
   - Upgrade lux history format to 5000-entry capacity
   - Enable service persistence features
   - Update all version references

3. **No configuration changes required** - all existing settings preserved

### First-time Installation

Follow the standard installation process from the main README.md

---

## 🐛 Bug Fixes

- Fixed string/float type conversion errors in LED service lux calculations
- Resolved service state persistence across system reboots
- Corrected dashboard mode default setting
- Enhanced error handling for hardware communication timeouts

---

## 📁 New Files Added

- `core/service_persistence.py` - Comprehensive service state management
- `core/dashboard_state.py` - Dashboard configuration persistence
- `cos_service_state.json` - Permanent service state storage
- `dashboard_state.json` - Persistent dashboard configurations
- `version_info.py` - Centralized version management

---

## 🔮 Looking Ahead to v2.2.0

Planned features for the next release:
- Advanced scheduling system for timed exhibitions
- Cloud-based configuration backup
- Extended hardware module support
- Multi-device synchronization capabilities

---

## 🤝 Credits

**Art Project Collaboration:**
- **Werapol Bejranonda** (Engineer)
- **Eunji Lee** (Artist)

This release represents the continued evolution of Code of the Sea as a professional-grade platform for interactive art installations, combining technical precision with artistic vision.

---

**Full Changelog:** [v2.0.0...v2.1.0](https://github.com/your-username/code-of-the-sea/compare/v2.0.0...v2.1.0)