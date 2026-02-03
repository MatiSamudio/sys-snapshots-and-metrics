# src/collector.py
# -*- coding: utf-8 -*-
"""
collector.py — Recolección de métricas (SOLO captura)

Responsabilidad:
- Leer el estado ACTUAL del sistema operativo y devolver un snapshot (dict).
- NO guarda DB, NO calcula deltas, NO analiza, NO imprime.

Contrato (schema) del snapshot (NO cambiar sin consultar):

snapshot = {
  "ts": "ISO timestamp",
  "hostname": "string",
  "os": {"name": "string", "release": "string"},
  "cpu": {"percent": float},                          # 0..100
  "mem": {"total": int, "used": int, "percent": float},# bytes y 0..100
  "disk": {"path": "string", "total": int, "used": int, "percent": float},
  "net": {
    "sent": int, "recv": int,                          # counters absolutos
    "sent_delta": None, "recv_delta": None             # deltas se calculan en runner
  },
  "top_processes": [
    {"pid": int, "name": str, "cpu_percent": float, "mem_rss": int}
  ]
}
"""

from __future__ import annotations

from datetime import datetime, timezone
import platform
import psutil


def _default_disk_path() -> str:
    """Devuelve un disk_path razonable según SO."""
    return "C:\\" if platform.system() == "Windows" else "/"


def _iso_now() -> str:
    """Timestamp ISO en UTC (Z)."""
    return datetime.now(timezone.utc).isoformat()

def collect_snapshot(cfg: dict) -> dict:
    """
    Función única de entrada para el sistema.

    Args:
        cfg: dict con (mínimo):
          - "disk_path": str (opcional)
          - "top_n_processes": int (opcional)

    Returns:
        snapshot dict completo y consistente con el schema.
    """
    snapshot = _collect_system(cfg)

    top_n = int(cfg.get("top_n_processes", 5))
    snapshot["top_processes"] = collect_top_processes(top_n)

    return snapshot


def _collect_system(cfg: dict) -> dict:
    """
    Captura CPU/RAM/DISK/NET/metadata.
    Nota: net.sent/net.recv son counters absolutos.
    """
    disk_path = cfg.get("disk_path") or _default_disk_path()

    # Estructura base cerrada (schema)
    snapshot = {
        "ts": _iso_now(),
        "hostname": platform.node() or "unknown",
        "os": {"name": platform.system() or "unknown", "release": platform.release() or "unknown"},
        "cpu": {"percent": 0.0},
        "mem": {"total": 0, "used": 0, "percent": 0.0},
        "disk": {"path": str(disk_path), "total": 0, "used": 0, "percent": 0.0},
        "net": {"sent": 0, "recv": 0, "sent_delta": None, "recv_delta": None},
        "top_processes": [],
    }

    # CPU: no bloquear el programa (interval=None -> lectura no bloqueante)
    try:
        snapshot["cpu"]["percent"] = float(psutil.cpu_percent(interval=None))
    except Exception:
        snapshot["cpu"]["percent"] = 0.0

    # RAM
    try:
        m = psutil.virtual_memory()
        snapshot["mem"]["total"] = int(m.total)
        snapshot["mem"]["used"] = int(m.used)
        snapshot["mem"]["percent"] = float(m.percent)
    except Exception:
        snapshot["mem"] = {"total": 0, "used": 0, "percent": 0.0}

    # Disco
    try:
        d = psutil.disk_usage(disk_path)
        snapshot["disk"]["path"] = str(disk_path)
        snapshot["disk"]["total"] = int(d.total)
        snapshot["disk"]["used"] = int(d.used)
        snapshot["disk"]["percent"] = float(d.percent)
    except Exception:
        snapshot["disk"] = {"path": str(disk_path), "total": 0, "used": 0, "percent": 0.0}

    # Red (counters absolutos)
    try:
        n = psutil.net_io_counters()
        snapshot["net"]["sent"] = int(n.bytes_sent)
        snapshot["net"]["recv"] = int(n.bytes_recv)
        # deltas siempre None aquí (runner los completa)
        snapshot["net"]["sent_delta"] = None
        snapshot["net"]["recv_delta"] = None
    except Exception:
        snapshot["net"] = {"sent": 0, "recv": 0, "sent_delta": None, "recv_delta": None}

    # Normalización mínima (rangos)
    snapshot["cpu"]["percent"] = _clamp_percent(snapshot["cpu"]["percent"])
    snapshot["mem"]["percent"] = _clamp_percent(snapshot["mem"]["percent"])
    snapshot["disk"]["percent"] = _clamp_percent(snapshot["disk"]["percent"])

    return snapshot


def _clamp_percent(x: float) -> float:
    """Asegura 0..100 y float."""
    try:
        v = float(x)
    except Exception:
        return 0.0
    if v < 0:
        return 0.0
    if v > 100:
        return 100.0
    return v


def collect_top_processes(top_n: int) -> list[dict]:
    """
    Top N procesos (best-effort) sin bloquear (sin interval por proceso).
    Diseñado para ser rápido y tolerante a permisos.

    Estrategia MVP:
    - Captura cpu_percent "instantáneo" (puede ser 0 si no hubo warmup)
    - Captura mem_rss
    - Ordena por (cpu_percent desc, mem_rss desc)
    """
    if top_n <= 0:
        return []

    procs: list[dict] = []

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            pid = int(proc.info["pid"])
            name = proc.info["name"] or "unknown"

            # cpu_percent(None): no bloquea; puede dar 0 si no hay datos previos
            cpu = float(proc.cpu_percent(interval=None))
            mem_rss = int(proc.memory_info().rss)

            procs.append(
                {"pid": pid, "name": name, "cpu_percent": cpu if cpu >= 0 else 0.0, "mem_rss": mem_rss if mem_rss >= 0 else 0}
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        except Exception:
            continue

    # Ordenar por CPU y RAM
    procs.sort(key=lambda p: (p["cpu_percent"], p["mem_rss"]), reverse=True)
    return procs[:top_n]


