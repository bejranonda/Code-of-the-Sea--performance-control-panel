# 🌊 Code of the Sea - Startup Guide

## 🚀 Quick Start (Automatic Boot)

**Recommended for exhibitions and long-term use:**

```bash
./install-service.sh
```

This will:
- Install as a systemd service
- Auto-start on Raspberry Pi boot
- Auto-restart if it crashes
- Run in the background

## 🛠️ Manual Start (Development)

### Option 1: Using the optimized script
```bash
./start.sh
```

### Option 2: Your original method
```bash
source venv/bin/activate
cd ~/cos/
python run.py unified
```

## 📋 Service Management Commands

After installing the service:

```bash
# Check status
sudo systemctl status cos-control-panel

# View logs
sudo journalctl -u cos-control-panel -f

# Stop service
sudo systemctl stop cos-control-panel

# Start service  
sudo systemctl start cos-control-panel

# Restart service
sudo systemctl restart cos-control-panel

# Disable auto-start
sudo systemctl disable cos-control-panel
```

## 🔧 First Time Setup

If this is a fresh installation:

```bash
./setup.sh
```

## 🌐 Access

After starting, access your control panel at:
- Local: http://localhost:5000
- Network: http://[YOUR-PI-IP]:5000

## 📁 Broadcast Service Features

The broadcast service now includes:
- 📂 **Playlist display** - See all your audio files
- 📤 **File upload** - Add new audio files via web interface  
- 🗑️ **File deletion** - Remove files you don't want
- ▶️ **Currently playing indicator** - See which file is playing
- 🔄 **Auto-loop** - Continuous playback of your playlist

Supported formats: MP3, WAV, OGG, M4A, FLAC