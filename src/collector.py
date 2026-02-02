# -*- coding: utf-8 -*-
"""
Módulo de recolección de métricas del sistema
Responsable: Dev 1 - System Metrics (CPU/RAM/DISK/NET)
             Dev 2 - Top Procesos

Responsabilidad única: Leer el estado actual del sistema operativo
No guarda, no compara, no reporta - solo recolecta.
"""

import psutil
import platform
import socket
from datetime import datetime


# =============================================================================
# DEV 1 — SYSTEM METRICS (CPU/RAM/DISK/NET)
# =============================================================================

def collect_system(config: dict) -> dict:
    """
    Recolecta métricas básicas del sistema operativo.
    
    Args:
        config (dict): Configuración del sistema. Debe contener:
            - "disk_path" (str): Path del disco a medir (ej: "/" o "C:\\")
    
    Returns:
        dict: Snapshot con métricas del sistema en estructura fija
              Keys: schema_version, ts, hostname, os, cpu, mem, disk, net, top_processes
    """
    # Estructura base del snapshot según contrato de datos
    snapshot = {
        "schema_version": 1,
        "ts": "",
        "hostname": "",
        "os": {"name": "", "release": ""},
        "cpu": {"percent": 0.0},
        "mem": {"total": 0, "used": 0, "percent": 0.0},
        "disk": {"path": "", "total": 0, "used": 0, "percent": 0.0},
        "net": {
            "sent": 0,
            "recv": 0,
            "sent_delta": None,
            "recv_delta": None
        },
        "top_processes": []
    }

    # =========================================
    # 1. TIMESTAMP (marca de tiempo ISO)
    # =========================================
    try:
        snapshot["ts"] = datetime.now().isoformat()
    except Exception as e:
        print(f"⚠️  Error capturando timestamp: {e}")
        snapshot["ts"] = "unknown"

    # =========================================
    # 2. HOSTNAME (nombre de la computadora)
    # =========================================
    try:
        snapshot["hostname"] = platform.node()
    except Exception as e:
        print(f"⚠️  Error capturando hostname: {e}")
        snapshot["hostname"] = "unknown"

    # =========================================
    # 3. SISTEMA OPERATIVO
    # =========================================
    try:
        snapshot["os"]["name"] = platform.system()
        snapshot["os"]["release"] = platform.release()
    except Exception as e:
        print(f"⚠️  Error capturando OS info: {e}")
        snapshot["os"]["name"] = "unknown"
        snapshot["os"]["release"] = "unknown"

    # =========================================
    # 4. CPU (procesador)
    # =========================================
    try:
        cpu_porcentaje = psutil.cpu_percent(interval=1)
        snapshot["cpu"]["percent"] = round(cpu_porcentaje, 2)
    except Exception as e:
        print(f"⚠️  Error capturando CPU: {e}")
        snapshot["cpu"]["percent"] = 0.0

    # =========================================
    # 5. MEMORIA RAM
    # =========================================
    try:
        mem = psutil.virtual_memory()
        snapshot["mem"]["total"] = mem.total
        snapshot["mem"]["used"] = mem.used
        snapshot["mem"]["percent"] = round(mem.percent, 2)
    except Exception as e:
        print(f"⚠️  Error capturando memoria: {e}")
        snapshot["mem"]["total"] = 0
        snapshot["mem"]["used"] = 0
        snapshot["mem"]["percent"] = 0.0

    # =========================================
    # 6. DISCO DURO (usa config["disk_path"])
    # =========================================
    try:
        disk_path = config.get("disk_path", _get_default_disk_path())
        disco = psutil.disk_usage(disk_path)

        snapshot["disk"]["path"] = disk_path
        snapshot["disk"]["total"] = disco.total
        snapshot["disk"]["used"] = disco.used
        snapshot["disk"]["percent"] = round(disco.percent, 2)
    except Exception as e:
        print(f"⚠️  Error capturando disco: {e}")
        snapshot["disk"]["path"] = config.get("disk_path", "/")
        snapshot["disk"]["total"] = 0
        snapshot["disk"]["used"] = 0
        snapshot["disk"]["percent"] = 0.0

    # =========================================
    # 7. RED (net) - sent/recv acumulados
    # =========================================
    try:
        red = psutil.net_io_counters()
        snapshot["net"]["sent"] = red.bytes_sent
        snapshot["net"]["recv"] = red.bytes_recv
        snapshot["net"]["sent_delta"] = None
        snapshot["net"]["recv_delta"] = None
    except Exception as e:
        print(f"⚠️  Error capturando red: {e}")
        snapshot["net"]["sent"] = 0
        snapshot["net"]["recv"] = 0
        snapshot["net"]["sent_delta"] = None
        snapshot["net"]["recv_delta"] = None

    return snapshot


