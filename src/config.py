# src/config.py
# -*- coding: utf-8 -*-

from __future__ import annotations

# Configuración central (solo datos, sin lógica)
CFG: dict = {
    # Persistencia
    "db_path": "snapshots.db",

    # Collector
    "disk_path": "C:\\",          # Windows default
    "top_n_processes": 5,

    # Analyzer (umbrales MVP)
    "anomalies": {
        "cpu_percent_high": 90.0,
        "mem_percent_high": 90.0,
        # opcional: si no querés checkear red, poné None
        "net_delta_high": None,
    },

    # Reportes
    "reports": {
        "dir": "reports",          # carpeta en raíz
        "default_name": "report.md",
        # si True: nombre único por ejecución (report-YYYYMMDD-HHMMSS.md)
        "timestamped": False,
    },
}
