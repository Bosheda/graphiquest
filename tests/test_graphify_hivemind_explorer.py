"""Tests for scripts/graphify_hivemind_explorer.py (Mission G3).

Builds the read model IN MEMORY from the committed G2 graph fixture (no extra fixture,
no big graph), then validates the generated explorer HTML. Standard library unittest:
  python tests/test_graphify_hivemind_explorer.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# Test the SHIPPED default taxonomy regardless of any local override a developer
# may have on this machine -- pin the config to a path that does not exist.
os.environ["GRAPHIQUEST_TAXONOMY_CONFIG"] = str(REPO_ROOT / "tests" / "_no_local_taxonomy.json")

from graphify_hivemind_readmodel import build_read_model, load_graph  # noqa: E402
from graphify_hivemind_explorer import render_html, write_explorer  # noqa: E402

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "graphify_hivemind_sample_graph.json"
FIXED_TIME = "2026-06-09T00:00:00+00:00"

# Generic directory slices the synthetic fixture produces (no project vocabulary).
SLICE_IDS = ["dir-src", "dir-docs", "dir-tests", "dir-data"]


def _model() -> dict:
    graph = load_graph(FIXTURE)
    return build_read_model(graph, repo_root="fixture", source_graph_path=str(FIXTURE),
                            max_per_slice=10, generated_at=FIXED_TIME)


class TestExplorerGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = _model()
        cls.html = render_html(cls.model, FIXED_TIME)

    def test_output_written_to_requested_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "views" / "graph-explorer.html"
            written = write_explorer(self.model, out, FIXED_TIME)
            self.assertTrue(written.exists())
            self.assertEqual(written, out)
            self.assertGreater(out.stat().st_size, 10_000)

    def test_data_embedded(self) -> None:
        self.assertIn('id="data" type="application/json"', self.html)
        self.assertIn('"graph_built_at_commit":"fixture0001"', self.html)

    def test_all_slices_present(self) -> None:
        for sid in SLICE_IDS:
            self.assertIn(sid, self.html, f"slice {sid} missing")

    def test_search_ui_exists(self) -> None:
        self.assertIn('id="q"', self.html)
        self.assertIn('data-m="label"', self.html)
        self.assertIn('data-m="path"', self.html)
        self.assertIn('data-m="concept"', self.html)

    def test_inspector_ui_exists(self) -> None:
        self.assertIn("Node inspector", self.html)
        self.assertIn("1-hop", self.html)
        self.assertIn("2-hop", self.html)
        self.assertIn("Copy file path", self.html)

    def test_shortest_path_ui_exists(self) -> None:
        self.assertIn('id="src"', self.html)
        self.assertIn('id="dst"', self.html)
        self.assertIn('id="traceBtn"', self.html)
        self.assertIn("No path exists", self.html)

    def test_filters_ui_exists(self) -> None:
        self.assertIn('id="hideTests"', self.html)
        self.assertIn('id="hideGen"', self.html)
        self.assertIn('id="hideLow"', self.html)
        self.assertIn('id="concepts"', self.html)

    def test_warnings_rendered(self) -> None:
        self.assertIn("Graphify first, repo truth second", self.html)
        self.assertIn("Runtime truth is NOT inferred", self.html)
        # standing warnings from the read model itself are embedded in the data blob
        self.assertIn("first-pass structural memory", self.html)
        self.assertIn("semantic layer", self.html.lower())

    def test_metadata_rendered(self) -> None:
        self.assertIn("graph_build_mode", self.html)
        self.assertIn("built_at_commit", self.html)

    def test_no_cdn_or_external_refs(self) -> None:
        srcs = re.findall(r'(?:src|href)\s*=\s*["\']([^"\']+)', self.html)
        external = [s for s in srcs if s.startswith(("http://", "https://", "//"))]
        self.assertEqual(external, [], f"external refs found: {external}")

    def test_deterministic(self) -> None:
        again = render_html(_model(), FIXED_TIME)
        self.assertEqual(self.html, again)

    def test_generated_at_stamp(self) -> None:
        self.assertIn(FIXED_TIME, self.html)


class TestOutputPathIgnorable(unittest.TestCase):
    def test_default_output_under_graphify_out(self) -> None:
        from graphify_hivemind_explorer import DEFAULT_OUT, DEFAULT_READ_MODEL
        self.assertEqual(DEFAULT_OUT.parts[0], "graphify-out")
        self.assertEqual(DEFAULT_READ_MODEL.parts[0], "graphify-out")


class TestG3bPolish(unittest.TestCase):
    """Mission G3b operator-grade polish markers."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.html = render_html(_model(), FIXED_TIME)

    def test_preset_ui_exists(self) -> None:
        self.assertIn('id="presets"', self.html)
        # presets are generic + data-driven: a single Overview plus per-slice
        # buttons built at runtime from the read model. No project vocabulary.
        self.assertIn("Overview", self.html)
        self.assertIn("buildGenericPresets", self.html)

    def test_no_project_taxonomy_in_view(self) -> None:
        # the shipped explorer must not bake any project-specific taxonomy
        for forbidden in ("Pepper", "Director", "War Room", "DCLA",
                          "Workbench", "apps/workbench"):
            self.assertNotIn(forbidden, self.html, f"leaked taxonomy: {forbidden}")

    def test_mission_mode_panel(self) -> None:
        self.assertIn("Mission Mode", self.html)
        self.assertIn("Start with Graphify", self.html)
        self.assertIn("Repo truth required", self.html)

    def test_copyable_prompt_snippet(self) -> None:
        self.assertIn("Use Graphify first for structural context, then verify "
                      "load-bearing claims with Read/Grep before editing.", self.html)
        self.assertIn('id="copySnippet"', self.html)

    def test_trace_ux_path_length_and_copy(self) -> None:
        self.assertIn("path length", self.html)
        self.assertIn('id="copyPath"', self.html)
        self.assertIn("No path exists", self.html)           # no-path wording kept
        self.assertIn("whole read model", self.html)          # fallback labeling

    def test_inspector_grouped_connections_and_reminder(self) -> None:
        self.assertIn("conn-group", self.html)
        self.assertIn("repo-truth verify", self.html)
        self.assertIn("nodeKind", self.html)

    def test_density_controls(self) -> None:
        for marker in ('id="labelDensity"', 'id="edgesOn"', 'id="maxNodes"',
                       'id="hideDocs"', 'id="hideTests"', 'id="hideGen"', 'id="hideLow"'):
            self.assertIn(marker, self.html, f"{marker} missing")

    def test_share_controls(self) -> None:
        self.assertIn('id="copyView"', self.html)
        self.assertIn('id="copyNodes"', self.html)

    def test_staleness_status_fields(self) -> None:
        self.assertIn("semantic layer: ABSENT", self.html)
        self.assertIn("generated_at", self.html)
        self.assertIn("built_at_commit", self.html)
        self.assertIn("source:", self.html)

    def test_not_runtime_truth_banner(self) -> None:
        self.assertIn("NOT RUNTIME TRUTH", self.html)

    def test_still_no_cdn(self) -> None:
        srcs = re.findall(r'(?:src|href)\s*=\s*["\']([^"\']+)', self.html)
        external = [s for s in srcs if s.startswith(("http://", "https://", "//"))]
        self.assertEqual(external, [])

    def test_still_deterministic(self) -> None:
        self.assertEqual(self.html, render_html(_model(), FIXED_TIME))


