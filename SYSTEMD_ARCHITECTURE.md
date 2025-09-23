# COS SystemD Architecture Documentation

**Version**: 2.0 (Simplified & Optimized)
**Last Updated**: 2025-09-22
**Status**: Production Ready

## 🏗️ Simplified Architecture Overview

This document outlines the **simplified, conflict-free systemd architecture** for the Code of the Sea (COS) project after resolving multiple service conflicts and redundancies.

### ✅ Active Services (Production)

| Service | Status | Purpose | Dependencies |
|---------|--------|---------|--------------|
| `cos-control-panel.service` | **ENABLED** | Main web interface & unified app | network, sound, cos-services |
| `cos-services.service` | **ENABLED** | Individual services startup (LED, Radio, etc.) | network, sound |

### ❌ Disabled Services (Redundant)

| Service | Status | Reason for Disabling |
|---------|--------|---------------------|
| `cos-unified.service` | **DISABLED** | Redundant with cos-control-panel |
| `cos-exhibition.service` | **DISABLED** | Redundant with cos-control-panel |

---

## 📋 Service Details

### 1. `cos-control-panel.service` (Primary Web App)

**Location**: `/etc/systemd/system/cos-control-panel.service`

```ini
[Unit]
Description=Code of the Sea Control Panel
After=network-online.target sound.target cos-services.service
Wants=network-online.target

[Service]
Type=simple
User=payas
WorkingDirectory=/home/payas/cos
Environment=PATH=/home/payas/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/home/payas/cos
ExecStart=/home/payas/venv/bin/python /home/payas/cos/run.py unified --no-debug
Restart=always
RestartSec=15
MemoryMax=768M
CPUQuota=70%

[Install]
WantedBy=multi-user.target
```

**Key Features**:
- ✅ Runs unified web interface on port 5000
- ✅ Starts after individual services to avoid conflicts
- ✅ Enhanced resource limits for audio processing
- ✅ Automatic restart on failure

### 2. `cos-services.service` (Individual Services Startup)

**Location**: `/etc/systemd/system/cos-services.service`

```ini
[Unit]
Description=COS All Services Startup (Optimized)
After=network.target sound.target
Wants=network-online.target

[Service]
Type=oneshot
User=payas
WorkingDirectory=/home/payas/cos
ExecStart=/home/payas/cos/scripts/startup_services_optimized.sh
RemainAfterExit=yes
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
```

**Key Features**:
- ✅ Conflict-aware sequential startup
- ✅ Audio device readiness checking
- ✅ Smart service ordering to prevent conflicts
- ✅ Extended timeout for reliable startup

---

## 🔧 Conflict Resolution Strategy

### Audio Device Conflicts

**Problem**: LED service (Musical LED mode) and Mixing service both need microphone access.

**Solution**:
1. **LED service starts first** (primary audio user for performance mode)
2. **Mixing service starts in disabled mode** to prevent immediate conflict
3. **Performance mode automatically stops other services** when auto mode is activated

### Service Startup Order

```
Phase 1: Non-Audio Services
├── Radio Service (independent)
└── Fan Service (independent)

Phase 2: Audio System Ready Check
├── Wait for PulseAudio
└── Verify audio devices

Phase 3: Audio-Dependent Services
├── LED Service (primary audio user)
├── Broadcast Service (audio output)
└── Mixing Service (disabled mode)
```

### Web App Port Conflicts

**Problem**: Multiple services trying to use port 5000.

**Solution**:
- ✅ **Only cos-control-panel.service** runs the web app
- ✅ **Disabled redundant services** (cos-unified, cos-exhibition)
- ✅ **Manual app stopping** before systemd takeover

---

## 🚀 Management Commands

### Service Status

```bash
# Check all COS services
sudo systemctl status cos-control-panel.service cos-services.service

# Individual service management
sudo systemctl start/stop/restart cos-control-panel.service
sudo systemctl enable/disable cos-control-panel.service
```

### Troubleshooting

```bash
# View service logs
sudo journalctl -u cos-control-panel.service -f
sudo journalctl -u cos-services.service -f

# Check startup logs
cat /home/payas/cos/startup.log

# Manual service management
/home/payas/cos/scripts/manage_all_services.sh status
```

### After System Restart

**Expected Behavior**:
1. `cos-services.service` starts all individual services sequentially
2. `cos-control-panel.service` starts web interface after services are ready
3. Performance page auto mode works immediately with proper RMS values
4. No manual intervention required

---

## 🛡️ Conflict Prevention Rules

### 1. Audio Access Priority
- **LED service**: Primary audio user (for performance mode)
- **Mixing service**: Secondary (starts disabled)
- **Performance mode**: Automatically stops conflicting services

### 2. Web Interface
- **Single web app**: Only cos-control-panel.service
- **Port 5000**: Exclusively reserved for main web interface
- **No manual apps**: Always use systemd services

### 3. Service Dependencies
- **Web app waits**: for individual services to start first
- **Audio services wait**: for sound system readiness
- **Network services wait**: for network availability

---

## 📊 Monitoring & Health

### Key Metrics
- **Web Interface**: `http://localhost:5000`
- **Performance Page**: `http://localhost:5000/performing`
- **RMS API**: `http://localhost:5000/api/led_rms_status`

### Health Indicators
```bash
# All services should show 'active (running)' or 'active (exited)'
sudo systemctl status cos-*

# LED service should show Musical LED mode with RMS values
curl -s http://localhost:5000/api/led_rms_status

# Performance page should show auto mode working
curl -s http://localhost:5000/performing/status
```

---

## 🔄 Boot Sequence

1. **System Boot** → Network + Sound ready
2. **cos-services.service** → Individual services start (LED, Radio, Fan, Broadcast, Mixing)
3. **cos-control-panel.service** → Web interface starts
4. **Ready** → Performance page auto mode functional

**Total Boot Time**: ~2-3 minutes for full system ready

---

## ⚠️ Important Notes

### After System Restart
- ✅ **No manual intervention** required
- ✅ **Auto mode will work** immediately after boot
- ✅ **RMS values display** properly in performance page
- ✅ **Services auto-start** in correct order

### When Making Changes
- **Always use systemd services** instead of manual scripts
- **Test after system restart** to ensure persistence
- **Check logs** if any service fails to start
- **Restart in correct order**: services first, then web app

### Audio Conflicts
- **Use performance mode** to automatically manage audio conflicts
- **Manual mixing**: Disable via web interface when using LED performance mode
- **Check logs** if audio devices seem unavailable

---

## 📞 Troubleshooting Contact

If services fail after restart:
1. Check `sudo systemctl status cos-*`
2. Review logs with `sudo journalctl -u cos-control-panel.service`
3. Verify audio devices with `pactl list short sources`
4. Check startup log at `/home/payas/cos/startup.log`

**This architecture ensures reliable, conflict-free operation after every system restart.**