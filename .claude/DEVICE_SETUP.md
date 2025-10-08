# Device Setup Guide
## Code of the Sea - Device Configuration

This guide explains how to configure your specific devices for the Code of the Sea installation.

## 🔐 Security-First Configuration

Your device credentials (Tuya keys, IP addresses, etc.) are kept separate from the code repository for security. This prevents accidentally sharing sensitive information when using git.

## 📋 Setup Steps

### 1. Copy Configuration Template
```bash
cd /path/to/code-of-the-sea
cp config/devices.example.json config/devices.json
```

### 2. Get Tuya Device Credentials
Run the Tuya wizard to get your LED controller credentials:
```bash
python3 -m tinytuya wizard
```

This will create `snapshot.json` and `devices.json` files with your device information.

### 3. Update Device Configuration
Edit `config/devices.json` with your specific device information:

```json
{
  "led": {
    "enabled": true,
    "tuya_controller": {
      "device_id": "your_device_id_from_wizard",
      "device_ip": "your_device_ip", 
      "device_key": "your_device_key_from_wizard",
      "protocol_version": "3.5"
    },
    "veml7700_sensor": {
      "enabled": true,
      "i2c_bus": 1
    }
  },
  
  "radio": {
    "enabled": true,
    "tea5767": {
      "i2c_bus": 1,
      "i2c_address": "0x60"
    }
  },
  
  "fan": {
    "enabled": true,
    "grove_mosfet": {
      "fan_pwm_pin": 18,
      "pwm_frequency": 10
    }
  }
}
```

### 4. Verify Configuration
Test that your configuration loads correctly:
```bash
python3 -c "
from core.device_config import get_device_config
config = get_device_config()
print('Configuration loaded successfully!')
print('Tuya credentials:', config.get_tuya_credentials()[:2])  # Hide sensitive data
"
```

## 🛡️ Security Features

- **Automatic .gitignore**: `config/devices.json` is automatically excluded from git
- **Fallback handling**: System continues working even with config errors
- **Template preservation**: Example config stays safe in repository
- **Credential separation**: No sensitive data in source code

## 🔧 Troubleshooting

### Configuration Not Found
```
Error: Device configuration not found: config/devices.json
```
**Solution**: Copy the example config and update with your credentials
```bash
cp config/devices.example.json config/devices.json
```

### Invalid Tuya Credentials
```
Error: Missing Tuya credentials in config file
```
**Solution**: Run tinytuya wizard and update config file
```bash
python3 -m tinytuya wizard
# Then update config/devices.json with the new credentials
```

### Module Not Working
1. Check if module is enabled in config: `"enabled": true`
2. Verify hardware connections (see README.md hardware section)
3. Check system logs: `sudo journalctl -u cos-control-panel -f`

## 📝 Configuration Reference

### LED Module Configuration
```json
"led": {
  "enabled": true,
  "tuya_controller": {
    "device_id": "string - from tinytuya wizard",
    "device_ip": "string - device IP address", 
    "device_key": "string - local key from wizard",
    "protocol_version": "string - usually 3.5"
  },
  "veml7700_sensor": {
    "enabled": boolean,
    "i2c_bus": number
  }
}
```

### Radio Module Configuration
```json
"radio": {
  "enabled": boolean,
  "tea5767": {
    "i2c_bus": number,
    "i2c_address": "string - hex address"
  }
}
```

### Fan Module Configuration  
```json
"fan": {
  "enabled": boolean,
  "grove_mosfet": {
    "fan_pwm_pin": number,
    "pwm_frequency": number
  }
}
```

---

**Remember**: Never commit `config/devices.json` to git - it contains your private device credentials!