class TestG3cBrainMode(unittest.TestCase):
    """Mission G3c Brain Mode markers (generic, data-driven regions)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.html = render_html(_model(), FIXED_TIME)

    def test_mode_toggle_exists(self) -> None:
        self.assertIn('id="modeBrain"', self.html)
        self.assertIn('id="modeGraph"', self.html)
        self.assertIn("Brain Mode", self.html)
        self.assertIn("Structural Graph Mode", self.html)

    def test_regions_are_generic_and_data_driven(self) -> None:
        # regions are built at runtime from the read model's directories/concepts
        # or an optional local config -- no project anatomy baked in the template.
        self.assertIn("buildGenericRegions", self.html)
        self.assertIn("REGION_POS", self.html)
        self.assertIn("other directories", self.html)

    def test_region_mapping_is_generic(self) -> None:
        # generic-structure repos route by top-level directory; otherwise by concept
        self.assertIn("if(GENERIC2D)", self.html)
        self.assertIn("region_routes", self.html)

    def test_disconnected_explanation_renders(self) -> None:
        self.assertIn("Disconnected does not automatically mean broken", self.html)
        self.assertIn("orphaned source file", self.html)
        self.assertIn("Graphify first, then repo Read/Grep", self.html)

    def test_loose_review_queue_renders(self) -> None:
        self.assertIn('id="looseQueue"', self.html)
        self.assertIn("Copy review list", self.html)
        self.assertIn("suspicious candidate", self.html)
        self.assertIn("likely normal", self.html)

    def test_connectedness_summary_renders(self) -> None:
        self.assertIn('id="connSummary"', self.html)
        self.assertIn("connected components", self.html)
        self.assertIn("isolated", self.html)

    def test_whole_brain_overview_preset(self) -> None:
        self.assertIn("Whole Brain Overview", self.html)

    def test_brain_warning_no_runtime_truth_claim(self) -> None:
        self.assertIn("Brain Mode is a metaphorical structural map. It is not runtime "
                      "truth. Disconnected nodes are review signals, not automatic defects.",
                      self.html)
        self.assertIn("runtime-live is NOT inferred", self.html)
        self.assertIn("NOT RUNTIME TRUTH", self.html)

    def test_structural_mode_preserved(self) -> None:
        # G3/G3b markers still present
        for marker in ('id="q"', "Node inspector", 'id="traceBtn"', 'id="presets"',
                       "Mission Mode", 'id="copyView"'):
            self.assertIn(marker, self.html)

    def test_still_no_cdn(self) -> None:
        srcs = re.findall(r'(?:src|href)\s*=\s*["\']([^"\']+)', self.html)
        self.assertEqual([s for s in srcs if s.startswith(("http://", "https://", "//"))], [])

    def test_still_deterministic(self) -> None:
        self.assertEqual(self.html, render_html(_model(), FIXED_TIME))


if __name__ == "__main__":
    unittest.main(verbosity=2)
