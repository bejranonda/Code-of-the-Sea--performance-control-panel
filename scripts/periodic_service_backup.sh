#!/bin/bash
# Periodic Service State Backup
# Ensures service state is regularly saved to handle shutdown timing issues

cd /home/payas/cos

# Get current timestamp
timestamp=$(date '+%Y-%m-%d %H:%M:%S')

# Save current service state
echo "[$timestamp] Performing periodic service state backup..."
python3 core/service_persistence.py save

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "[$timestamp] Periodic backup completed successfully"
else
    echo "[$timestamp] ERROR: Periodic backup failed"
fi