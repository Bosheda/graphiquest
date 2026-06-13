#!/usr/bin/env python3
"""graphify_dashboard_bridge.py -- loopback-only local bridge for the Graphify
Dashboard (G5P.3). Serves the generated views AND a hard-allowlisted Graphify
generate/rebuild API. This is NOT a shell runner.

SECURITY MODEL (the whole point):
  - binds 127.0.0.1 only; every request additionally checks the client address
    is loopback (no LAN exposure, no remote access).
  - ONE operation exists: run `graphify update .` in a validated directory.
    The argv is FIXED ([<graphify>, "update", "."]); the browser supplies only
    a project id and a repo path, and the path is data (used as cwd after
    validation), never command text. No shell is involved (list argv).
  - path validation: must be absolute, exist, be a directory, and not be a
    filesystem/system root (drive roots, Windows/system dirs, bare home).
  - one rebuild at a time (global lock -> HTTP 409), watchdog timeout
    (GRAPHIFY_REBUILD_TIMEOUT, default 600s) tree-kills a hung run.
  - success is PROOF-based: exit 0 AND <repo>/graphify-out/graph.json exists
    AND the view pipeline completes. No proof -> error, never a fake ready.
    (Freshness is intentionally not required: `graphify update` legitimately
    no-ops when nothing changed -- an existing graph is a valid current graph.)
  - log tail kept in memory (8 KB cap) + appended to
    ~/.cache/graphify-dashboard-bridge.log. No secrets handled anywhere.

Run:  python scripts/graphify_dashboard_bridge.py [--port 8787]
Then open http://127.0.0.1:8787/views/graphify-dashboard.html
(The dashboard feature-detects this bridge; without it, RUN GRAPHIFY falls
back to an honest manual command pack.)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BRIDGE_NAME = "graphify-dashboard-bridge"
BRIDGE_VERSION = "g5q1s-1"
# Bumping this invalidates every existing manifest (scan -> rebuild_required).
# Bump whenever the emitted-view contract changes (e.g. the G5P.4a absolute-asset
# fix would have been caught by exactly this).
GENERATOR_CONTRACT = "g5p5-abs-assets-1"
STATIC_ROOT = Path(__file__).resolve().parents[1] / "graphify-out"
# G5Q.1c: required design assets are TRACKED here (graphify-out/ stays gitignored).
# On startup they seed graphify-out/design/ so the served /design/ + ../design/
# paths resolve on a fresh clone. Never overwrites an existing file (preserves
# a live operator's freshly-generated art).
TRACKED_ASSETS = Path(__file__).resolve().parents[1] / "graphify_assets" / "design"
LOG_FILE = Path(os.path.expanduser("~")) / ".cache" / "graphify-dashboard-bridge.log"
TAIL_CAP = 8192
LOOPBACK = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}

# Windows + unix system roots that must never be scan targets. Comparison is on
# resolved, case-normalized paths.
_ENV_DIRS = [os.environ.get(k) for k in ("WINDIR", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMDATA")]
DANGEROUS_PATHS = [p for p in _ENV_DIRS if p] + ["/", "/etc", "/usr", "/bin", "/var", "/boot", os.path.expanduser("~")]


def _norm(p: str) -> str:
    return os.path.normcase(os.path.normpath(str(p)))


def graphify_exe() -> str | None:
    """Resolve the graphify launcher honestly -- None when not installed."""
    return shutil.which("graphify")


_GFY_VER: dict = {}


def graphify_version() -> str | None:
    """Best-effort `graphify --version`, cached per process."""
    if "v" not in _GFY_VER:
        try:
            exe = graphify_exe()
            r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=15) if exe else None
            _GFY_VER["v"] = (r.stdout or "").strip() or None if r else None
        except Exception:
            _GFY_VER["v"] = None
    return _GFY_VER["v"]


DASHBOARD_ROOT = STATIC_ROOT.parent     # the repo this dashboard is generated from


def resolve_repo_path(raw: str) -> tuple[Path, str]:
    """G5P.5: relative paths resolve against the DASHBOARD repo root only --
    monorepo-friendly (apps/calfel) and never a surprising location. Returns
    (validated_path, kind) where kind is 'absolute' | 'relative-resolved'."""
    if raw and isinstance(raw, str) and not Path(raw).is_absolute() and not any(ch in raw for ch in "\x00\r\n"):
        candidate = DASHBOARD_ROOT / raw
        return validate_repo_path(str(candidate)), "relative-resolved"
    return validate_repo_path(raw), "absolute"


def validate_repo_path(raw: str) -> Path:
    """Path is DATA. Reject anything that is not a safe, existing project dir.
    Raises ValueError with an operator-readable reason."""
    if not raw or not isinstance(raw, str):
        raise ValueError("no repo path given")
    if any(ch in raw for ch in "\x00\r\n"):
        raise ValueError("control characters in path")
    p = Path(raw)
    if not p.is_absolute():
        raise ValueError("path must be absolute (got a relative path)")
    rp = Path(os.path.realpath(p))
    if not rp.exists():
        raise ValueError("path does not exist on this machine")
    if not rp.is_dir():
        raise ValueError("path is not a directory")
    rn = _norm(rp)
    # drive roots (C:\, D:\, ...) and filesystem root
    if rp.parent == rp:
        raise ValueError("refusing a filesystem/drive root")
    for bad in DANGEROUS_PATHS:
        if rn == _norm(bad):
            raise ValueError(f"refusing a protected system path ({bad})")
    return rp


def build_command(repo: Path) -> list[str]:
    """FIXED allowlisted argv. The repo path is the cwd, never an argument the
    client controls inside the command line."""
    exe = graphify_exe()
    if not exe:
        raise ValueError("graphify is not installed on PATH (uv tool install graphifyy)")
    return [exe, "update", "."]


def expected_proof(repo: Path) -> Path:
    return repo / "graphify-out" / "graph.json"


# ---- G5P.4: per-project view pipeline + real output detection -----------------
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = STATIC_ROOT / "projects"
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


def sanitize_project_id(raw) -> str:
    """Project ids become directory names under graphify-out/projects/ -- the
    pattern forbids traversal, separators and anything exotic."""
    pid = str(raw or "")
    if not SAFE_ID.match(pid):
        raise ValueError("invalid project id (allowed: a-z 0-9 dash, max 40 chars)")
    return pid


def readmodel_mode_for(repo) -> str:
    """Every project -- including the dashboard's own host repo -- is built in
    'auto' mode: generic structure by default (file-kind concepts + top-level
    directory slices), with a custom taxonomy applied ONLY if a local config
    (graphiquest.taxonomy.local.json) supplies one AND it covers the repo. The
    shipped package has no local config, so this is always generic."""
    return "auto"


def build_views_for(pid: str, repo: Path, log=lambda line: None) -> dict:
    """graph.json -> read-model -> brain3d + explorer views, all under
    graphify-out/projects/<pid>/. Writes manifest.json with HONEST status:
    'ready' (with counts from the real read-model) or 'generated_incompatible'
    (with the exact reason). Fixed argv / in-process imports only -- nothing
    client-controlled executes."""
    pid = sanitize_project_id(pid)
    proj_dir = PROJECTS_DIR / pid
    proj_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = proj_dir / "manifest.json"
    graph_path = expected_proof(repo)

    def finish(m: dict) -> dict:
        m.update({
            "projectId": pid, "sanitizedId": pid,
            "repoPath": str(repo),
            "graphOutputPath": str(repo / "graphify-out"),
            "graphJsonPath": str(graph_path),
            "readModelPath": str(proj_dir / "read-model.json"),
            "view3dPath": str(proj_dir / "brain-3d-prototype.html"),
            "view2dPath": str(proj_dir / "graph-explorer.html"),
            "graphMtime": graph_path.stat().st_mtime if graph_path.exists() else None,
            "graphifyVersion": graphify_version(),
            "generatorContract": GENERATOR_CONTRACT,
            "bridgeVersion": BRIDGE_VERSION,
            "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
        manifest_path.write_text(json.dumps(m, indent=1), encoding="utf-8")
        return m

    try:
        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))
        from graphify_hivemind_readmodel import build_read_model, load_graph
        log("[bridge] building read-model from " + str(graph_path) + "\n")
        graph = load_graph(graph_path)
        mode = readmodel_mode_for(repo)
        log("[bridge] read-model mode: " + mode + "\n")
        rm = build_read_model(graph, repo_root=str(repo), source_graph_path=str(graph_path),
                              mode=mode)
        rm_path = proj_dir / "read-model.json"
        rm_path.write_text(json.dumps(rm), encoding="utf-8")
    except Exception as exc:
        log("[bridge] read-model failed: " + str(exc) + "\n")
        return finish({"status": "generated_incompatible",
                       "reason": f"graph output could not be adapted to the dashboard read-model: {exc}"})
    try:
        env = {**os.environ, "PYTHONHASHSEED": "0"}
        log("[bridge] generating 2D explorer view\n")
        r1 = subprocess.run([sys.executable, str(SCRIPTS_DIR / "graphify_hivemind_explorer.py"),
                             "--read-model", str(rm_path), "--out", str(proj_dir / "graph-explorer.html")],
                            capture_output=True, text=True, timeout=300, env=env, cwd=str(SCRIPTS_DIR.parent))
        if r1.returncode != 0:
            raise RuntimeError("explorer generator exited %s: %s" % (r1.returncode, (r1.stderr or r1.stdout)[-400:]))
        log("[bridge] generating 3D hivemind view\n")
        env3 = {**env, "GRAPHIFY_READ_MODEL": str(rm_path),
                "GRAPHIFY_VIEW_OUT": str(proj_dir / "brain-3d-prototype.html")}
        r2 = subprocess.run([sys.executable, str(SCRIPTS_DIR / "graphify_brain3d.py")],
                            capture_output=True, text=True, timeout=300, env=env3, cwd=str(SCRIPTS_DIR.parent))
        if r2.returncode != 0:
            raise RuntimeError("brain3d generator exited %s: %s" % (r2.returncode, (r2.stderr or r2.stdout)[-400:]))
    except Exception as exc:
        log("[bridge] view generation failed: " + str(exc) + "\n")
        return finish({"status": "generated_incompatible",
                       "reason": f"views could not be generated from the read-model: {exc}"})
    meta = rm.get("metadata", {})
    from collections import Counter
    ccounts = Counter(n.get("concept", "unknown") for n in rm.get("nodes", []))
    return finish({"status": "ready",
                   "nodes": meta.get("emitted_nodes"), "edges": meta.get("emitted_edges"),
                   "slices": len(rm.get("slices", [])),
                   "concepts": sorted(ccounts.items()),
                   "viewsBase": "/projects/" + pid + "/"})


def clean_project_views(pid: str) -> dict:
    """Delete ONLY graphify-out/projects/<sanitized-id>. The realpath guard makes
    escape impossible even if sanitization ever regressed; source repos, design
    assets and the default views are structurally out of reach."""
    pid = sanitize_project_id(pid)
    target = (PROJECTS_DIR / pid).resolve()
    projects_root = PROJECTS_DIR.resolve()
    if projects_root not in target.parents:
        raise ValueError("cleanup target escapes graphify-out/projects -- refused")
    if not target.exists():
        return {"projectId": pid, "cleaned": False, "reason": "no generated views to clean"}
    shutil.rmtree(target)
    return {"projectId": pid, "cleaned": True}


GITHUB_URL = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")


def validate_repo_url(raw) -> tuple[str, str, str]:
    """G5P.6a (operator-requested URL import): the URL is DATA and must match
    graphify clone's documented target shape -- https GitHub repo only. Returns
    (canonical_url, owner, repo). Anything else is refused with a clear reason."""
    url = str(raw or "").strip()
    m = GITHUB_URL.match(url)
    if not m:
        raise ValueError("only https://github.com/<owner>/<repo> URLs are supported")
    owner, repo = m.group(1), m.group(2)
    if owner.startswith("-") or repo.startswith("-"):
        raise ValueError("invalid owner/repo name")
    return f"https://github.com/{owner}/{repo}", owner, repo


def expected_clone_dir(owner: str, repo: str) -> Path:
    """graphify clone's documented default: ~/.graphify/repos/<owner>/<repo>."""
    return Path(os.path.expanduser("~")) / ".graphify" / "repos" / owner / repo


