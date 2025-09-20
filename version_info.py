"""
Version information for Code of the Sea
"""

VERSION = "3.0.0"
VERSION_INFO = {
    "major": 3,
    "minor": 0,
    "patch": 0,
    "release_type": "stable",
    "build_date": "2025-09-20",
    "codename": "Production-Ready Exhibition System"
}

RELEASE_NOTES = {
    "3.0.0": {
        "date": "2025-09-20",
        "type": "major",
        "highlights": [
            "Production-grade stability for 24/7 art installations",
            "Enhanced broadcast control with improved mpg123 startup reliability",
            "Exhibition monitor integration with dedicated monitoring interface",
            "Advanced metrics collection and system health monitoring",
            "Optimized resource management for long-running installations",
            "Control panel screenshots and enhanced documentation",
            "Zero-maintenance operation with automatic recovery mechanisms"
        ],
        "breaking_changes": False,
        "upgrade_required": False
    },
    "2.1.0": {
        "date": "2025-09-17",
        "type": "minor",
        "highlights": [
            "Automatic service restoration across system restarts",
            "Dashboard configuration persistence and state management",
            "Enhanced LED service with comprehensive lux history (5000 entries)",
            "Intelligent file size management with automatic trimming",
            "Robust environmental monitoring even without hardware LED",
            "Exhibition-grade reliability for uninterrupted art installations"
        ],
        "breaking_changes": False,
        "upgrade_required": False
    },
    "2.0.0": {
        "date": "2025-09-17",
        "type": "major",
        "highlights": [
            "Complete service management overhaul",
            "100% audio recording reliability",
            "Zero service conflicts and duplicate processes",
            "Production-ready for 24/7 art installations",
            "Enhanced network resilience with dual WiFi"
        ],
        "breaking_changes": True,
        "upgrade_required": True
    }
}

def get_version():
    """Get current version string"""
    return VERSION

def get_version_info():
    """Get detailed version information"""
    return VERSION_INFO

def is_production_ready():
    """Check if this is a production-ready release"""
    return VERSION_INFO["release_type"] == "stable"

def get_release_highlights(version=None):
    """Get release highlights for a specific version"""
    if version is None:
        version = VERSION
    return RELEASE_NOTES.get(version, {}).get("highlights", [])