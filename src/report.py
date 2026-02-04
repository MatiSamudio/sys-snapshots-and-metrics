# src/report.py
# -*- coding: utf-8 -*-
"""
report.py — Reporte

Contrato:
- NO ejecuta nada al import.
- NO lee DB.
- write_report(analysis, out_path): escribe Markdown
- write_report_html(md_path, html_path): convierte MD a HTML y lo escribe
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def write_report(analysis: dict, out_path: str) -> None:
    out = Path(out_path)

    chart_name = _maybe_write_chart_png(analysis or {}, out)
    md = _render_markdown(analysis or {}, chart_name)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")


def write_report_html(md_path: str, html_path: str) -> None:
    """
    Convierte un .md existente a HTML y lo guarda.
    Requiere: pip install markdown
    """
    md_file = Path(md_path)
    html_file = Path(html_path)

    text = md_file.read_text(encoding="utf-8")

    # Render real de Markdown
    import markdown as md
    body = md.markdown(
        text,
        extensions=["tables", "fenced_code"],
        output_format="html5",
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>System snapshots report</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 24px; }}
  code, pre {{ font-family: Consolas, monospace; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
  th {{ background: #f5f5f5; }}
</style>
</head>
<body>
{body}
</body>
</html>"""

    html_file.parent.mkdir(parents=True, exist_ok=True)
    html_file.write_text(html, encoding="utf-8")


def _maybe_write_chart_png(analysis: dict, out: Path) -> str | None:
    count = int(analysis.get("count", 0) or 0)
    if count <= 0:
        return None

    metrics = analysis.get("metrics") or {}
    cpu = metrics.get("cpu_percent") or {}
    mem = metrics.get("mem_percent") or {}
    disk = metrics.get("disk_percent") or {}

    if cpu.get("avg") is None or cpu.get("max") is None:
        return None
    if mem.get("avg") is None or mem.get("max") is None:
        return None
    if disk.get("avg") is None or disk.get("max") is None:
        return None

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = ["CPU", "Memory", "Disk"]
    avg_values = [float(cpu["avg"]), float(mem["avg"]), float(disk["avg"])]
    max_values = [float(cpu["max"]), float(mem["max"]), float(disk["max"])]

    png_path = out.with_suffix("")  # report.md -> report
    png_file = f"{png_path.name}_resources.png"
    png_full = out.parent / png_file

    x = [0, 1, 2]
    width = 0.35

    fig, ax = plt.subplots()
    ax.bar([i - width / 2 for i in x], avg_values, width, label="Average")
    ax.bar([i + width / 2 for i in x], max_values, width, label="Max")

    ax.set_ylabel("Usage (%)")
    ax.set_title("Average vs Max resource usage")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()

    fig.tight_layout()
    fig.savefig(png_full)
    plt.close(fig)

    return png_file


