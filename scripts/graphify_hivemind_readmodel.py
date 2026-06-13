#!/usr/bin/env python3
"""Graphify -> Hivemind read-model adapter (Mission G2, g-wb-os-graphify-hivemind-readmodel).

Reads the local, gitignored Graphify graph (graphify-out/graph.json) and emits a compact,
deterministic dashboard-ready read model (metadata + slices + nodes + edges + warnings) to
the gitignored output path graphify-out/hivemind/read-model.json.

Taxonomy: every repo is classified with a generic, repo-agnostic taxonomy (file-kind +
top-level-directory slices). An optional local config may overlay a custom taxonomy --
see scripts/graphify_taxonomy_config.py.
Operating principle: Graphify is structural memory and FIRST-PASS context. Repo files remain
the source of truth; load-bearing claims require Read/Grep verification. This adapter never
infers runtime truth from the structural graph.

Standard library only. Deterministic (stable sorts; optional --fixed-time for byte-stable
output). Never mutates tracked repo files; never calls the Graphify CLI.

Usage:
  python scripts/graphify_hivemind_readmodel.py
  python scripts/graphify_hivemind_readmodel.py --graph graphify-out/graph.json \
      --out graphify-out/hivemind/read-model.json --max-per-slice 800
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

DEFAULT_GRAPH = Path("graphify-out") / "graph.json"
DEFAULT_OUT = Path("graphify-out") / "hivemind" / "read-model.json"
DEFAULT_MAX_PER_SLICE = 800
MAX_EDGES = 12000

# Optional LOCAL taxonomy override (gitignored; NEVER shipped). The published
# package classifies every repo with the GENERIC taxonomy below; a maintainer
# can drop graphiquest.taxonomy.local.json to overlay a bespoke concept/slice
# vocabulary for their own repo. See scripts/graphify_taxonomy_config.py.
try:  # importable as a sibling when scripts/ is on sys.path (tests, bridge)
    from graphify_taxonomy_config import load_local_taxonomy
except ImportError:  # run from elsewhere -- degrade to generic-only, never fail
    def load_local_taxonomy() -> Dict[str, Any]:  # type: ignore
        return {}

_LOCAL_TAXONOMY: Dict[str, Any] = load_local_taxonomy()


def _compile_hide(rules: Iterable[Dict[str, Any]]) -> List[Tuple[str, "re.Pattern[str]"]]:
    out: List[Tuple[str, re.Pattern[str]]] = []
    for r in rules or []:
        try:
            out.append((str(r["name"]), re.compile(str(r["pattern"]), re.I)))
        except (KeyError, re.error, TypeError):
            continue
    return out


def _compile_concept_rules(rules: Iterable[Dict[str, Any]]) -> List[Tuple[str, "re.Pattern[str]", bool]]:
    out: List[Tuple[str, re.Pattern[str], bool]] = []
    for r in rules or []:
        try:
            out.append((str(r["name"]), re.compile(str(r["pattern"]), re.I), bool(r.get("match_label", False))))
        except (KeyError, re.error, TypeError):
            continue
    return out


def _compile_slices(specs: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in specs or []:
        try:
            extra = s.get("extra")
            out.append(dict(
                id=str(s["id"]), label=str(s["label"]), purpose=str(s.get("purpose", "")),
                concepts=set(s.get("concepts", [])),
                extra=re.compile(str(extra), re.I) if extra else None))
        except (KeyError, re.error, TypeError):
            continue
    return out


# ---------------------------------------------------------------------------
# Noise filters (hidden by default; counted per rule). Universal noise only --
# project-specific hide patterns come from the optional local config.
# ---------------------------------------------------------------------------
HIDE_RULES: List[Tuple[str, "re.Pattern[str]"]] = [
    ("graphify-out", re.compile(r"^graphify-out/", re.I)),
    ("vcs/meta", re.compile(r"(^|/)\.(git|hg|svn)/", re.I)),
    ("next-build", re.compile(r"(^|/)\.next(-build|-proof[^/]*)?/", re.I)),
    ("build-output", re.compile(r"(^|/)(dist|build|out|coverage|\.cache|__pycache__)/", re.I)),
    ("node_modules", re.compile(r"(^|/)node_modules/", re.I)),
    ("venv", re.compile(r"(^|/)(\.venv|venv|env|site-packages)/", re.I)),
    ("minified-bundle", re.compile(r"\.min\.(m?js|css)\b", re.I)),
    ("browser-extension", re.compile(r"(^|/)Extensions/[a-p]{32}/", re.I)),
] + _compile_hide(_LOCAL_TAXONOMY.get("hide"))

# ---------------------------------------------------------------------------
# Concept classification (first match wins). EMPTY in the shipped package --
# every node falls through to the GENERIC file-kind taxonomy below. A local
# config may overlay project-specific concept rules.
# ---------------------------------------------------------------------------
CONCEPT_RULES: List[Tuple[str, "re.Pattern[str]", bool]] = _compile_concept_rules(
    _LOCAL_TAXONOMY.get("concepts"))

WARNINGS: List[str] = [
    "Graphify is first-pass structural memory, not source of truth.",
    "Repo-truth verification (Read/Grep) is required for load-bearing claims.",
    "Docs/images semantic layer is NOT built (graph is code-only structural extraction).",
    "Runtime truth is NOT inferred from this graph; runtime telemetry is a separate, governed source.",
]

# ---------------------------------------------------------------------------
# Slice definitions. EMPTY in the shipped package -- the read model defaults to
# generic top-level-directory slices. A local config may overlay named slices.
# ---------------------------------------------------------------------------
SLICES: List[Dict[str, Any]] = _compile_slices(_LOCAL_TAXONOMY.get("slices"))


# ---------------------------------------------------------------------------
# Unit-testable core
# ---------------------------------------------------------------------------
def load_graph(path: Path) -> Dict[str, Any]:
    """Load a Graphify node-link graph JSON. Raises FileNotFoundError if absent."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def should_hide_node(file_path: str) -> Optional[str]:
    """Return the hide-rule name if the node's source file is noise, else None."""
    for name, rx in HIDE_RULES:
        if rx.search(file_path or ""):
            return name
    return None


