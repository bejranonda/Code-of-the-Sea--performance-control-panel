#!/usr/bin/env python3
"""
Debug wrapper for LED service to catch startup issues
"""

import sys
import os
import traceback
import subprocess
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

def main():
    try:
        print("DEBUG: Starting LED service wrapper")
        print(f"DEBUG: Python executable: {sys.executable}")
        print(f"DEBUG: Working directory: {os.getcwd()}")
        print(f"DEBUG: Python path: {sys.path[:3]}")
        
        # Test imports
        print("DEBUG: Testing imports...")
        import tinytuya
        print("DEBUG: tinytuya import successful")
        
        import asyncio
        print("DEBUG: asyncio import successful")
        
        # Try to import the main service
        print("DEBUG: Importing lighting_menu...")
        import lighting_menu
        print("DEBUG: lighting_menu import successful")
        
        print("DEBUG: Starting main service...")
        asyncio.run(lighting_menu.main())
        
    except Exception as e:
        error_msg = f"DEBUG: Fatal error in LED service: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        
        # Write error to log file
        try:
            with open("led_debug_error.txt", "w") as f:
                f.write(error_msg)
        except:
            pass
            
        sys.exit(1)

if __name__ == "__main__":
    main()