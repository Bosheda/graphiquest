"""Tests for the G5Q.1 packaging/docs foundation.

Honesty contract: the README's command examples reference scripts that exist;
no doc claims connector execution or remote import is live; apps/workbench
appears only as a future/possible-source mention; the start script is safe
(foreground, no shell=True, loopback); generated outputs stay ignored.

Standard library unittest:
  python tests/test_graphify_docs_packaging.py
"""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# GraphiQuest README: docs/GRAPHIFY_DASHBOARD_README.md in the monorepo, promoted
# to root README.md in the standalone repo -- prefer the monorepo path.
README = next((c for c in (REPO_ROOT / "docs" / "GRAPHIFY_DASHBOARD_README.md",
                           REPO_ROOT / "README.md") if c.is_file()),
              REPO_ROOT / "docs" / "GRAPHIFY_DASHBOARD_README.md")
START = REPO_ROOT / "scripts" / "start_graphify_dashboard.py"
TEXT = README.read_text(encoding="utf-8")


class ReadmeTests(unittest.TestCase):
    def test_required_sections_present(self):
        for heading in ("What this is", "What this is not", "Current status",
                        "Requirements", "Quick start", "Manual fallback",
                        "Project registry", "Generated outputs", "Safety model",
                        "Troubleshooting", "Using it with Claude Code", "Credits",
                        "Roadmap"):
            self.assertIn(heading, TEXT, heading)

    def test_referenced_scripts_exist(self):
        refs = set(re.findall(r"scripts/([A-Za-z0-9_]+\.py)", TEXT))
        self.assertGreaterEqual(len(refs), 3)
        for name in refs:
            self.assertTrue((REPO_ROOT / "scripts" / name).is_file(), name)

    def test_no_false_live_claims(self):
        # the connector must be described as gated/planned, never executing
        self.assertIn("never makes a call", TEXT)
        self.assertIn("gated", TEXT.lower())
        low = TEXT.lower()
        self.assertNotIn("connector is connected", low)
        # G5P.6a: URL import is REAL (operator-requested) -- the README must be
        # honest that it is the ONE network flow, github-https only
        self.assertIn("graphify clone", TEXT)
        self.assertIn("ONE network flow", TEXT)   # single-line phrase (others wrap)
        self.assertIn("GitHub-https only", TEXT)

    def test_workbench_mentions_are_future_or_negative_only(self):
        for line in TEXT.splitlines():
            if "workbench" in line.lower():
                self.assertTrue(
                    re.search(r"future|never|not |refus|possible|DaForgeLayer Workbench", line, re.I),
                    f"workbench mention without future/negative/project-name framing: {line!r}")

    def test_registry_file_link_target_exists(self):
        self.assertTrue((REPO_ROOT / "graphify.projects.json").is_file())


class StartScriptTests(unittest.TestCase):
    SRC = START.read_text(encoding="utf-8")

    def test_exists_and_compiles(self):
        compile(self.SRC, str(START), "exec")

    def test_safety_markers(self):
        self.assertIn("FOREGROUND", self.SRC)            # no orphan processes
        self.assertNotIn("shell=True", self.SRC)         # never a shell
        self.assertNotIn("Popen", self.SRC)              # no detaching
        self.assertIn("Ctrl+C", self.SRC)
        self.assertIn("127.0.0.1", self.SRC)             # loopback wording
        # code-only check: the docstring's "never touches apps/workbench" is the
        # safety claim itself; the CODE must not reference the path
        code_only = re.sub(r'""".*?"""', "", self.SRC, flags=re.S)
        self.assertNotIn("apps/workbench", code_only)

    def test_help_runs(self):
        import sys
        r = subprocess.run([sys.executable, str(START), "--help"],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0)


class IgnoredOutputsTests(unittest.TestCase):
    def test_generated_outputs_stay_ignored(self):
        r = subprocess.run(["git", "check-ignore", "graphify-out/views/graphify-dashboard.html",
                            "graphify-out/projects/x/manifest.json"],
                           capture_output=True, text=True, cwd=str(REPO_ROOT))
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()


class HowToHonestyTests(unittest.TestCase):
    """Refute-lane coverage gap: the in-dashboard How-To lives in the generator
    source -- stale claims there must fail tests, not wait for operators."""

    GEN = (REPO_ROOT / "scripts" / "graphify_dashboard_mock.py").read_text(encoding="utf-8")

    def test_no_stale_mission_jargon_or_false_claims(self):
        self.assertNotIn("lands in G5P.2", self.GEN)            # shipped; jargon
        self.assertNotIn("No network, no agents", self.GEN)     # CDN exception exists
        self.assertNotIn("Repo import/switching", self.GEN)     # switching IS built

    def test_start_script_chain_is_complete(self):
        src = START.read_text(encoding="utf-8")
        # fresh-clone chain: read-model builder must be part of generation
        self.assertIn("graphify_hivemind_readmodel.py", src)
        self.assertIn("GRAPH_JSON", src)                        # graph gate, not read-model dead-loop
        self.assertIn("pipx install graphifyy", src)            # uv alternative
        for f in ("brain-3d-prototype.html", "graph-explorer.html", "graphify-dashboard.html"):
            self.assertIn(f, src)                               # all views checked, not just one


class G5P10HonestyTests(unittest.TestCase):
    """G5P.10 release-blocker honesty guards: no false open-source claim while
    the project has no LICENSE; the network story names BOTH exceptions; the
    optional tkinter dependency is documented."""

    def test_license_is_mit_and_not_blocked(self):
        # G5Q.1c: operator chose MIT -- the old "not yet licensed / blocked"
        # wording must be GONE and the README must point at the MIT LICENSE.
        self.assertNotIn("Not yet licensed", TEXT)
        self.assertNotIn("no LICENSE file yet", TEXT)
        self.assertNotIn("open-source claim blocked", TEXT.lower().replace(" ", "-"))
        self.assertIn("MIT License", TEXT)

    def test_network_story_includes_cdn_exception(self):
        # the old absolute 'nothing else ever touches the network' was false
        self.assertNotIn("nothing else", TEXT.split("## What this is not", 1)[-1].split("## Current status", 1)[0])
        self.assertIn("first paint", TEXT.lower())

    def test_tkinter_documented_optional(self):
        low = TEXT.lower()
        self.assertIn("tkinter", low)
        self.assertIn("python3-tk", low)
