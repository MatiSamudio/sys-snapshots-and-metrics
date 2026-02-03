import matplotlib.pyplot as plt
import numpy as np
from analyzer import summarize

# obtenemos summary y las listas crudas

summary, cpu_values, mem_percent, disk_percent = summarize()

def write_report_md(path, summary):

    # --- Gráfico comparativo en barras ---
    
    labels = ["CPU", "Memoria", "Disco"]
    avg_values = [
        summary["metrics"]["cpu"]["avg"],
        summary["metrics"]["mem"]["avg"],
        summary["metrics"]["disk"]["avg"]
    ]
    max_values = [
        summary["metrics"]["cpu"]["max"],
        summary["metrics"]["mem"]["max"],
        summary["metrics"]["disk"]["max"]
    ]

    x = np.arange(len(labels))  # posiciones de categorías
    width = 0.35

    fig, ax = plt.subplots()
    rects1 = ax.bar(x - width/2, avg_values, width, label="Promedio")
    rects2 = ax.bar(x + width/2, max_values, width, label="Máximo")

    ax.set_ylabel("Uso (%)")
    ax.set_title("Uso promedio y máximo por recurso")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()

    plt.savefig("resources_usage.png")
    plt.close()

    # --- Escribir el reporte en Markdown ---

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Reporte de monitoreo del sistema\n")
        f.write(f"\nRango de tiempo: {summary['time_range']['start']} a {summary['time_range']['end']}\n")
        f.write(f"\nTotal de snapshots analizados: {summary['count']}\n\n")

        # Tabla de métricas

        f.write("|  Recurso |  Promedio |  Máximo  |\n")
        f.write("|----------|-----------|----------|\n")
        for resource, values in summary['metrics'].items():
            f.write(f"| {resource} | {values['avg']:.2f} | {values['max']} |\n")
        f.write("\n")

        # Anomalías

        f.write("Anomalías relativas detectadas:\n")
        if not summary['anomalies']:
            f.write("- Ninguna anomalía relativa detectada\n")
        else:
            for anomaly in summary['anomalies']:
                f.write(f"- {anomaly['ts']}: {anomaly['reason']}\n")
        f.write("\n")

        f.write("Anomalías extremas detectadas:\n")
        if not summary['extreme_anomalies']:
            f.write("- Ninguna anomalía extrema detectada\n")
        else:
            for extreme in summary['extreme_anomalies']:
                f.write(f"- {extreme['ts']}: {extreme['reason']}\n")

        # Último snapshot

        f.write("\nÚltimo snapshot registrado:\n")
        last = summary['last_snapshot']
        f.write(f"- Timestamp: {last['ts']}\n")
        f.write(f"- CPU: {last['cpu']['percent']}%\n")
        f.write(f"- Memoria: {last['mem']['percent']}% ({last['mem']['used']}/{last['mem']['total']})\n")
        f.write(f"- Disco: {last['disk']['percent']}% ({last['disk']['used']}/{last['disk']['total']}) en {last['disk']['path']}\n")
        f.write(f"- Red: Enviados {last['net']['sent']} bytes, Recibidos {last['net']['recv']} bytes\n\n")

        f.write("Procesos principales:\n")
        for proc in last['top_processes']:
            f.write(f"  - PID {proc['pid']}: {proc['name']} - CPU: {proc['cpu_percent']}%, Memoria RSS: {proc['mem_rss']} bytes\n")
        f.write("\n")

        # Gráficos

        f.write("## Gráfico comparativo de recursos\n")
        f.write("![Uso de recursos](resources_usage.png)\n")

# Generar reporte

write_report_md("reporte.md", summary)