def pick_folder() -> dict:
    """G5P.6: REAL native folder picker on the bridge host (tkinter). The browser
    cannot expose absolute paths (File System Access API returns handles only),
    so page-side pickers would be fake -- this one is genuine, loopback-only,
    takes ZERO client-controlled arguments, and only ever returns a path string
    the user chose in their own OS dialog. Honest error when headless/unavailable."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(title="Select a project folder to graph")
        root.destroy()
        if not path:
            return {"cancelled": True}
        return {"path": path}
    except Exception as exc:
        return {"error": f"native folder picker unavailable on this machine: {exc}"}


def list_generated_projects() -> list[str]:
    if not PROJECTS_DIR.exists():
        return []
    return sorted(d.name for d in PROJECTS_DIR.iterdir() if d.is_dir())


def scan_project(pid: str, repo_raw) -> dict:
    """REAL output detection, zero side effects. Honest states only."""
    try:
        pid = sanitize_project_id(pid)
    except ValueError as exc:
        return {"status": "error", "reason": str(exc)}
    manifest_path = PROJECTS_DIR / pid / "manifest.json"
    repo, path_kind = None, None
    if repo_raw:
        try:
            repo, path_kind = resolve_repo_path(repo_raw)
        except ValueError as exc:
            return {"status": "invalid_path", "reason": str(exc), "pathKind": "invalid"}
    graph_exists = bool(repo) and expected_proof(repo).exists()
    if manifest_path.exists():
        try:
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            return {"status": "generated_incompatible", "reason": f"manifest unreadable: {exc}"}
        if m.get("status") == "ready":
            missing = [f for f in ("read-model.json", "brain-3d-prototype.html", "graph-explorer.html")
                       if not (PROJECTS_DIR / pid / f).exists()]
            if missing:
                return {"status": "views_missing",
                        "reason": "generated view files are missing (" + ", ".join(missing) + ") -- rebuild"}
            # G5P.5 staleness gates -- honest, narrow, file-based:
            if m.get("generatorContract") != GENERATOR_CONTRACT:
                return {**m, "status": "rebuild_required",
                        "reason": f"views were generated under an older contract ({m.get('generatorContract') or 'pre-contract'}) -- rebuild to pick up generator fixes"}
            if repo and graph_exists and m.get("graphMtime") is not None:
                if expected_proof(repo).stat().st_mtime > float(m["graphMtime"]) + 2:
                    return {**m, "status": "rebuild_required",
                            "reason": "graph.json is newer than the generated views -- rebuild"}
            if repo and not graph_exists:
                m = {**m, "sourceGone": True}
            return {**m, "pathKind": path_kind, "resolvedPath": str(repo) if repo else None}
        return m   # generated_incompatible manifest carries its reason
    if graph_exists:
        return {"status": "generated_pending_reload", "pathKind": path_kind,
                "resolvedPath": str(repo) if repo else None,
                "reason": "graph.json exists but dashboard views have not been generated -- run RUN GRAPHIFY (bridge) to build them"}
    return {"status": "no_output", "pathKind": path_kind, "resolvedPath": str(repo) if repo else None}


class RunState:
    """One rebuild at a time, watchdog-bounded, proof-checked."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.current: dict = {"state": "idle"}
        self._proc: subprocess.Popen | None = None

    def snapshot(self) -> dict:
        c = dict(self.current)
        c["tail"] = (c.get("tail") or "")[-2000:]   # UI gets a bounded tail
        return c

    def start(self, project_id: str, repo: Path, timeout: int | None = None) -> tuple[bool, str]:
        if not self._lock.acquire(blocking=False):
            return False, "another rebuild is already running"
        try:
            if self.current.get("state") == "running":
                return False, "another rebuild is already running"
            cmd = build_command(repo)
            timeout = timeout or int(os.environ.get("GRAPHIFY_REBUILD_TIMEOUT", "600"))
            started = time.time()
            self.current = {"state": "running", "projectId": project_id, "repoPath": str(repo),
                            "startedAt": started, "tail": "", "cmd": " ".join(cmd) + f"  (cwd={repo})"}
            env = {**os.environ, "PYTHONHASHSEED": "0"}
            proc = subprocess.Popen(cmd, cwd=str(repo), stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True,
                                    encoding="utf-8", errors="replace")
            self._proc = proc
            threading.Thread(target=self._pump, args=(proc, project_id, repo, started, timeout), daemon=True).start()
            return True, "started"
        except ValueError as exc:
            self.current = {"state": "error", "projectId": project_id, "error": str(exc)}
            return False, str(exc)
        finally:
            self._lock.release()

    def _pump(self, proc: subprocess.Popen, project_id: str, repo: Path, started: float, timeout: int) -> None:
        killer = threading.Timer(timeout, lambda: self._kill(proc, timeout))
        killer.daemon = True
        killer.start()
        tail = ""
        try:
            for line in proc.stdout or []:
                tail = (tail + line)[-TAIL_CAP:]
                self.current["tail"] = tail
            proc.wait()
        finally:
            killer.cancel()
        proof = expected_proof(repo)
        # G5P.4: graphify update legitimately no-ops when nothing changed since
        # the last run ('outputs left untouched') -- an existing graph.json after
        # exit 0 is a VALID current graph, not a stale artifact. Freshness is not
        # required; absence still fails honestly.
        ok = proc.returncode == 0 and proof.exists()
        manifest = None
        if ok:
            def _log(line: str) -> None:
                self.current["tail"] = ((self.current.get("tail") or "") + line)[-TAIL_CAP:]
            try:
                manifest = build_views_for(project_id, repo, log=_log)
            except ValueError as exc:           # bad project id -> honest error
                manifest = {"status": "generated_incompatible", "reason": str(exc)}
            ok = manifest.get("status") == "ready"
        self.current = {
            "state": "success" if ok else "error",
            "projectId": project_id, "repoPath": str(repo),
            "startedAt": started, "finishedAt": time.time(),
            "exitCode": proc.returncode, "tail": self.current.get("tail", tail),
            "proof": {"graphJson": proof.exists(), "path": str(proof)},
            "manifest": manifest,
            "error": None if ok else (
                f"graphify exited {proc.returncode}" if proc.returncode != 0
                else (manifest or {}).get("reason")
                or "graphify exited 0 but produced no graph.json"),
        }
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, "a", encoding="utf-8") as fh:
                fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {project_id} {self.current['state']} "
                         f"exit={proc.returncode} repo={repo}\n")
        except OSError:
            pass

    def start_import(self, project_id: str, url_raw, timeout: int | None = None) -> tuple[bool, str]:
        """URL import pipeline: graphify clone -> graphify update (in clone) ->
        read-model -> views. Same busy-lock as generate (one operation at a time);
        every stage is fixed argv; the URL is validated data."""
        if not self._lock.acquire(blocking=False):
            return False, "another rebuild/import is already running"
        try:
            if self.current.get("state") in ("running", "cloning"):
                return False, "another rebuild/import is already running"
            url, owner, repo_name = validate_repo_url(url_raw)
            exe = graphify_exe()
            if not exe:
                raise ValueError("graphify is not installed on PATH")
            timeout = timeout or int(os.environ.get("GRAPHIFY_REBUILD_TIMEOUT", "600"))
            started = time.time()
            self.current = {"state": "cloning", "stage": "cloning", "projectId": project_id,
                            "url": url, "startedAt": started,
                            "tail": f"[bridge] importing {url}\n"}
            threading.Thread(target=self._pump_import,
                             args=(project_id, url, owner, repo_name, started, timeout),
                             daemon=True).start()
            return True, "started"
        except ValueError as exc:
            self.current = {"state": "error", "projectId": project_id, "error": str(exc)}
            return False, str(exc)
        finally:
            self._lock.release()

    def _pump_import(self, project_id, url, owner, repo_name, started, timeout):
        def _log(line):
            self.current["tail"] = ((self.current.get("tail") or "") + line)[-TAIL_CAP:]
        manifest, repo, err = None, None, None
        try:
            target = expected_clone_dir(owner, repo_name)
            if target.exists():
                # G5P.8: re-importing the same URL refreshes the existing clone
                # instead of failing -- skip straight to graphing.
                _log("[bridge] clone already exists at " + str(target)
                     + " -- skipping clone, refreshing graph\n")
                clone = None
            else:
                clone = subprocess.run([graphify_exe(), "clone", url], capture_output=True,
                                       text=True, timeout=timeout, encoding="utf-8", errors="replace")
                _log((clone.stdout or "")[-1500:] + (clone.stderr or "")[-500:])
            if not target.exists():
                err = (f"clone did not produce {target} (exit {clone.returncode}) -- "
                       "check the URL and network access")
            else:
                repo = validate_repo_path(str(target))
                self.current.update({"state": "running", "stage": "graphing", "repoPath": str(repo)})
                _log(f"[bridge] cloned to {repo}; running graphify update\n")
                upd = subprocess.run(build_command(repo), cwd=str(repo), capture_output=True,
                                     text=True, timeout=timeout,
                                     env={**os.environ, "PYTHONHASHSEED": "0"},
                                     encoding="utf-8", errors="replace")
                _log((upd.stdout or "")[-1500:])
                if upd.returncode != 0 or not expected_proof(repo).exists():
                    err = f"graphify update failed in the clone (exit {upd.returncode})"
                else:
                    self.current["stage"] = "building views"
                    manifest = build_views_for(project_id, repo, log=_log)
                    if manifest.get("status") != "ready":
                        err = manifest.get("reason")
        except subprocess.TimeoutExpired:
            err = f"import exceeded {timeout}s"
        except (ValueError, OSError) as exc:
            err = str(exc)
        ok = err is None
        self.current = {"state": "success" if ok else "error", "projectId": project_id,
                        "url": url, "repoPath": str(repo) if repo else None,
                        "startedAt": started, "finishedAt": time.time(),
                        "tail": self.current.get("tail", ""), "manifest": manifest,
                        "clonedPath": str(repo) if repo else None, "error": err}
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, "a", encoding="utf-8") as fh:
                fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {project_id} import "
                         f"{self.current['state']} url={url}\n")
        except OSError:
            pass

    def _kill(self, proc: subprocess.Popen, timeout: int) -> None:
        self.current["tail"] = (self.current.get("tail") or "") + f"\n[bridge] watchdog: exceeded {timeout}s - killing\n"
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
            else:
                proc.terminate()
        except OSError:
            pass


