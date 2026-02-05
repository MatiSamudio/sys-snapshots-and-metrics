"""
Central configuration module for sys-snapshots-and-metrics.

This module contains all application configuration as a single dictionary.
No logic is executed here - only data definitions.

Configuration sections:
- db_path: SQLite database file location
- disk_path: Disk partition to monitor
- top_n_processes: Number of top processes to capture
- anomalies: Threshold values for anomaly detection
- reports: Report generation settings
"""

from __future__ import annotations

# Central configuration dictionary (data only, no logic)
CFG: dict = {
    # Database persistence
    "db_path": "snapshots.db",

    # Collector settings
    "disk_path": "C:\\",          # Windows default (use "/" for Unix-like systems)
    "top_n_processes": 5,         # Number of top processes to capture per snapshot

    # Analyzer thresholds (MVP)
    "anomalies": {
        "cpu_percent_high": 90.0,      # CPU usage threshold (0-100)
        "mem_percent_high": 90.0,      # Memory usage threshold (0-100)
        # Optional: Set to None to disable network anomaly detection
        # Set to an integer (bytes) to enable
        "net_delta_high": None,        # Network delta threshold in bytes
    },

    # Report generation settings
    "reports": {
        "dir": "reports",              # Output directory for reports (relative to project root)
        "default_name": "report.md",   # Default report filename
        # If True: generates unique timestamped filenames (report-YYYYMMDD-HHMMSS.md)
        # If False: uses default_name (overwrites previous reports)
        "timestamped": False,
    },
}
