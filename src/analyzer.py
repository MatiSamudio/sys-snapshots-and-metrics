"""
Statistical analysis and anomaly detection module.

Responsibilities:
- Calculate min/avg/max statistics for CPU, memory, and disk usage
- Compute network totals from delta values
- Detect anomalies based on configurable thresholds
- Generate time series data for visualization

The module processes snapshots from storage and produces a comprehensive
analysis dictionary for the report generator.
"""

from __future__ import annotations
from typing import Any

def analyze(snapshots: list[dict], cfg: dict) -> dict:
    """
    Analyze a list of snapshots and detect anomalies.

    Args:
        snapshots: List of snapshot dictionaries from storage.
        cfg: Configuration dictionary containing anomaly thresholds.

    Returns:
        Analysis dictionary containing:
        - time_range: Start and end timestamps
        - count: Number of snapshots analyzed
        - metrics: Min/avg/max statistics for CPU, memory, disk
        - disk: Last snapshot disk information
        - net: Network totals calculated from deltas
        - anomalies: List of detected anomalies with details
        - last_snapshot: Most recent snapshot for reference
        - series: Time series data for visualization
    """
    # Extract anomaly thresholds from configuration
    anomalies_cfg = (cfg or {}).get("anomalies") or {}
    cpu_hi = float(anomalies_cfg.get("cpu_percent_high", 90.0))
    mem_hi = float(anomalies_cfg.get("mem_percent_high", 90.0))
    net_hi = anomalies_cfg.get("net_delta_high", None)
    net_hi = None if net_hi is None else int(net_hi)

    # Handle empty snapshot list
    if not snapshots:
        return {
            "time_range": {"start": None, "end": None},
            "count": 0,
            "metrics": {
                "cpu_percent": {"min": None, "avg": None, "max": None},
                "mem_percent": {"min": None, "avg": None, "max": None},
                "disk_percent": {"min": None, "avg": None, "max": None},
            },
            "disk": {"path": None, "last_percent": None},
            "net": {"sent_total": 0, "recv_total": 0, "deltas_ignored": 0},
            "anomalies": [],
            "last_snapshot": None,
            "series": {"cpu_percent": [], "mem_percent": [], "disk_percent": []},
        }

    def num(x: Any, default: float = 0.0) -> float:
        """Convert value to float, returning default on error."""
        try:
            v = float(x)
            return v
        except Exception:
            return float(default)

    def int_or_none(x: Any):
        """Convert value to int, returning None on error."""
        if x is None:
            return None
        try:
            return int(x)
        except Exception:
            return None

    # Assume chronological order (storage guarantees this)
    start_ts = snapshots[0].get("ts")
    end_ts = snapshots[-1].get("ts")

    cpu_vals: list[float] = []
    mem_vals: list[float] = []
    disk_vals: list[float] = []

    sent_total = 0
    recv_total = 0
    deltas_ignored = 0
    anomalies: list[dict] = []

    # Process each snapshot
    for s in snapshots:
        ts = s.get("ts")

        cpu_p = num(((s.get("cpu") or {}).get("percent")), 0.0)
        mem_p = num(((s.get("mem") or {}).get("percent")), 0.0)
        disk_p = num(((s.get("disk") or {}).get("percent")), 0.0)

        cpu_vals.append(cpu_p)
        mem_vals.append(mem_p)
        disk_vals.append(disk_p)

        # Anomaly detection
        reasons: list[str] = []
        if cpu_p >= cpu_hi:
            reasons.append(f"cpu_percent_high (>= {cpu_hi})")
        if mem_p >= mem_hi:
            reasons.append(f"mem_percent_high (>= {mem_hi})")

        net = s.get("net") or {}
        ds = int_or_none(net.get("sent_delta"))
        dr = int_or_none(net.get("recv_delta"))

        # Network delta processing
        if ds is None:
            deltas_ignored += 1
        else:
            if ds < 0: ds = 0  # Protect against negative deltas
            sent_total += ds
            if net_hi is not None and ds >= net_hi:
                reasons.append(f"net_sent_delta_high (>= {net_hi})")

        if dr is None:
            deltas_ignored += 1
        else:
            if dr < 0: dr = 0  # Protect against negative deltas
            recv_total += dr
            if net_hi is not None and dr >= net_hi:
                reasons.append(f"net_recv_delta_high (>= {net_hi})")

        # Record anomaly if any threshold exceeded
        if reasons:
            anomalies.append({
                "ts": ts,
                "reasons": reasons,
                "cpu_percent": cpu_p,
                "mem_percent": mem_p,
                "disk_percent": disk_p,
                "net_sent_delta": ds,
                "net_recv_delta": dr,
            })

    def min_avg_max(vals: list[float]) -> dict:
        """Calculate min, average, and max from a list of values."""
        if not vals:
            return {"min": None, "avg": None, "max": None}
        return {
            "min": min(vals),
            "avg": (sum(vals) / len(vals)),
            "max": max(vals),
        }

    # Extract disk information from last snapshot
    last_disk = snapshots[-1].get("disk") or {}
    disk_path = last_disk.get("path")
    disk_last_percent = num(last_disk.get("percent"), 0.0)

    return {
        "time_range": {"start": start_ts, "end": end_ts},
        "count": len(snapshots),
        "metrics": {
            "cpu_percent": min_avg_max(cpu_vals),
            "mem_percent": min_avg_max(mem_vals),
            "disk_percent": min_avg_max(disk_vals),
        },
        "disk": {"path": disk_path, "last_percent": disk_last_percent},
        "net": {"sent_total": sent_total, "recv_total": recv_total, "deltas_ignored": deltas_ignored},
        "anomalies": anomalies,
        "last_snapshot": snapshots[-1],
        "series": {"cpu_percent": cpu_vals, "mem_percent": mem_vals, "disk_percent": disk_vals},
    }
