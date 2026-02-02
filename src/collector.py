"""
Módulo de recolección de métricas del sistema
Responsable: Dev 1 - System Metrics (CPU/RAM/DISK/NET)

Responsabilidad única: Leer el estado actual del sistema operativo
No guarda, no compara, no reporta - solo recolecta.
"""

import psutil
import platform
from datetime import datetime


def obtener_snapshot_sistema(config=None):
    """
    Recolecta métricas básicas del sistema operativo.
    
    Args:
        config (dict, optional): Configuración del sistema (no usado actualmente)
    
    Returns:
        dict: Snapshot con métricas del sistema en estructura fija
    """
    
    # Estructura base del snapshot
    snapshot = {
        "schema_version": 1,
        "ts": "",
        "hostname": "",
        "os": {"name": "", "release": ""},
        "cpu": {"percent": 0.0},
        "mem": {"total": 0, "used": 0, "percent": 0.0},
        "disk": {"path": "", "total": 0, "used": 0, "percent": 0.0},
        "network": {
            "bytes_sent": 0,
            "bytes_recv": 0
        }
    }
    
    # ========================================
    # 1. TIMESTAMP (marca de tiempo)
    # ========================================
    try:
        snapshot["ts"] = datetime.now().isoformat()
    except Exception as e:
        print(f"⚠️  Error capturando timestamp: {e}")
        snapshot["ts"] = "unknown"
    
    # ========================================
    # 2. HOSTNAME (nombre de la computadora)
    # ========================================
    try:
        snapshot["hostname"] = platform.node()
    except Exception as e:
        print(f"⚠️  Error capturando hostname: {e}")
        snapshot["hostname"] = "unknown"
    
    # ========================================
    # 3. SISTEMA OPERATIVO
    # ========================================
    try:
        snapshot["os"]["name"] = platform.system()
        snapshot["os"]["release"] = platform.release()
    except Exception as e:
        print(f"⚠️  Error capturando OS info: {e}")
        snapshot["os"]["name"] = "unknown"
        snapshot["os"]["release"] = "unknown"
    
    # ========================================
    # 4. CPU (procesador)
    # ========================================
    try:
        # ⚠️ CRÍTICO: interval debe ser > 0 para obtener valores reales
        # Primera lectura tarda 1 segundo (es normal)
        cpu_porcentaje = psutil.cpu_percent(interval=1)
        snapshot["cpu"]["percent"] = round(cpu_porcentaje, 2)
    except Exception as e:
        print(f"⚠️  Error capturando CPU: {e}")
        snapshot["cpu"]["percent"] = 0.0
    
    # ========================================
    # 5. MEMORIA RAM
    # ========================================
    try:
        mem = psutil.virtual_memory()
        snapshot["mem"]["total"] = mem.total      # bytes totales
        snapshot["mem"]["used"] = mem.used        # bytes usados
        snapshot["mem"]["percent"] = round(mem.percent, 2)
    except Exception as e:
        print(f"⚠️  Error capturando memoria: {e}")
        snapshot["mem"]["total"] = 0
        snapshot["mem"]["used"] = 0
        snapshot["mem"]["percent"] = 0.0
    
    # ========================================
    # 6. DISCO DURO
    # ========================================
    try:
        # Detectar path según sistema operativo
        disco_path = _obtener_path_disco()
        disco = psutil.disk_usage(disco_path)
        
        snapshot["disk"]["path"] = disco_path
        snapshot["disk"]["total"] = disco.total   # bytes totales
        snapshot["disk"]["used"] = disco.used     # bytes usados
        snapshot["disk"]["percent"] = round(disco.percent, 2)
    except Exception as e:
        print(f"⚠️  Error capturando disco: {e}")
        snapshot["disk"]["path"] = "/"
        snapshot["disk"]["total"] = 0
        snapshot["disk"]["used"] = 0
        snapshot["disk"]["percent"] = 0.0
    
    # ========================================
    # 7. RED (network)
    # ========================================
    try:
        red = psutil.net_io_counters()
        snapshot["network"]["bytes_sent"] = red.bytes_sent      # total enviado
        snapshot["network"]["bytes_recv"] = red.bytes_recv      # total recibido
    except Exception as e:
        print(f"⚠️  Error capturando red: {e}")
        snapshot["network"]["bytes_sent"] = 0
        snapshot["network"]["bytes_recv"] = 0
    
    return snapshot


def _obtener_path_disco():
    """
    Determina el path del disco principal según el sistema operativo.
    
    Returns:
        str: Path del disco ('/' para Unix/Mac, 'C:\\' para Windows)
    """
    sistema = platform.system()
    if sistema == "Windows":
        return "C:\\"
    else:
        return "/"


# ========================================
# FUNCIONES DE UTILIDAD PARA VER RESULTADOS
# ========================================

def imprimir_snapshot_bonito(snapshot):
    """
    Muestra un snapshot de forma legible en consola.
    Útil para debugging y verificar que todo funciona.
    
    Args:
        snapshot (dict): Snapshot a imprimir
    """
    print("\n" + "="*60)
    print("📸 SNAPSHOT DEL SISTEMA")
    print("="*60)
    print(f"🕐 Timestamp:  {snapshot['ts']}")
    print(f"💻 Hostname:   {snapshot['hostname']}")
    print(f"🖥️  OS:         {snapshot['os']['name']} {snapshot['os']['release']}")
    print(f"⚙️  CPU:        {snapshot['cpu']['percent']}%")
    
    # Convertir bytes a GB para que sea más legible
    ram_gb_usado = snapshot['mem']['used'] / (1024**3)
    ram_gb_total = snapshot['mem']['total'] / (1024**3)
    print(f"🧠 RAM:        {snapshot['mem']['percent']}% ({ram_gb_usado:.2f} / {ram_gb_total:.2f} GB)")
    
    disco_gb_usado = snapshot['disk']['used'] / (1024**3)
    disco_gb_total = snapshot['disk']['total'] / (1024**3)
    print(f"💾 Disco:      {snapshot['disk']['percent']}% ({disco_gb_usado:.2f} / {disco_gb_total:.2f} GB)")
    
    red_mb_enviado = snapshot['network']['bytes_sent'] / (1024**2)
    red_mb_recibido = snapshot['network']['bytes_recv'] / (1024**2)
    print(f"🌐 Red:        ↑{red_mb_enviado:.2f} MB | ↓{red_mb_recibido:.2f} MB")
    print("="*60 + "\n")


# ========================================
# BLOQUE DE PRUEBA (solo para ti)
# ========================================

if __name__ == "__main__":
    """
    Este bloque solo se ejecuta cuando corres este archivo directamente.
    Es para que puedas probar tu código sin depender de otros módulos.
    """
    print("🧪 DEV 1: Analizando sistema completo (CPU, RAM, Disco, Red)...")
    
    # Obtener las métricas
    datos = obtener_snapshot_sistema()
    
    # Mostrar de forma bonita
    imprimir_snapshot_bonito(datos)
    
    # Mostrar también el JSON puro (para verificar estructura)
    print("📋 REPORTE GENERADO CON ÉXITO:")
    # Imprimimos bonito el diccionario
    import json
    print(json.dumps(datos, indent=4))
    
    print("\n✅ ¡Test completado exitosamente!")