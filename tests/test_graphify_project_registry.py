"""Tests for the G5P.2 local-first project registry (graphify.projects.json)
and its honest baking into the generated dashboard.

The registry's honesty contract:
  - statuses come from the allowed set only;
  - exactly one default project;
  - non-ready projects carry NO counts (counts are never stored; the generator
    fills them from the live read-model for ready graphs only);
  - 'ready' entries name a readModelPath (the generator demotes to
    graph_missing when it is absent at build time).

Standard library unittest:
  python tests/test_graphify_project_registry.py
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REG = json.loads((REPO_ROOT / "graphify.projects.json").read_text(encoding="utf-8"))
GEN = (REPO_ROOT / "scripts" / "graphify_dashboard_mock.py").read_text(encoding="utf-8")
OUT = REPO_ROOT / "graphify-out" / "views" / "graphify-dashboard.html"


class RegistryFileTests(unittest.TestCase):
    def test_statuses_allowed(self):
        allowed = set(REG["allowed_statuses"])
        self.assertIn("ready", allowed)
        for p in REG["projects"]:
            self.assertIn(p["graphStatus"], allowed, p["id"])

    def test_no_shipped_default(self):
        # G5Q.1o packaging: no DaForgeLayer Workbench default ships -- the
        # dashboard boots to the first ready project or an honest no-graph state
        self.assertEqual(sum(1 for p in REG["projects"] if p.get("isDefault")), 0)

    def test_no_stored_counts_anywhere(self):
        # counts are generator-filled for ready graphs; storing them in the
        # registry would let them go stale/fake
        for p in REG["projects"]:
            for k in ("nodeCount", "edgeCount", "conceptCount"):
                self.assertIsNone(p.get(k), f"{p['id']}.{k} must not be stored")

    def test_ready_entries_name_a_read_model(self):
        for p in REG["projects"]:
            if p["graphStatus"] == "ready":
                self.assertTrue(p.get("readModelPath"), p["id"])

    def test_non_ready_entries_have_honest_messages(self):
        for p in REG["projects"]:
            if p["graphStatus"] != "ready":
                self.assertTrue(p.get("statusMessage"), p["id"])
                self.assertIsNone(p.get("graphId"), p["id"])

    def test_unique_ids(self):
        ids = [p["id"] for p in REG["projects"]]
        self.assertEqual(len(ids), len(set(ids)))


class GeneratorContractTests(unittest.TestCase):
    def test_generator_reads_this_registry(self):
        self.assertIn('graphify.projects.json', GEN)
        self.assertIn('def load_projects', GEN)

    def test_generator_demotes_missing_read_model(self):
        # the honesty demotion must exist: ready + absent read-model -> graph_missing
        self.assertIn('graph_missing', GEN)
        self.assertIn('read-model is missing', GEN)

    def test_no_hardcoded_fake_card_counts(self):
        # the old hardcoded CARDS block invented per-card stats; the registry
        # build must derive stats from status or live counts only
        self.assertNotIn('"— files · — clusters"', GEN)
        self.assertNotIn("slice of shared graph", GEN)


@unittest.skipUnless(OUT.exists(), "generated dashboard not present (ignored output)")
class EmittedPageTests(unittest.TestCase):
    def test_registry_baked_with_all_ids(self):
        page = OUT.read_text(encoding="utf-8")
        m = re.search(r"const REGISTRY = (\[.*?\]);", page, re.S)
        self.assertTrue(m, "baked REGISTRY not found")
        baked = json.loads(m.group(1))
        self.assertEqual({p["id"] for p in baked}, {p["id"] for p in REG["projects"]})
        ready = [p for p in baked if p["graphStatus"] == "ready"]
        for p in baked:
            if p["graphStatus"] != "ready":
                self.assertIsNone(p.get("nodeCount"), p["id"])
        # ready graphs got live counts at bake time (or were demoted)
        for p in ready:
            self.assertTrue(p.get("nodeCount"), p["id"])

    def test_page_carries_honest_flow_markers(self):
        page = OUT.read_text(encoding="utf-8")
        for marker in ("nograph-card", "saved locally in this browser",
                       "CURRENT_VIEWS",   # G5P.5: pills must follow the switched graph's views
                       # G5P.3: RUN GRAPHIFY is wired (bridge) with an honest
                       # manual fallback -- the old "pending" label is gone
                       # (G5P.3a compacted the button labels; the long wording
                       # moved into title attributes)
                       "RUN GRAPHIFY", "PREPARE COMMAND",
                       "/api/graphify/generate", "waiting_for_manual_run",
                       "ask_blocked_no_graph"):
            self.assertIn(marker, page, marker)


if __name__ == "__main__":
    unittest.main()


class TopStripRulesTests(unittest.TestCase):
    """G5P.6: top-strip visibility is an honest display rule, not deletion."""

    def test_registry_carries_visibility_fields(self):
        for p in REG["projects"]:
            self.assertIn("showInTopBar", p, p["id"])
            self.assertIn("pinned", p, p["id"])
            self.assertFalse(p.get("removable"), p["id"])   # tracked entries never browser-deletable

    def test_no_workbench_in_registry_or_page(self):
        # G5Q.1o audit: the only shipped DaForgeLayer reference is the footer link
        self.assertNotIn("workbench", json.dumps(REG).lower())
        if OUT.exists():
            page = OUT.read_text(encoding="utf-8")
            self.assertNotIn("DaForgeLayer Workbench", page)
            self.assertIn('id="powered"', page)

    @unittest.skipUnless(OUT.exists(), "generated dashboard not present")
    def test_page_carries_strip_and_modal_markers(self):
        page = OUT.read_text(encoding="utf-8")
        for marker in ("renderTopStrip", "project_unloaded", "local_project_removed",
                       "add_project_opened", "/api/projects/pick-folder",
                       "folder_picker_unavailable", "repo_path_validated",
                       # G5P.6a (operator request): URL import is REAL via the bridge
                       "/api/projects/import-url", "repo_url_import_started",
                       "graphify clone",
                       "tracked registry projects cannot be deleted"):
            self.assertIn(marker, page, marker)
        # the URL input is live (not disabled) and the import flow is honest about network
        import re as _re
        m = _re.search(r'id="am-url"[^>]*', page)
        self.assertTrue(m and "disabled" not in m.group(0), "am-url must be enabled (URL import is wired)")
        self.assertIn("uses the network", page)


class MemorySectionTests(unittest.TestCase):
    """G5P.7 (operator catch): Memory must be REAL -- sessions, notes, history,
    data manager -- and the placeholder wording must be gone."""

    @unittest.skipUnless(OUT.exists(), "generated dashboard not present")
    def test_memory_is_built(self):
        page = OUT.read_text(encoding="utf-8")
        self.assertNotIn("no memory system yet", page)
        for marker in ("graphify-sessions-v1", "graphify-node-notes-v1",
                       "SAVE CURRENT SESSION", "mem-note-add", "mem-ask-q",
                       "session_saved", "session_restored", "note_added",
                       "memory_key_cleared", "mem-keys"):
            self.assertIn(marker, page, marker)


class BrandCleanupTests(unittest.TestCase):
    """G5P.10: the standalone product must not brand itself 'Graphify OS' (a
    naming collision with the upstream Graphify CLI project) or label the user
    'OPERATOR' (an internal role). It is the Graphify Dashboard, used locally."""

    def test_no_graphify_os_in_emitted_page(self):
        # the emitted page is the user surface -- no 'Graphify OS' anywhere in it
        if OUT.exists():
            self.assertNotIn("Graphify OS", OUT.read_text(encoding="utf-8"),
                             "user-facing 'Graphify OS' brand must be gone")

    def test_brand_is_graphiquest(self):
        # G5Q.1v operator rebrand: the APP is GraphiQuest; the scanner stays Graphify
        self.assertIn("GraphiQuest", GEN)
        self.assertNotIn("Graphify Dashboard", GEN)
        self.assertNotIn("<b>Graphify OS</b>", GEN)
        self.assertIn("graphiquest_logo_mark_seed711002c.png", GEN)
