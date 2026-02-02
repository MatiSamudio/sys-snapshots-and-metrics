function summarize(snapshots: list[dict]) -> dict:
    if snapshots está vacío:
        return summary vacío con valores None o listas vacías

    inicializar acumuladores:
        cpu_values = []
        ram_values = []
        disk_values = []
        anomalies = []

    para cada snapshot en snapshots:
        extraer cpu_percent, mem_percent, disk_percent
        agregar a listas cpu_values, ram_values, disk_values

        # detectar anomalías
        if cpu_percent > threshold_cpu:
            anomalies.append({ "ts": snapshot["ts"], "reason": "High CPU" })
        if mem_percent > threshold_mem:
            anomalies.append({ "ts": snapshot["ts"], "reason": "High Memory" })
        if disk_percent > threshold_disk:
            anomalies.append({ "ts": snapshot["ts"], "reason": "High Disk" })

    calcular métricas:
        avg_cpu = promedio(cpu_values)
        max_cpu = máximo(cpu_values)
        avg_mem = promedio(ram_values)
        max_mem = máximo(ram_values)
        max_disk = máximo(disk_values)

    construir summary dict:
        summary = {
            "time_range": (primer_ts, último_ts),
            "count": cantidad de snapshots,
            "metrics": {
                "cpu": {"avg": avg_cpu, "max": max_cpu},
                "mem": {"avg": avg_mem, "max": max_mem},
                "disk": {"max": max_disk}
            },
            "anomalies": anomalies,
            "last_snapshot": último snapshot completo
        }

    return summary


function diff(prev: dict, curr: dict) -> dict:
    if prev o curr es None:
        return {}

    calcular diferencias campo por campo:
        cpu_diff = curr["cpu"]["percent"] - prev["cpu"]["percent"]
        mem_diff = curr["mem"]["percent"] - prev["mem"]["percent"]
        disk_diff = curr["disk"]["percent"] - prev["disk"]["percent"]

    return {
        "cpu_diff": cpu_diff,
        "mem_diff": mem_diff,
        "disk_diff": disk_diff
    }