def classify_node(file_path: str, label: str) -> str:
    """Classify a node via the configured concept rules (first match wins).

    CONCEPT_RULES is EMPTY in the shipped package (returns 'unknown' here, then
    the caller reclassifies generically); a local config may populate it."""
    fp = file_path or ""
    lb = label or ""
    for concept, rx, also_label in CONCEPT_RULES:
        if rx.search(fp) or (also_label and rx.search(lb)):
            return concept
    return "unknown"


def _build_index(graph: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, int],
                                                 Dict[str, List[Tuple[str, float]]]]:
    """Return (kept node id -> info, id -> degree, adjacency). Noise + hidden counted by caller."""
    nodes: Dict[str, Dict[str, Any]] = {}
    for n in graph.get("nodes", []):
        nid = str(n.get("id"))
        nodes[nid] = {
            "id": nid,
            "label": (n.get("label") or nid)[:90],
            "file_path": n.get("source_file") or "",
            "community": n.get("community") if isinstance(n.get("community"), int) else None,
        }
    degree: Dict[str, int] = defaultdict(int)
    adj: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for e in graph.get("links", []):
        a, b = str(e.get("source")), str(e.get("target"))
        if a == b or a not in nodes or b not in nodes:
            continue
        w = float(e.get("weight") or 1.0)
        degree[a] += 1
        degree[b] += 1
        adj[a].append((b, w))
        adj[b].append((a, w))
    return nodes, degree, adj


def shortest_path(adj: Dict[str, List[Tuple[str, float]]], src: str, dst: str,
                  allowed: Optional[set] = None) -> Optional[List[str]]:
    """Deterministic unweighted BFS shortest path (sorted neighbor order). None if no path."""
    if src == dst:
        return [src]
    if allowed is not None and (src not in allowed or dst not in allowed):
        return None
    prev: Dict[str, Optional[str]] = {src: None}
    q: deque[str] = deque([src])
    while q:
        u = q.popleft()
        for v, _w in sorted(adj.get(u, ())):
            if v in prev or (allowed is not None and v not in allowed):
                continue
            prev[v] = u
            if v == dst:
                path = [v]
                while prev[path[-1]] is not None:
                    path.append(prev[path[-1]])  # type: ignore[arg-type]
                return list(reversed(path))
            q.append(v)
    return None


