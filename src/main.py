"""
Main entry point and CLI orchestrator for sys-snapshots-and-metrics.

This module provides:
- Automatic mode: Double-click execution that captures metrics and generates reports
- CLI mode: Manual control over database initialization, metric collection, and reporting
- Path resolution: Manages database and report file locations
- Logging configuration: Sets up application-wide logging

The module coordinates between collector, storage, runner, analyzer, and report modules
to provide a complete system metrics monitoring solution.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone
import sys
import os

from src.config import CFG
from src import storage
from src import runner
from src import analyzer
from src import report


# =========================================================
# Logging Configuration
# =========================================================
def setup_logging(verbose: bool) -> None:
    """
    Configure application-wide logging.

    Args:
        verbose: If True, enables DEBUG level logging; otherwise INFO level.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
    )


# =========================================================
# Path Resolution (main module controls all paths)
# =========================================================
def resolve_db_path(cli_db: str | None) -> str:
    """
    Resolve the database file path from CLI argument or configuration.

    Args:
        cli_db: Database path from command-line argument, or None to use config default.

    Returns:
        Resolved database file path as string.
    """
    return str(cli_db or CFG.get("db_path", "snapshots.db"))


def ensure_reports_dir() -> Path:
    """
    Ensure the reports directory exists, creating it if necessary.

    Returns:
        Path object pointing to the reports directory.
    """
    reports_cfg = CFG.get("reports", {}) if isinstance(CFG, dict) else {}
    d = Path(reports_cfg.get("dir", "reports"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve_report_path(cli_out: str | None) -> Path:
    """
    Resolve the output report file path.

    If a CLI output path is provided, it takes precedence. Otherwise, uses
    configuration settings to determine the path, optionally adding a timestamp.

    Args:
        cli_out: Output path from command-line argument, or None to use config.

    Returns:
        Resolved Path object for the report file.
    """
    # If user provides --out, respect it exactly
    if cli_out:
        out = Path(cli_out)
        # Ensure parent directory exists if specified
        if out.parent and str(out.parent) not in (".", ""):
            out.parent.mkdir(parents=True, exist_ok=True)
        return out

    reports_cfg = CFG.get("reports", {}) if isinstance(CFG, dict) else {}
    reports_dir = ensure_reports_dir()

    base = reports_cfg.get("default_name", "report.md")
    timestamped = bool(reports_cfg.get("timestamped", False))

    if not timestamped:
        return reports_dir / base

    # Generate timestamped filename
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return reports_dir / f"report-{ts}.md"


# =========================================================
# Automatic Execution Mode
# =========================================================
def run_auto() -> int:
    """
    Execute automatic mode (triggered by double-click or no arguments).

    This mode provides a complete, self-contained workflow:
    1. Resets snapshots.db to avoid mixing data from different runs
    2. Initializes a fresh database
    3. Captures metrics for approximately 20 seconds
    4. Generates Markdown and HTML reports with charts
    5. Opens the HTML report in the default browser

    All files are created in the executable's directory (portable mode).

    Returns:
        Exit code (0 for success).
    """
    # Determine base directory: executable folder if frozen, otherwise project root
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

    # Step 0: Reset database on each autorun to avoid noise between runs/machines
    try:
        if db_path.exists():
            db_path.unlink()
    except Exception:
        # If file is locked, continue with existing database
        pass

    # Step 1: Initialize database (idempotent operation)
    storage.init_db(str(db_path))

    # Step 2: Run metric collection
    runner.run(
        interval=2,
        duration=20,
        cfg=CFG,
        db_path=str(db_path),
    )

    # Step 3: Generate reports (Markdown + HTML)
    snapshots = storage.get_snapshots(str(db_path), last_lines=50)
    analysis = analyzer.analyze(snapshots, CFG)

    report.write_report(analysis, str(report_path))
    report.write_report_html(str(report_path), str(html_path))

    # Step 4: Open HTML report in default browser
    try:
        os.startfile(str(html_path))
    except Exception:
        pass

    return 0


# =========================================================
# CLI Parser
# =========================================================
def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line argument parser.

    Supports three subcommands:
    - init-db: Initialize the SQLite database
    - run: Execute metric collection loop
    - report: Generate report from stored snapshots

    Returns:
        Configured ArgumentParser instance.
    """
    p = argparse.ArgumentParser(prog="sys-snapshots-and-metrics")
    p.add_argument("--verbose", action="store_true", help="Enable debug logging")

    sub = p.add_subparsers(dest="cmd", required=True)

    # init-db subcommand
    pi = sub.add_parser("init-db", help="Initialize SQLite database")
    pi.add_argument("--db", type=str, default=None)

    # run subcommand
    pr = sub.add_parser("run", help="Run automated snapshots loop")
    pr.add_argument("--interval", type=int, default=1)
    pr.add_argument("--duration", type=int, default=10)  # 0 => infinite (Ctrl+C to stop)
    pr.add_argument("--db", type=str, default=None)

    # report subcommand
    prep = sub.add_parser("report", help="Generate Markdown report from last N snapshots")
    prep.add_argument("--last", type=int, default=20)
    prep.add_argument("--db", type=str, default=None)
    prep.add_argument("--out", type=str, default=None)

    return p


# =========================================================
# Command Implementations
# =========================================================
def cmd_init_db(db_path: str) -> int:
    """
    Initialize the SQLite database.

    Args:
        db_path: Path to the database file.

    Returns:
        Exit code (0 for success).
    """
    storage.init_db(db_path)
    print({"db_path": db_path, "status": "initialized"})
    return 0


def cmd_run(db_path: str, interval: int, duration: int) -> int:
    """
    Execute the metric collection loop.

    Args:
        db_path: Path to the database file.
        interval: Seconds between snapshots.
        duration: Total duration in seconds (0 for infinite).

    Returns:
        Exit code (0 for success).
    """
    # Ensure database is ready (idempotent operation)
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
    """
    Generate a report from stored snapshots.

    Args:
        db_path: Path to the database file.
        last_n: Number of most recent snapshots to include.
        out_path: Output file path for the report.

    Returns:
        Exit code (0 for success).
    """
    # Ensure database exists (creates empty if missing)
    storage.init_db(db_path)

    snapshots = storage.get_snapshots(db_path, last_n)
    analysis = analyzer.analyze(snapshots, CFG)

    # Write Markdown report
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
# Main Entry Point
# =========================================================
def main(argv: list[str] | None = None) -> int:
    """
    Main entry point for the application.

    Supports two modes:
    - Automatic mode: Executed when no arguments are provided (double-click)
    - CLI mode: Executed with subcommands (init-db, run, report)

    Args:
        argv: Command-line arguments, or None to use sys.argv.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """

    # If executed without arguments (double-click), run automatic mode
    # Note: main(argv=[]) is not considered a double-click
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
