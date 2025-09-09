#!/usr/bin/env python3
"""
Raspberry Pi Control Panel - Main Startup Script
Provides multiple ways to run the refactored application
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# Application modes and their corresponding files
APPLICATIONS = {
    'unified': {
        'file': 'unified_app.py',
        'description': 'Unified application with all features and modes',
        'features': ['Multiple UI modes', 'Unified service management', 'Advanced monitoring']
    },
    'legacy-simple': {
        'file': 'app.py', 
        'description': 'Original simple Flask application',
        'features': ['Basic service control', 'Simple UI', 'Lightweight']
    },
    'legacy-enhanced': {
        'file': 'app_option.py',
        'description': 'Enhanced Flask application with fan controls',
        'features': ['Themed UI', 'Advanced fan controls', 'Code of the Sea styling']
    },
    'legacy-dashboard': {
        'file': 'app_menu.py',
        'description': 'Full dashboard with hardware monitoring',
        'features': ['Hardware monitoring', 'Service health', 'Comprehensive logging']
    }
}

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'flask', 'psutil'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing required packages: {', '.join(missing)}")
        print("📦 Install with: pip install " + " ".join(missing))
        return False
    
    print("✅ All dependencies satisfied")
    return True

def check_permissions():
    """Check if running with appropriate permissions"""
    # Check if we can access GPIO (usually requires being in gpio group)
    gpio_accessible = os.path.exists('/dev/gpiomem') and os.access('/dev/gpiomem', os.R_OK | os.W_OK)
    
    if not gpio_accessible:
        print("⚠️  GPIO access may be limited. Consider running with appropriate permissions or adding user to gpio group.")
    else:
        print("✅ GPIO access available")
    
    return True

def setup_environment():
    """Setup environment and directory structure"""
    # Create necessary directories
    directories = ['logs', 'core', 'templates']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    # Ensure core module is in Python path
    core_path = os.path.join(os.path.dirname(__file__), 'core')
    if core_path not in sys.path:
        sys.path.insert(0, core_path)
    
    print("✅ Environment setup complete")
    return True

def list_applications():
    """List available applications and their features"""
    print("\n🚀 Available Applications:")
    print("=" * 50)
    
    for app_name, app_info in APPLICATIONS.items():
        status = "✅" if os.path.exists(app_info['file']) else "❌"
        print(f"\n{status} {app_name}")
        print(f"   📁 File: {app_info['file']}")
        print(f"   📝 Description: {app_info['description']}")
        print(f"   ⭐ Features:")
        for feature in app_info['features']:
            print(f"      • {feature}")

def run_application(app_name: str, host: str = "0.0.0.0", port: int = 5000, debug: bool = True):
    """Run the specified application"""
    if app_name not in APPLICATIONS:
        print(f"❌ Unknown application: {app_name}")
        print(f"Available applications: {', '.join(APPLICATIONS.keys())}")
        return False
    
    app_info = APPLICATIONS[app_name]
    app_file = app_info['file']
    
    if not os.path.exists(app_file):
        print(f"❌ Application file not found: {app_file}")
        return False
    
    print(f"\n🚀 Starting {app_name}...")
    print(f"📁 File: {app_file}")
    print(f"🌐 URL: http://{host}:{port}")
    print(f"🔧 Debug mode: {'ON' if debug else 'OFF'}")
    print("\n" + "=" * 50)
    
    try:
        # Set environment variables
        env = os.environ.copy()
        env['FLASK_APP'] = app_file
        env['FLASK_ENV'] = 'development' if debug else 'production'
        
        # Run the application
        cmd = [sys.executable, app_file]
        subprocess.run(cmd, env=env)
        
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
        return True
    except Exception as e:
        print(f"❌ Error running application: {e}")
        return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Raspberry Pi Control Panel - Startup Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                          # List available applications
  python run.py unified                  # Run unified application (recommended)  
  python run.py legacy-simple            # Run original simple app
  python run.py unified --port 8080      # Run on different port
  python run.py unified --no-debug       # Run without debug mode
        """
    )
    
    parser.add_argument(
        'application', 
        nargs='?',
        choices=list(APPLICATIONS.keys()),
        help='Application to run'
    )
    
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=5000,
        help='Port to bind to (default: 5000)'
    )
    
    parser.add_argument(
        '--no-debug',
        action='store_true',
        help='Disable debug mode'
    )
    
    parser.add_argument(
        '--skip-checks',
        action='store_true', 
        help='Skip dependency and permission checks'
    )
    
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List available applications and exit'
    )
    
    args = parser.parse_args()
    
    print("🐍 Raspberry Pi Control Panel")
    print("🔧 Refactored Application Launcher")
    print("=" * 50)
    
    # List applications and exit if requested
    if args.list or not args.application:
        list_applications()
        if not args.application:
            print(f"\n💡 Recommendation: Run 'python {sys.argv[0]} unified' for the best experience")
        return
    
    # Run checks unless skipped
    if not args.skip_checks:
        print("\n🔍 Running pre-flight checks...")
        
        if not check_dependencies():
            sys.exit(1)
            
        if not check_permissions():
            sys.exit(1)
            
        if not setup_environment():
            sys.exit(1)
    
    # Run the requested application
    debug = not args.no_debug
    success = run_application(args.application, args.host, args.port, debug)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()