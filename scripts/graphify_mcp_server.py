#!/usr/bin/env python3
"""Graphify local MCP server (G5P.9) -- the REAL connector behind the dashboard's
Claude Desktop / Claude Code gates.

A minimal stdio JSON-RPC 2.0 server implementing the Model Context Protocol
(newline-delimited messages on stdin/stdout; logs to stderr only). It exposes
the LOCAL Graphify read-model -- read-only, no network, no code execution.

Tools:
  graph_summary    -- counts, build mode, slice mode, honest warnings
  find_node        -- exact > prefix > contains on label/id/path, degree tiebreak
                      (the same match ladder the 3D view uses)
  node_neighbors   -- direct connections of a node, ranked by degree
  list_concepts    -- concept buckets with node counts

Consumers (both verified upstream 2026-06-11):
  Claude Desktop -- claude_desktop_config.json:
    { "mcpServers": { "graphify": { "command": "python",
        "args": ["<abs>/scripts/graphify_mcp_server.py", "--repo", "<abs repo>"] } } }
    (full app restart required; per-server logs land in %APPDATA%/Claude/logs)
  Claude Code -- claude mcp add -s user graphify -- "<abs python>"
        "<abs>/scripts/graphify_mcp_server.py" --repo "<abs repo>"
    (stored in ~/.claude.json top-level mcpServers; verify with: claude mcp list)

Usage:
  python scripts/graphify_mcp_server.py --repo <repo-root>
  python scripts/graphify_mcp_server.py --read-model <path/to/read-model.json>
  python scripts/graphify_mcp_server.py --selftest        # offline smoke test

Standard library only. Read-only: this process never writes anything anywhere.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

SERVER_NAME = "graphify"
SERVER_VERSION = "g5q1m-1"
PROTOCOL_VERSION = "2024-11-05"


def log(msg: str) -> None:
    print(f"[graphify-mcp] {msg}", file=sys.stderr, flush=True)


class GraphStore:
    """Lazy read-model loader + adjacency index (read-only)."""

    def __init__(self, rm_path: Path):
        self.path = rm_path
        self._rm = None
        self._adj = None
        self._by_id = None

    def load(self):
        if self._rm is None:
            with open(self.path, "r", encoding="utf-8") as fh:
                self._rm = json.load(fh)
            self._by_id = {n["id"]: n for n in self._rm.get("nodes", [])}
            adj = defaultdict(list)
            for e in self._rm.get("edges", []):
                a, b = e.get("source"), e.get("target")
                if a in self._by_id and b in self._by_id:
                    adj[a].append(b)
                    adj[b].append(a)
            self._adj = adj
            md = self._rm.get("metadata", {})
            log(f"read-model loaded: {md.get('emitted_nodes')} nodes / "
                f"{md.get('emitted_edges')} edges ({self.path})")
        return self._rm

    def summary(self) -> dict:
        rm = self.load()
        md = rm.get("metadata", {})
        return {
            "nodes": md.get("emitted_nodes"),
            "edges": md.get("emitted_edges"),
            "slices": len(rm.get("slices", [])),
            "slice_mode": md.get("slice_mode"),
            "graph_build_mode": md.get("graph_build_mode"),
            "built_at_commit": md.get("graph_built_at_commit"),
            "generated_at": md.get("generated_at"),
            "source_nodes_total": md.get("total_source_nodes"),
            "source_edges_total": md.get("total_source_edges"),
            "warnings": rm.get("warnings", []),
        }

    def find(self, query: str, limit: int = 5) -> dict:
        rm = self.load()
        q = (query or "").strip().lower()
        scored = []
        if q:
            for n in rm.get("nodes", []):
                lbl = str(n.get("label", "")).lower()
                nid = str(n.get("id", "")).lower()
                fp = str(n.get("file_path", "")).lower()
                if lbl == q or nid == q:
                    score = 3
                elif lbl.startswith(q):
                    score = 2
                elif q in lbl or q in nid or q in fp:
                    score = 1
                else:
                    continue
                scored.append((score, n.get("degree", 0), n))
        scored.sort(key=lambda t: (-t[0], -t[1], t[2]["id"]))
        hits = [self._node_out(n) for _s, _d, n in scored[: max(1, min(int(limit or 5), 25))]]
        return {"query": query, "matches": len(scored), "hits": hits}

    def neighbors(self, id_or_label: str, limit: int = 10) -> dict:
        self.load()
        node = self._by_id.get(id_or_label)
        if node is None:
            hit = self.find(id_or_label, limit=1)["hits"]
            if not hit:
                return {"error": f"no node matches {id_or_label!r}"}
            node = self._by_id[hit[0]["id"]]
        nbs = [self._by_id[x] for x in self._adj.get(node["id"], []) if x in self._by_id]
        nbs.sort(key=lambda n: (-n.get("degree", 0), n["id"]))
        cap = max(1, min(int(limit or 10), 50))
        return {"node": self._node_out(node), "total_neighbors": len(nbs),
                "neighbors": [self._node_out(n) for n in nbs[:cap]]}

    def concepts(self) -> dict:
        rm = self.load()
        counts: dict = defaultdict(int)
        for n in rm.get("nodes", []):
            counts[n.get("concept", "unknown")] += 1
        return {"concepts": [{"concept": k, "nodes": v}
                             for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]}

    def hunter(self, max_findings: int = 30) -> dict:
        """The dashboard Hunter's structural checks, read-only. Findings are
        graph EVIDENCE (candidate / possible / inspect), never proof of bugs.
        nodeIds are real node ids -- the dashboard can jump to them in 3D."""
        rm = self.load()
        nodes = rm.get("nodes", [])
        findings = []

        def add(kind, sev, title, evidence, node_ids, confidence):
            findings.append({"kind": kind, "sev": sev, "title": title,
                             "evidence": evidence, "nodeIds": node_ids[:5],
                             "confidence": confidence})

        orphans = [n for n in nodes if not self._adj.get(n["id"])]
        if orphans:
            add("orphan", "medium", f"{len(orphans)} orphan candidate(s) (no connections in this view)",
                "examples: " + ", ".join(str(n.get("label")) for n in orphans[:5]),
                [n["id"] for n in orphans], "medium")
        leaves = [n for n in nodes if len(self._adj.get(n["id"], [])) == 1]
        if leaves:
            add("leaf", "low", f"{len(leaves)} single-link leaf file(s)",
                "examples: " + ", ".join(str(n.get("label")) for n in leaves[:5]),
                [n["id"] for n in leaves], "low")
        # connected components (BFS) -- disconnected groups beyond the main one
        seen, comps = set(), []
        for n in nodes:
            if n["id"] in seen:
                continue
            comp, queue = [], [n["id"]]
            seen.add(n["id"])
            while queue:
                cur = queue.pop()
                comp.append(cur)
                for nb in self._adj.get(cur, []):
                    if nb not in seen:
                        seen.add(nb)
                        queue.append(nb)
            comps.append(comp)
        comps.sort(key=len, reverse=True)
        for comp in comps[1:6]:
            if len(comp) < 2:
                continue
            add("component", "medium", f"disconnected group of {len(comp)} files",
                "examples: " + ", ".join(str((self._by_id.get(i) or {}).get("label")) for i in comp[:4]),
                comp, "medium")
        # same-folder, zero internal edges -> possible missing relationships
        folders = defaultdict(list)
        for n in nodes:
            fp = str(n.get("file_path") or "")
            if "/" in fp:
                folders[fp.rsplit("/", 1)[0]].append(n["id"])
        folder_hits = 0
        for folder, ids in sorted(folders.items()):
            if not (3 <= len(ids) <= 15) or folder_hits >= 5:
                continue
            idset = set(ids)
            internal = sum(1 for i in ids for nb in self._adj.get(i, []) if nb in idset)
            if internal == 0:
                folder_hits += 1
                add("missing-link", "low",
                    f"folder '{folder}' has {len(ids)} files with no connections between them",
                    "possible missing relationships -- or genuinely independent files; inspect",
                    ids, "low")
        hot = sorted(nodes, key=lambda n: -(n.get("degree") or 0))[:8]
        if hot:
            add("hotspot", "info", "highest-connectivity hotspots (change ripples widest here)",
                ", ".join(f"{n.get('label')} ({n.get('degree')})" for n in hot[:5]),
                [n["id"] for n in hot], "high")
        for w in (rm.get("warnings") or [])[:3]:
            add("graph-warning", "info", "read-model warning", str(w), [], "high")
        findings = findings[: max(1, min(int(max_findings or 30), 60))]
        counts = {"high": 0, "medium": 0, "low": 0, "info": 0}
        for f in findings:
            counts[f["sev"]] = counts.get(f["sev"], 0) + 1
        return {"findings": findings, "counts": counts,
                "note": "graph evidence only -- candidates to inspect, not proof of bugs; "
                        "verify with find_node/node_neighbors before recommending"}

    @staticmethod
    def _node_out(n: dict) -> dict:
        return {"id": n.get("id"), "label": n.get("label"), "file_path": n.get("file_path"),
                "concept": n.get("concept"), "degree": n.get("degree")}


TOOLS = [
    {"name": "graph_summary",
     "description": "Summary of the local Graphify knowledge graph: node/edge/slice counts, "
                    "build mode, and the read-model's honest warnings (structural memory, "
                    "not source of truth).",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "find_node",
     "description": "Find nodes by name/id/path. Match ladder: exact > prefix > contains, "
                    "degree tiebreak (same ranking the 3D view uses).",
     "inputSchema": {"type": "object",
                     "properties": {"query": {"type": "string"},
                                    "limit": {"type": "integer", "minimum": 1, "maximum": 25}},
                     "required": ["query"], "additionalProperties": False}},
    {"name": "node_neighbors",
     "description": "Direct connections of a node (by id or best name match), ranked by degree.",
     "inputSchema": {"type": "object",
                     "properties": {"id_or_label": {"type": "string"},
                                    "limit": {"type": "integer", "minimum": 1, "maximum": 50}},
                     "required": ["id_or_label"], "additionalProperties": False}},
    {"name": "list_concepts",
     "description": "Concept buckets of the loaded graph with node counts.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "run_hunter",
     "description": "Run the dashboard Hunter's structural audit over the graph: orphan "
                    "candidates, single-link leaves, disconnected components, same-folder "
                    "no-edge candidates, hotspots, and read-model warnings. Findings are "
                    "graph evidence with nodeIds (jumpable in the dashboard's 3D view), "
                    "never proof of bugs. Read-only.",
     "inputSchema": {"type": "object",
                     "properties": {"max_findings": {"type": "integer", "minimum": 1, "maximum": 60}},
                     "additionalProperties": False}},
]


def call_tool(store: GraphStore, name: str, args: dict) -> dict:
    if name == "graph_summary":
        return store.summary()
    if name == "find_node":
        return store.find(str(args.get("query", "")), args.get("limit", 5))
    if name == "node_neighbors":
        return store.neighbors(str(args.get("id_or_label", "")), args.get("limit", 10))
    if name == "list_concepts":
        return store.concepts()
    if name == "run_hunter":
        return store.hunter(args.get("max_findings", 30))
    raise KeyError(f"unknown tool: {name}")


def handle(store: GraphStore, msg: dict):
    """Return a JSON-RPC response dict, or None for notifications."""
    method = msg.get("method")
    mid = msg.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION}}}
    if method in ("notifications/initialized", "initialized"):
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        try:
            out = call_tool(store, name, params.get("arguments") or {})
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": json.dumps(out, indent=1)}],
                "isError": False}}
        except FileNotFoundError:
            text = (f"read-model not found at {store.path} -- run `graphify update .` "
                    "in the repo, then python scripts/graphify_hivemind_readmodel.py")
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": text}], "isError": True}}
        except Exception as exc:  # honest tool error, never a crash
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": f"tool error: {exc}"}], "isError": True}}
    if mid is None:
        return None                       # unknown notification: ignore
    return {"jsonrpc": "2.0", "id": mid,
            "error": {"code": -32601, "message": f"method not found: {method}"}}


def serve(store: GraphStore) -> int:
    log(f"serving MCP over stdio (read-model: {store.path})")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            log(f"skipping non-JSON line ({line[:80]!r})")
            continue
        resp = handle(store, msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
    log("stdin closed -- exiting")
    return 0


def selftest(store: GraphStore) -> int:
    """Offline smoke test: initialize -> tools/list -> one call per tool."""
    seq = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "graph_summary", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "list_concepts", "arguments": {}}},
    ]
    ok = True
    for msg in seq:
        resp = handle(store, msg)
        good = resp and ("result" in resp) and not (resp.get("result") or {}).get("isError")
        print(f"  {msg['method']:<12} -> {'OK' if good else 'FAIL'}")
        ok = ok and bool(good)
    if ok:
        s = store.summary()
        print(f"  graph: {s['nodes']} nodes / {s['edges']} edges / {s['slices']} slices "
              f"({s['slice_mode']})")
    print("selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=".",
                    help="repo root containing graphify-out/hivemind/read-model.json")
    ap.add_argument("--read-model", default=None,
                    help="explicit read-model path (overrides --repo)")
    ap.add_argument("--selftest", action="store_true",
                    help="offline smoke test against the read-model, then exit")
    args = ap.parse_args(argv)

    rm_path = (Path(args.read_model) if args.read_model
               else Path(args.repo) / "graphify-out" / "hivemind" / "read-model.json")
    store = GraphStore(rm_path)
    if args.selftest:
        if not rm_path.exists():
            print(f"selftest: FAIL -- read-model not found: {rm_path}")
            print("run `graphify update .` then "
                  "`python scripts/graphify_hivemind_readmodel.py` first")
            return 2
        return selftest(store)
    return serve(store)


if __name__ == "__main__":
    sys.exit(main())