# GENERIC, repo-agnostic taxonomy -- the DEFAULT and ONLY taxonomy shipped in
# the public package. Path + extension heuristics, first match wins. Ordering
# matters: more specific locations (tests, workflows, scripts) before broad
# file-kind buckets. No project-specific vocabulary appears here.
GENERIC_CONCEPTS: List[Tuple[str, "re.Pattern[str]"]] = [
    ("tests", re.compile(r"(^|/)(tests?|__tests__|spec|e2e|__mocks__)/|(^|/|[._-])(test|spec)\.[a-z0-9]+$|[._](test|spec)\.[a-z0-9]+$", re.I)),
    ("workflows", re.compile(r"(^|/)\.github/workflows/|(^|/)workflows?/|(^|/)\.gitlab-ci|(^|/)(Dockerfile|Makefile|Jenkinsfile)$|\.ya?ml$.*(^|/)(ci|cd|pipelines?)/", re.I)),
    ("scripts", re.compile(r"(^|/)(scripts?|bin|tools)/|\.(sh|ps1|psm1|bat|cmd|zsh|bash|fish)$", re.I)),
    ("assets", re.compile(r"(^|/)(assets?|public|static|images?|img|media|fonts?)/|\.(png|jpe?g|gif|svg|webp|ico|bmp|mp4|webm|mov|mp3|wav|woff2?|ttf|otf|eot)$", re.I)),
    ("data", re.compile(r"(^|/)(data|datasets?|fixtures?|seeds?)/|\.(csv|tsv|sql|db|sqlite3?|parquet|avro|ndjson|xml)$", re.I)),
    ("frontend", re.compile(r"(^|/)(components?|pages?|views?|ui|client|frontend|web|src/app)/|\.(jsx|tsx|vue|svelte|css|scss|sass|less|styl|html?)$", re.I)),
    ("backend", re.compile(r"(^|/)(api|server|backend|routes?|controllers?|services?|handlers?|models?|middleware|db|migrations?)/|\.(go|rs|rb|java|kt|scala|php|cs|ex|exs|py|pyi)$", re.I)),
    ("config", re.compile(r"(^|/)\.[^/]+rc(\.[a-z0-9]+)?$|(^|/)\.(env|editorconfig|gitignore|gitattributes)$|\.(json|ya?ml|toml|ini|cfg|conf|lock|properties)$", re.I)),
    ("docs", re.compile(r"(^|/)docs?/|\.(md|mdx|rst|txt|adoc)$|(^|/)(README|CHANGELOG|LICENSE|CONTRIBUTING|AUTHORS|NOTICE)(\.[a-z]+)?$", re.I)),
]


def generic_concept(file_path: str, label: str) -> str:
    """Generic file-kind/location bucket -- the shipped default taxonomy.

    Returns one of: tests, workflows, scripts, assets, data, frontend, backend,
    config, docs, or 'other'. Repo-agnostic; no project vocabulary.
    """
    target = (file_path or label or "").replace("\\", "/")
    for name, pat in GENERIC_CONCEPTS:
        if pat.search(target):
            return name
    return "other"


def build_generic_slices(node_info: Dict[str, Dict[str, Any]], degree: Dict[str, int],
                         max_per_slice: int) -> List[Dict[str, Any]]:
    """Top-level-directory slices for generic repos (deterministic; max 12 dirs,
    overflow grouped into 'other directories')."""
    groups: Dict[str, List[str]] = {}
    for nid, info in node_info.items():
        fp = (info.get("file_path") or "").replace("\\", "/")
        top = fp.split("/", 1)[0] if "/" in fp else "(root)"
        groups.setdefault(top or "(root)", []).append(nid)
    ranked = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    main, overflow = ranked[:12], ranked[12:]
    if overflow:
        rest = [nid for _, ids in overflow for nid in ids]
        main.append(("other directories", rest))
    out: List[Dict[str, Any]] = []
    for name, ids in main:
        ids.sort(key=lambda i: (-degree.get(i, 0), i))
        kept = ids[:max_per_slice]
        warnings = []
        if len(ids) > len(kept):
            warnings.append(f"capped: {len(ids)} matched, top {len(kept)} by degree kept")
        out.append(dict(spec_id=f"dir-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') or 'root'}",
                        label=name, purpose="top-level directory (generic structure)",
                        node_ids=kept, matched=len(ids), warnings=warnings))
    return out


GENERIC_TOTAL_CAP = 4000


def custom_coverage_ok(slices_sel: List[Dict[str, Any]]) -> bool:
    """A custom (local-config) taxonomy is only honest when its named slices
    genuinely describe the repo. A repo it was not written for picks up a few
    accidental substring matches and must fall back to generic structure.
    Threshold: >=4 slices with >=5 matches; otherwise use generic directories."""
    return sum(1 for s in slices_sel if s["matched"] >= 5) >= 4


