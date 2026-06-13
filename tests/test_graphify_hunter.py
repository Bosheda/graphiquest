"""G5P.9 Hunter: pure-core logic tests (node harness over the extracted
HUNTER_JS block) + dashboard wiring markers.

The Hunter core is a pure JS function (window.__huntAnalyze) emitted into the
dashboard page; it contains no backslash escapes by design, so the text block
extracted from the generator source IS the runtime code.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GEN = (REPO_ROOT / "scripts" / "graphify_dashboard_mock.py").read_text(encoding="utf-8")
NODE = shutil.which("node")


def _hunter_js() -> str:
    block = GEN.split('HUNTER_JS = """', 1)[1].split('"""', 1)[0]
    assert "__huntAnalyze" in block
    return block


FIXTURE_RM = {
    "metadata": {"slice_mode": "generic-structure", "emitted_nodes": 10, "filtered_nodes": 10,
                 "emitted_edges": 6, "total_source_nodes": 10, "total_source_edges": 6},
    "warnings": [],
    "slices": [],
    "nodes": [
        {"id": "a", "label": "core.py", "file_path": "src/core.py", "concept": "python", "degree": 6},
        {"id": "b", "label": "api.py", "file_path": "src/api.py", "concept": "python", "degree": 2},
        {"id": "c", "label": "db.py", "file_path": "src/db.py", "concept": "python", "degree": 2},
        {"id": "d", "label": "tool1.py", "file_path": "tools/tool1.py", "concept": "python", "degree": 1},
        {"id": "e", "label": "tool2.py", "file_path": "tools/tool2.py", "concept": "python", "degree": 1},
        {"id": "o1", "label": "lonely.py", "file_path": "src/lonely.py", "concept": "python", "degree": 0},
        {"id": "vi", "label": "busy.py", "file_path": "src/busy.py", "concept": "python", "degree": 5},
        {"id": "f", "label": "p1.py", "file_path": "pkg/p1.py", "concept": "python", "degree": 1},
        {"id": "g", "label": "p2.py", "file_path": "pkg/p2.py", "concept": "python", "degree": 1},
        {"id": "h", "label": "p3.py", "file_path": "pkg/p3.py", "concept": "python", "degree": 1},
    ],
    "edges": [
        {"source": "a", "target": "b", "weight": 1}, {"source": "a", "target": "c", "weight": 1},
        {"source": "b", "target": "c", "weight": 1}, {"source": "d", "target": "e", "weight": 1},
        {"source": "a", "target": "f", "weight": 1}, {"source": "a", "target": "g", "weight": 1},
    ],
}


@unittest.skipIf(NODE is None, "node not on PATH")
class HunterCoreTests(unittest.TestCase):
    """Runs the real emitted analyzer in node against a crafted fixture."""

    @classmethod
    def setUpClass(cls):
        harness = ("const window={};\n" + _hunter_js() + "\n"
                   + "const rm=" + json.dumps(FIXTURE_RM) + ";\n"
                   + "console.log(JSON.stringify(window.__huntAnalyze(rm,{})));")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                         encoding="utf-8") as fh:
            fh.write(harness)
            cls.tmp = fh.name
        out = subprocess.run([NODE, cls.tmp], capture_output=True, text=True, timeout=60)
        assert out.returncode == 0, out.stderr[-800:]
        cls.res = json.loads(out.stdout)
        Path(cls.tmp).unlink(missing_ok=True)

    def _by_kind(self, kind):
        return [f for f in self.res["findings"] if f["kind"] == kind]

    def test_orphan_detected_and_clickable(self):
        o = self._by_kind("orphan")
        self.assertTrue(o, "orphan finding missing")
        self.assertEqual(o[0]["nodeIds"], ["o1"])
        self.assertTrue(o[0]["clickable"])

    def test_components_detected_with_jump_head(self):
        c = self._by_kind("component")
        self.assertTrue(c and "disconnected groups" in c[0]["title"])
        self.assertTrue(c[0]["nodeIds"], "smaller-group head should be a jump target")

    def test_view_isolated_split_from_orphans(self):
        vi = self._by_kind("view-isolated")
        self.assertTrue(vi and "isolated in this view only" in vi[0]["title"])
        self.assertFalse(vi[0]["clickable"])

    def test_missing_rel_candidate_same_dir(self):
        mr = self._by_kind("missing-rel")
        self.assertTrue(any("pkg/" in f["title"] for f in mr),
                        "pkg/ (3 files, 0 internal links) should be a candidate")

    def test_hotspots(self):
        h = self._by_kind("hotspot")
        self.assertTrue(h and "core.py" in h[0]["title"])

    def test_no_overclaim_language(self):
        text = json.dumps(self.res["findings"]).lower()
        for banned in ("definitely", "certainly", "guaranteed", "bug found", "is broken"):
            self.assertNotIn(banned, text)
        self.assertIn("candidate", text)
        self.assertIn("inspect", text)

    def test_counts_and_schema(self):
        c = self.res["counts"]
        self.assertEqual(sum(c.values()), len(self.res["findings"]))
        for f in self.res["findings"]:
            self.assertIn(f["sev"], ("high", "medium", "low", "info"))
            for field in ("id", "kind", "title", "nodeIds", "evidence", "action",
                          "confidence", "clickable", "localOnly", "in3d"):
                self.assertIn(field, f, field)
            self.assertTrue(f["localOnly"])


class HunterDashboardMarkersTests(unittest.TestCase):
    def test_reports_section_and_events(self):
        for marker in ('data-sec="reports"', "RUN HUNTER", "graphify-hunter-reports-v1",
                       "hunter_run_started", "hunter_report_created", "report_finding_opened",
                       "hunter_blocked_no_graph", "hunter_enriched", "__huntAnalyze",
                       "no call was made", "not proof of bugs"):
            self.assertIn(marker, GEN, marker)

    def test_storage_capped_and_size_guarded(self):
        self.assertIn("all.slice(0, 10)", GEN)
        self.assertIn("200000", GEN)

    def test_skill_card_present(self):
        self.assertIn("Hunter — project auditor", GEN)
        self.assertIn("skill-hunt-run", GEN)

    def test_enrichment_real_but_never_automatic(self):
        # G5Q.1m: ENRICH is a real bounded call per explicit click
        self.assertIn("ENRICH WITH CLAUDE CODE", GEN)
        self.assertIn("one real call", GEN)
        self.assertIn("'/api/claudecode/enrich'", GEN)
        self.assertNotIn("ENRICH WITH CLAUDE DESKTOP", GEN)


if __name__ == "__main__":
    unittest.main()
