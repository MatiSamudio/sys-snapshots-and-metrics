from storage import get_snapshots

# simulamos lo que devolvería get_snapshots()

# def get_snapshots():
#     return [
#         # id, ts, hostname, os_name, os_release,
#         # cpu_percent, mem_total, mem_used, mem_percent,
#         # disk_path, disk_total, disk_used, disk_percent,
#         # net_sent, net_recv, net_sent_delta, net_recv_delta,
#         # pid, name, proc_cpu, proc_mem_used

#         (1, "2026-02-03 18:30:00", "server1", "Linux", "5.15",
#          45.0, 16000, 8000, 50.0,
#          "/", 100000, 50000, 50.0,
#          1000000, 2000000, 200000, 400000,
#          101, "nginx", 5.0, 120000),

#         (1, "2026-02-03 18:30:00", "server1", "Linux", "5.15",
#          45.0, 16000, 8000, 50.0,
#          "/", 100000, 50000, 50.0,
#          1000000, 2000000, 200000, 400000,
#          102, "postgres", 10.0, 250000),

#         (2, "2026-02-03 18:35:00", "server1", "Linux", "5.15",
#          70.0, 16000, 12000, 75.0,
#          "/", 100000, 80000, 80.0,
#          2000000, 3000000, 300000, 500000,
#          103, "python", 20.0, 500000),

#         (2, "2026-02-03 18:35:00", "server1", "Linux", "5.15",
#          70.0, 16000, 12000, 75.0,
#          "/", 100000, 80000, 80.0,
#          2000000, 3000000, 300000, 500000,
#          104, "redis", 15.0, 150000),
#     ]

def summarize():
    rows = get_snapshots()

    if rows is None or len(rows) == 0:
        return "El snapshot está vacío"

    # Umbrales de uso para anomalías extremas

    threshold_cpu = 89.9
    threshold_mem = 89.9
    threshold_disk = 95.0
    threshold_net = 960000000

    # Reconstruimos snapshots agrupando por id

    snapshots = {}
    for row in rows:
        (
            id, ts, hostname, os_name, os_release,
            cpu_percent, mem_total, mem_used, mem_percent,
            disk_path, disk_total, disk_used, disk_percent,
            net_sent, net_recv, net_sent_delta, net_recv_delta,
            pid, name, proc_cpu, proc_mem_used
        ) = row

        if id not in snapshots:
            snapshots[id] = {
                "id": id,
                "ts": ts,
                "hostname": hostname,
                "os_name": os_name,
                "os_release": os_release,
                "cpu": {"percent": cpu_percent},
                "mem": {"total": mem_total, "used": mem_used, "percent": mem_percent},
                "disk": {"path": disk_path, "total": disk_total, "used": disk_used, "percent": disk_percent},
                "net": {"sent": net_sent, "recv": net_recv, "sent_delta": net_sent_delta, "recv_delta": net_recv_delta},
                "top_processes": []
            }

        snapshots[id]["top_processes"].append({
            "pid": pid,
            "name": name,
            "cpu_percent": proc_cpu,
            "mem_rss": proc_mem_used
        })

    # Convertimos a lista ordenada por timestamp

    snapshots = sorted(snapshots.values(), key=lambda s: s["ts"])

    # Inicializamos acumuladores

    cpu_values = [s["cpu"]["percent"] for s in snapshots]
    mem_percent = [s["mem"]["percent"] for s in snapshots]
    disk_percent = [s["disk"]["percent"] for s in snapshots]
    net_sent = [s["net"]["sent"] for s in snapshots]
    net_recv = [s["net"]["recv"] for s in snapshots]

    anomalies = []
    extreme_anomalies = []

    # Calculamos promedios y máximos

    avg_cpu = sum(cpu_values) / len(cpu_values)
    max_cpu = max(cpu_values)

    avg_mem = sum(mem_percent) / len(mem_percent)
    max_mem = max(mem_percent)

    avg_disk = sum(disk_percent) / len(disk_percent)
    max_disk = max(disk_percent)

    avg_net_sent = sum(net_sent) / len(net_sent)
    max_net_sent = max(net_sent)

    avg_net_recv = sum(net_recv) / len(net_recv)
    max_net_recv = max(net_recv)

    # Detectamos anomalías en el último snapshot

    last = snapshots[-1]

    if last["cpu"]["percent"] > threshold_cpu:
        extreme_anomalies.append({"ts": last["ts"], "reason": "Uso de CPU muy alto"})
    elif last["cpu"]["percent"] > avg_cpu + 15:
        anomalies.append({"ts": last["ts"], "reason": "Uso de CPU por encima del 15% promedio"})
    elif avg_cpu + 5 < last["cpu"]["percent"] <= avg_cpu + 10:
        anomalies.append({"ts": last["ts"], "reason": "Uso de CPU por encima del 5% promedio"})

    if last["mem"]["percent"] > threshold_mem:
        extreme_anomalies.append({"ts": last["ts"], "reason": "Uso de memoria muy alto"})
    elif last["mem"]["percent"] > avg_mem + 15:
        anomalies.append({"ts": last["ts"], "reason": "Uso de memoria por encima del 15% promedio"})
    elif avg_mem + 5 < last["mem"]["percent"] <= avg_mem + 10:
        anomalies.append({"ts": last["ts"], "reason": "Uso de memoria por encima del 5% promedio"})

    if last["disk"]["percent"] > threshold_disk:
        extreme_anomalies.append({"ts": last["ts"], "reason": "Uso de disco muy alto"})

    if last["net"]["sent"] > threshold_net or last["net"]["recv"] > threshold_net:
        extreme_anomalies.append({"ts": last["ts"], "reason": "Uso de red muy alto"})

    # Creamos el resumen

    summary = {
        "time_range": {"start": snapshots[0]["ts"], "end": snapshots[-1]["ts"]},
        "count": len(snapshots),
        "metrics": {
            "cpu": {"avg": avg_cpu, "max": max_cpu},
            "mem": {"avg": avg_mem, "max": max_mem},
            "disk": {"avg": avg_disk, "max": max_disk},
            "net_sent": {"avg": avg_net_sent, "max": max_net_sent},
            "net_recv": {"avg": avg_net_recv, "max": max_net_recv}
        },
        "anomalies": anomalies,
        "extreme_anomalies": extreme_anomalies,
        "last_snapshot": last
    }

    return summary, cpu_values, mem_percent, disk_percent
