"""Tests for scripts/graphify_hivemind_readmodel.py (Mission G2).

The shipped package classifies every repo with a GENERIC, repo-agnostic taxonomy
(file-kind / location concepts + top-level-directory slices). These tests run
against the tiny committed SYNTHETIC fixture (a generic web-app shape -- no
project-specific paths). A local-config override is exercised separately.

Standard library unittest; run directly:
  python tests/test_graphify_hivemind_readmodel.py
"""
from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# Test the SHIPPED default taxonomy regardless of any local override a developer
# may have on this machine. LocalOverrideTests sets its own temp config and
# restores back to this sentinel (a path that does not exist -> generic).
_NO_LOCAL = str(REPO_ROOT / "tests" / "_no_local_taxonomy.json")
os.environ["GRAPHIQUEST_TAXONOMY_CONFIG"] = _NO_LOCAL

from graphify_hivemind_readmodel import (  # noqa: E402
    build_generic_slices,
    build_read_model,
    classify_node,
    generic_concept,
    load_graph,
    should_hide_node,
    shortest_path,
    _build_index,
)

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "graphify_hivemind_sample_graph.json"


class TestGenericClassification(unittest.TestCase):
    """The shipped default: file-kind/location buckets, repo-agnostic."""

    def test_frontend(self) -> None:
        self.assertEqual(generic_concept("src/components/Button.jsx", "x"), "frontend")
        self.assertEqual(generic_concept("src/styles/main.css", "x"), "frontend")

    def test_backend(self) -> None:
        self.assertEqual(generic_concept("src/api/server.js", "x"), "backend")
        self.assertEqual(generic_concept("src/services/auth.js", "x"), "backend")
        self.assertEqual(generic_concept("src/models/user.py", "x"), "backend")

    def test_scripts(self) -> None:
        self.assertEqual(generic_concept("scripts/build.sh", "x"), "scripts")

    def test_tests(self) -> None:
        self.assertEqual(generic_concept("tests/auth.test.js", "x"), "tests")
        self.assertEqual(generic_concept("src/components/Button.test.jsx", "x"), "tests")

    def test_docs(self) -> None:
        self.assertEqual(generic_concept("docs/README.md", "x"), "docs")

    def test_config(self) -> None:
        self.assertEqual(generic_concept("package.json", "x"), "config")
        self.assertEqual(generic_concept("tsconfig.json", "x"), "config")

    def test_data(self) -> None:
        self.assertEqual(generic_concept("data/seed.sql", "x"), "data")

    def test_assets(self) -> None:
        self.assertEqual(generic_concept("public/logo.png", "x"), "assets")

    def test_workflows(self) -> None:
        self.assertEqual(generic_concept(".github/workflows/ci.yml", "x"), "workflows")

    def test_other(self) -> None:
        self.assertEqual(generic_concept("misc/notes.bin", "x"), "other")

    def test_no_project_vocabulary(self) -> None:
        # Sanity: classify never invents project-specific concepts.
        bucket = generic_concept("apps/whatever/app/components/Thing.tsx", "x")
        self.assertIn(bucket, {"frontend", "backend", "tests", "config", "docs",
                               "scripts", "assets", "data", "workflows", "other"})

    def test_classify_node_is_empty_by_default(self) -> None:
        # No local config -> CONCEPT_RULES empty -> everything is 'unknown' here,
        # then build_read_model reclassifies generically.
        self.assertEqual(classify_node("src/components/Button.jsx", "x"), "unknown")


class TestNoiseFilters(unittest.TestCase):
    def test_graphify_out_hidden(self) -> None:
        self.assertEqual(should_hide_node("graphify-out/GRAPH_REPORT.md"), "graphify-out")

    def test_node_modules_hidden(self) -> None:
        self.assertEqual(should_hide_node("node_modules/react/index.js"), "node_modules")

    def test_next_hidden(self) -> None:
        self.assertEqual(should_hide_node(".next/static/chunk.js"), "next-build")

    def test_build_output_hidden(self) -> None:
        self.assertEqual(should_hide_node("dist/app.js"), "build-output")

    def test_minified_hidden(self) -> None:
        self.assertEqual(should_hide_node("src/vendor/lib.min.js"), "minified-bundle")

    def test_clean_file_not_hidden(self) -> None:
        self.assertIsNone(should_hide_node("src/services/auth.js"))


