import sqlite3
from datetime import datetime, timedelta

import runner

snapshot_id = 0 # variable donde se va a guardar el id del ultimo snapshot 

# =========================================================
# Inicializa la base de datos
# Crea las tablas si no existen
# =========================================================
def init_db(db_path: str) -> None:
    """
    Crea el archivo SQLite y define el schema.
    Si las tablas ya existen, no hace nada.
    """

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Tabla principal: un snapshot = una fila
    cur.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY,
            ts TEXT,
            hostname TEXT,

            os_name TEXT,
            os_release TEXT,

            cpu_percent REAL,

            mem_total INTEGER,
            mem_used INTEGER,
            mem_percent REAL,

            disk_path TEXT,
            disk_total INTEGER,
            disk_used INTEGER,
            disk_percent REAL,

            net_sent INTEGER,
            net_recv INTEGER,
            net_sent_delta INTEGER,
            net_recv_delta INTEGER
        )
    """)

    # Tabla secundaria: muchos procesos por snapshot
    cur.execute("""
        CREATE TABLE IF NOT EXISTS process_samples (
            id INTEGER PRIMARY KEY,
            ts TEXT,
            pid INTEGER,
            name TEXT,
            cpu_percent REAL,
            mem_rss INTEGER
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# Guarda un snapshot completo de forma atómica
# =========================================================
def save_snapshot(db_path: str, snapshot: dict) -> int:
    """
    Inserta un snapshot completo en la base.
    Si algo falla, no se guarda nada.
    Devuelve el snapshot_id generado.
    """

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # -------------------------------
        # 1. Insertar en tabla snapshots
        # -------------------------------
        cur.execute("""
            INSERT INTO snapshots (
                schema_version,
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot.get("schema_version"),
            snapshot.get("ts"),
            snapshot.get("hostname"),

            snapshot.get("os", {}).get("name"),
            snapshot.get("os", {}).get("release"),

            snapshot.get("cpu", {}).get("percent"),

            snapshot.get("mem", {}).get("total"),
            snapshot.get("mem", {}).get("used"),
            snapshot.get("mem", {}).get("percent"),

            snapshot.get("disk", {}).get("path"),
            snapshot.get("disk", {}).get("total"),
            snapshot.get("disk", {}).get("used"),
            snapshot.get("disk", {}).get("percent"),

            snapshot.get("net", {}).get("sent"),
            snapshot.get("net", {}).get("recv"),
            snapshot.get("net", {}).get("sent_delta"),
            snapshot.get("net", {}).get("recv_delta")
        ))

        # ID autogenerado del snapshot recién insertado
        snapshot_id = cur.lastrowid

        # -----------------------------------
        # 2. Insertar procesos relacionados
        # -----------------------------------
        for proc in snapshot.get("top_processes", []):
            cur.execute("""
                INSERT INTO process_samples (
                    ts,
                    pid,
                    name,
                    cpu_percent,
                    mem_rss
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                proc.get("ts"),
                proc.get("pid"),
                proc.get("name"),
                proc.get("cpu_percent"),
                proc.get("mem_rss")
            ))

        # -----------------------------------
        # 3. Confirmar transacción
        # -----------------------------------
        conn.commit()
        return snapshot_id

    except Exception as e:
        # Si algo falla: rollback total
        conn.rollback()
        # raise e > a evaluar a detalle como aplicar dentro del log. Comentado para que no pare la ejecucion de los otros snapshots 

    finally:
        conn.close()



#=========   koa la query 100% real no feik   =======

results_query = 0 # Esta variable, actualizada como lista con tuplas, es lo consume el analyzer de Carlos.

def get_snapshots(db_path):
    
    duration = runner.summary["duration"]

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("SELECT ts FROM snapshots WHERE id = ?", (snapshot_id,))
    last_ts = cur.fetchone()[0]

    last_datetime = datetime.fromisoformat(last_ts)
    start_ts = (last_datetime - timedelta(seconds=duration)).isoformat()
    
    query = """
        SELECT s.*, p.pid, p.name, p.cpu_percent as proc_cpu, p.mem_rss
        FROM snapshots s
        INNER JOIN process_samples p ON s.ts = p.ts
        WHERE s.ts >= ? AND s.ts <= ?
        ORDER BY s.ts ASC
    """
    
    cur.execute(query, (start_ts, last_ts))
    results = cur.fetchall()
    conn.close()
    results_query.append(results)

    return results_query
