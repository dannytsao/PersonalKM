#!/usr/bin/env python3
"""Manage PersonalKM launchd cron jobs from config/cron_jobs.yaml.

Usage:
  python scripts/manage_cron.py list                  # show all jobs + schedules
  python scripts/manage_cron.py status                # show launchd status (PID, exit, last run)
  python scripts/manage_cron.py deploy                # deploy ALL jobs (generate plist + install + reload)
  python scripts/manage_cron.py deploy --job phase-a-tech   # deploy one job
  python scripts/manage_cron.py run phase-a-tech      # trigger immediate run
  python scripts/manage_cron.py logs phase-a-tech     # tail recent logs

After editing config/cron_jobs.yaml, run `deploy` to apply changes.
The generated plists are written to launchd/ (repo) AND installed to
~/Library/LaunchAgents/, then bootout+bootstrap'd in launchd.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config" / "cron_jobs.yaml"
LAUNCHD_REPO_DIR = REPO_ROOT / "launchd"
LAUNCHD_INSTALLED_DIR = Path.home() / "Library" / "LaunchAgents"
SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "PersonalKM"
LOG_DIR = Path.home() / "Library" / "Logs" / "PersonalKM"
LABEL_PREFIX = "com.dannytsao.personalkm"
UID = os.getuid()


# ─── Config loading ─────────────────────────────────────────────────────

def load_config() -> dict[str, Any]:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def expand(path: str) -> str:
    """Expand ~ and env vars."""
    return os.path.expanduser(os.path.expandvars(path))


def job_label(job_name: str) -> str:
    return f"{LABEL_PREFIX}.{job_name}"


def job_plist_path(job_name: str) -> Path:
    return LAUNCHD_INSTALLED_DIR / f"{job_label(job_name)}.plist"


def vault_path(cfg: dict, job: dict) -> str:
    vault_name = job.get("vault", "tech")
    return expand(cfg["vaults"][vault_name]["path"])


def installed_script_path(job: dict) -> Path:
    return SUPPORT_DIR / job["script"]


# ─── Plist generation ───────────────────────────────────────────────────

def generate_plist(job_name: str, job: dict, cfg: dict) -> str:
    """Generate launchd plist XML for a job."""
    label = job_label(job_name)
    script = installed_script_path(job)
    vault = vault_path(cfg, job)
    repo = expand(cfg["defaults"]["repo_root"])
    python_bin = cfg["defaults"]["python"]
    log_name = job.get("log_name", job_name)

    sched = job.get("schedule", {})
    times = sched.get("times")
    interval = sched.get("interval")

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"',
        '  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">',
        '<plist version="1.0">',
        '<dict>',
        f'  <key>Label</key>',
        f'  <string>{label}</string>',
        '',
        '  <key>ProgramArguments</key>',
        '  <array>',
        f'    <string>{script}</string>',
        '  </array>',
        '',
        '  <key>WorkingDirectory</key>',
        f'  <string>{repo}</string>',
        '',
    ]

    # Schedule
    if times:
        lines.append('  <key>StartCalendarInterval</key>')
        lines.append('  <array>')
        for t in times:
            parts = t.strip().split(":")
            h, m = int(parts[0]), int(parts[1])
            lines.append('    <dict>')
            lines.append('      <key>Hour</key>')
            lines.append(f'      <integer>{h}</integer>')
            lines.append('      <key>Minute</key>')
            lines.append(f'      <integer>{m}</integer>')
            lines.append('    </dict>')
        lines.append('  </array>')
    elif interval:
        lines.append('  <key>StartInterval</key>')
        lines.append(f'  <integer>{interval}</integer>')

    lines.extend([
        '',
        '  <key>StandardOutPath</key>',
        f'  <string>{LOG_DIR}/{log_name}.out.log</string>',
        '',
        '  <key>StandardErrorPath</key>',
        f'  <string>{LOG_DIR}/{log_name}.err.log</string>',
        '',
        '  <key>EnvironmentVariables</key>',
        '  <dict>',
        '    <key>PATH</key>',
        '    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>',
        '    <key>PERSONALKM_REPO_ROOT</key>',
        f'    <string>{repo}</string>',
        '    <key>PERSONALKM_VAULT_ROOT</key>',
        f'    <string>{vault}</string>',
        '    <key>PERSONALKM_PYTHON</key>',
        f'    <string>{python_bin}</string>',
        '  </dict>',
        '</dict>',
        '</plist>',
    ])
    return "\n".join(lines) + "\n"


# ─── Launchd operations ─────────────────────────────────────────────────

def reload_job(job_name: str) -> bool:
    """Bootout + bootstrap a job. Returns True on success."""
    label = job_label(job_name)
    plist = job_plist_path(job_name)

    # Bootout (ignore errors if not loaded)
    subprocess.run(
        ["launchctl", "bootout", f"gui/{UID}/{label}"],
        capture_output=True,
    )
    # Bootstrap
    result = subprocess.run(
        ["launchctl", "bootstrap", f"gui/{UID}", str(plist)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  ❌ Failed to reload {job_name}: {result.stderr.strip()}")
        return False
    return True


def deploy_job(job_name: str, job: dict, cfg: dict, verbose: bool = True) -> bool:
    """Generate plist, copy script, install, and reload a single job."""
    if verbose:
        print(f"📦 Deploying {job_name}...")

    # 1. Generate plist
    plist_content = generate_plist(job_name, job, cfg)

    # 2. Write to repo launchd/ (for version control)
    LAUNCHD_REPO_DIR.mkdir(parents=True, exist_ok=True)
    repo_plist = LAUNCHD_REPO_DIR / f"{job_label(job_name)}.plist"
    repo_plist.write_text(plist_content, encoding="utf-8")

    # 3. Install plist to ~/Library/LaunchAgents/
    LAUNCHD_INSTALLED_DIR.mkdir(parents=True, exist_ok=True)
    installed_plist = job_plist_path(job_name)
    installed_plist.write_text(plist_content, encoding="utf-8")

    # 4. Copy shell script to Application Support/
    repo_script = REPO_ROOT / "scripts" / job["script"]
    installed_script = installed_script_path(job)
    if repo_script.exists():
        installed_script.parent.mkdir(parents=True, exist_ok=True)
        installed_script.write_bytes(repo_script.read_bytes())
        os.chmod(installed_script, 0o755)

    # 5. Reload in launchd
    ok = reload_job(job_name)
    if verbose and ok:
        sched = job.get("schedule", {})
        times = sched.get("times")
        interval = sched.get("interval")
        if times:
            sched_str = ", ".join(times)
        elif interval:
            sched_str = f"every {interval}s"
        else:
            sched_str = "no schedule"
        print(f"  ✅ {job_name}: {sched_str}")
    return ok


# ─── Commands ───────────────────────────────────────────────────────────

def cmd_list(cfg: dict) -> None:
    """List all jobs and their schedules."""
    print(f"{'Job':<25} {'Schedule':<25} {'Vault':<12} {'Script'}")
    print("-" * 85)
    for name, job in cfg["jobs"].items():
        sched = job.get("schedule", {})
        times = sched.get("times")
        interval = sched.get("interval")
        if times:
            sched_str = ", ".join(times)
        elif interval:
            sched_str = f"every {interval}s"
        else:
            sched_str = "—"
        vault = job.get("vault", "tech")
        print(f"{name:<25} {sched_str:<25} {vault:<12} {job['script']}")


def cmd_status(cfg: dict) -> None:
    """Show launchd status for all jobs."""
    # Get launchctl list output
    result = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")

    print(f"{'Job':<25} {'PID':<8} {'Exit':<8} {'Schedule':<25} {'Last Log'}")
    print("-" * 95)
    for name, job in cfg["jobs"].items():
        label = job_label(name)
        # Find in launchctl output
        pid = "-"
        exit_code = "-"
        for line in lines:
            if label in line:
                parts = line.split()
                if len(parts) >= 3:
                    pid = parts[0]
                    exit_code = parts[1]
                break

        sched = job.get("schedule", {})
        times = sched.get("times")
        interval = sched.get("interval")
        if times:
            sched_str = ", ".join(times)
        elif interval:
            sched_str = f"every {interval}s"
        else:
            sched_str = "—"

        # Last log line
        log_name = job.get("log_name", name)
        log_path = LOG_DIR / f"{log_name}.out.log"
        last_log = ""
        if log_path.exists():
            try:
                last_log = log_path.read_text(encoding="utf-8", errors="replace").strip().split("\n")[-1][:30]
            except Exception:
                pass

        print(f"{name:<25} {pid:<8} {exit_code:<8} {sched_str:<25} {last_log}")


def cmd_deploy(cfg: dict, job_name: str | None) -> None:
    """Deploy one or all jobs."""
    if job_name:
        if job_name not in cfg["jobs"]:
            print(f"❌ Unknown job: {job_name}")
            print(f"   Available: {', '.join(cfg['jobs'].keys())}")
            sys.exit(1)
        deploy_job(job_name, cfg["jobs"][job_name], cfg)
    else:
        ok_count = 0
        for name, job in cfg["jobs"].items():
            if deploy_job(name, job, cfg):
                ok_count += 1
        print(f"\n✅ Deployed {ok_count}/{len(cfg['jobs'])} jobs.")


def cmd_run(cfg: dict, job_name: str) -> None:
    """Trigger an immediate run of a job."""
    if job_name not in cfg["jobs"]:
        print(f"❌ Unknown job: {job_name}")
        sys.exit(1)
    label = job_label(job_name)
    print(f"🚀 Triggering {job_name}...")
    result = subprocess.run(
        ["launchctl", "start", label],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"  ✅ Triggered. Check logs: python scripts/manage_cron.py logs {job_name}")
    else:
        print(f"  ❌ Failed: {result.stderr.strip()}")


def cmd_logs(cfg: dict, job_name: str, lines: int = 20) -> None:
    """Tail recent logs for a job."""
    if job_name not in cfg["jobs"]:
        print(f"❌ Unknown job: {job_name}")
        sys.exit(1)
    job = cfg["jobs"][job_name]
    log_name = job.get("log_name", job_name)
    log_path = LOG_DIR / f"{log_name}.out.log"
    if not log_path.exists():
        print(f"No log file: {log_path}")
        return
    content = log_path.read_text(encoding="utf-8", errors="replace")
    all_lines = content.strip().split("\n")
    for line in all_lines[-lines:]:
        print(line)


# ─── Main ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage PersonalKM launchd cron jobs from YAML.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all jobs and schedules")
    sub.add_parser("status", help="Show launchd status for all jobs")

    p_deploy = sub.add_parser("deploy", help="Generate plists + install + reload")
    p_deploy.add_argument("--job", "-j", help="Deploy only this job (default: all)")

    p_run = sub.add_parser("run", help="Trigger immediate run")
    p_run.add_argument("job", help="Job name")

    p_logs = sub.add_parser("logs", help="Show recent log output")
    p_logs.add_argument("job", help="Job name")
    p_logs.add_argument("-n", "--lines", type=int, default=20, help="Number of lines")

    args = parser.parse_args()
    cfg = load_config()

    if args.command == "list":
        cmd_list(cfg)
    elif args.command == "status":
        cmd_status(cfg)
    elif args.command == "deploy":
        cmd_deploy(cfg, args.job)
    elif args.command == "run":
        cmd_run(cfg, args.job)
    elif args.command == "logs":
        cmd_logs(cfg, args.job, args.lines)


if __name__ == "__main__":
    main()