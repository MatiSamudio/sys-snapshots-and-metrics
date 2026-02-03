# src/runner.py
# -*- coding: utf-8 -*-
"""
runner.py — Automatización (SOLO repetición + deltas + guardado)

Responsabilidad:
- Mantener un loop por interval/duration.
- En cada tick:
  1) pedir snapshot crudo al collector (counters absolutos)
  2) calcular deltas de red comparando con el tick anterior
  3) guardar snapshot en SQLite vía storage.save_snapshot

Reglas:
- runner NO analiza, NO reporta.
- deltas se calculan aquí (no en collector).
- Debe tolerar fallos por tick (log y continuar).
"""

from __future__ import annotations

import time
import logging

import collector
import storage 
summary=0

def run(interval: int, duration: int, cfg: dict, db_path: str) -> dict:
    """
    Ejecuta un run automático.

    Args:
        interval: segundos entre capturas (>=1 recomendado)
        duration: segundos totales; si 0 => hasta Ctrl+C
        cfg: dict de config (disk_path, top_n_processes, etc.)
        db_path: ruta al sqlite db

    Returns:
        summary dict (útil para logs/demo)
    """
    # Sanitizar inputs
    interval = int(interval)
    duration = int(duration)

    if interval <= 0:
        interval = 1

    # Asegurar DB lista (si main ya lo hace, esto es idempotente)
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
            # Corte por duración
            if end is not None and time.monotonic() >= end:
                break

            tick_start = time.monotonic()
            ticks += 1

            try:
                # 1) Snapshot crudo
                snap = collector.collect_snapshot(cfg)

                # 2) Deltas de red (comparación entre ticks del MISMO run)
                sent = snap["net"]["sent"]
                recv = snap["net"]["recv"]

                if prev_sent is None or prev_recv is None:
                    snap["net"]["sent_delta"] = None
                    snap["net"]["recv_delta"] = None
                else:
                    ds = int(sent) - int(prev_sent)
                    dr = int(recv) - int(prev_recv)

                    # Protección: counters pueden resetearse -> delta negativo
                    if ds < 0:
                        logging.warning("net.sent counter reset detectado; sent_delta=0")
                        ds = 0
                    if dr < 0:
                        logging.warning("net.recv counter reset detectado; recv_delta=0")
                        dr = 0

                    snap["net"]["sent_delta"] = ds
                    snap["net"]["recv_delta"] = dr

                prev_sent = int(sent)
                prev_recv = int(recv)

                # 3) Guardar
                storage.save_snapshot(db_path, snap)
                snapshots_saved += 1

                logging.info(f"tick={ticks} saved ts={snap.get('ts')}")

            except Exception as e:
                # Resiliencia: el run sigue aunque un tick falle
                logging.error(f"tick={ticks} failed: {e}")

            # 4) Ritmo (reduce drift)
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