def _render_markdown(analysis: dict, chart_name: str | None) -> str:
    tr = analysis.get("time_range") or {}
    count = int(analysis.get("count", 0) or 0)

    metrics = analysis.get("metrics") or {}
    cpu = metrics.get("cpu_percent") or {}
    mem = metrics.get("mem_percent") or {}
    disk = metrics.get("disk_percent") or {}

    disk_last = analysis.get("disk") or {}
    net = analysis.get("net") or {}
    anomalies = analysis.get("anomalies") or []
    last = analysis.get("last_snapshot")

    lines: list[str] = []
    lines.append("# System snapshots report")
    lines.append("")
    # ASCII estable
    lines.append(f"- Time range: `{tr.get('start')}` -> `{tr.get('end')}`")
    lines.append(f"- Snapshots analyzed: **{count}**")
    lines.append("")

    lines.append("## Metrics summary")
    lines.append("")
    lines.append("| Metric | Min | Avg | Max |")
    lines.append("|---|---:|---:|---:|")
    lines.append(f"| CPU (%) | {fmt_num(cpu.get('min'))} | {fmt_num(cpu.get('avg'))} | {fmt_num(cpu.get('max'))} |")
    lines.append(f"| MEM (%) | {fmt_num(mem.get('min'))} | {fmt_num(mem.get('avg'))} | {fmt_num(mem.get('max'))} |")
    lines.append(f"| DISK (%) | {fmt_num(disk.get('min'))} | {fmt_num(disk.get('avg'))} | {fmt_num(disk.get('max'))} |")
    lines.append("")

    lines.append("## Disk (last snapshot)")
    lines.append("")
    lines.append(f"- Path: `{disk_last.get('path')}`")
    lines.append(f"- Used: **{fmt_num(disk_last.get('last_percent'))}%**")
    lines.append("")

    lines.append("## Network totals (from deltas)")
    lines.append("")
    lines.append(f"- Sent total: **{fmt_bytes(net.get('sent_total', 0))}**")
    lines.append(f"- Recv total: **{fmt_bytes(net.get('recv_total', 0))}**")
    lines.append(f"- Deltas ignored (None): **{int(net.get('deltas_ignored', 0) or 0)}**")
    lines.append("")

    lines.append("## Anomalies")
    lines.append("")
    if not anomalies:
        lines.append("- None")
    else:
        for a in anomalies:
            ts = a.get("ts")
            reasons = ", ".join(a.get("reasons") or [])
            cpu_p = fmt_num(a.get("cpu_percent"))
            mem_p = fmt_num(a.get("mem_percent"))
            ds = a.get("net_sent_delta")
            dr = a.get("net_recv_delta")
            lines.append(
                f"- `{ts}` - {reasons} "
                f"(cpu={cpu_p}%, mem={mem_p}%, "
                f"sent_delta={fmt_bytes(ds) if ds is not None else 'None'}, "
                f"recv_delta={fmt_bytes(dr) if dr is not None else 'None'})"
            )
    lines.append("")

    if chart_name:
        lines.append("## Resource chart")
        lines.append("")
        lines.append(f"![Average vs Max usage]({chart_name})")
        lines.append("")

    lines.append("## Last snapshot (raw)")
    lines.append("")
    if not last:
        lines.append("- None")
        lines.append("")
        return "\n".join(lines)

    cpu_last = (last.get("cpu") or {}).get("percent")
    mem_last = last.get("mem") or {}
    disk_last_raw = last.get("disk") or {}
    net_last = last.get("net") or {}
    os_info = last.get("os") or {}

    lines.append(f"- ts: `{last.get('ts')}`")
    lines.append(f"- hostname: `{last.get('hostname')}`")
    lines.append(f"- os: `{os_info.get('name')} {os_info.get('release')}`")
    lines.append(f"- cpu: **{fmt_num(cpu_last)}%**")
    lines.append(
        f"- mem: **{fmt_num(mem_last.get('percent'))}%** "
        f"({fmt_bytes(mem_last.get('used'))} / {fmt_bytes(mem_last.get('total'))})"
    )
    lines.append(
        f"- disk: **{fmt_num(disk_last_raw.get('percent'))}%** "
        f"({fmt_bytes(disk_last_raw.get('used'))} / {fmt_bytes(disk_last_raw.get('total'))}) at `{disk_last_raw.get('path')}`"
    )
    lines.append(
        f"- net: sent={fmt_bytes(net_last.get('sent'))}, recv={fmt_bytes(net_last.get('recv'))}, "
        f"sent_delta={fmt_bytes(net_last.get('sent_delta')) if net_last.get('sent_delta') is not None else 'None'}, "
        f"recv_delta={fmt_bytes(net_last.get('recv_delta')) if net_last.get('recv_delta') is not None else 'None'}"
    )
    lines.append("")

    lines.append("### Top processes (last snapshot)")
    lines.append("")
    procs = last.get("top_processes") or []
    if not procs:
        lines.append("- None")
    else:
        lines.append("| PID | Name | CPU (%) | RSS |")
        lines.append("|---:|---|---:|---:|")
        for p in procs:
            lines.append(
                f"| {int_or(p.get('pid'))} | {safe(p.get('name'))} | {fmt_num(p.get('cpu_percent'))} | {fmt_bytes(p.get('mem_rss'))} |"
            )
    lines.append("")

    return "\n".join(lines)


def fmt_num(x: Any) -> str:
    if x is None:
        return "-"
    try:
        return f"{float(x):.2f}"
    except Exception:
        return "-"


def fmt_bytes(x: Any) -> str:
    if x is None:
        return "-"
    try:
        n = int(x)
    except Exception:
        return "-"
    if n < 0:
        n = 0
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    v = float(n)
    i = 0
    while v >= 1024.0 and i < len(units) - 1:
        v /= 1024.0
        i += 1
    if i == 0:
        return f"{int(v)} {units[i]}"
    return f"{v:.2f} {units[i]}"


def int_or(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def safe(x: Any) -> str:
    if x is None:
        return "unknown"
    s = str(x)
    return s.replace("\n", " ").strip() or "unknown"
