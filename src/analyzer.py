# importamos el snapshot

from src.storage import SnapshotStorage

# función para analizar un snapshot y devolver un resumen

def summarize(snapshots):

    # controlamos que el snapshot no esté vacío

    if snapshots is None or len(snapshots) == 0:
        return "El snampshot está vacío"
    
    # umbral de uso para detectar anomalías

    threshold_cpu = 89.9
    threshold_mem = 89.9
    threshold_disk = 95.0
    threshold_net = 960000000

    # inicializamos los acumuladores

    cpu_values = []
    mem_percent = []
    mem_used = []
    mem_total = []
    disk_percent = []
    disk_used = []
    disk_total = []
    net_sent = []
    net_recv = []
    net_sent_delta = []
    net_recv_delta = []
    anomalies = []

    for snapshot in snapshots:
        cpu_values.append(snapshot["cpu"]["percent"])
        mem_percent.append(snapshot["mem"]["percent"])
        mem_used.append(snapshot["mem"]["used"])
        mem_total.append(snapshot["mem"]["total"])
        disk_percent.append(snapshot["disk"]["percent"])
        disk_used.append(snapshot["disk"]["used"])
        disk_total.append(snapshot["disk"]["total"])
        net_sent.append(snapshot["net"]["sent"])
        net_recv.append(snapshot["net"]["recv"])
        net_sent_delta.append(snapshot["net"]["sent_delta"])
        net_recv_delta.append(snapshot["net"]["recv_delta"])

    # deteccion de valores anómalos simples

    if snapshot["cpu"]["percent"] > threshold_cpu:
        anomalies.append({"ts": snapshot["ts"], "reason": "Uso de CPU muy alto"})
    elif snapshot["mem"]["percent"] > threshold_mem:
        anomalies.append({"ts": snapshot["ts"], "reason": "Uso de memoria muy alto"})
    elif snapshot["disk"]["percent"] > threshold_disk:
        anomalies.append({"ts": snapshot["ts"], "reason": "Uso de disco muy alto"})
    elif snapshot["net"]["sent"] > threshold_net or snapshot["net"]["recv"] > threshold_net:
        anomalies.append({"ts": snapshot["ts"], "reason": "Uso de red muy alto"})
    
    # calculamos los promedios y maximos de uso para cada recurso
    
    avg_cpu = sum(cpu_values) / len(cpu_values)
    max_cpu = max(cpu_values)

    avg_mem = sum(mem_percent) / len(mem_percent)
    max_mem = max(mem_percent)

    max_disk = max(disk_percent)

    avg_net_sent = sum(net_sent) / len(net_sent)
    max_net_sent = max(net_sent)

    avg_net_recv = sum(net_recv) / len(net_recv)
    max_net_recv = max(net_recv)

    # creamos el resumen del snapshot
    
    summary = {
        "avg_cpu": avg_cpu,
        "max_cpu": max_cpu,
        "avg_mem": avg_mem,
        "max_mem": max_mem,
        "avg_disk": sum(disk_percent) / len(disk_percent),
        "max_disk": max_disk,
        "avg_net_sent": avg_net_sent,
        "max_net_sent": max_net_sent,
        "avg_net_recv": avg_net_recv,
        "max_net_recv": max_net_recv,
    }

    # devolvemos el resumen y las anomalías detectadas
    
    return summary, anomalies
