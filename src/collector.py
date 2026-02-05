"""
System metrics collector module.

Responsibility:
- Read the CURRENT state of the operating system and return a snapshot (dict)
- Does NOT save to database, calculate deltas, analyze, or print

Snapshot schema contract (do not change without consultation):

snapshot = {
  "ts": "ISO timestamp",
  "hostname": "string",
  "os": {"name": "string", "release": "string"},
  "cpu": {"percent": float},                          # 0..100
  "mem": {"total": int, "used": int, "percent": float},# bytes and 0..100
  "disk": {"path": "string", "total": int, "used": int, "percent": float},
  "net": {
    "sent": int, "recv": int,                          # absolute counters
    "sent_delta": None, "recv_delta": None             # deltas calculated in runner
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
    """
    Return a reasonable default disk path based on the operating system.

    Returns:
        "C:\\" for Windows, "/" for Unix-like systems.
    """
    return "C:\\" if platform.system() == "Windows" else "/"


def _iso_now() -> str:
    """
    Get current timestamp in ISO format (UTC with Z suffix).

    Returns:
        ISO 8601 formatted timestamp string.
    """
    return datetime.now(timezone.utc).isoformat()

def collect_snapshot(cfg: dict) -> dict:
    """
    Main entry point for system metrics collection.

    This function orchestrates the collection of all system metrics and
    returns a complete snapshot conforming to the module's schema.

    Args:
        cfg: Configuration dictionary with (minimum):
          - "disk_path": str (optional) - disk path to monitor
          - "top_n_processes": int (optional) - number of top processes to capture

    Returns:
        Complete snapshot dictionary consistent with the schema.
    """
    snapshot = _collect_system(cfg)

    top_n = int(cfg.get("top_n_processes", 5))
    snapshot["top_processes"] = collect_top_processes(top_n)

    return snapshot


def _collect_system(cfg: dict) -> dict:
    """
    Capture CPU, RAM, disk, network, and system metadata.

    Note: Network sent/recv are absolute counters. Deltas are calculated
    by the runner module.

    Args:
        cfg: Configuration dictionary.

    Returns:
        Snapshot dictionary with system metrics.
    """
    disk_path = cfg.get("disk_path") or _default_disk_path()

    # Initialize base structure (closed schema)
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

    # CPU: Non-blocking read (interval=None => instant reading)
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

    # Disk
    try:
        d = psutil.disk_usage(disk_path)
        snapshot["disk"]["path"] = str(disk_path)
        snapshot["disk"]["total"] = int(d.total)
        snapshot["disk"]["used"] = int(d.used)
        snapshot["disk"]["percent"] = float(d.percent)
    except Exception:
        snapshot["disk"] = {"path": str(disk_path), "total": 0, "used": 0, "percent": 0.0}

    # Network (absolute counters)
    try:
        n = psutil.net_io_counters()
        snapshot["net"]["sent"] = int(n.bytes_sent)
        snapshot["net"]["recv"] = int(n.bytes_recv)
        # Deltas always None here (runner fills them in)
        snapshot["net"]["sent_delta"] = None
        snapshot["net"]["recv_delta"] = None
    except Exception:
        snapshot["net"] = {"sent": 0, "recv": 0, "sent_delta": None, "recv_delta": None}

    # Minimal normalization (ensure valid ranges)
    snapshot["cpu"]["percent"] = _clamp_percent(snapshot["cpu"]["percent"])
    snapshot["mem"]["percent"] = _clamp_percent(snapshot["mem"]["percent"])
    snapshot["disk"]["percent"] = _clamp_percent(snapshot["disk"]["percent"])

    return snapshot


def _clamp_percent(x: float) -> float:
    """
    Ensure percentage value is within 0..100 range and is a float.

    Args:
        x: Value to clamp.

    Returns:
        Clamped float value between 0.0 and 100.0.
    """
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
    Collect top N processes by CPU and memory usage (best-effort, non-blocking).

    Designed to be fast and tolerant of permission issues.

    Strategy:
    - Captures "instant" cpu_percent (may be 0 if no warmup data)
    - Captures memory RSS
    - Sorts by (cpu_percent desc, mem_rss desc)

    Args:
        top_n: Number of top processes to return.

    Returns:
        List of process dictionaries, sorted by resource usage.
    """
    if top_n <= 0:
        return []

    procs: list[dict] = []

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            pid = int(proc.info["pid"])
            name = proc.info["name"] or "unknown"

            # cpu_percent(None): non-blocking; may return 0 if no prior data
            cpu = float(proc.cpu_percent(interval=None))
            mem_rss = int(proc.memory_info().rss)

            procs.append(
                {"pid": pid, "name": name, "cpu_percent": cpu if cpu >= 0 else 0.0, "mem_rss": mem_rss if mem_rss >= 0 else 0}
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Process terminated or access denied - skip
            continue
        except Exception:
            # Any other error - skip this process
            continue

    # Sort by CPU and RAM usage (descending)
    procs.sort(key=lambda p: (p["cpu_percent"], p["mem_rss"]), reverse=True)
    return procs[:top_n]


