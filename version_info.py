"""
Version information for Code of the Sea
"""

VERSION = "2.1.0"
VERSION_INFO = {
    "major": 2,
    "minor": 1,
    "patch": 0,
    "release_type": "stable",
    "build_date": "2025-09-17",
    "codename": "Enhanced Persistence & Environmental Monitoring"
}

RELEASE_NOTES = {
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