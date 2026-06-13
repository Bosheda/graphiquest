#!/usr/bin/env python3
"""cleanup_graphify_processes.py -- detect (and optionally kill) stale graphify
post-commit rebuild processes. TRACKED safety checker for the G5P.0c/G5P.0d
process-hygiene work.

WHY: the graphify-installed post-commit hook detaches a full-core rebuild python
per commit. Before the hygiene patch (scripts/install_graphify_hooks_safe.py)
these could stack per commit and -- on Windows, where the template's SIGALRM
timeout is inert -- hang forever. This utility lets any machine VERIFY and
recover without touching unrelated python services.

USAGE:
  python scripts/cleanup_graphify_processes.py            # report only (default)
  python scripts/cleanup_graphify_processes.py --kill-stale
  python scripts/cleanup_graphify_processes.py --max-age 600

SAFETY MODEL (what may ever be killed):
  A process is a graphify rebuild ONLY if its command line matches the strict
  fingerprint below (the hook's embedded `-c` source). ComfyUI, Hermes,
  chat-proxy, dev servers, and arbitrary pythons can never match: their command
  lines do not contain the rebuild source. Kills are tree-kills of fingerprinted
  PIDs only, and only when classified stale:
    - older than --max-age seconds (default 600 = the rebuild watchdog budget), or
    - superseded (more than one concurrent rebuild: all but the newest are stale).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

# Both the uv launcher shim and the real interpreter carry the embedded -c source
# in their command line; either of these substrings is unique to the rebuild.
FINGERPRINTS = (
    "from graphify.watch import _rebuild_code",
    "[graphify hook]",
)


def is_rebuild_cmdline(cmdline: str) -> bool:
    """Strict classifier: True only for the hook's detached rebuild processes."""
    if not cmdline or "python" not in cmdline.lower():
        return False
    return any(fp in cmdline for fp in FINGERPRINTS)


def list_processes() -> list[dict]:
    """Return [{pid, ppid, age_s, cmdline}] for all python processes (stdlib only)."""
    procs: list[dict] = []
    if os.name == "nt":
        ps = (
            "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | "
            "ForEach-Object { @{ pid = $_.ProcessId; ppid = $_.ParentProcessId; "
            "age = [int]((Get-Date) - $_.CreationDate).TotalSeconds; "
            "cmd = [string]$_.CommandLine } } | ConvertTo-Json -Compress"
        )
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True,
        ).stdout.strip()
        if out:
            data = json.loads(out)
            if isinstance(data, dict):
                data = [data]
            for d in data:
                procs.append({"pid": int(d["pid"]), "ppid": int(d["ppid"]),
                              "age_s": int(d["age"]), "cmdline": d.get("cmd") or ""})
    else:
        out = subprocess.run(
            ["ps", "-eo", "pid=,ppid=,etimes=,args="], capture_output=True, text=True
        ).stdout
        for line in out.splitlines():
            parts = line.split(None, 3)
            if len(parts) == 4 and "python" in parts[3].lower():
                procs.append({"pid": int(parts[0]), "ppid": int(parts[1]),
                              "age_s": int(parts[2]), "cmdline": parts[3]})
    return procs


def classify(rebuilds: list[dict], max_age: int) -> tuple[list[dict], list[dict]]:
    """Split fingerprinted rebuilds into (healthy, stale).

    Parent/child shim pairs share a spawn time; treat processes within 5s of the
    NEWEST spawn as one active rebuild generation. Anything older is superseded;
    anything past max_age is hung.
    """
    if not rebuilds:
        return [], []
    newest_age = min(r["age_s"] for r in rebuilds)
    healthy, stale = [], []
    for r in rebuilds:
        if r["age_s"] > max_age:
            r["reason"] = f"older than --max-age {max_age}s (hung; watchdog budget exceeded)"
            stale.append(r)
        elif r["age_s"] > newest_age + 5:
            r["reason"] = "superseded by a newer rebuild (newest-wins)"
            stale.append(r)
        else:
            healthy.append(r)
    return healthy, stale


def tree_kill(pid: int) -> bool:
    if os.name == "nt":
        r = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F", "/FI", "IMAGENAME eq python.exe"],
            capture_output=True, text=True,
        )
        return r.returncode == 0
    try:
        os.kill(pid, 15)
        return True
    except OSError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kill-stale", action="store_true", help="kill processes classified stale (report-only without this)")
    ap.add_argument("--max-age", type=int, default=600, help="seconds before a rebuild counts as hung (default 600)")
    args = ap.parse_args()

    everything = list_processes()
    rebuilds = [p for p in everything if is_rebuild_cmdline(p["cmdline"])]
    others = len(everything) - len(rebuilds)
    healthy, stale = classify(rebuilds, args.max_age)

    print(f"python processes: {len(everything)} total | {others} non-graphify (NEVER touched) | "
          f"{len(rebuilds)} graphify rebuild ({len(healthy)} healthy, {len(stale)} stale)")
    for r in healthy:
        print(f"  HEALTHY pid {r['pid']} age {r['age_s']}s - active rebuild, leave to finish")
    for r in stale:
        print(f"  STALE   pid {r['pid']} age {r['age_s']}s - {r['reason']}")

    if not stale:
        return 0
    if not args.kill_stale:
        print("re-run with --kill-stale to remove the stale rebuilds (tree-kill, python.exe-validated)")
        return 1

    failures = 0
    for r in sorted(stale, key=lambda x: -x["age_s"]):
        ok = tree_kill(r["pid"])
        print(f"  {'killed' if ok else 'KILL FAILED (may have already exited)'}: pid {r['pid']} ({r['reason']})")
        failures += 0 if ok else 1
    time.sleep(0.5)
    leftover = [p for p in list_processes() if is_rebuild_cmdline(p["cmdline"]) and any(p["pid"] == s["pid"] for s in stale)]
    print(f"post-kill check: {len(leftover)} of {len(stale)} stale rebuild processes remain")
    return 0 if not leftover else 1


if __name__ == "__main__":
    sys.exit(main())
