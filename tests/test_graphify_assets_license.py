"""G5Q.1c: MIT LICENSE + required-asset gate guards.

Locks in: a real MIT LICENSE at repo root; the EXACT 11 required design assets
are tracked under graphify_assets/design/ and nothing else (no test junk / old
attempts / unused palettes / cells / contact sheets); the asset manifest
references only existing files; views reference absolute and ../design paths
that the seed serves; graphify-out/ (generated views + projects) stays ignored.
"""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LICENSE = REPO / "LICENSE"
ASSET_DIR = REPO / "graphify_assets" / "design"
MANIFEST = REPO / "docs" / "GRAPHIFY_ASSET_MANIFEST.md"

# the exact runtime-required set (grill-verified complete + minimal, G5Q.1c)
REQUIRED = sorted([
    "agentic-os-visual-system/proofs-v4/proof_v4_hivemind_viewport_backing_i2i_seed309104.png",
    "graphify-ui-materials/graphiquest_logo_mark_seed711002c.png",
    "graphify-molten-cores-v4/molten_core_atlas_v4.png",
    "graphify-molten-cores-v4/molten_core_atlas_v4_obsidian.png",
    "graphify-molten-cores-v4/molten_core_atlas_v4_forge.png",
    "graphify-molten-cores-v4/molten_core_atlas_v4_ice.png",
    "graphify-molten-cores-v4/molten_core_atlas_v4_royal.png",
    "graphify-molten-cores-v4/molten_core_atlas_v4_enterprise.png",
    "graphify-molten-cores-v4/molten_core_atlas_v4_access.png",
    "graphify-molten-cores-v4/molten_core_atlas_v4_space.png",
    "graphify-molten-cores-v4/molten_core_atlas_v4_solar.png",
])
# things that MUST NOT be committed (dev junk / build-only)
FORBIDDEN_SUBSTRINGS = ("_cool", "_contrast", "contact-sheet", "GENERATION_LOG",
                        "/cells/", "molten_core_atlas.png", "_v2", "_v3",
                        "_qa_crop", "MANIFEST.md", "proofs/", "proofs-v2",
                        "proofs-v3", "guides/")


class LicenseTests(unittest.TestCase):
    def test_license_exists(self):
        self.assertTrue(LICENSE.is_file(), "repo-root LICENSE missing")

    def test_license_is_mit(self):
        t = LICENSE.read_text(encoding="utf-8")
        self.assertIn("MIT License", t)
        self.assertIn("Permission is hereby granted, free of charge", t)
        self.assertIn("THE SOFTWARE IS PROVIDED \"AS IS\"", t)
        # holder differs between the monorepo and the standalone GraphiQuest repo;
        # accept either rather than hardcoding one layout.
        self.assertRegex(t, r"Copyright \(c\) 2026 (DaForgeLayer-AI|GraphiQuest) contributors")

    def test_license_is_tracked(self):
        out = subprocess.run(["git", "ls-files", "LICENSE"], cwd=REPO,
                             capture_output=True, text=True)
        self.assertIn("LICENSE", out.stdout, "LICENSE must be tracked by git")


class AssetGateTests(unittest.TestCase):
    def _present(self):
        return sorted(str(p.relative_to(ASSET_DIR)).replace("\\", "/")
                      for p in ASSET_DIR.rglob("*") if p.is_file())

    def test_required_assets_present(self):
        self.assertTrue(ASSET_DIR.is_dir(), "graphify_assets/design missing")
        for rel in REQUIRED:
            self.assertTrue((ASSET_DIR / rel).is_file(), rel)

    def test_asset_set_is_exactly_the_required_11_minimal(self):
        # operator rule: ship NOTHING the dashboard does not use right now
        self.assertEqual(self._present(), REQUIRED)

    def test_no_dev_junk_committed(self):
        present = "\n".join(self._present())
        for bad in FORBIDDEN_SUBSTRINGS:
            self.assertNotIn(bad, present, f"dev junk leaked into the asset gate: {bad}")

    def test_assets_are_tracked_or_staged(self):
        # every required asset must be tracked (committed) or staged for commit
        tracked = subprocess.run(["git", "ls-files", "graphify_assets/design"],
                                 cwd=REPO, capture_output=True, text=True).stdout
        staged = subprocess.run(["git", "diff", "--cached", "--name-only",
                                 "graphify_assets/design"], cwd=REPO,
                                capture_output=True, text=True).stdout
        seen = tracked + staged
        for rel in REQUIRED:
            self.assertTrue(rel in seen.replace("\\", "/"),
                            f"{rel} is neither tracked nor staged")


class ManifestTests(unittest.TestCase):
    def test_manifest_exists_and_lists_required(self):
        self.assertTrue(MANIFEST.is_file())
        t = MANIFEST.read_text(encoding="utf-8")
        for rel in REQUIRED:
            self.assertIn(rel, t, f"manifest must document {rel}")

    def test_manifest_references_only_existing_files(self):
        import re
        t = MANIFEST.read_text(encoding="utf-8")
        for m in re.findall(r"`([A-Za-z0-9_\-./]+\.png)`", t):
            # only assertion targets under the tracked asset dir layout
            if m.startswith(("agentic-os", "graphify-")):
                self.assertTrue((ASSET_DIR / m).is_file(), f"manifest names a missing file: {m}")


class GeneratedOutputsStayIgnoredTests(unittest.TestCase):
    def test_generated_views_and_projects_ignored(self):
        for p in ("graphify-out/views/graphify-dashboard.html",
                  "graphify-out/projects/local-graphify/read-model.json",
                  "graphify-out/graph.json"):
            r = subprocess.run(["git", "check-ignore", p], cwd=REPO,
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{p} must stay gitignored")

    def test_tracked_assets_not_ignored(self):
        r = subprocess.run(
            ["git", "check-ignore",
             "graphify_assets/design/graphify-molten-cores-v4/molten_core_atlas_v4_obsidian.png"],
            cwd=REPO, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0, "tracked assets must NOT be ignored")


class SeedFunctionTests(unittest.TestCase):
    def test_seed_copies_only_missing(self):
        import sys
        import tempfile
        sys.path.insert(0, str(REPO / "scripts"))
        import graphify_dashboard_bridge as bridge
        orig = bridge.STATIC_ROOT
        try:
            with tempfile.TemporaryDirectory() as td:
                bridge.STATIC_ROOT = Path(td)
                n1 = bridge.seed_design_assets()
                self.assertEqual(n1, len(REQUIRED))           # all seeded first time
                n2 = bridge.seed_design_assets()
                self.assertEqual(n2, 0)                        # idempotent: nothing re-copied
                got = sorted(str(p.relative_to(Path(td) / "design")).replace("\\", "/")
                             for p in (Path(td) / "design").rglob("*") if p.is_file())
                self.assertEqual(got, REQUIRED)
        finally:
            bridge.STATIC_ROOT = orig


if __name__ == "__main__":
    unittest.main()