RUNS = RunState()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(STATIC_ROOT), **kw)

    def _loopback_only(self) -> bool:
        if self.client_address[0] not in LOOPBACK:
            self.send_error(403, "loopback only")
            return False
        return True

    def _csrf_ok(self) -> bool:
        """G5P.10 security: the loopback PEER check alone does NOT stop a
        malicious web page from POSTing here -- the victim's browser connects
        FROM 127.0.0.1, so the peer check passes. Browser-issued cross-origin
        requests are identified by Sec-Fetch-Site / Origin and refused; the
        dashboard's own same-origin fetches and non-browser clients (curl, the
        tests, the selftest -- no Origin header) are allowed. Closes the
        cross-site-request-forgery vector on every state-changing endpoint."""
        site = self.headers.get("Sec-Fetch-Site")
        if site and site not in ("same-origin", "same-site", "none"):
            self._drain()
            self.send_error(403, "cross-site request refused")
            return False
        origin = self.headers.get("Origin")
        if origin:
            port = self.server.server_address[1]
            allowed = {f"http://127.0.0.1:{port}", f"http://localhost:{port}",
                       f"http://[::1]:{port}"}
            if origin not in allowed:
                self._drain()
                self.send_error(403, "cross-origin request refused")
                return False
        return True

    def _drain(self) -> None:
        """Consume an unread request body so a refusal returns a CLEAN status
        instead of resetting the socket (Content-Length unread -> the client
        sees a connection reset, not the 403)."""
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 0:
                self.rfile.read(min(n, 1 << 20))
        except (ValueError, OSError):
            pass

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self):  # noqa: N802 -- loopback check covers HEAD too (refute-lane catch)
        if not self._loopback_only():
            return
        return super().do_HEAD()

    def do_GET(self):  # noqa: N802
        if not self._loopback_only():
            return
        if self.path == "/api/bridge/status":
            return self._json(200, {"bridge": BRIDGE_NAME, "version": BRIDGE_VERSION,
                                    "graphifyDetected": bool(graphify_exe()),
                                    "run": RUNS.snapshot()})
        if self.path.startswith("/api/graphify/status"):
            return self._json(200, {"run": RUNS.snapshot()})
        if self.path == "/api/connectors/status":
            return self._json(200, connectors_status())
        if self.path.startswith("/api/"):
            return self._json(404, {"error": "unknown endpoint"})
        return super().do_GET()

    def do_POST(self):  # noqa: N802
        if not self._loopback_only():
            return
        if not self._csrf_ok():
            return
        if self.path == "/api/projects/import-url":
            try:
                n = int(self.headers.get("Content-Length") or 0)
                data = json.loads(self.rfile.read(min(n, 65536)) or b"{}")
                project_id = sanitize_project_id(data.get("projectId"))
                url, _o, _r = validate_repo_url(data.get("url"))
            except (ValueError, json.JSONDecodeError) as exc:
                return self._json(400, {"error": str(exc)})
            ok, msg = RUNS.start_import(project_id, url)
            return self._json(202 if ok else 409, {"started": ok, "message": msg, "run": RUNS.snapshot()})
        if self.path == "/api/claudecode/stop":
            self._drain()
            return self._json(200, claude_code_stop())
        if self.path == "/api/claudecode/ask":
            # G5Q.1l: one explicit user ask = one bounded headless call. The
            # ONLY client input is the question string (passed as argv data).
            try:
                n = int(self.headers.get("Content-Length") or 0)
                data = json.loads(self.rfile.read(min(n, 8192)) or b"{}")
            except (ValueError, json.JSONDecodeError):
                data = {}
            entry = None
            ask_cwd = None
            label = str(data.get("projectLabel") or "")[:60]
            rp = data.get("repoPath")
            if rp:
                try:
                    ask_cwd, _k = resolve_repo_path(str(rp))
                except (ValueError, OSError):
                    ask_cwd = None
            pid = data.get("projectId")
            if pid:
                # pin THIS call's graph server to the dashboard's selected
                # project via its generated read-model (id sanitized as data)
                try:
                    pid = sanitize_project_id(pid)
                    rmp = PROJECTS_DIR / pid / "read-model.json"
                    if rmp.is_file():
                        e0 = graphify_mcp_entry()
                        entry = {"command": e0["command"],
                                 "args": [e0["args"][0], "--read-model", str(rmp)]}
                except ValueError:
                    entry = None
            qq = str(data.get("q") or "")
            if qq and (entry or ask_cwd):
                qq = ("(You are analyzing the project '" + (label or pid or "selected")
                      + "'. Its graph server" + (" and your working directory are" if ask_cwd else " is")
                      + " pinned to that project -- never describe or reference any other repo.)\n\n") + qq
            if qq:
                qq += ("\n\n(If this is a navigation request -- jump/find/show a node -- "
                       "first locate it with find_node, then ALSO end your reply with one "
                       "line exactly: JUMP: <the node id from find_node>)")
            return self._json(200, claude_code_ask(qq, mcp_entry=entry, cwd=ask_cwd))
        if self.path == "/api/setup/install-graphify":
            # G5Q.1q: explicit SETUP click only; no client input (body drained).
            self._drain()
            return self._json(200, install_graphify())
        if self.path == "/api/claudecode/enrich":
            # G5Q.1m: one bounded enrichment call per explicit ENRICH click.
            try:
                n = int(self.headers.get("Content-Length") or 0)
                data = json.loads(self.rfile.read(min(n, 65536)) or b"{}")
            except (ValueError, json.JSONDecodeError):
                data = {}
            return self._json(200, claude_code_enrich(data.get("report") or {}))
        if self.path == "/api/claudecode/register":
            # G5Q.1h: one-click registration -- fixed argv, no client input at
            # all (the body is drained and ignored). Explicit click only.
            self._drain()
            return self._json(200, claude_code_register())
        if self.path == "/api/mcp/selftest":
            # G5Q.1e: run the SHIPPED MCP server's own --selftest -- fixed argv,
            # read-only, no client input. Proves the local server works so the
            # connector "CHECK SELF-TEST" can show an honest pass/fail.
            self._drain()
            mcp = Path(__file__).resolve().parent / "graphify_mcp_server.py"
            if not mcp.exists():
                return self._json(200, {"ok": False, "summary": "graphify_mcp_server.py not found"})
            try:
                r = subprocess.run([sys.executable, str(mcp), "--repo", str(DASHBOARD_ROOT), "--selftest"],
                                   capture_output=True, text=True, timeout=30,
                                   encoding="utf-8", errors="replace")
                out = (r.stdout or "") + (r.stderr or "")
                ok = r.returncode == 0 and "selftest: PASS" in out
                summary = next((ln.strip() for ln in out.splitlines()
                                if "graph:" in ln or "selftest:" in ln), out.strip()[-200:])
            except subprocess.TimeoutExpired:
                ok, summary = False, "selftest timed out after 30s"
            except OSError as exc:
                ok, summary = False, f"could not run python: {exc}"
            return self._json(200, {"ok": ok, "summary": summary})
        if self.path == "/api/projects/pick-folder":
            return self._json(200, pick_folder())   # no body read: nothing client-controlled
        if self.path == "/api/projects/clean":
            try:
                n = int(self.headers.get("Content-Length") or 0)
                data = json.loads(self.rfile.read(min(n, 65536)) or b"{}")
                if data.get("all"):
                    results = [clean_project_views(pid) for pid in list_generated_projects()]
                else:
                    results = [clean_project_views(str(data.get("projectId") or ""))]
            except (ValueError, json.JSONDecodeError) as exc:
                return self._json(400, {"error": str(exc)})
            return self._json(200, {"results": results})
        if self.path == "/api/projects/scan":
            try:
                n = int(self.headers.get("Content-Length") or 0)
                data = json.loads(self.rfile.read(min(n, 65536)) or b"{}")
                results = {}
                for entry in (data.get("projects") or [])[:50]:
                    pid = str((entry or {}).get("id") or "")[:80]
                    results[pid] = scan_project(pid, (entry or {}).get("repoPath"))
            except (ValueError, json.JSONDecodeError) as exc:
                return self._json(400, {"error": str(exc)})
            return self._json(200, {"results": results})
        if self.path != "/api/graphify/generate":
            return self._json(404, {"error": "unknown endpoint (the bridge allowlists graphify generation + read-only output scans)"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(min(n, 65536)) or b"{}")
            project_id = str(data.get("projectId") or "")[:80]
            repo, _kind = resolve_repo_path(data.get("repoPath"))
        except (ValueError, json.JSONDecodeError) as exc:
            return self._json(400, {"error": str(exc)})
        if not project_id:
            return self._json(400, {"error": "projectId required"})
        ok, msg = RUNS.start(project_id, repo)
        return self._json(202 if ok else 409, {"started": ok, "message": msg, "run": RUNS.snapshot()})

    def log_message(self, fmt, *args):  # quiet static serving; API events go to LOG_FILE
        first = args[0] if args else ""
        # send_error() logs with an int code as args[0] -- guard the substring check
        if isinstance(first, str) and "/api/" in first:
            super().log_message(fmt, *args)


def graphify_mcp_entry() -> dict:
    """The ONLY content the config writer can write -- computed server-side
    (absolute interpreter beats bare 'python': GUI apps may not see the PATH)."""
    server = SCRIPTS_DIR / "graphify_mcp_server.py"
    return {"command": sys.executable,
            "args": [str(server), "--repo", str(DASHBOARD_ROOT)]}


def claude_code_config_path() -> Path:
    """Claude Code stores user-scope MCP servers in ~/.claude.json (top-level
    mcpServers key). Read-only here -- Claude Code writes its own config via
    `claude mcp add`; this bridge NEVER writes that file."""
    return Path(os.path.expanduser("~")) / ".claude.json"


def claude_code_add_cmd() -> str:
    """The exact one-line registration command, computed server-side so the
    absolute paths are correct for THIS machine. Doc-canonical flag order
    (code.claude.com/docs/en/mcp, verified 2026-06-11): options before the
    name; -s user = available in every project; -- separates claude's own
    flags from the server command."""
    e = graphify_mcp_entry()
    return ('claude mcp add -s user graphify -- "' + e["command"] + '" "'
            + e["args"][0] + '" --repo "' + e["args"][2] + '"')


def connectors_status() -> dict:
    """Read-only, honest facts the connect wizard shows: is the claude CLI on
    PATH, is graphify registered in Claude Code (~/.claude.json -- READ-only,
    this bridge never writes it), is the Graphify scanner CLI installed.
    Nothing here claims 'connected' -- these are the real rungs."""
    out = {"claudeCodeOnPath": bool(shutil.which("claude")),
           "claudeCodeConfigPath": str(claude_code_config_path()),
           "claudeCodeRegistered": False, "claudeCodeCurrent": False,
           "claudeCodeConfigMalformed": False,
           "claudeCodeAddCmd": claude_code_add_cmd(),
           "graphifyDetected": bool(graphify_exe()),
           "graphifyVersion": graphify_version(),
           "serverPath": str(SCRIPTS_DIR / "graphify_mcp_server.py")}
    cc = claude_code_config_path()
    if cc.is_file():
        try:
            # ~/.claude.json also stores history and can grow multi-MB
            # (claude-code#6394) -- cap reads at 64MB as a pathology guard.
            if cc.stat().st_size > 64 * 1024 * 1024:
                raise OSError("config too large to read safely")
            data = json.loads(cc.read_text(encoding="utf-8-sig"))
            entry = (data.get("mcpServers") or {}).get("graphify")
            if entry is not None:
                # stored entries carry extra keys (type/env) -- compare only
                # what we control (live-verified shape 2026-06-11)
                want = graphify_mcp_entry()
                out["claudeCodeRegistered"] = True
                out["claudeCodeCurrent"] = (entry.get("command") == want["command"]
                                            and list(entry.get("args") or []) == want["args"])
        except (json.JSONDecodeError, OSError, AttributeError):
            out["claudeCodeConfigMalformed"] = True
    return out


def claude_code_register() -> dict:
    """G5Q.1h: the one-click connect. Runs Claude Code's OWN registration
    command with a FIXED argv (zero client input; same bounded-op class as the
    MCP selftest -- this is NOT a command runner). The bridge still never
    writes ~/.claude.json itself; the claude CLI does. Refuses when the CLI is
    absent. Result includes a re-read of the registration status."""
    exe = shutil.which("claude")
    if not exe:
        return {"ok": False,
                "reason": "the claude CLI is not on PATH -- install Claude Code "
                          "first (step 1), then retry"}
    e = graphify_mcp_entry()
    argv = [exe, "mcp", "add", "-s", "user", "graphify", "--", e["command"]] + e["args"]
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=30,
                           encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "claude mcp add timed out after 30s"}
    except OSError as exc:
        return {"ok": False, "reason": f"could not run the claude CLI: {exc}"}
    st = connectors_status()
    ok = r.returncode == 0 and bool(st.get("claudeCodeRegistered"))
    tail = ((r.stdout or "") + ("\n" + r.stderr if r.stderr else "")).strip()[-400:]
    return {"ok": ok, "exit": r.returncode, "output": tail, "status": st}

