#!/bin/bash
# Simple reboot script that can be called from the web interface

echo "$(date): Reboot requested via web interface" >> /home/payas/cos/reboot.log

# Use sudo reboot (requires sudoers entry for NOPASSWD reboot)
sudo /sbin/reboot