class TestReadModelGeneric(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = load_graph(FIXTURE)
        cls.model = build_read_model(
            cls.graph, repo_root="fixture", source_graph_path=str(FIXTURE),
            max_per_slice=10, generated_at="2026-06-09T00:00:00+00:00")
        cls.slices = {s["label"]: s for s in cls.model["slices"]}

    def test_default_is_generic_structure(self) -> None:
        self.assertEqual(self.model["metadata"]["slice_mode"], "generic-structure")

    def test_concepts_are_generic(self) -> None:
        concepts = {n["concept"] for n in self.model["nodes"]}
        allowed = {"frontend", "backend", "tests", "config", "docs",
                   "scripts", "assets", "data", "workflows", "other"}
        self.assertTrue(concepts.issubset(allowed), f"non-generic concept(s): {concepts - allowed}")

    def test_directory_slices_present(self) -> None:
        # generic slices are top-level directories
        self.assertIn("src", self.slices)
        self.assertIn("docs", self.slices)

    def test_noise_excluded_everywhere(self) -> None:
        all_paths = " ".join(n["file_path"] for n in self.model["nodes"])
        self.assertNotIn("node_modules/", all_paths)
        self.assertNotIn("graphify-out/", all_paths)
        self.assertNotIn(".next/", all_paths)
        self.assertNotIn(".min.", all_paths)

    def test_hidden_counts_by_rule(self) -> None:
        hidden = self.model["metadata"]["hidden_noise_counts"]
        self.assertEqual(hidden.get("node_modules"), 1)
        self.assertEqual(hidden.get("graphify-out"), 1)
        self.assertEqual(hidden.get("next-build"), 1)
        self.assertEqual(hidden.get("minified-bundle"), 1)

    def test_warnings_present(self) -> None:
        joined = " ".join(self.model["warnings"]).lower()
        self.assertIn("first-pass", joined)
        self.assertIn("source of truth", joined)
        self.assertIn("repo-truth verification", joined)
        self.assertIn("runtime truth", joined)
        self.assertIn("semantic layer", joined)

    def test_metadata_fields(self) -> None:
        md = self.model["metadata"]
        self.assertEqual(md["graph_built_at_commit"], "fixture0001")
        self.assertIn("code-only", md["graph_build_mode"])
        self.assertEqual(md["total_source_nodes"], 19)
        self.assertEqual(md["total_source_edges"], 11)
        self.assertTrue(md["source_graph_exists"])

    def test_deterministic(self) -> None:
        model2 = build_read_model(
            self.graph, repo_root="fixture", source_graph_path=str(FIXTURE),
            max_per_slice=10, generated_at="2026-06-09T00:00:00+00:00")
        self.assertEqual(json.dumps(self.model, sort_keys=True),
                         json.dumps(model2, sort_keys=True))

    def test_compact(self) -> None:
        payload = json.dumps(self.model)
        self.assertLess(len(payload), 64_000)


class TestShortestPath(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        graph = load_graph(FIXTURE)
        _nodes, _deg, cls.adj = _build_index(graph)

    def test_path_button_to_auth(self) -> None:
        path = shortest_path(self.adj, "comp_button", "svc_auth")
        self.assertEqual(path, ["comp_button", "api_server", "svc_auth"])

    def test_path_auth_to_seed(self) -> None:
        path = shortest_path(self.adj, "svc_auth", "data_seed")
        self.assertEqual(path, ["svc_auth", "model_user", "data_seed"])

    def test_no_path(self) -> None:
        self.assertIsNone(shortest_path(self.adj, "comp_button", "other_notes"))

    def test_allowed_restriction(self) -> None:
        allowed = {"comp_button", "svc_auth"}  # excludes the api_server bridge
        self.assertIsNone(shortest_path(self.adj, "comp_button", "svc_auth", allowed=allowed))


class TestGenericSliceBuilder(unittest.TestCase):
    def test_cap_and_determinism(self) -> None:
        graph = load_graph(FIXTURE)
        nodes, degree, _adj = _build_index(graph)
        info = {}
        for nid, n in nodes.items():
            if should_hide_node(n["file_path"]):
                continue
            n = dict(n)
            n["concept"] = generic_concept(n["file_path"], n["label"])
            info[nid] = n
        s1 = build_generic_slices(info, degree, max_per_slice=1)
        s2 = build_generic_slices(info, degree, max_per_slice=1)
        self.assertEqual(s1, s2)
        for s in s1:
            self.assertLessEqual(len(s["node_ids"]), 1)
            if s["matched"] > 1:
                self.assertTrue(any("capped" in w for w in s["warnings"]))


class ModeSelectionTests(unittest.TestCase):
    @staticmethod
    def _graph(n=80):
        nodes = [{"id": f"n{i}", "label": f"file_{i}",
                  "source_file": f"src/mod{i % 7}/f{i}.py", "community": 1}
                 for i in range(n)]
        links = [{"source": f"n{i}", "target": f"n{(i + 1) % n}", "weight": 1.0}
                 for i in range(n - 1)]
        return {"nodes": nodes, "links": links}

    def test_auto_is_generic_without_config(self):
        m = build_read_model(self._graph(), repo_root="x", source_graph_path="x", mode="auto")
        self.assertEqual(m["metadata"]["slice_mode"], "generic-structure")
        self.assertGreater(m["metadata"]["emitted_nodes"], 50)

    def test_forced_generic(self):
        m = build_read_model(self._graph(), repo_root="x", source_graph_path="x", mode="generic")
        self.assertEqual(m["metadata"]["slice_mode"], "generic-structure")

    def test_generic_total_cap_holds(self):
        g = {"nodes": [{"id": f"n{i}", "label": f"f{i}",
                        "source_file": f"d{i % 8}/f{i}.py", "community": 0}
                       for i in range(4480)],
             "links": [{"source": f"n{i}", "target": f"n{i + 1}", "weight": 1.0}
                       for i in range(4479)]}
        m = build_read_model(g, repo_root="x", source_graph_path="x", mode="generic")
        self.assertLessEqual(m["metadata"]["emitted_nodes"], 4000)
        self.assertTrue(any("global cap" in w for sl in m["slices"] for w in sl["warnings"]))

    def test_mode_recorded_in_metadata(self):
        m = build_read_model(self._graph(), repo_root="x", source_graph_path="x", mode="auto")
        self.assertEqual(m["metadata"]["mode_requested"], "auto")


class LocalOverrideTests(unittest.TestCase):
    """Requirement #9: a maintainer's optional local taxonomy config still works
    when present (loaded from GRAPHIQUEST_TAXONOMY_CONFIG / the repo-root file)."""

    def test_local_config_applies_custom_taxonomy(self):
        cfg = {
            "concepts": [{"name": "widget", "pattern": "components/", "match_label": False}],
            "slices": [{"id": "widgets", "label": "Widgets", "purpose": "demo",
                        "concepts": ["widget"]}],
        }
        old = os.environ.get("GRAPHIQUEST_TAXONOMY_CONFIG")
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "tax.json")
            Path(p).write_text(json.dumps(cfg), encoding="utf-8")
            os.environ["GRAPHIQUEST_TAXONOMY_CONFIG"] = p
            try:
                import graphify_taxonomy_config as tc
                importlib.reload(tc)
                import graphify_hivemind_readmodel as rm
                importlib.reload(rm)
                self.assertTrue(rm.CONCEPT_RULES, "custom concept rules loaded from local config")
                self.assertTrue(rm.SLICES, "custom slices loaded from local config")
                model = rm.build_read_model(
                    rm.load_graph(FIXTURE), repo_root="x", source_graph_path="x", mode="custom")
                self.assertEqual(model["metadata"]["slice_mode"], "custom-taxonomy")
                self.assertIn("Widgets", {s["label"] for s in model["slices"]})
                self.assertIn("widget", {n["concept"] for n in model["nodes"]})
            finally:
                if old is None:
                    os.environ.pop("GRAPHIQUEST_TAXONOMY_CONFIG", None)
                else:
                    os.environ["GRAPHIQUEST_TAXONOMY_CONFIG"] = old
                importlib.reload(tc)   # restore generic default for later tests
                importlib.reload(rm)


if __name__ == "__main__":
    unittest.main(verbosity=2)
