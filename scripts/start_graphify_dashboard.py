#!/usr/bin/env python3
"""start_graphify_dashboard.py -- one-command local start for the Graphify
Dashboard (G5Q.1). Stdlib only, cross-platform, FOREGROUND.

What it does (and nothing else):
  1. Generates the dashboard views if they are missing (this repo's own
     generators -- fixed argv, no shell).
  2. Starts the loopback-only bridge (scripts/graphify_dashboard_bridge.py)
     in the FOREGROUND of this terminal -- Ctrl+C stops everything; no
     detached windows, no orphan processes (the G5P.0c lesson is policy here).
  3. Prints the dashboard URL and the safety model summary.

It never runs arbitrary commands (one allowlisted pipeline only), never calls
the network, and never stores credentials.

Usage:  python scripts/start_graphify_dashboard.py [--port 8787]
Stop:   Ctrl+C   (stale Graphify rebuilds, if any: python scripts/cleanup_graphify_processes.py)
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
VIEWS = REPO_ROOT / "graphify-out" / "views"
READ_MODEL = REPO_ROOT / "graphify-out" / "hivemind" / "read-model.json"
GRAPH_JSON = REPO_ROOT / "graphify-out" / "graph.json"

# Fresh-clone chain (refute-lane catch: every link must be here, in order):
# graph.json (graphify update .) -> read-model -> 3D + 2D views -> dashboard
VIEW_FILES = ["brain-3d-prototype.html", "graph-explorer.html", "graphify-dashboard.html"]
GENERATORS = [  # order matters: read-model first, dashboard (which hashes views) last
    SCRIPTS / "graphify_hivemind_readmodel.py",
    SCRIPTS / "graphify_brain3d.py",
    SCRIPTS / "graphify_hivemind_explorer.py",
    SCRIPTS / "graphify_dashboard_mock.py",
]


def ensure_views() -> None:
    if all((VIEWS / f).exists() for f in VIEW_FILES) and READ_MODEL.exists():
        return
    if not GRAPH_JSON.exists():
        print("[start] this repo has not been graphed yet (no graphify-out/graph.json).\n"
              "[start] one-time setup:\n"
              "[start]   uv tool install graphifyy   # or: pipx install graphifyy\n"
              "[start]   graphify update .           # graph this repo\n"
              "[start] then re-run this script -- it builds the read-model and all views itself.")
        sys.exit(2)
    print("[start] building read-model + dashboard views (one time)...")
    for gen in GENERATORS:
        if gen.name == "graphify_hivemind_readmodel.py" and READ_MODEL.exists():
            continue   # already built; the view generators consume it as-is
        r = subprocess.run([sys.executable, str(gen)], cwd=str(REPO_ROOT))
        if r.returncode != 0:
            print(f"[start] {gen.name} failed (exit {r.returncode}) -- aborting.")
            sys.exit(r.returncode)


def bridge_already_running(port: int) -> bool:
    """G5P.10: probe before doing anything -- a second start must be a friendly
    no-op, not a generator run followed by the bridge's refusal (exit 2)."""
    try:
        import json as _json
        import urllib.request
        with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/bridge/status", timeout=1.5) as r:
            return _json.loads(r.read() or b"{}").get("bridge") == "graphify-dashboard-bridge"
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args()

    if bridge_already_running(args.port):
        print(f"[start] Graphify Dashboard is ALREADY RUNNING -- nothing to do.\n"
              f"        open:  http://127.0.0.1:{args.port}/views/graphify-dashboard.html\n"
              f"        (stop the running terminal with Ctrl+C first if you want a fresh start)")
        return 0

    ensure_views()
    if not shutil.which("graphify"):
        print("[start] note: graphify CLI not found on PATH -- the dashboard works, "
              "but RUN GRAPHIFY will honestly fail until you `uv tool install graphifyy`.")

    print(f"""
[start] Graphify Dashboard
        open:    http://127.0.0.1:{args.port}/views/graphify-dashboard.html
        safety:  loopback-only bridge; allowlisted pipeline (graphify update ->
                 read-model -> views) in validated paths; one rebuild at a time;
                 cleanup sandboxed to graphify-out/projects/<id>; no credentials;
                 no external calls by default
        stop:    Ctrl+C (this terminal owns the server -- nothing detaches)
""")
    # FOREGROUND on purpose: the bridge dies with this terminal.
    return subprocess.call([sys.executable, str(SCRIPTS / "graphify_dashboard_bridge.py"),
                            "--port", str(args.port)], cwd=str(REPO_ROOT))


if __name__ == "__main__":
    sys.exit(main())