_CC_ASK_LOCK = threading.Lock()
_CC_PROC: dict = {"p": None}


def _cc_kill(proc) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
        else:
            proc.terminate()
    except OSError:
        pass


def claude_code_stop() -> dict:
    """G5Q.1s: the STOP button -- kills only OUR held claude child process.
    Explicit click; honest no-op when nothing is running."""
    p = _CC_PROC.get("p")
    if not p or p.poll() is not None:
        return {"ok": True, "stopped": False, "reason": "nothing is running"}
    _cc_kill(p)
    return {"ok": True, "stopped": True}


def claude_code_ask(question: str, max_len: int = 4000, mcp_entry=None, cwd=None) -> dict:
    """G5Q.1l (operator-directed): run ONE bounded headless Claude Code call
    and return its answer for the dashboard's response window. Triggered ONLY
    by an explicit user ask in the Claude Code lane -- never automatically.
    Safety: argv list (question is a DATA argument, no shell anywhere);
    --strict-mcp-config exposes ONLY our read-only graphify server (the
    operator's other MCP servers are never loaded); --allowedTools scoped to
    that server; single-flight; 180s watchdog."""
    q = (question or "").strip()
    if not q:
        return {"ok": False, "reason": "empty question"}
    if len(q) > max_len:
        return {"ok": False, "reason": f"question too long ({max_len} chars max)"}
    exe = shutil.which("claude")
    if not exe:
        return {"ok": False, "reason": "the claude CLI is not on PATH -- open the CLAUDE CODE pill to set it up"}
    st = connectors_status()
    if not st.get("claudeCodeRegistered"):
        return {"ok": False, "reason": "graphify is not registered in Claude Code yet -- open the CLAUDE CODE pill and press REGISTER FOR ME"}
    mcp_cfg = json.dumps({"mcpServers": {"graphify": (mcp_entry or graphify_mcp_entry())}})
    argv = [exe, "-p", q, "--output-format", "json",
            "--mcp-config", mcp_cfg, "--strict-mcp-config",
            "--allowedTools", "mcp__graphify"]
    if not _CC_ASK_LOCK.acquire(blocking=False):
        return {"ok": False, "reason": "Claude Code is already answering another ask -- wait for it to finish"}
    started = time.time()
    try:
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, cwd=str(cwd or DASHBOARD_ROOT),
                                encoding="utf-8", errors="replace")
        _CC_PROC["p"] = proc                      # held so STOP can kill it
        try:
            out_s, err_s = proc.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            _cc_kill(proc)
            return {"ok": False, "reason": "Claude Code did not answer within 180s -- try a narrower question"}
        r = type("R", (), {})()
        r.returncode, r.stdout, r.stderr = proc.returncode, out_s, err_s
    except OSError as exc:
        return {"ok": False, "reason": f"could not run the claude CLI: {exc}"}
    finally:
        _CC_PROC["p"] = None
        _CC_ASK_LOCK.release()
    dur = round(time.time() - started, 1)
    out = (r.stdout or "").strip()
    if r.returncode != 0:
        tail = ((r.stderr or "") + out)[-300:].strip()
        return {"ok": False, "reason": f"claude exited {r.returncode}: {tail or 'no output'}", "durationS": dur}
    answer, cost = None, None
    try:
        data = json.loads(out)
        if isinstance(data, dict):
            answer = data.get("result")
            cost = data.get("total_cost_usd")
    except json.JSONDecodeError:
        answer = out or None
    if not answer:
        return {"ok": False, "reason": "claude returned no answer text", "durationS": dur}
    return {"ok": True, "answer": answer, "durationS": dur, "costUsd": cost}


