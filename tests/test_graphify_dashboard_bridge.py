"""Tests for the G5P.3 loopback Graphify bridge (scripts/graphify_dashboard_bridge.py).

Safety contract under test: fixed allowlisted argv (never client text), path
validated as data (injection strings are just invalid paths), one rebuild at a
time, success only with on-disk proof, loopback-only HTTP surface.

Standard library unittest:
  python tests/test_graphify_dashboard_bridge.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import graphify_dashboard_bridge as bridge  # noqa: E402


class PathValidationTests(unittest.TestCase):
    def test_accepts_real_directory(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(bridge.validate_repo_path(d), Path(os.path.realpath(d)))

    def test_rejects_relative_missing_and_files(self):
        for bad in ("relative/path", "C:\\definitely\\not\\a\\real\\dir\\xyz123", ""):
            with self.assertRaises(ValueError):
                bridge.validate_repo_path(bad)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            name = f.name
        try:
            with self.assertRaises(ValueError):
                bridge.validate_repo_path(name)  # a file, not a directory
        finally:
            os.unlink(name)

    def test_rejects_roots_and_system_paths(self):
        for bad in ("C:\\", os.path.expanduser("~"),
                    os.environ.get("WINDIR", "/etc"),
                    os.environ.get("PROGRAMFILES", "/usr")):
            with self.assertRaises(ValueError, msg=bad):
                bridge.validate_repo_path(bad)

    def test_injection_strings_are_just_invalid_paths(self):
        # The path is DATA: shell metacharacters never reach a shell (argv list,
        # fixed verb) and these strings simply fail existence validation.
        for inj in ('C:\\x; rm -rf /', 'C:\\x && calc.exe', 'C:\\x | whoami',
                    'C:\\x" & del *', "C:\\x' || shutdown", "C:\\x`id`",
                    "C:\\x\nC:\\y", "C:\\x$(reboot)"):
            with self.assertRaises(ValueError, msg=inj):
                bridge.validate_repo_path(inj)


class CommandConstructionTests(unittest.TestCase):
    def test_command_is_fixed_allowlist(self):
        if not bridge.graphify_exe():
            self.skipTest("graphify not on PATH")
        with tempfile.TemporaryDirectory() as d:
            cmd = bridge.build_command(bridge.validate_repo_path(d))
        self.assertEqual(cmd[1:], ["update", "."])     # verb is hardcoded
        self.assertEqual(len(cmd), 3)                  # nothing else, ever
        # the repo path is NOT part of the argv (it is the cwd)
        self.assertNotIn(str(d), " ".join(cmd))

    def test_proof_path(self):
        self.assertEqual(bridge.expected_proof(Path("X:/r")), Path("X:/r/graphify-out/graph.json"))


class RunStateTests(unittest.TestCase):
    def _patched_run(self, script: str):
        # isolate RunState semantics from the (separately tested) view pipeline:
        # a successful update hands off to build_views_for, stubbed 'ready' here
        orig = bridge.build_command
        orig_views = bridge.build_views_for
        bridge.build_command = lambda repo: [sys.executable, "-c", script]
        bridge.build_views_for = lambda pid, repo, log=None: {"status": "ready", "nodes": 1}
        try:
            rs = bridge.RunState()
            with tempfile.TemporaryDirectory() as d:
                repo = Path(os.path.realpath(d))
                ok, msg = rs.start("p1", repo)
                self.assertTrue(ok, msg)
                busy_ok, busy_msg = rs.start("p2", repo)   # one at a time
                self.assertFalse(busy_ok)
                self.assertIn("already running", busy_msg)
                for _ in range(100):
                    if rs.current["state"] in ("success", "error"):
                        break
                    time.sleep(0.1)
                return rs.current, repo
        finally:
            bridge.build_command = orig
            bridge.build_views_for = orig_views

    def test_exit_zero_without_proof_is_error_not_fake_success(self):
        cur, _ = self._patched_run("print('done')")
        self.assertEqual(cur["state"], "error")
        self.assertIn("produced no graph.json", cur["error"])

    def test_success_requires_real_proof_file(self):
        cur, _ = self._patched_run(
            "import os; os.makedirs('graphify-out', exist_ok=True);"
            "open('graphify-out/graph.json','w').write('{}'); print('built')")
        self.assertEqual(cur["state"], "success")
        self.assertTrue(cur["proof"]["graphJson"])

    def test_nonzero_exit_is_error(self):
        cur, _ = self._patched_run("import sys; sys.exit(3)")
        self.assertEqual(cur["state"], "error")
        self.assertEqual(cur["exitCode"], 3)


class HttpSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from http.server import ThreadingHTTPServer
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), bridge.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def _get(self, path):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def _post(self, path, payload):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}",
                                     data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_status_endpoint(self):
        code, j = self._get("/api/bridge/status")
        self.assertEqual(code, 200)
        self.assertEqual(j["bridge"], "graphify-dashboard-bridge")

    def test_generate_rejects_bad_paths_with_400(self):
        for bad in ("not-absolute", "C:\\no\\such\\dir\\xyz987", "C:\\x; rm -rf /"):
            code, j = self._post("/api/graphify/generate", {"projectId": "t", "repoPath": bad})
            self.assertEqual(code, 400, bad)
            self.assertIn("error", j)

    def test_unknown_endpoints_404(self):
        code, j = self._post("/api/shell/run", {"cmd": "whoami"})
        self.assertEqual(code, 404)
        self.assertIn("allowlists", j["error"])   # wording covers the G5P.4 scan endpoint too
        code, _ = self._get("/api/anything")
        self.assertEqual(code, 404)


if __name__ == "__main__":
    unittest.main()


class ProjectIdSanitizationTests(unittest.TestCase):
    def test_valid_ids_pass(self):
        for ok in ("workbench", "local-test-app", "a", "x" * 40, "a1-b2"):
            self.assertEqual(bridge.sanitize_project_id(ok), ok)

    def test_traversal_and_junk_rejected(self):
        for bad in ("../x", "a/b", "a\\b", "..", ".git", "A", "x y", "x" * 41,
                    "-leading", "", None, "x;rm", "x$(id)"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                bridge.sanitize_project_id(bad)


class ScanProjectTests(unittest.TestCase):
    def setUp(self):
        self._orig_projects = bridge.PROJECTS_DIR
        self._tmp = tempfile.TemporaryDirectory()
        bridge.PROJECTS_DIR = Path(self._tmp.name) / "projects"

    def tearDown(self):
        bridge.PROJECTS_DIR = self._orig_projects
        self._tmp.cleanup()

    def test_bad_id_and_bad_path(self):
        self.assertEqual(bridge.scan_project("../etc", None)["status"], "error")
        with tempfile.TemporaryDirectory():
            r = bridge.scan_project("ok-id", "C:\\no\\such\\dir\\xyz")
            self.assertEqual(r["status"], "invalid_path")

    def test_no_output(self):
        with tempfile.TemporaryDirectory() as repo:
            self.assertEqual(bridge.scan_project("p1", repo)["status"], "no_output")

    def test_graph_without_views_is_pending(self):
        with tempfile.TemporaryDirectory() as repo:
            g = Path(repo) / "graphify-out"
            g.mkdir()
            (g / "graph.json").write_text("{}", encoding="utf-8")
            r = bridge.scan_project("p1", repo)
            self.assertEqual(r["status"], "generated_pending_reload")

    def test_ready_requires_view_files_no_fake_ready(self):
        with tempfile.TemporaryDirectory() as repo:
            pdir = bridge.PROJECTS_DIR / "p1"
            pdir.mkdir(parents=True)
            (pdir / "manifest.json").write_text(json.dumps(
                {"status": "ready", "nodes": 3, "edges": 2, "viewsBase": "/projects/p1/",
                 "generatorContract": bridge.GENERATOR_CONTRACT}), encoding="utf-8")
            # manifest says ready but the view files are MISSING -> views_missing (G5P.5), not ready
            r = bridge.scan_project("p1", repo)
            self.assertEqual(r["status"], "views_missing")
            for f in ("read-model.json", "brain-3d-prototype.html", "graph-explorer.html"):
                (pdir / f).write_text("x", encoding="utf-8")
            r2 = bridge.scan_project("p1", repo)
            self.assertEqual(r2["status"], "ready")
            self.assertEqual(r2["nodes"], 3)   # counts come from the real manifest

    def test_corrupt_manifest_is_incompatible(self):
        pdir = bridge.PROJECTS_DIR / "p1"
        pdir.mkdir(parents=True)
        (pdir / "manifest.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(bridge.scan_project("p1", None)["status"], "generated_incompatible")


class BuildViewsTests(unittest.TestCase):
    def setUp(self):
        self._orig_projects = bridge.PROJECTS_DIR
        self._tmp = tempfile.TemporaryDirectory()
        bridge.PROJECTS_DIR = Path(self._tmp.name) / "projects"

    def tearDown(self):
        bridge.PROJECTS_DIR = self._orig_projects
        self._tmp.cleanup()

    def test_corrupt_graph_is_incompatible_with_reason(self):
        with tempfile.TemporaryDirectory() as repo:
            g = Path(repo) / "graphify-out"
            g.mkdir()
            (g / "graph.json").write_text("{definitely not json", encoding="utf-8")
            m = bridge.build_views_for("p1", Path(os.path.realpath(repo)))
            self.assertEqual(m["status"], "generated_incompatible")
            self.assertIn("read-model", m["reason"])
            # manifest persisted so the scan reports the same honest state
            self.assertEqual(bridge.scan_project("p1", repo)["status"], "generated_incompatible")

    def test_full_pipeline_on_fixture_graph(self):
        fixture = REPO_ROOT / "tests" / "fixtures" / "graphify_hivemind_sample_graph.json"
        with tempfile.TemporaryDirectory() as repo:
            g = Path(repo) / "graphify-out"
            g.mkdir()
            (g / "graph.json").write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
            m = bridge.build_views_for("fixture-proj", Path(os.path.realpath(repo)))
            self.assertEqual(m["status"], "ready", m.get("reason"))
            self.assertTrue(m["nodes"] and m["edges"] is not None)
            pdir = bridge.PROJECTS_DIR / "fixture-proj"
            for f in ("read-model.json", "brain-3d-prototype.html", "graph-explorer.html", "manifest.json"):
                self.assertTrue((pdir / f).exists(), f)
            self.assertEqual(bridge.scan_project("fixture-proj", repo)["status"], "ready")


class GenericRepoFallbackTests(unittest.TestCase):
    """The shipped default taxonomy is generic for every repo -- the read model
    emits honest generic structure (file-kind concepts + directory slices)."""

    GENERIC_GRAPH = {
        "nodes": [
            {"id": "app", "label": "app.py", "file_type": "code", "source_file": "app.py"},
            {"id": "core", "label": "core.py", "file_type": "code", "source_file": "core.py"},
            {"id": "readme", "label": "README.md", "file_type": "doc", "source_file": "README.md"},
            {"id": "util", "label": "util.py", "file_type": "code", "source_file": "lib/util.py"},
        ],
        "links": [
            {"source": "app", "target": "core"},
            {"source": "app", "target": "util"},
        ],
    }

    def test_generic_fallback_emits_nodes(self):
        from graphify_hivemind_readmodel import build_read_model
        rm = build_read_model(self.GENERIC_GRAPH, repo_root="x", source_graph_path="y")
        self.assertEqual(rm["metadata"]["slice_mode"], "generic-structure")
        self.assertGreater(rm["metadata"]["emitted_nodes"], 0)
        labels = {s["label"] for s in rm["slices"]}
        self.assertIn("(root)", labels)            # flat files -> root slice
        self.assertIn("lib", labels)               # top-level dir slice
        concepts = {n["concept"] for n in rm["nodes"]}
        self.assertIn("backend", concepts)   # .py -> generic backend bucket
        self.assertIn("docs", concepts)

    def test_generic_pipeline_end_to_end(self):
        orig = bridge.PROJECTS_DIR
        tmp = tempfile.TemporaryDirectory()
        bridge.PROJECTS_DIR = Path(tmp.name) / "projects"
        try:
            with tempfile.TemporaryDirectory() as repo:
                g = Path(repo) / "graphify-out"
                g.mkdir()
                (g / "graph.json").write_text(json.dumps(self.GENERIC_GRAPH), encoding="utf-8")
                m = bridge.build_views_for("tiny-generic", Path(os.path.realpath(repo)))
                self.assertEqual(m["status"], "ready", m.get("reason"))
                self.assertGreater(m["nodes"], 0)
        finally:
            bridge.PROJECTS_DIR = orig
            tmp.cleanup()


class ViewPortabilityTests(unittest.TestCase):
    """G5P.4a (operator catch): per-project views live at /projects/<id>/ -- any
    RELATIVE asset/link path resolves a level too deep there. The atlas 404'd,
    the honest fallback kept default spheres, and the old glossy look returned.
    Emitted views must use absolute paths for shared assets/links."""

    def test_brain_generator_emits_absolute_shared_paths(self):
        gen = (REPO_ROOT / "scripts" / "graphify_brain3d.py").read_text(encoding="utf-8")
        self.assertIn("'/design/graphify-molten-cores-v4", gen)
        self.assertNotIn("'../design/", gen)
        self.assertIn('href="/views/graphify-dashboard.html"', gen)

    def test_default_emitted_view_has_no_relative_design_refs(self):
        out = REPO_ROOT / "graphify-out" / "views" / "brain-3d-prototype.html"
        if not out.exists():
            self.skipTest("generated view absent (ignored output)")
        h = out.read_text(encoding="utf-8")
        self.assertNotIn("../design/", h)
        self.assertIn("/design/graphify-molten-cores-v4", h)


class HardeningTests(unittest.TestCase):
    """G5P.5: staleness detection, cleanup sandboxing, relative path resolution."""

    def setUp(self):
        self._orig = bridge.PROJECTS_DIR
        self._tmp = tempfile.TemporaryDirectory()
        bridge.PROJECTS_DIR = Path(self._tmp.name) / "projects"

    def tearDown(self):
        bridge.PROJECTS_DIR = self._orig
        self._tmp.cleanup()

    def _ready_project(self, pid, repo, contract=None, graph_mtime=None):
        pdir = bridge.PROJECTS_DIR / pid
        pdir.mkdir(parents=True)
        for f in ("read-model.json", "brain-3d-prototype.html", "graph-explorer.html"):
            (pdir / f).write_text("x", encoding="utf-8")
        m = {"status": "ready", "nodes": 3, "edges": 2, "viewsBase": f"/projects/{pid}/",
             "generatorContract": contract if contract is not None else bridge.GENERATOR_CONTRACT}
        if graph_mtime is not None:
            m["graphMtime"] = graph_mtime
        (pdir / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
        return pdir

    def test_contract_mismatch_is_rebuild_required(self):
        with tempfile.TemporaryDirectory() as repo:
            self._ready_project("p1", repo, contract="old-contract")
            r = bridge.scan_project("p1", repo)
            self.assertEqual(r["status"], "rebuild_required")
            self.assertIn("older contract", r["reason"])

    def test_newer_graph_is_rebuild_required(self):
        with tempfile.TemporaryDirectory() as repo:
            g = Path(repo) / "graphify-out"
            g.mkdir()
            gp = g / "graph.json"
            gp.write_text("{}", encoding="utf-8")
            # manifest claims the graph was much older at build time
            self._ready_project("p1", repo, graph_mtime=gp.stat().st_mtime - 9999)
            r = bridge.scan_project("p1", repo)
            self.assertEqual(r["status"], "rebuild_required")
            self.assertIn("newer than the generated views", r["reason"])

    def test_current_everything_stays_ready(self):
        with tempfile.TemporaryDirectory() as repo:
            g = Path(repo) / "graphify-out"
            g.mkdir()
            gp = g / "graph.json"
            gp.write_text("{}", encoding="utf-8")
            self._ready_project("p1", repo, graph_mtime=gp.stat().st_mtime)
            self.assertEqual(bridge.scan_project("p1", repo)["status"], "ready")

    def test_cleanup_removes_only_project_dir(self):
        with tempfile.TemporaryDirectory() as repo:
            keep = self._ready_project("keep-me", repo)
            target = self._ready_project("clean-me", repo)
            outside = Path(self._tmp.name) / "outside.txt"
            outside.write_text("untouched", encoding="utf-8")
            r = bridge.clean_project_views("clean-me")
            self.assertTrue(r["cleaned"])
            self.assertFalse(target.exists())
            self.assertTrue(keep.exists())          # sibling untouched
            self.assertTrue(outside.exists())       # outside untouched
            # repo source untouched
            self.assertTrue(Path(repo).exists())

    def test_cleanup_rejects_bad_ids_and_missing(self):
        for bad in ("../escape", "a/b", "", "ALLCAPS"):
            with self.assertRaises(ValueError, msg=bad):
                bridge.clean_project_views(bad)
        r = bridge.clean_project_views("never-generated")
        self.assertFalse(r["cleaned"])

    def test_relative_path_resolves_against_dashboard_root_only(self):
        rp, kind = bridge.resolve_repo_path("apps/calfel")
        self.assertEqual(kind, "relative-resolved")
        self.assertTrue(str(rp).lower().endswith(os.path.join("apps", "calfel")))
        with self.assertRaises(ValueError):
            bridge.resolve_repo_path("definitely/not/a/real/subdir")

    def test_manifest_carries_hardened_fields(self):
        fixture = REPO_ROOT / "tests" / "fixtures" / "graphify_hivemind_sample_graph.json"
        with tempfile.TemporaryDirectory() as repo:
            g = Path(repo) / "graphify-out"
            g.mkdir()
            (g / "graph.json").write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
            m = bridge.build_views_for("hardened", Path(os.path.realpath(repo)))
            self.assertEqual(m["status"], "ready", m.get("reason"))
            for key in ("sanitizedId", "repoPath", "graphJsonPath", "readModelPath",
                        "view3dPath", "view2dPath", "graphMtime", "generatorContract",
                        "bridgeVersion", "generatedAt", "nodes", "edges", "concepts"):
                self.assertIn(key, m, key)
            self.assertEqual(m["generatorContract"], bridge.GENERATOR_CONTRACT)


class UrlImportTests(unittest.TestCase):
    """G5P.6a: repo-URL import (operator-requested). The URL is data with a
    strict GitHub-https allowlist; the clone dir is computed, never parsed
    from client input."""

    def test_valid_urls(self):
        for url in ("https://github.com/octocat/Hello-World",
                    "https://github.com/oWnEr-1/repo.name",
                    "https://github.com/a/b.git",
                    "https://github.com/a/b/"):
            u, owner, repo = bridge.validate_repo_url(url)
            self.assertTrue(u.startswith("https://github.com/"))
            self.assertNotIn(".git", u)

    def test_invalid_urls_refused(self):
        for bad in ("http://github.com/a/b",            # not https
                    "https://gitlab.com/a/b",            # not github
                    "https://github.com/a",              # no repo
                    "https://github.com/a/b/c",          # extra path
                    "https://github.com/a/b; rm -rf /",  # injection-ish
                    "git@github.com:a/b.git",            # ssh form
                    "", None, "ftp://x"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                bridge.validate_repo_url(bad)

    def test_clone_dir_is_computed_not_parsed(self):
        d = bridge.expected_clone_dir("octocat", "Hello-World")
        self.assertTrue(str(d).endswith(os.path.join(".graphify", "repos", "octocat", "Hello-World")))

    def test_import_endpoint_rejects_garbage(self):
        # uses the running HttpSurfaceTests server pattern inline
        from http.server import ThreadingHTTPServer
        srv = ThreadingHTTPServer(("127.0.0.1", 0), bridge.Handler)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            import urllib.request as ur, urllib.error as ue
            def post(payload):
                req = ur.Request(f"http://127.0.0.1:{port}/api/projects/import-url",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
                try:
                    with ur.urlopen(req, timeout=5) as r:
                        return r.status
                except ue.HTTPError as e:
                    return e.code
            self.assertEqual(post({"projectId": "x", "url": "https://evil.example/a/b"}), 400)
            self.assertEqual(post({"projectId": "../bad", "url": "https://github.com/a/b"}), 400)
        finally:
            srv.shutdown()


class ModeRoutingTests(unittest.TestCase):
    """Every project -- including the dashboard's own host repo -- builds in
    'auto' mode: generic by default, a custom taxonomy only if a local config
    supplies one and it covers the repo. No project-vocabulary leakage."""

    def test_host_repo_is_auto(self):
        self.assertEqual(bridge.readmodel_mode_for(bridge.DASHBOARD_ROOT), "auto")

    def test_foreign_path_is_auto(self):
        import tempfile
        from pathlib import Path as _P
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(bridge.readmodel_mode_for(_P(td)), "auto")


class CsrfDefenseTests(unittest.TestCase):
    """G5P.10: a malicious web page must not be able to drive the local bridge.
    The loopback PEER check passes for browser-issued cross-origin POSTs (the
    victim's browser connects from 127.0.0.1), so state-changing POSTs also
    require a same-origin Origin / Sec-Fetch-Site. Non-browser clients (no
    Origin header -- curl, these tests, the MCP selftest) stay allowed."""

    def setUp(self):
        from http.server import ThreadingHTTPServer
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), bridge.Handler)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()

    def _post(self, headers):
        import urllib.error as ue
        import urllib.request as ur
        req = ur.Request(f"http://127.0.0.1:{self.port}/api/projects/scan",
                         data=b'{"projects":[]}', headers=headers, method="POST")
        try:
            with ur.urlopen(req, timeout=5) as r:
                return r.status
        except ue.HTTPError as e:
            return e.code

    def test_cross_origin_post_refused(self):
        self.assertEqual(self._post({"Origin": "http://evil.com",
                                     "Content-Type": "application/json"}), 403)

    def test_cross_site_fetch_metadata_refused(self):
        self.assertEqual(self._post({"Sec-Fetch-Site": "cross-site",
                                     "Content-Type": "application/json"}), 403)

    def test_same_origin_post_allowed(self):
        self.assertEqual(self._post({"Origin": f"http://127.0.0.1:{self.port}",
                                     "Content-Type": "application/json"}), 200)

    def test_no_origin_client_allowed(self):
        # curl / the test suite / the MCP selftest send no Origin -> not blocked
        self.assertEqual(self._post({"Content-Type": "application/json"}), 200)