def cap_generic_total(slices_sel: List[Dict[str, Any]], used_ids: List[str],
                      degree: Dict[str, int]) -> List[str]:
    """Generic mode at function-level scale (8k+ nodes) exceeds what the 3D
    view holds; keep the top GENERIC_TOTAL_CAP by degree (deterministic)."""
    if len(used_ids) <= GENERIC_TOTAL_CAP:
        return used_ids
    ranked = sorted(used_ids, key=lambda i: (-degree.get(i, 0), i))
    keep = set(ranked[:GENERIC_TOTAL_CAP])
    for s in slices_sel:
        before = len(s["node_ids"])
        s["node_ids"] = [i for i in s["node_ids"] if i in keep]
        trimmed = before - len(s["node_ids"])
        if trimmed:
            s["warnings"].append(
                f"global cap: {trimmed} low-degree nodes trimmed (total cap {GENERIC_TOTAL_CAP})")
    return sorted(keep)


def build_slices(node_info: Dict[str, Dict[str, Any]], degree: Dict[str, int],
                 max_per_slice: int) -> List[Dict[str, Any]]:
    """Select per-slice node id lists (deterministic: degree desc, then id asc)."""
    out: List[Dict[str, Any]] = []
    for spec in SLICES:
        ids: List[str] = []
        for nid, info in node_info.items():
            if info["concept"] in spec["concepts"] or (
                    spec["extra"] is not None and (
                        spec["extra"].search(info["file_path"]) or spec["extra"].search(info["label"]))):
                ids.append(nid)
        matched = len(ids)
        ids.sort(key=lambda i: (-degree.get(i, 0), i))
        kept = ids[:max_per_slice]
        warnings = []
        if matched > len(kept):
            warnings.append(f"capped: {matched} matched, top {len(kept)} by degree kept")
        if matched == 0:
            warnings.append("empty slice: no nodes matched in this graph build")
        out.append(dict(spec_id=spec["id"], label=spec["label"], purpose=spec["purpose"],
                        node_ids=kept, matched=matched, warnings=warnings))
    return out


