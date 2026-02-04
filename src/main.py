# src/main.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone
import sys
import os
from pathlib import Path

from src.config import CFG
from src import storage
from src import runner
from src import analyzer
from src import report



# =========================================================
# Logging
# =========================================================
def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
    )


# =========================================================
# Paths (solo main decide)
# =========================================================
def resolve_db_path(cli_db: str | None) -> str:
    return str(cli_db or CFG.get("db_path", "snapshots.db"))


def ensure_reports_dir() -> Path:
    reports_cfg = CFG.get("reports", {}) if isinstance(CFG, dict) else {}
    d = Path(reports_cfg.get("dir", "reports"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve_report_path(cli_out: str | None) -> Path:
    # Si el usuario da --out, se respeta literal
    if cli_out:
        out = Path(cli_out)
        # si incluye carpeta, aseguramos que exista
        if out.parent and str(out.parent) not in (".", ""):
            out.parent.mkdir(parents=True, exist_ok=True)
        return out

    reports_cfg = CFG.get("reports", {}) if isinstance(CFG, dict) else {}
    reports_dir = ensure_reports_dir()

    base = reports_cfg.get("default_name", "report.md")
    timestamped = bool(reports_cfg.get("timestamped", False))

    if not timestamped:
        return reports_dir / base

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    # si base ya termina en .md, lo reemplazamos por report-TS.md
    return reports_dir / f"report-{ts}.md"


# =========================================================
# Auto Run 
# =========================================================
def run_auto() -> int:
    """
    Autorun (doble click / sin args):
    - Resetea snapshots.db (para no mezclar corridas)
    - init-db
    - run (captura)
    - report.md + report.html (+ PNG si aplica)
    - abre report.html en el navegador
    Todo dentro de la carpeta del .exe (portable).
    """
    # Base: carpeta del .exe si está empaquetado; si no, raíz del repo
    base_dir = (
        Path(sys.executable).resolve().parent
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parent.parent
    )

    db_path = base_dir / "snapshots.db"
    reports_dir = base_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_path = reports_dir / "report.md"
    html_path = reports_dir / "report.html"

    # 0) Reset DB en cada autorun (evita ruido entre corridas/máquinas)
    try:
        if db_path.exists():
            db_path.unlink()
    except Exception:
        # Si está bloqueado, no detenemos el autorun (reusará la DB existente)
        pass

    # 1) init db (idempotente)
    storage.init_db(str(db_path))

    # 2) run captura
    runner.run(
        interval=2,
        duration=20,
        cfg=CFG,
        db_path=str(db_path),
    )

    # 3) report (MD + HTML)
    snapshots = storage.get_snapshots(str(db_path), last_lines=50)
    analysis = analyzer.analyze(snapshots, CFG)

    report.write_report(analysis, str(report_path))
    report.write_report_html(str(report_path), str(html_path))

    # 4) abrir en navegador
    try:
        os.startfile(str(html_path))
    except Exception:
        pass

    return 0


# =========================================================
# CLI
# =========================================================
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sys-snapshots-and-metrics")
    p.add_argument("--verbose", action="store_true", help="Enable debug logging")

    sub = p.add_subparsers(dest="cmd", required=True)

    # init-db
    pi = sub.add_parser("init-db", help="Initialize SQLite database")
    pi.add_argument("--db", type=str, default=None)

    # run
    pr = sub.add_parser("run", help="Run automated snapshots loop")
    pr.add_argument("--interval", type=int, default=1)
    pr.add_argument("--duration", type=int, default=10)  # 0 => Ctrl+C
    pr.add_argument("--db", type=str, default=None)

    # report
    prep = sub.add_parser("report", help="Generate Markdown report from last N snapshots")
    prep.add_argument("--last", type=int, default=20)
    prep.add_argument("--db", type=str, default=None)
    prep.add_argument("--out", type=str, default=None)

    return p


# =========================================================
# Commands
# =========================================================
def cmd_init_db(db_path: str) -> int:
    storage.init_db(db_path)
    print({"db_path": db_path, "status": "initialized"})
    return 0


def cmd_run(db_path: str, interval: int, duration: int) -> int:
    # Asegurar DB lista (idempotente)
    storage.init_db(db_path)

    summary = runner.run(
        interval=interval,
        duration=duration,
        cfg=CFG,
        db_path=db_path,
    )
    print(summary)
    return 0


def cmd_report(db_path: str, last_n: int, out_path: Path) -> int:
    # Asegurar DB lista (si no existe, queda vacía)
    storage.init_db(db_path)

    snapshots = storage.get_snapshots(db_path, last_n)
    analysis = analyzer.analyze(snapshots, CFG)

    # report debe escribir markdown
    report.write_report(analysis, str(out_path))

    print(
        {
            "db_path": db_path,
            "snapshots_used": len(snapshots),
            "report_path": str(out_path),
        }
    )
    return 0


# =========================================================
# Entry
# =========================================================
def main(argv: list[str] | None = None) -> int:
    import sys

    # Si se ejecuta sin argumentos (doble click), correr modo automático.
    # Nota: si el usuario llama main(argv=[]), eso no se considera doble click.
    if argv is None and len(sys.argv) == 1:
        return run_auto()

    parser = build_parser()
    args = parser.parse_args(argv)

    setup_logging(args.verbose)

    db_path = resolve_db_path(getattr(args, "db", None))

    if args.cmd == "init-db":
        return cmd_init_db(db_path)

    if args.cmd == "run":
        return cmd_run(db_path, args.interval, args.duration)

    if args.cmd == "report":
        out_path = resolve_report_path(args.out)
        return cmd_report(db_path, args.last, out_path)

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