ENRICH_PROMPT = (
    "You are the Hunter enrichment lane of the Graphify dashboard. Disciplines: "
    "silver-platter (hand the operator ready-to-act recommendations), grill-me "
    "(adversarially VERIFY each finding with the graphify tools before "
    "recommending -- refute what does not hold), guess-what (predict the "
    "operator's next questions), missing-sweep (state what the structural scan "
    "cannot see). Use the graphify MCP tools (graph_summary, find_node, "
    "node_neighbors, list_concepts, run_hunter) to verify. Findings JSON from "
    "the local structural scan follows. Respond ONLY with JSON, no prose: "
    '{"recommendations":[{"title":"...","why":"...","action":"...",'
    '"confidence":"high|medium|low","nodeIds":["<node id or exact label>"]}]} '
    "-- at most 6, ordered by priority, nodeIds MUST be copied character-for-character from the findings nodeIds arrays (or omitted) -- never invent or normalize ids.\n"
    "FINDINGS:\n")


def claude_code_enrich(report: dict) -> dict:
    """G5Q.1m: REAL Hunter enrichment -- one bounded call per explicit ENRICH
    click. The report findings are DATA inside the prompt (argv, no shell),
    size-capped; the strict graphify-only MCP config rides along unchanged."""
    if not isinstance(report, dict):
        return {"ok": False, "reason": "no report payload"}
    slim = {"project": report.get("projLbl") or report.get("proj"),
            "counts": report.get("counts"),
            "findings": [{"kind": f.get("kind"), "sev": f.get("sev"),
                          "title": str(f.get("title") or "")[:160],
                          "evidence": str(f.get("evidence") or "")[:200],
                          "nodeIds": (f.get("nodeIds") or [])[:3]}
                         for f in (report.get("findings") or [])[:20]]}
    payload = json.dumps(slim)
    if len(payload) > 16000:
        payload = payload[:16000] + "...(truncated)"
    res = claude_code_ask(ENRICH_PROMPT + payload, max_len=20000)
    if not res.get("ok"):
        return res
    raw = str(res.get("answer") or "")
    recs = None
    i, j = raw.find("{"), raw.rfind("}")
    if i != -1 and j > i:
        try:
            data = json.loads(raw[i:j + 1])
            recs = data.get("recommendations")
        except json.JSONDecodeError:
            recs = None
    if not isinstance(recs, list) or not recs:
        # honest fallback: surface Claude's text rather than faking structure
        recs = [{"title": "Claude Code answered in prose (JSON parse failed)",
                 "why": raw[:600], "action": "read the full answer; re-run enrich for structured output",
                 "confidence": "low", "nodeIds": []}]
    clean = []
    for r0 in recs[:6]:
        if not isinstance(r0, dict):
            continue
        clean.append({"title": str(r0.get("title") or "")[:200],
                      "why": str(r0.get("why") or "")[:600],
                      "action": str(r0.get("action") or "")[:400],
                      "confidence": str(r0.get("confidence") or "low")[:10],
                      "nodeIds": [str(x)[:200] for x in (r0.get("nodeIds") or [])[:5]]})
    return {"ok": True, "recommendations": clean, "durationS": res.get("durationS"),
            "costUsd": res.get("costUsd")}


