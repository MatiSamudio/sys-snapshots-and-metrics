"""
Automated metric collection runner module.

Responsibilities:
- Maintain an execution loop based on interval/duration parameters
- On each tick:
  1) Request raw snapshot from collector (with absolute network counters)
  2) Calculate network deltas by comparing with previous tick
  3) Save snapshot to SQLite via storage module

Rules:
- Runner does NOT analyze or generate reports
- Network deltas are calculated here (not in collector)
- Must tolerate per-tick failures (log and continue)
"""

from __future__ import annotations

import time
import logging

from src import collector
from src import storage


def run(interval: int, duration: int, cfg: dict, db_path: str) -> dict:
    """
    Execute an automated metric collection run.

    Args:
        interval: Seconds between snapshots (>=1 recommended).
        duration: Total duration in seconds; 0 => infinite (until Ctrl+C).
        cfg: Configuration dictionary (disk_path, top_n_processes, etc.).
        db_path: Path to the SQLite database file.

    Returns:
        Summary dictionary with execution statistics (useful for logs/demo).
    """
    # Sanitize inputs
    interval = int(interval)
    duration = int(duration)

    if interval <= 0:
        interval = 1

    # Ensure database is ready (idempotent if main already initialized)
    storage.init_db(db_path)

    prev_sent = None
    prev_recv = None

    snapshots_saved = 0
    ticks = 0

    start = time.monotonic()
    end = None if duration == 0 else (start + duration)

    logging.info(f"RUN start interval={interval}s duration={duration}s db={db_path}")
   
    try:
        while True:
            # Check duration cutoff
            if end is not None and time.monotonic() >= end:
                break

            tick_start = time.monotonic()
            ticks += 1

            try:
                # Step 1: Collect raw snapshot
                snap = collector.collect_snapshot(cfg)

                # Step 2: Calculate network deltas (comparison between ticks of SAME run)
                sent = snap["net"]["sent"]
                recv = snap["net"]["recv"]

                if prev_sent is None or prev_recv is None:
                    # First tick: no previous data for delta calculation
                    snap["net"]["sent_delta"] = None
                    snap["net"]["recv_delta"] = None
                else:
                    ds = int(sent) - int(prev_sent)
                    dr = int(recv) - int(prev_recv)

                    # Protection: counters can reset => negative delta
                    if ds < 0:
                        logging.warning("net.sent counter reset detected; sent_delta=0")
                        ds = 0
                    if dr < 0:
                        logging.warning("net.recv counter reset detected; recv_delta=0")
                        dr = 0

                    snap["net"]["sent_delta"] = ds
                    snap["net"]["recv_delta"] = dr

                prev_sent = int(sent)
                prev_recv = int(recv)

                # Step 3: Save to database
                storage.save_snapshot(db_path, snap)
                snapshots_saved += 1

                logging.info(f"tick={ticks} saved ts={snap.get('ts')}")

            except Exception as e:
                # Resilience: run continues even if a tick fails
                logging.error(f"tick={ticks} failed: {e}")

            # Step 4: Maintain rhythm (reduce drift)
            elapsed = time.monotonic() - tick_start
            sleep_s = interval - elapsed
            if sleep_s > 0:
                time.sleep(sleep_s)

    except KeyboardInterrupt:
        logging.warning("RUN interrupted by user (Ctrl+C)")

    total_elapsed = time.monotonic() - start
    summary = {
        "ticks": ticks,
        "snapshots_saved": snapshots_saved,
        "interval": interval,
        "duration": duration,
        "elapsed_sec": round(total_elapsed, 3),
        "db_path": db_path,
    }
    logging.info(f"RUN end {summary}")
    return summary


