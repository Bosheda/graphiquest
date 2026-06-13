"""G5P.9: local MCP server (scripts/graphify_mcp_server.py) -- protocol + tools
over a real read-model built from the test fixture graph. The server is the
REAL connector behind the dashboard's Claude Code gate:
read-only, stdio JSON-RPC, stdlib-only.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import graphify_mcp_server as mcp                                     # noqa: E402
from graphify_hivemind_readmodel import build_read_model, load_graph  # noqa: E402

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "graphify_hivemind_sample_graph.json"


class McpServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        graph = load_graph(FIXTURE)
        rm = build_read_model(graph, repo_root="x", source_graph_path=str(FIXTURE))
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.rm_path = Path(cls.tmpdir.name) / "read-model.json"
        cls.rm_path.write_text(json.dumps(rm), encoding="utf-8")
        cls.store = mcp.GraphStore(cls.rm_path)
        cls.first_label = rm["nodes"][0]["label"] if rm["nodes"] else None

    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()

    def _call(self, method, params=None, mid=1):
        return mcp.handle(self.store, {"jsonrpc": "2.0", "id": mid, "method": method,
                                       "params": params or {}})

    def test_initialize(self):
        r = self._call("initialize")
        self.assertEqual(r["result"]["serverInfo"]["name"], "graphify")
        self.assertIn("tools", r["result"]["capabilities"])

    def test_initialized_notification_is_silent(self):
        self.assertIsNone(mcp.handle(self.store, {"jsonrpc": "2.0",
                                                  "method": "notifications/initialized"}))

    def test_tools_list(self):
        r = self._call("tools/list")
        names = {t["name"] for t in r["result"]["tools"]}
        self.assertEqual(names, {"graph_summary", "find_node",
                                 "node_neighbors", "list_concepts", "run_hunter"})

    def test_graph_summary_carries_honest_warnings(self):
        r = self._call("tools/call", {"name": "graph_summary", "arguments": {}})
        self.assertFalse(r["result"]["isError"])
        out = json.loads(r["result"]["content"][0]["text"])
        self.assertGreater(out["nodes"], 0)
        self.assertTrue(out["warnings"])

    def test_find_node_exact_match(self):
        if not self.first_label:
            self.skipTest("empty fixture")
        r = self._call("tools/call", {"name": "find_node",
                                      "arguments": {"query": self.first_label}})
        out = json.loads(r["result"]["content"][0]["text"])
        self.assertGreaterEqual(out["matches"], 1)
        self.assertEqual(out["hits"][0]["label"], self.first_label)

    def test_node_neighbors(self):
        if not self.first_label:
            self.skipTest("empty fixture")
        r = self._call("tools/call", {"name": "node_neighbors",
                                      "arguments": {"id_or_label": self.first_label}})
        out = json.loads(r["result"]["content"][0]["text"])
        self.assertIn("total_neighbors", out)

    def test_list_concepts(self):
        r = self._call("tools/call", {"name": "list_concepts", "arguments": {}})
        out = json.loads(r["result"]["content"][0]["text"])
        self.assertTrue(out["concepts"])

    def test_unknown_tool_is_honest_error_not_crash(self):
        r = self._call("tools/call", {"name": "rm_rf", "arguments": {}})
        self.assertTrue(r["result"]["isError"])

    def test_unknown_method_returns_jsonrpc_error(self):
        r = self._call("definitely/not/a/method")
        self.assertEqual(r["error"]["code"], -32601)

    def test_missing_read_model_is_honest(self):
        store = mcp.GraphStore(Path(self.tmpdir.name) / "nope.json")
        r = mcp.handle(store, {"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                               "params": {"name": "graph_summary", "arguments": {}}})
        self.assertTrue(r["result"]["isError"])
        self.assertIn("graphify update", r["result"]["content"][0]["text"])

    def test_selftest_passes(self):
        self.assertEqual(mcp.selftest(self.store), 0)


if __name__ == "__main__":
    unittest.main()


class RunHunterToolTests(McpServerTests):
    """G5Q.1m: the dashboard Hunter skill exposed to Claude Code as a
    read-only MCP tool, findings carry jumpable nodeIds."""

    def test_tool_registered(self):
        self.assertIn("run_hunter", [t["name"] for t in mcp.TOOLS])

    def test_hunter_findings_shape(self):
        out = self.store.hunter()
        self.assertIn("findings", out)
        self.assertIn("counts", out)
        self.assertIn("not proof of bugs", out["note"])
        for f in out["findings"]:
            for k in ("kind", "sev", "title", "evidence", "nodeIds", "confidence"):
                self.assertIn(k, f, k)

    def test_dispatch(self):
        out = mcp.call_tool(self.store, "run_hunter", {"max_findings": 10})
        self.assertLessEqual(len(out["findings"]), 10)