_SETUP_LOCK = threading.Lock()


def install_graphify() -> dict:
    """G5Q.1q: one-click first-run setup -- installs the Graphify scanner CLI
    (open source by safishamsi -- github.com/safishamsi/graphify, MIT) via a
    FIXED installer chain (uv tool -> pipx -> python -m pip --user). Runs ONLY
    on the user's explicit SETUP click; zero client input; honest failures."""
    if graphify_exe():
        return {"ok": True, "already": True, "version": graphify_version()}
    if not _SETUP_LOCK.acquire(blocking=False):
        return {"ok": False, "reason": "setup is already running -- give it a moment"}
    try:
        attempts = []
        for argv in (["uv", "tool", "install", "graphifyy"],
                     ["pipx", "install", "graphifyy"],
                     [sys.executable, "-m", "pip", "install", "--user", "graphifyy"]):
            exe = argv[0] if argv[0] == sys.executable else shutil.which(argv[0])
            if not exe:
                attempts.append(argv[0] + ": not found")
                continue
            try:
                r = subprocess.run([exe] + argv[1:], capture_output=True, text=True,
                                   timeout=300, encoding="utf-8", errors="replace")
            except subprocess.TimeoutExpired:
                attempts.append(argv[0] + ": timed out after 300s")
                continue
            except OSError as exc:
                attempts.append(argv[0] + f": {exc}")
                continue
            if r.returncode == 0:
                _GFY_VER.clear()
                if graphify_exe():
                    return {"ok": True, "installer": argv[0], "version": graphify_version()}
                attempts.append(argv[0] + ": installed, but graphify is not on PATH yet "
                                          "-- restart the dashboard (Ctrl+C, run the start "
                                          "script again) so the new PATH is picked up")
            else:
                attempts.append(argv[0] + ": exit " + str(r.returncode) + " "
                                + ((r.stderr or r.stdout or "")[-120:]).strip())
        return {"ok": False,
                "reason": "; ".join(attempts) or "no installer found -- install uv or pipx first"}
    finally:
        _SETUP_LOCK.release()