def build_read_model(graph: Dict[str, Any], *, repo_root: str, source_graph_path: str,
                     max_per_slice: int = DEFAULT_MAX_PER_SLICE,
                     generated_at: Optional[str] = None,
                     mode: str = "auto") -> Dict[str, Any]:
    """Build the compact deterministic read model from a loaded Graphify graph."""
    raw_nodes = len(graph.get("nodes", []))
    raw_edges = len(graph.get("links", []))
    all_info, degree, adj = _build_index(graph)

    hidden_counts: Dict[str, int] = defaultdict(int)
    node_info: Dict[str, Dict[str, Any]] = {}
    for nid, info in all_info.items():
        rule = should_hide_node(info["file_path"])
        if rule:
            hidden_counts[rule] += 1
            continue
        info = dict(info)
        info["concept"] = classify_node(info["file_path"], info["label"])
        info["degree"] = degree.get(nid, 0)
        node_info[nid] = info

    slice_mode = "custom-taxonomy"
    slices_sel = []
    used_ids = []
    if mode != "generic" and CONCEPT_RULES and SLICES:
        # A custom taxonomy is only attempted when a local config supplied one;
        # the shipped default has neither, so this branch is skipped entirely.
        slices_sel = build_slices(node_info, degree, max_per_slice)
        used_ids = sorted({nid for s in slices_sel for nid in s["node_ids"]})
        if mode == "auto" and used_ids and not custom_coverage_ok(slices_sel):
            # Accidental substring matches on a repo the custom taxonomy was not
            # written for must NOT keep custom mode -- fall through to generic.
            slices_sel, used_ids = [], []
    if not used_ids and node_info:
        # Generic structure (G5P.4 fallback; now also the forced/auto path):
        # concepts = file-kind buckets, slices = top-level directories.
        slice_mode = "generic-structure"
        for info in node_info.values():
            info["concept"] = generic_concept(info["file_path"], info["label"])
        slices_sel = build_generic_slices(node_info, degree, max_per_slice)
        used_ids = sorted({nid for s in slices_sel for nid in s["node_ids"]})
        used_ids = cap_generic_total(slices_sel, used_ids, degree)
    used_set = set(used_ids)

    # induced edges on the union, deduped (max weight), deterministic cap
    best: Dict[Tuple[str, str], float] = {}
    for a in used_ids:
        for b, w in adj.get(a, ()):
            if b in used_set and a < b:
                key = (a, b)
                if w > best.get(key, -1.0):
                    best[key] = w
    edges_sorted = sorted(best.items(), key=lambda kv: (-kv[1], kv[0]))[:MAX_EDGES]

    nodes_out = [
        dict(id=i, label=node_info[i]["label"], file_path=node_info[i]["file_path"],
             concept=node_info[i]["concept"], degree=node_info[i]["degree"],
             community=node_info[i]["community"])
        for i in used_ids
    ]
    edge_index = {(a, b) for (a, b), _ in edges_sorted}
    slices_out = []
    for s in slices_sel:
        sset = set(s["node_ids"])
        e_count = sum(1 for (a, b) in edge_index if a in sset and b in sset)
        concept_counts: Dict[str, int] = defaultdict(int)
        for nid in s["node_ids"]:
            concept_counts[node_info[nid]["concept"]] += 1
        top = [dict(id=i, label=node_info[i]["label"], degree=node_info[i]["degree"])
               for i in s["node_ids"][:10]]
        slices_out.append(dict(
            id=s["spec_id"], label=s["label"], purpose=s["purpose"],
            node_count=len(s["node_ids"]), edge_count=e_count, matched=s["matched"],
            top_nodes=top, concept_counts=dict(sorted(concept_counts.items())),
            node_ids=s["node_ids"], warnings=s["warnings"]))

    return dict(
        metadata=dict(
            generated_at=generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
            repo_root=repo_root,
            source_graph_path=source_graph_path,
            source_graph_exists=True,
            graph_build_mode="code-only (docs/images semantic layer NOT built)",
            graph_built_at_commit=str(graph.get("built_at_commit") or "unknown"),
            total_source_nodes=raw_nodes,
            total_source_edges=raw_edges,
            slice_mode=slice_mode,
            mode_requested=mode,
            filtered_nodes=len(node_info),
            filtered_edges_estimate=sum(degree[n] for n in node_info) // 2,
            emitted_nodes=len(nodes_out),
            emitted_edges=len(edges_sorted),
            hidden_noise_counts=dict(sorted(hidden_counts.items())),
            max_per_slice=max_per_slice,
        ),
        warnings=list(WARNINGS),
        slices=slices_out,
        nodes=nodes_out,
        edges=[dict(source=a, target=b, weight=w) for (a, b), w in edges_sorted],
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Graphify -> Hivemind read-model adapter (G2)")
    ap.add_argument("--graph", default=str(DEFAULT_GRAPH))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--max-per-slice", type=int, default=DEFAULT_MAX_PER_SLICE)
    ap.add_argument("--mode", choices=["auto", "custom", "generic"], default="auto",
                    help="slice mode: auto (use the local custom taxonomy if it covers the repo, "
                         "else generic), custom (force the local-config taxonomy), "
                         "generic (file-kind concepts + top-level-dir slices)")
    ap.add_argument("--fixed-time", default=None,
                    help="ISO timestamp for deterministic output (tests/diffing)")
    args = ap.parse_args(argv)

    graph_path = Path(args.graph)
    if not graph_path.exists():
        print(f"[graphify-hivemind-readmodel] source graph not found: {graph_path}")
        print("Run `graphify update .` first (or pass --graph). Nothing written; exit 1.")
        return 1

    graph = load_graph(graph_path)
    model = build_read_model(
        graph, repo_root=str(Path.cwd()), source_graph_path=str(graph_path),
        max_per_slice=args.max_per_slice, generated_at=args.fixed_time, mode=args.mode)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(model, fh, indent=1, sort_keys=True)

    md = model["metadata"]
    print("[graphify-hivemind-readmodel] OK")
    print(f"  source graph        : {md['source_graph_path']} (exists)")
    print(f"  source nodes/edges  : {md['total_source_nodes']} / {md['total_source_edges']}")
    print(f"  after noise filters : {md['filtered_nodes']} nodes "
          f"(hidden: {sum(md['hidden_noise_counts'].values())} -> {md['hidden_noise_counts']})")
    print(f"  emitted             : {md['emitted_nodes']} nodes / {md['emitted_edges']} edges "
          f"across {len(model['slices'])} slices (cap {md['max_per_slice']}/slice)")
    for s in model["slices"]:
        print(f"    - {s['id']:<26} {s['node_count']:>5} nodes  {s['edge_count']:>6} edges"
              + (f"  [{'; '.join(s['warnings'])}]" if s["warnings"] else ""))
    print(f"  build mode          : {md['graph_build_mode']}")
    print(f"  built_at_commit     : {md['graph_built_at_commit']}")
    print(f"  output              : {out_path}  (gitignored; never commit)")
    for w in model["warnings"]:
        print(f"  warning             : {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
