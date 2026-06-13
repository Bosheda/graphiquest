"""Guard: the shipped/default GraphiQuest package must stay GENERIC.

Requirement (operator, G5Q.2a): fail if any shipped DEFAULT source file contains
public-facing, project-specific taxonomy vocabulary (Pepper / Director / War Room
/ DCLA / Workbench-runtime wording / apps/workbench). A maintainer's bespoke
taxonomy is allowed only through the gitignored local override
(graphiquest.taxonomy.local.json), never in shipped source.

Also asserts apps/workbench is untouched by this work (requirement #10).

Standard library unittest:
  python tests/test_graphify_package_clean.py
"""
from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# The files that constitute the shipped/published GraphiQuest package and define
# its DEFAULT behavior. Monorepo-only scripts (chat-proxy, asset-pipeline-*, the
# visual-proof generator, etc.) are NOT part of the package and are excluded.
SHIPPED_SOURCE = [
    "scripts/graphify_dashboard_mock.py",
    "scripts/graphify_brain3d.py",
    "scripts/graphify_hivemind_explorer.py",
    "scripts/graphify_hivemind_readmodel.py",
    "scripts/graphify_dashboard_bridge.py",
    "scripts/graphify_mcp_server.py",
    "scripts/graphify_taxonomy_config.py",
    "scripts/start_graphify_dashboard.py",
    "scripts/cleanup_graphify_processes.py",
    "scripts/install_graphify_hooks_safe.py",
    "graphify.projects.json",
    "graphiquest.taxonomy.example.json",
    "docs/GRAPHIQUEST_TAXONOMY.md",
]

# Project-specific taxonomy that must never appear in shipped/default source.
FORBIDDEN = [
    re.compile(r"\bpepper\b", re.I),
    re.compile(r"\bdirector\b", re.I),
    re.compile(r"war[\s.\-]?room", re.I),
    re.compile(r"\bDCLA\b"),
    re.compile(r"workbench", re.I),
    re.compile(r"apps/workbench", re.I),
]


class PackageCleanlinessTests(unittest.TestCase):
    def test_no_project_taxonomy_in_shipped_source(self) -> None:
        offenders = []
        for rel in SHIPPED_SOURCE:
            p = REPO_ROOT / rel
            if not p.is_file():
                continue
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                for rx in FORBIDDEN:
                    if rx.search(line):
                        offenders.append(f"{rel}:{i}: {line.strip()[:100]}")
        self.assertEqual(offenders, [], "project taxonomy leaked into shipped source:\n"
                         + "\n".join(offenders))

    def test_example_config_is_generic(self) -> None:
        # the shipped example config must demonstrate the schema with GENERIC
        # vocabulary only (no project names)
        txt = (REPO_ROOT / "graphiquest.taxonomy.example.json").read_text(encoding="utf-8")
        for rx in FORBIDDEN:
            self.assertIsNone(rx.search(txt), f"example config contains forbidden vocabulary: {rx.pattern}")

    def test_local_override_is_gitignored(self) -> None:
        # the optional local taxonomy must be gitignored so it can never ship
        r = subprocess.run(["git", "check-ignore", "graphiquest.taxonomy.local.json"],
                           cwd=str(REPO_ROOT), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0,
                         "graphiquest.taxonomy.local.json must be gitignored")

    def test_apps_workbench_untouched(self) -> None:
        # requirement #10: this work must not modify apps/workbench at all
        r = subprocess.run(["git", "diff", "HEAD", "--name-only", "--", "apps/workbench"],
                           cwd=str(REPO_ROOT), capture_output=True, text=True)
        self.assertEqual(r.stdout.strip(), "", "apps/workbench must remain untouched")


def _read_readme() -> str:
    # The GraphiQuest README is docs/GRAPHIFY_DASHBOARD_README.md in the monorepo
    # and the promoted root README.md in the standalone repo -- prefer the monorepo
    # path, fall back to root so the same tests pass in both layouts.
    for c in (REPO_ROOT / "docs" / "GRAPHIFY_DASHBOARD_README.md", REPO_ROOT / "README.md"):
        if c.is_file():
            return c.read_text(encoding="utf-8")
    return ""