def _get_default_disk_path() -> str:
    """
    Función auxiliar: Determina el path del disco por defecto según el SO.
    """
    if platform.system() == "Windows":
        return "C:\\"
    else:
        return "/"


# =============================================================================
# DEV 2 — TOP PROCESOS
# =============================================================================

def collect_top_processes(top_n: int) -> list[dict]:
    """
    Obtiene los top N procesos ordenados por uso de CPU y RAM combinados.
    
    Args:
        top_n (int): Cantidad de procesos top a retornar
    
    Returns:
        list[dict]: Lista única de diccionarios con los top N procesos.
                    Cada dict tiene: pid, name, cpu_percent, mem_rss
    """
    procesos = []

    # Primer muestreo de CPU (necesario para que cpu_percent tenga datos reales)
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            proc.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Segundo muestreo con intervalo para obtener valores actualizados
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            cpu = proc.cpu_percent(interval=0.1)
            mem_rss = proc.memory_info().rss
            
            procesos.append({
                "pid": proc.info['pid'],
                "name": proc.info['name'] or "desconocido",
                "cpu_percent": cpu or 0.0,
                "mem_rss": mem_rss or 0
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Normalizar: asegurar que no haya None
    for p in procesos:
        p["cpu_percent"] = p.get("cpu_percent", 0.0)
        p["mem_rss"] = p.get("mem_rss", 0)

    # Ordenar por CPU + RAM combinados
    if procesos:
        max_cpu = max(p["cpu_percent"] for p in procesos) or 1
        max_ram = max(p["mem_rss"] for p in procesos) or 1
        
        for p in procesos:
            p["_score"] = (p["cpu_percent"] / max_cpu) + (p["mem_rss"] / max_ram)
        
        procesos_ordenados = sorted(procesos, key=lambda x: x["_score"], reverse=True)[:top_n]
        
        for p in procesos_ordenados:
            del p["_score"]
        
        return procesos_ordenados
    
    return []


# =============================================================================
# BLOQUE DE PRUEBA
# =============================================================================

if __name__ == "__main__":
    import json

    print("🔧 TEST: collector.py (Dev 1 + Dev 2)")
    print("=" * 60)

    # Test Dev 1
    print("\n📍 Probando collect_system(config)...")
    test_config = {
        "disk_path": "C:\\" if platform.system() == "Windows" else "/"
    }
    
    snapshot = collect_system(test_config)
    
    print(f"✅ schema_version: {snapshot['schema_version']}")
    print(f"✅ ts: {snapshot['ts']}")
    print(f"✅ hostname: {snapshot['hostname']}")
    print(f"✅ os: {snapshot['os']}")
    print(f"✅ cpu: {snapshot['cpu']}")
    print(f"✅ mem: {snapshot['mem']}")
    print(f"✅ disk: {snapshot['disk']}")
    print(f"✅ net: {snapshot['net']}")
    print(f"✅ top_processes: {snapshot['top_processes']}")

    print("\n📄 JSON del snapshot:")
    print(json.dumps(snapshot, indent=2))

    # Test Dev 2
    print("\n" + "=" * 60)
    print("📍 Probando collect_top_processes(5)...")
    
    top_procs = collect_top_processes(5)
    
    print(f"✅ Cantidad: {len(top_procs)}")
    
    print("\n📄 Top 5 procesos:")
    for i, p in enumerate(top_procs, 1):
        mem_mb = p['mem_rss'] / (1024**2)
        print(f"  {i}. PID:{p['pid']:>6} | {p['name']:<25} | CPU:{p['cpu_percent']:>6.2f}% | RAM:{mem_mb:>8.2f} MB")

    # Verificación
    print("\n" + "=" * 60)
    print("🔍 VERIFICACIÓN DE CONTRATO:")
    print("=" * 60)
    
    required_keys = ["schema_version", "ts", "hostname", "os", "cpu", "mem", "disk", "net", "top_processes"]
    for key in required_keys:
        status = "✅" if key in snapshot else "❌"
        print(f"  {status} snapshot['{key}']")
    
    net_keys = ["sent", "recv", "sent_delta", "recv_delta"]
    for key in net_keys:
        status = "✅" if key in snapshot["net"] else "❌"
        print(f"  {status} net['{key}']")
    
    if top_procs:
        proc_keys = ["pid", "name", "cpu_percent", "mem_rss"]
        for key in proc_keys:
            status = "✅" if key in top_procs[0] else "❌"
            print(f"  {status} proceso['{key}']")

    print("\n✅ ¡Test completado!")