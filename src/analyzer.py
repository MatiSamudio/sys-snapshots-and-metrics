# src/analyzer.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any

def analyze(snapshots: list[dict], cfg: dict) -> dict:
    anomalies_cfg = (cfg or {}).get("anomalies") or {}
    cpu_hi = float(anomalies_cfg.get("cpu_percent_high", 90.0))
    mem_hi = float(anomalies_cfg.get("mem_percent_high", 90.0))
    net_hi = anomalies_cfg.get("net_delta_high", None)
    net_hi = None if net_hi is None else int(net_hi)

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
        try:
            v = float(x)
            return v
        except Exception:
            return float(default)

    def int_or_none(x: Any):
        if x is None:
            return None
        try:
            return int(x)
        except Exception:
            return None

    # asume cronológico (storage lo garantiza)
    start_ts = snapshots[0].get("ts")
    end_ts = snapshots[-1].get("ts")

    cpu_vals: list[float] = []
    mem_vals: list[float] = []
    disk_vals: list[float] = []

    sent_total = 0
    recv_total = 0
    deltas_ignored = 0
    anomalies: list[dict] = []

    for s in snapshots:
        ts = s.get("ts")

        cpu_p = num(((s.get("cpu") or {}).get("percent")), 0.0)
        mem_p = num(((s.get("mem") or {}).get("percent")), 0.0)
        disk_p = num(((s.get("disk") or {}).get("percent")), 0.0)

        cpu_vals.append(cpu_p)
        mem_vals.append(mem_p)
        disk_vals.append(disk_p)

        reasons: list[str] = []
        if cpu_p >= cpu_hi:
            reasons.append(f"cpu_percent_high (>= {cpu_hi})")
        if mem_p >= mem_hi:
            reasons.append(f"mem_percent_high (>= {mem_hi})")

        net = s.get("net") or {}
        ds = int_or_none(net.get("sent_delta"))
        dr = int_or_none(net.get("recv_delta"))

        if ds is None:
            deltas_ignored += 1
        else:
            if ds < 0: ds = 0
            sent_total += ds
            if net_hi is not None and ds >= net_hi:
                reasons.append(f"net_sent_delta_high (>= {net_hi})")

        if dr is None:
            deltas_ignored += 1
        else:
            if dr < 0: dr = 0
            recv_total += dr
            if net_hi is not None and dr >= net_hi:
                reasons.append(f"net_recv_delta_high (>= {net_hi})")

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
        if not vals:
            return {"min": None, "avg": None, "max": None}
        return {
            "min": min(vals),
            "avg": (sum(vals) / len(vals)),
            "max": max(vals),
        }

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