class AttributionAndBrandingTests(unittest.TestCase):
    """G5Q.2b: GraphiQuest branding + honest Graphify attribution."""

    README = _read_readme()
    GEN = (REPO_ROOT / "scripts" / "graphify_dashboard_mock.py").read_text(encoding="utf-8")

    def test_readme_is_graphiquest_and_credits_graphify(self) -> None:
        self.assertIn("# GraphiQuest", self.README)
        self.assertIn("Built on Graphify", self.README)
        self.assertIn("safishamsi/graphify", self.README)
        self.assertIn("MIT", self.README)

    def test_third_party_licenses_exists_and_credits(self) -> None:
        p = REPO_ROOT / "THIRD_PARTY_LICENSES.md"
        self.assertTrue(p.is_file(), "THIRD_PARTY_LICENSES.md must exist")
        txt = p.read_text(encoding="utf-8")
        for needed in ("Graphify", "Safi Shamsi", "three.js", "3d-force-graph", "OFL"):
            self.assertIn(needed, txt, needed)

    def test_in_app_footer_credits_graphify(self) -> None:
        self.assertIn("Built on", self.GEN)
        self.assertIn("safishamsi/graphify", self.GEN)

    def test_does_not_claim_ownership_of_graphify(self) -> None:
        # never present Graphify as GraphiQuest's own work
        self.assertNotIn("our scanner", self.README.lower())
        self.assertNotIn("graphiquest scanner", self.README.lower())

    def test_attribution_boundary_is_explicit(self) -> None:
        # README must state the build-on relationship, the who-did-what split,
        # and that GraphiQuest is a SEPARATE project (not Graphify renamed).
        # Normalize away markdown punctuation + whitespace so wrapped/quoted
        # prose phrases still match (blockquote '>' and '*' sit between words).
        low = re.sub(r"[^a-z0-9]+", " ", self.README.lower())
        self.assertIn("built on top of", low)
        self.assertIn("separate project", low)
        self.assertIn("not graphify renamed", low)
        # the operator's required verb framing: Graphify scans/generates;
        # GraphiQuest visualizes, queries, audits, navigates.
        self.assertIn("graphify scans", low)
        for verb in ("visualizes", "queries", "audits", "navigates"):
            self.assertIn(verb, low)
        # THIRD_PARTY_LICENSES carries the same boundary
        tpl = re.sub(r"\s+", " ", (REPO_ROOT / "THIRD_PARTY_LICENSES.md").read_text(encoding="utf-8").lower())
        self.assertIn("separate project", tpl)
        # the in-app surface also states the boundary
        gen = re.sub(r"\s+", " ", self.GEN)
        self.assertIn("not Graphify renamed", gen)


class ConnectorHonestyTests(unittest.TestCase):
    """G5Q.2b: connector never shows a stale LIVE from a prior session, and
    never claims 'connected' without verification."""

    GEN = (REPO_ROOT / "scripts" / "graphify_dashboard_mock.py").read_text(encoding="utf-8")

    def test_live_is_current_session_scoped(self) -> None:
        # the LIVE LED must read a CURRENT-SESSION marker (sessionStorage), so a
        # fresh browser cannot show a stale LIVE carried over in localStorage.
        self.assertIn("graphify-cc-live-session", self.GEN)
        self.assertIn("sessionStorage.getItem('graphify-cc-live-session')", self.GEN)

    def test_live_cache_is_clearable(self) -> None:
        # the legacy localStorage LIVE cache is in MEM_KEYS so "Clear ALL" wipes it
        self.assertIn("graphify-claudecode-live-v1", self.GEN)

    def test_no_false_connected_claim(self) -> None:
        # the honesty rule must be present; 'connected' is never claimed
        self.assertIn("never claimed", self.GEN)


class EmptyDefaultProjectTests(unittest.TestCase):
    """G5Q.2b: a clean first run has no baked default project and shows an
    honest 'add your first project' state."""

    def test_no_default_project_in_registry(self) -> None:
        reg = json.loads((REPO_ROOT / "graphify.projects.json").read_text(encoding="utf-8"))
        self.assertEqual(reg.get("projects"), [], "registry must ship empty (no default project)")

    def test_clean_first_run_state_exists(self) -> None:
        gen = (REPO_ROOT / "scripts" / "graphify_dashboard_mock.py").read_text(encoding="utf-8")
        self.assertIn("Add your first project", gen)
        # the empty-state must point Ask/Hunter/Reports/Savings at loading a graph
        self.assertIn("activate once a graph is loaded", gen)


if __name__ == "__main__":
    unittest.main(verbosity=2)
