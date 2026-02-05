"""
SQLite database storage module for system snapshots.

Responsibilities:
- Initialize database schema with snapshots and process_samples tables
- Save complete snapshots atomically with transaction support
- Retrieve snapshots with full process data rehydration

The module maintains a 1:N relationship between snapshots and process samples,
using foreign keys and indexes for efficient querying.
"""

from __future__ import annotations

import sqlite3


# =========================================================
# Database Initialization
# Creates tables if they don't exist
# =========================================================
def init_db(db_path: str) -> None:
    """
    Initialize the SQLite database with required schema.

    Creates two tables:
    - snapshots: Main table storing one row per snapshot
    - process_samples: Secondary table storing process data (1:N with snapshots)

    This operation is idempotent - safe to call multiple times.

    Args:
        db_path: Path to the SQLite database file.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Main table: one snapshot = one row
    cur.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            hostname TEXT NOT NULL,

            os_name TEXT NOT NULL,
            os_release TEXT NOT NULL,

            cpu_percent REAL NOT NULL,

            mem_total INTEGER NOT NULL,
            mem_used INTEGER NOT NULL,
            mem_percent REAL NOT NULL,

            disk_path TEXT NOT NULL,
            disk_total INTEGER NOT NULL,
            disk_used INTEGER NOT NULL,
            disk_percent REAL NOT NULL,

            net_sent INTEGER NOT NULL,
            net_recv INTEGER NOT NULL,
            net_sent_delta INTEGER NULL,
            net_recv_delta INTEGER NULL
        )
    """)

    # Secondary table: many processes per snapshot (1:N relationship)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS process_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER NOT NULL,
            pid INTEGER NOT NULL,
            name TEXT NOT NULL,
            cpu_percent REAL NOT NULL,
            mem_rss INTEGER NOT NULL,
            FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
        )
    """)

    # Index to accelerate reads by snapshot_id
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_process_samples_snapshot_id
        ON process_samples(snapshot_id)
    """)

    conn.commit()
    conn.close()


# =========================================================
# Save Complete Snapshot Atomically
# =========================================================
def save_snapshot(db_path: str, snapshot: dict) -> int:
    """
    Save a complete snapshot to the database atomically.

    Inserts the snapshot into the snapshots table and related processes
    into the process_samples table within a single transaction.

    Args:
        db_path: Path to the SQLite database file.
        snapshot: Snapshot dictionary conforming to the collector schema.

    Returns:
        The snapshot_id (primary key) of the inserted snapshot.

    Raises:
        Exception: If database operation fails (transaction is rolled back).
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # Step 1: Insert into snapshots table
        cur.execute("""
            INSERT INTO snapshots (
                ts,
                hostname,
                os_name,
                os_release,
                cpu_percent,
                mem_total,
                mem_used,
                mem_percent,
                disk_path,
                disk_total,
                disk_used,
                disk_percent,
                net_sent,
                net_recv,
                net_sent_delta,
                net_recv_delta
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot.get("ts"),
            snapshot.get("hostname"),

            (snapshot.get("os") or {}).get("name"),
            (snapshot.get("os") or {}).get("release"),

            (snapshot.get("cpu") or {}).get("percent"),

            (snapshot.get("mem") or {}).get("total"),
            (snapshot.get("mem") or {}).get("used"),
            (snapshot.get("mem") or {}).get("percent"),

            (snapshot.get("disk") or {}).get("path"),
            (snapshot.get("disk") or {}).get("total"),
            (snapshot.get("disk") or {}).get("used"),
            (snapshot.get("disk") or {}).get("percent"),

            (snapshot.get("net") or {}).get("sent"),
            (snapshot.get("net") or {}).get("recv"),
            (snapshot.get("net") or {}).get("sent_delta"),
            (snapshot.get("net") or {}).get("recv_delta"),
        ))

        snapshot_id = int(cur.lastrowid)

        # Step 2: Insert related processes
        for proc in snapshot.get("top_processes", []) or []:
            cur.execute("""
                INSERT INTO process_samples (
                    snapshot_id,
                    pid,
                    name,
                    cpu_percent,
                    mem_rss
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                snapshot_id,
                int(proc.get("pid")),
                str(proc.get("name") or "unknown"),
                float(proc.get("cpu_percent") or 0.0),
                int(proc.get("mem_rss") or 0),
            ))

        conn.commit()
        return snapshot_id

    except Exception:
        conn.rollback()
        # Storage does not silence errors: runner handles per-tick failures
        raise

    finally:
        conn.close()


# =========================================================
# Read Snapshots for Analyzer (Exactly N Complete Snapshots)
# =========================================================
def get_snapshots(db_path: str, last_lines: int) -> list[dict]:
    """
    Retrieve the last N snapshots in chronological order (oldest to newest).

    Snapshots are fully rehydrated with their associated process data.

    Note: We don't use JOIN+LIMIT because that limits rows, not snapshots.
    Instead, we fetch the last N snapshots, then fetch all their processes.

    Args:
        db_path: Path to the SQLite database file.
        last_lines: Number of most recent snapshots to retrieve.

    Returns:
        List of snapshot dictionaries in chronological order, rehydrated
        with top_processes data.
    """
    n = int(last_lines)
    if n <= 0:
        return []

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Step 1: Fetch last N snapshots by insertion order
        snap_rows = cur.execute(
            "SELECT * FROM snapshots ORDER BY id DESC LIMIT ?",
            (n,),
        ).fetchall()

        if not snap_rows:
            return []

        # Reverse to chronological order for period/from-to and disk last%
        snap_rows = list(reversed(snap_rows))
        ids = [int(r["id"]) for r in snap_rows]

        # Step 2: Fetch processes ONLY for these snapshots
        placeholders = ",".join(["?"] * len(ids))
        proc_rows = cur.execute(
            f"""
            SELECT snapshot_id, pid, name, cpu_percent, mem_rss
            FROM process_samples
            WHERE snapshot_id IN ({placeholders})
            ORDER BY snapshot_id
            """,
            ids,
        ).fetchall()

    # Step 3: Group processes by snapshot_id
    procs_by_id: dict[int, list[dict]] = {}
    for p in proc_rows:
        sid = int(p["snapshot_id"])
        procs_by_id.setdefault(sid, []).append({
            "pid": int(p["pid"]),
            "name": p["name"] or "unknown",
            "cpu_percent": float(p["cpu_percent"]),
            "mem_rss": int(p["mem_rss"]),
        })

    # Step 4: Rehydrate to closed schema
    out: list[dict] = []
    for r in snap_rows:
        sid = int(r["id"])
        out.append({
            "ts": r["ts"],
            "hostname": r["hostname"] or "unknown",
            "os": {"name": r["os_name"] or "unknown", "release": r["os_release"] or "unknown"},
            "cpu": {"percent": float(r["cpu_percent"])},
            "mem": {"total": int(r["mem_total"]), "used": int(r["mem_used"]), "percent": float(r["mem_percent"])},
            "disk": {
                "path": r["disk_path"] or "",
                "total": int(r["disk_total"]),
                "used": int(r["disk_used"]),
                "percent": float(r["disk_percent"]),
            },
            "net": {
                "sent": int(r["net_sent"]),
                "recv": int(r["net_recv"]),
                "sent_delta": None if r["net_sent_delta"] is None else int(r["net_sent_delta"]),
                "recv_delta": None if r["net_recv_delta"] is None else int(r["net_recv_delta"]),
            },
            "top_processes": procs_by_id.get(sid, []),
        })

    return out