def seed_design_assets() -> int:
    """G5Q.1c: copy tracked required design assets into the served
    graphify-out/design/ for any file that is MISSING (never overwrites). This
    is what makes a fresh clone render the approved molten visual -- the assets
    are committed under graphify_assets/design/ while graphify-out/ stays
    gitignored. Returns the number of files seeded."""
    if not TRACKED_ASSETS.is_dir():
        return 0
    seeded = 0
    for src in TRACKED_ASSETS.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(TRACKED_ASSETS)
        dst = STATIC_ROOT / "design" / rel
        if dst.exists():
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            seeded += 1
        except OSError:
            pass
    return seeded


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args()
    seeded = seed_design_assets()
    if seeded:
        print(f"[{BRIDGE_NAME}] seeded {seeded} required design asset(s) into "
              f"{STATIC_ROOT / 'design'} (fresh-clone visual)")
    # G5P.8: Windows allows a second bind on the same port (SO_REUSEADDR),
    # which split run-state across two bridges and made import status polls
    # land on a bridge that knew nothing about the run. Probe before binding.
    try:
        import urllib.request
        with urllib.request.urlopen(
                f"http://127.0.0.1:{args.port}/api/bridge/status", timeout=1.5) as r:
            if json.loads(r.read() or b"{}").get("bridge") == BRIDGE_NAME:
                print(f"[{BRIDGE_NAME}] another bridge is already serving "
                      f"127.0.0.1:{args.port} -- refusing to double-start. "
                      f"Use the running one, or stop it first.")
                raise SystemExit(2)
    except SystemExit:
        raise
    except Exception:
        pass  # nothing answering -> safe to bind
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as exc:
        print(f"[{BRIDGE_NAME}] cannot bind 127.0.0.1:{args.port} ({exc}) -- "
              f"is another instance running? Try --port {args.port + 1}.")
        raise SystemExit(1)
    print(f"[{BRIDGE_NAME}] loopback-only on http://127.0.0.1:{args.port} "
          f"(static: {STATIC_ROOT}; allowlisted op: graphify update <validated-dir>)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
