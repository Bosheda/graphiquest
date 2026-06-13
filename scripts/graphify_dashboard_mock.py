#!/usr/bin/env python3
"""Graphify Knowledge Graph dashboard — local prototype generator (G5D-corrected v2).

Deterministically regenerates the IGNORED local prototype at
graphify-out/views/graphify-dashboard.html, visually mirroring the
reference video's Knowledge Graph dashboard: left rail (Home / Skills /
Memory / Knowledge Graph / Activity + small HERMES / CLAUDE CODE agent
badges), clean project cards, a large dark molten-brain graph viewport
(live iframe embed of the local 3D molten-core viewer), a compact right stats panel (files / links / clusters / map confidence /
most important files / est. savings / selected node), and small query
chips. Less text, less governance, more graph — heavy governance and
asset provenance live in the evidence docs, NOT in this UI.

Architecture: standalone/local GraphiQuest dashboard. Any repo the user points
it at is just a project card — there is no privileged host project.

Stdlib only. Reads live counts from graphify-out/hivemind/read-model.json
when present. The viewport embeds the LOCAL 3D molten-brain viewer
(brain-3d-prototype.html — connected molten cores; Graphify clusters map
to brain regions/nuclei). Iframe is prototype-only (this page is ignored).
Output is gitignored.

Usage: python scripts/graphify_dashboard_mock.py
"""
from __future__ import annotations

import html
import json
import pathlib

OUT = pathlib.Path("graphify-out/views/graphify-dashboard.html")
READ_MODEL = pathlib.Path("graphify-out/hivemind/read-model.json")


def live_counts() -> dict:
    base = {"nodes": "—", "edges": "—", "slices": "—", "built_at": "read-model absent", "mode": "code-only"}
    if not READ_MODEL.exists():
        return base
    try:
        rm = json.loads(READ_MODEL.read_text(encoding="utf-8"))
        meta = rm.get("metadata", {})

        def fmt(key: str) -> str:
            v = meta.get(key, "—")
            return f"{v:,}" if isinstance(v, int) else str(v)

        return {
            "nodes": fmt("emitted_nodes"),
            "edges": fmt("emitted_edges"),
            "slices": str(len(rm.get("slices", [])) or "—"),
            "built_at": str(meta.get("graph_built_at_commit", "unknown"))[:10],
            "mode": str(meta.get("graph_build_mode", "code-only")),
        }
    except (json.JSONDecodeError, OSError):
        return base


C = live_counts()


def view_hash(name: str) -> str:
    """8-char content hash of a sibling generated view -- cache-bust that tracks
    GENERATOR changes, not just graph rebuilds (G5M: ?b=built_at proved useless
    when only the generator changed; Chrome kept serving stale views)."""
    import hashlib
    f = pathlib.Path("graphify-out/views") / name
    if not f.exists():
        return C["built_at"]
    return hashlib.md5(f.read_bytes()).hexdigest()[:8]


H3D = view_hash("brain-3d-prototype.html")
H2D = view_hash("graph-explorer.html")


def concept_counts() -> list:
    """Concept keys+counts from the SAME read-model the 2D explorer embeds --
    the right-panel CONCEPTS card must match the explorer checklist exactly
    (sorted keys == the explorer's [...new Set(...)].sort()). [] on any error
    so the dashboard still renders without a read-model (live_counts parity)."""
    try:
        from collections import Counter
        rm = json.loads(READ_MODEL.read_text(encoding="utf-8"))
        cnt = Counter(n.get("concept", "unknown") for n in rm.get("nodes", []))
        return [(k, cnt[k]) for k in sorted(cnt)]
    except Exception:
        return []


CONCEPTS = concept_counts()
CONCEPT_ROWS = "".join(
    f'<label class="crow"><input type="checkbox" checked data-key="{html.escape(k)}"/>'
    f'<span class="crow__n">{html.escape(k)}</span><span class="crow__c">{c}</span></label>'
    for k, c in CONCEPTS
)

# ---- G5P.2: tracked local-first project registry (graphify.projects.json) ----
REG_FILE = pathlib.Path("graphify.projects.json")

STATUS_LABEL = {
    "missing_repo_path": "no repo path — connect in Settings",
    "not_graphed": "not graphed yet",
    "graph_missing": "graph missing — regenerate",
    "rebuild_required": "rebuild required",
    "repo_path_configured": "path configured — not generated",
    "command_prepared": "command prepared — run it manually",
    "waiting_for_manual_run": "waiting for manual run",
    "generating": "generating…",
    "generated_pending_reload": "generated — views not built yet",
    "generated_incompatible": "generated — incompatible output",
    "pending": "pending setup",
    "error": "registry error",
}
KIND_CHIP = {"monorepo": "MONOREPO", "monorepo-slice": "SLICE", "future": "FUTURE", "import-slot": "IMPORT", "local": "LOCAL"}


def load_projects() -> list:
    """Tracked registry -> honest project list. 'ready' is DEMOTED to
    'graph_missing' when the read-model is absent at build time; counts are
    filled from the live read-model for ready graphs only (never stored)."""
    try:
        reg = json.loads(REG_FILE.read_text(encoding="utf-8"))
        allowed = set(reg.get("allowed_statuses", []))
        out = []
        for p in reg.get("projects", []):
            p = dict(p)
            if p.get("graphStatus") not in allowed:
                p["graphStatus"], p["statusMessage"] = "error", "invalid status in registry"
            if p.get("graphStatus") == "ready":
                rm = pathlib.Path(str(p.get("readModelPath") or ""))
                if rm.exists():
                    p["nodeCount"], p["edgeCount"], p["conceptCount"] = C["nodes"], C["edges"], len(CONCEPTS)
                    p["lastGraphedAt"] = C["built_at"]
                else:
                    p["graphStatus"] = "graph_missing"
                    p["statusMessage"] = "registry says ready but the read-model is missing — regenerate the graph"
            out.append(p)
        return out
    except Exception:
        return []


PROJECTS = load_projects()
REGISTRY_JS = json.dumps(PROJECTS)
CONCEPTS_JS = json.dumps(CONCEPTS)

# (id, name, chip, selected, description, stats-line) -- stats line is the honest
# status for non-ready projects; real counts only for ready graphs.
CARDS = [
    (p["id"], p["label"], KIND_CHIP.get(p.get("kind"), "PROJECT"),
     bool(p.get("isDefault")) and p["graphStatus"] == "ready",
     p["description"],
     f"{C['nodes']} nodes · {C['slices']} clusters" if p["graphStatus"] == "ready"
     else STATUS_LABEL.get(p["graphStatus"], p["graphStatus"]))
    for p in PROJECTS
]

CHIPS = ["What does this project do?", "How do I run it?", "Give me a quick tour", "Is anything broken or risky?",
         "What changed since last graph update?", "Which model/agent should handle this?"]

# G5E premium material plates (IGNORED staging; Juggernaut txt2img via
# scripts/graphify_ui_materials_gen.py -- materials only, never fake UI).
# Every surface keeps a solid-color fallback under the image layer.
MAT = "../design/graphify-ui-materials"


def graphify_version() -> str:
    """Best-effort `graphify --version` at DASHBOARD BUILD time (honest label in
    Settings). Never blocks generation -- 'not detected' on any failure."""
    try:
        import subprocess
        r = subprocess.run(["graphify", "--version"], capture_output=True, text=True, timeout=10)
        out = (r.stdout or "").strip()
        return out if out else "not detected"
    except Exception:
        return "not detected"


GFY_VER = graphify_version()

# ---- G5P.1 shell sections (Skills / How To / Activity / Settings / Memory) ----
# Plain strings (NOT f-strings) so CSS/JS braces stay single; injected into the
# page f-string via {SECTIONS_CSS} / {SECTIONS_HTML} / {SHELL_JS}. Tokens
# @@...@@ are replaced below with build-time values.
SECTIONS_CSS = """
 /* ==== G5P.1 shell sections: glass overlay over the stage, hero untouched */
 #sections{position:absolute;inset:0;z-index:60;display:none;flex-direction:column;background:linear-gradient(180deg,rgba(8,8,9,.965),rgba(11,11,13,.975));-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);border-radius:14px;border:1px solid var(--line);box-shadow:var(--bevel),var(--depth);overflow:hidden}
 body.sec-open #sections{display:flex}
 .sec{display:none;flex:1;min-height:0;overflow-y:auto;padding:22px 26px 26px}
 .sec.on{display:block}
 .sec::-webkit-scrollbar{width:7px}
 .sec::-webkit-scrollbar-thumb{background:rgba(255,255,255,.12);border-radius:4px}
 .sec::-webkit-scrollbar-track{background:transparent}
 .sec h2{font:600 19px var(--disp);letter-spacing:.04em;color:var(--ink);margin:0 0 4px}
 .sec .sec-sub{font:400 12.5px var(--ui);color:var(--steel-300);margin:0 0 16px;max-width:760px}
 .sec h3{font:600 11.5px var(--ui);letter-spacing:.15em;text-transform:uppercase;color:var(--steel-200);margin:20px 0 8px}
 .gcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:10px}
 .gcard{background:rgba(16,16,18,.55);border:1px solid var(--steel-700);border-radius:10px;padding:11px 13px;font:400 12px/1.5 var(--ui);color:var(--steel-200)}
 .gcard b{display:block;font:600 12.5px var(--ui);color:var(--ink);margin-bottom:2px}
 .gcard p{margin:4px 0}
 .gcard .gmeta{color:var(--steel-300);font-size:11px}
 .gcard code,.sec code{font:500 11px var(--mono);color:var(--molten-hot);background:rgba(255,122,24,.07);border:1px solid rgba(255,122,24,.18);border-radius:5px;padding:1px 5px}
 .gcard .cmd{display:block;margin:5px 0 0;padding:6px 9px;background:rgba(0,0,0,.45);border:1px solid var(--steel-700);border-radius:7px;font:500 11px var(--mono);color:var(--steel-100);overflow-x:auto;white-space:pre}
 .st{display:inline-block;font:700 9.5px var(--ui);letter-spacing:.1em;border-radius:var(--pill);padding:2.5px 8px;margin-left:7px;vertical-align:1px;border:1px solid}
 .st--imp{color:var(--good);border-color:rgba(74,222,128,.4);background:rgba(74,222,128,.08)}
 .st--part{color:var(--molten-hot);border-color:rgba(255,138,56,.45);background:rgba(255,122,24,.08)}
 .st--plan{color:var(--steel-300);border-color:var(--steel-700);background:rgba(255,255,255,.03)}
 .st--ext{color:var(--link);border-color:rgba(96,165,250,.4);background:rgba(96,165,250,.07)}
 .st--gate{color:#fbbf24;border-color:rgba(251,191,36,.4);background:rgba(251,191,36,.07)}
 .hguide p,.hguide li{font:400 12.5px/1.65 var(--ui);color:var(--steel-100)}
 .hguide ul{margin:4px 0 10px;padding-left:18px}
 .hguide kbd{font:500 10.5px var(--mono);color:var(--ink);background:rgba(255,255,255,.07);border:1px solid var(--steel-700);border-bottom-width:2px;border-radius:5px;padding:1px 6px}
 .arow{display:flex;gap:10px;align-items:baseline;padding:7px 10px;border-bottom:1px solid rgba(255,255,255,.05);font:400 12px var(--ui);color:var(--steel-100)}
 .arow .at{font:500 10.5px var(--mono);color:var(--steel-300);flex:none}
 .arow .as{flex:none}
 .arow .aq{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
 .aempty{font:400 12px var(--ui);color:var(--steel-300);padding:10px 2px}
 /* G5P.3a: the auto-fill masonry broke once cards grew (operator screenshots:
    unbalanced columns, dead zones). Settings is now sub-nav + ONE active card. */
 .sec--settings.on{display:flex;flex-direction:column}
 .sec--settings h2,.sec--settings .sec-sub{flex:none}
 #setwrap{flex:1;min-height:0;display:flex;gap:16px}
 #setnav{flex:none;width:188px;display:flex;flex-direction:column;gap:4px}
 #setnav .sn{font:500 12px var(--ui);color:var(--steel-200);border:1px solid transparent;border-radius:9px;padding:8px 12px;cursor:pointer;letter-spacing:.02em}
 #setnav .sn:hover{color:var(--ink);border-color:var(--steel-700)}
 #setnav .sn.on{color:var(--molten-hot);background:rgba(255,122,24,.08);border-color:rgba(255,138,56,.4)}
 #setbody{flex:1;min-width:0;overflow-y:auto;padding-right:8px}
 #setbody::-webkit-scrollbar{width:7px}
 #setbody::-webkit-scrollbar-thumb{background:rgba(255,255,255,.12);border-radius:4px}
 #setbody::-webkit-scrollbar-track{background:transparent}
 #setbody>.gcard{display:none;max-width:880px}
 #setbody>.gcard.on{display:block}
 .gcard .cmd::-webkit-scrollbar{height:6px}
 .gcard .cmd::-webkit-scrollbar-thumb{background:rgba(255,255,255,.14);border-radius:4px}
 .gcard .cmd::-webkit-scrollbar-track{background:transparent}
 .rrow__h{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
 .rrow__h .st{margin-left:0}
 .rrow__h .rbtn{margin:0 0 0 auto}
 .rrow__btns{display:flex;gap:7px;flex-wrap:wrap;margin-top:7px}
 .rrow__btns .rbtn{margin:0}
 .conn-warn{font:600 11px var(--ui);color:#fbbf24;border:1px solid rgba(251,191,36,.35);background:rgba(251,191,36,.06);border-radius:8px;padding:7px 10px;margin-top:7px}
 .sec-close{position:absolute;top:14px;right:18px;z-index:5;font:600 10.5px var(--ui);letter-spacing:.1em;color:var(--steel-200);border:1px solid var(--steel-700);border-radius:var(--pill);padding:4px 12px;cursor:pointer;background:rgba(18,18,18,.6)}
 .sec-close:hover{border-color:var(--molten);color:var(--ink)}
 .mrow2{display:flex;gap:9px;align-items:baseline;padding:7px 10px;border-bottom:1px solid rgba(255,255,255,.05);font:400 12px var(--ui);color:var(--steel-100)}
 .mrow2 .mt{font:500 10.5px var(--mono);color:var(--steel-300);flex:none}
 .mrow2 .mq{flex:1;min-width:0}
 .mrow2 .rbtn{margin:0;flex:none}
 select.rin{appearance:none;background:rgba(0,0,0,.45)}
 select.rin option{background:#0b0b0d;color:var(--ink)}
 .gflash{animation:gflash 1.6s ease 2}
 @keyframes gflash{0%,100%{border-color:var(--steel-700)}45%{border-color:var(--molten);box-shadow:0 0 0 3px var(--glow)}}
 .nav{cursor:pointer}
 /* ==== G5P.6 top strip: compact, rule-based, release-clean */
 #cards{display:flex;gap:9px;overflow-x:auto;padding-bottom:4px;align-items:stretch}
 #cards::-webkit-scrollbar{height:6px}
 #cards::-webkit-scrollbar-thumb{background:rgba(255,255,255,.12);border-radius:4px}
 #cards::-webkit-scrollbar-track{background:transparent}
 #cards .card{flex:0 0 215px;min-height:74px;display:flex;flex-direction:column;justify-content:space-between}
 .card__act{display:flex;gap:5px;margin-top:5px}
 .card__act .ca{font:700 9px var(--ui);letter-spacing:.09em;color:var(--steel-200);border:1px solid var(--steel-700);border-radius:var(--pill);padding:2.5px 9px;cursor:pointer;background:rgba(0,0,0,.35)}
 .card__act .ca:hover{border-color:var(--molten);color:var(--ink)}
 .card--add{flex:0 0 150px;display:flex;align-items:center;justify-content:center;text-align:center;border-style:dashed;color:var(--steel-300);font:600 11.5px var(--ui);cursor:pointer}
 .card--add:hover{border-color:var(--molten);color:var(--molten-hot)}
 /* ==== G5P.6 Add Project modal */
 #addmodal{position:fixed;inset:0;z-index:90;display:none;align-items:center;justify-content:center;background:rgba(0,0,0,.55);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px)}
 body.addmodal #addmodal{display:flex}
 #addmodal .am{width:480px;max-width:92vw;background:linear-gradient(160deg,rgba(16,17,20,.97),rgba(8,9,11,.98));border:1px solid var(--line2);border-radius:14px;box-shadow:var(--bevel),var(--depth);padding:20px 22px}
 #addmodal h4{font:600 15px var(--disp);letter-spacing:.04em;color:var(--ink);margin:0 0 2px}
 #addmodal .am-sub{font:400 11.5px var(--ui);color:var(--steel-300);margin:0 0 12px}
 #addmodal label{display:block;font:600 10px var(--ui);letter-spacing:.12em;text-transform:uppercase;color:var(--steel-300);margin:10px 0 4px}
 #addmodal .am-note{font:400 11px var(--ui);color:var(--steel-300);margin-top:6px}
 #addmodal .am-status{font:500 11px var(--ui);margin-top:8px;min-height:15px}
 #addmodal .am-btns{display:flex;gap:8px;justify-content:flex-end;margin-top:14px}
 #addmodal .st--plan{vertical-align:2px}
 #addmodal input[disabled]{opacity:.45}
 .am-opt{display:block;width:100%;text-align:left;background:rgba(18,18,18,.6);border:1px solid var(--steel-700);border-radius:11px;padding:13px 15px;cursor:pointer;color:var(--steel-100)}
 .am-opt:hover{border-color:var(--molten);box-shadow:0 0 0 3px var(--glow)}
 .am-opt b{display:block;font:600 13px var(--ui);color:var(--ink);margin-bottom:3px}
 .am-opt span{font:400 11.5px var(--ui);color:var(--steel-300)}
 .am-opt[disabled]{opacity:.45;cursor:not-allowed}
 .am-or{font:600 10px var(--ui);letter-spacing:.14em;text-transform:uppercase;color:var(--steel-300);text-align:center;margin:11px 0}
 .am-optwrap{background:rgba(18,18,18,.6);border:1px solid var(--steel-700);border-radius:11px;padding:13px 15px}
 /* ==== G5P.2 project registry: honest no-graph overlay + repositories flow */
 #nograph{position:absolute;inset:0;z-index:40;display:none;align-items:center;justify-content:center;background:linear-gradient(180deg,rgba(7,7,8,.94),rgba(10,10,12,.96));-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);border-radius:inherit}
 body.nograph #nograph{display:flex}
 #nograph-card{max-width:480px;background:rgba(16,16,18,.7);border:1px solid var(--steel-700);border-radius:12px;padding:22px 26px;font:400 13px/1.6 var(--ui);color:var(--steel-100);text-align:center}
 #nograph-card h4{font:600 16px var(--disp);color:var(--ink);margin:0 0 4px;letter-spacing:.03em}
 #nograph-card .ng-status{display:inline-block;font:700 9.5px var(--ui);letter-spacing:.1em;text-transform:uppercase;border:1px solid rgba(255,138,56,.45);color:var(--molten-hot);background:rgba(255,122,24,.08);border-radius:var(--pill);padding:3px 10px;margin:6px 0 10px}
 #nograph-card .ng-cta{display:inline-block;margin:10px 6px 0;font:600 10.5px var(--ui);letter-spacing:.1em;color:var(--steel-100);border:1px solid var(--steel-700);border-radius:var(--pill);padding:6px 14px;cursor:pointer;background:rgba(18,18,18,.6)}
 #nograph-card .ng-cta:hover{border-color:var(--molten);color:var(--ink)}
 body.nograph #concard #conlist,body.nograph #concard .k--row input{opacity:.3;pointer-events:none}
 body.nograph #statgrid,body.nograph .scard--files{opacity:.3}  /* counts/files describe the LOADED graph, not the selected project (G5P.4 honesty) */
 #con-unavail{display:none;font:400 11px var(--ui);color:var(--steel-300);padding:6px 2px}
 body.nograph #con-unavail{display:block}
 .rrow{border:1px solid var(--steel-700);border-radius:9px;padding:8px 10px;margin:7px 0;background:rgba(0,0,0,.3)}
 .rrow b{font:600 12px var(--ui);color:var(--ink)}
 .rrow .gmeta{margin:3px 0}
 .rin{background:rgba(0,0,0,.45);border:1px solid var(--steel-700);border-radius:7px;color:var(--ink);font:400 11px var(--mono);padding:5px 8px;width:100%;box-sizing:border-box;margin-top:5px}
 .rin:focus{outline:none;border-color:rgba(255,138,56,.5)}
 .rbtn{font:600 10px var(--ui);letter-spacing:.1em;color:var(--steel-100);border:1px solid var(--steel-700);border-radius:var(--pill);padding:4px 12px;cursor:pointer;background:rgba(18,18,18,.6);margin-top:6px}
 .rbtn:hover{border-color:var(--molten);color:var(--ink)}
 .rbtn[disabled]{opacity:.4;cursor:not-allowed}
 .rbtn[disabled]:hover{border-color:var(--steel-700);color:var(--steel-100)}
 .hrep{display:flex;gap:12px;align-items:center;max-width:880px;padding:9px 14px;margin:6px 0;border:1px solid var(--line);border-radius:11px;background:rgba(13,13,13,.55);cursor:pointer}
 .hrep:hover{border-color:var(--steel-500)}
 .hrep--on{border-color:rgba(255,138,56,.45)}
 .hrep .mono{font:500 10.5px var(--mono);color:var(--dim)}
 .hrep .hcounts{margin-left:auto;display:flex;gap:7px;align-items:center}
 .hsev{font:600 9px var(--mono);padding:2px 7px;border-radius:8px;letter-spacing:.4px}
 .hsev--high{background:rgba(248,113,113,.14);color:#f87171}
 .hsev--medium{background:rgba(251,191,36,.13);color:#fbbf24}
 .hsev--low{background:rgba(96,165,250,.12);color:#60a5fa}
 .hsev--info{background:rgba(148,163,184,.12);color:#94a3b8}
 .hkind{font:600 9.5px var(--mono);color:var(--steel-100);letter-spacing:.4px;text-transform:uppercase}
 .cpr{position:relative;display:block}
 .cpr .cpy{position:absolute;top:6px;right:6px}
 .cpy{font:600 9px var(--ui);letter-spacing:.08em;color:var(--steel-100);border:1px solid var(--steel-700);border-radius:7px;padding:3px 9px;cursor:pointer;background:rgba(20,20,20,.85)}
 .cpy:hover{border-color:var(--molten);color:var(--ink)}
 .cpy.ok{border-color:var(--good);color:var(--good)}
 .setup-step{display:flex;gap:11px;margin:11px 0;align-items:flex-start}
 .setup-step .n{flex:none;width:23px;height:23px;border-radius:50%;border:1px solid var(--steel-600);display:flex;align-items:center;justify-content:center;font:600 11px var(--mono);color:var(--steel-100);margin-top:1px}
 .setup-step .b{flex:1;min-width:0}
 .setup-step .b b{font:600 12.5px var(--ui);color:var(--ink)}
 .skrow{display:flex;gap:11px;align-items:flex-start;max-width:880px;padding:9px 13px;margin:5px 0;border:1px solid var(--line);border-radius:10px;background:rgba(13,13,13,.5)}
 .skrow .skmain{flex:1;min-width:0}
 .skrow .skname{font:600 12.5px var(--ui);color:var(--ink)}
 .skrow .skwhat{font:400 11.5px var(--ui);color:var(--ink-soft);margin:2px 0}
 .skrow .skmeta{font:500 10.5px var(--mono);color:var(--dim)}
 .skrow .sknext{font:500 10.5px var(--mono);color:var(--steel-300)}
 .setup-tip{border-left:2px solid rgba(255,138,56,.4);padding:5px 0 5px 11px;margin:8px 0;color:var(--ink-soft);font-size:11.5px}
 #savecard .sv-pct{font:700 26px var(--display,var(--ui));color:var(--good);line-height:1}
 #savecard .sv-row{display:flex;justify-content:space-between;font:500 11px var(--mono);color:var(--ink-soft);margin:3px 0}
 #savecard .sv-row b{color:var(--ink)}
 #savecard .sv-status{font:600 9px var(--mono);letter-spacing:.4px;padding:2px 7px;border-radius:8px;background:rgba(148,163,184,.12);color:#94a3b8}
 .conn-panel{border:1px solid rgba(255,138,56,.3);border-radius:12px;background:rgba(255,138,56,.05);padding:13px 15px;margin:4px 0 12px;max-width:880px}
 .conn-panel .cp-status{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-bottom:9px}
 .conn-panel .cp-led{font:600 10px var(--mono);letter-spacing:.4px;padding:3px 10px;border-radius:9px;background:rgba(148,163,184,.14);color:#94a3b8}
 .conn-panel .cp-led.ok{background:rgba(74,222,128,.15);color:var(--good)}
 .conn-btn{font:600 11px var(--ui);letter-spacing:.04em;color:var(--ink);border:1px solid var(--molten);border-radius:9px;padding:7px 15px;cursor:pointer;background:rgba(255,138,56,.14)}
 .conn-btn:hover{background:rgba(255,138,56,.24)}
 .conn-btn2{font:600 10px var(--ui);letter-spacing:.04em;color:var(--steel-100);border:1px solid var(--steel-700);border-radius:8px;padding:6px 12px;cursor:pointer;background:rgba(20,20,20,.7);margin:3px 5px 0 0}
 .conn-btn2:hover{border-color:var(--molten);color:var(--ink)}
 .conn-btn2.ok{border-color:var(--good);color:var(--good)}
 .conn-banner{font:500 11.5px var(--ui);color:var(--ink-soft);border-left:2px solid var(--good);padding:4px 0 4px 10px;margin:9px 0 2px}
 #skill-filter{display:flex;gap:7px;flex-wrap:wrap;margin:0 0 14px}
 .skf{font:600 10px var(--ui);letter-spacing:.05em;color:var(--steel-100);border:1px solid var(--steel-700);border-radius:999px;padding:5px 13px;cursor:pointer;background:rgba(18,18,18,.6)}
 .skf:hover{border-color:var(--steel-500)}
 .skf.on{border-color:var(--molten);color:var(--ink);background:rgba(255,138,56,.14)}
 .gcard .skact{font:600 10px var(--ui);letter-spacing:.04em;color:var(--ink);border:1px solid var(--molten);border-radius:8px;padding:6px 13px;cursor:pointer;background:rgba(255,138,56,.12);margin-top:8px}
 .gcard .skact:hover{background:rgba(255,138,56,.22)}
 #connmodal{display:none;position:fixed;inset:0;z-index:140;background:rgba(0,0,0,.66);-webkit-backdrop-filter:blur(7px);backdrop-filter:blur(7px);align-items:center;justify-content:center}
 body.connmodal #connmodal{display:flex}
 #connmodal .cm{width:min(760px,94vw);max-height:88vh;overflow-y:auto;overflow-x:hidden;overflow-wrap:anywhere;background:rgba(13,13,13,.97);border:1px solid rgba(255,138,56,.35);border-radius:14px;padding:24px 28px;box-shadow:0 18px 70px rgba(0,0,0,.75)}
 #connmodal h4{margin:0 0 6px;font:700 21px var(--display,var(--ui));color:var(--ink)}
 #connmodal .cm code{overflow-wrap:anywhere;word-break:break-all}
 .cm-led{font:600 11.5px var(--mono);letter-spacing:.4px;padding:5px 13px;border-radius:9px;background:rgba(148,163,184,.14);color:#94a3b8;display:inline-block;margin:6px 0 10px}
 .cm-led.ok{background:rgba(74,222,128,.15);color:var(--good)}
 .cm-led.mid{background:rgba(251,191,36,.13);color:#fbbf24}
 .cm-banner{font:500 13.5px/1.6 var(--ui);color:var(--ink-soft);border-left:2px solid var(--good);padding:7px 0 7px 13px;margin:8px 0 16px}
 .cm-step{display:flex;gap:14px;margin:18px 0;align-items:flex-start}
 .cm-step .n{flex:none;width:27px;height:27px;border-radius:50%;border:1px solid var(--steel-600);display:flex;align-items:center;justify-content:center;font:600 13px var(--mono);color:var(--steel-100)}
 .cm-step .n.ok{border-color:var(--good);color:var(--good)}
 .cm-step .b{flex:1;min-width:0}
 .cm-step .b b{font:600 15px var(--ui);color:var(--ink)}
 .cm-step .hint{font:500 13px/1.55 var(--ui);color:var(--ink-soft);margin:5px 0}
 .cm-step .res{font:500 12px/1.5 var(--mono);color:var(--steel-100);margin:6px 0;white-space:pre-wrap;word-break:break-word}
 .cm-prev{border:1px solid var(--line);border-radius:9px;background:rgba(20,20,20,.7);padding:10px 13px;font:500 12px/1.5 var(--mono);color:var(--ink-soft);margin:8px 0;white-space:pre-wrap;word-break:break-all}
 #connmodal .conn-btn{font-size:12px;padding:10px 18px;margin-top:6px}
 #connmodal .conn-btn2{font-size:11px;padding:8px 14px;margin-top:6px}
 #connmodal .gmeta{font-size:12.5px;line-height:1.55}
 #connmodal .rbtn{font-size:11px;padding:8px 16px}
 #stale-banner{position:fixed;top:14px;left:50%;transform:translateX(-50%);z-index:200;background:rgba(13,13,13,.97);border:1px solid var(--molten);border-radius:11px;padding:11px 18px;font:500 13px var(--ui);color:var(--ink);box-shadow:0 10px 40px rgba(0,0,0,.6);display:flex;align-items:center;gap:4px}
 #stale-banner button{margin-left:10px;font:600 11px var(--ui);letter-spacing:.05em;color:var(--ink);border:1px solid var(--molten);border-radius:8px;padding:6px 14px;cursor:pointer;background:rgba(255,138,56,.16)}
 #stale-banner button:hover{background:rgba(255,138,56,.28)}
 *{scrollbar-width:thin;scrollbar-color:rgba(255,138,56,.16) transparent}
 ::-webkit-scrollbar{width:6px;height:6px}
 ::-webkit-scrollbar-track{background:transparent}
 ::-webkit-scrollbar-thumb{background:rgba(255,138,56,.14);border-radius:6px}
 ::-webkit-scrollbar-thumb:hover{background:rgba(255,138,56,.32)}
 #console .k{display:flex;align-items:center}
 #resp-expand{margin-left:auto;font:600 9px var(--ui);letter-spacing:.06em;color:var(--steel-100);background:transparent;border:1px solid var(--steel-600);border-radius:7px;padding:3px 9px;cursor:pointer}
 #resp-expand:hover{color:var(--ink);border-color:var(--molten)}
 #resp-body .rcard__a{white-space:pre-wrap}
 .rcard__s--pending{color:#fbbf24}
 #chatfly{display:none;position:fixed;top:0;right:0;bottom:0;width:min(560px,92vw);z-index:130;background:rgba(11,11,11,.98);border-left:1px solid rgba(255,138,56,.3);box-shadow:-18px 0 70px rgba(0,0,0,.6);flex-direction:column}
 body.chatfly #chatfly{display:flex}
 #chatfly .cf-head{display:flex;align-items:center;gap:10px;padding:14px 18px;border-bottom:1px solid var(--line)}
 #chatfly .cf-head b{font:700 15px var(--display,var(--ui));color:var(--ink);flex:1}
 #cf-thread{flex:1;overflow-y:auto;padding:14px 18px;display:flex;flex-direction:column;gap:10px}
 .cf-msg{max-width:92%;border-radius:11px;padding:9px 13px;font:500 12.5px/1.55 var(--ui);white-space:pre-wrap;word-break:break-word}
 .cf-msg.q{align-self:flex-end;background:rgba(255,138,56,.14);border:1px solid rgba(255,138,56,.25);color:var(--ink)}
 .cf-msg.a{align-self:flex-start;background:rgba(20,20,20,.85);border:1px solid var(--line);color:var(--ink-soft)}
 .cf-msg .cf-meta{display:block;margin-top:6px;font:600 9px var(--mono);letter-spacing:.4px;color:var(--steel-300)}
 #chatfly .cf-foot{padding:12px 18px;border-top:1px solid var(--line)}
 #cf-in{width:100%;box-sizing:border-box;background:rgba(20,20,20,.8);border:1px solid var(--line);border-radius:9px;color:var(--ink);font:500 13px var(--ui);padding:10px 12px;outline:none}
 #cf-in:focus{border-color:rgba(255,138,56,.4)}
 #chatfly .cf-lanes{display:flex;gap:6px;margin-top:8px;align-items:center}
 #hunt-detail .gcard{max-width:none !important}
 #hunt-detail > h3{max-width:none}
 .hth,.htr{display:grid;grid-template-columns:minmax(240px,1fr) minmax(260px,1.15fr) minmax(240px,1fr) 76px;gap:0 18px;align-items:start}
 .hth{font:600 9.5px var(--ui);letter-spacing:.12em;color:var(--steel-300);padding:10px 12px 6px;border-bottom:1px solid var(--steel-600)}
 .htr{padding:11px 12px;border-bottom:1px solid var(--line);font:500 11.5px/1.5 var(--ui);color:var(--ink-soft)}
 .htr:nth-child(odd){background:rgba(255,255,255,.015)}
 .htr:hover{background:rgba(255,138,56,.04)}
 .htc{min-width:0;overflow-wrap:anywhere}
 .htt{font:600 12px var(--ui);color:var(--ink);margin-top:4px}
 .htc-act{justify-self:end}
 @media (max-width:1500px){.hth,.htr{grid-template-columns:minmax(200px,1fr) minmax(200px,1fr) 70px}.hth span:nth-child(3),.htr .htc:nth-child(3){display:none}}
 #ask-clr,#ask-stop{font:600 9px var(--ui);letter-spacing:.05em;border:1px solid var(--steel-600);border-radius:8px;background:transparent;color:var(--steel-100);padding:4px 9px;cursor:pointer;margin-right:4px}
 #ask-clr:hover{color:var(--ink);border-color:var(--molten)}
 #ask-stop{border-color:rgba(248,113,113,.5);color:#f87171}
 #landing{position:fixed;inset:0;z-index:150;background:radial-gradient(1200px 700px at 50% 30%,rgba(36,16,4,.92),rgba(5,5,5,.99)),#050505;display:flex;align-items:center;justify-content:center}
 #landing .ld{width:min(640px,92vw);text-align:center;padding:34px 38px;background:rgba(13,13,13,.92);border:1px solid rgba(255,138,56,.35);border-radius:16px;box-shadow:0 24px 90px rgba(0,0,0,.8)}
 #landing h1{margin:0 0 6px;font:700 26px var(--display,var(--ui));color:var(--ink)}
 #landing .ld-sub{font:500 13.5px/1.6 var(--ui);color:var(--ink-soft);margin:0 0 18px}
 #landing .ld-btn{font:700 13px var(--ui);letter-spacing:.06em;color:#1a0d04;background:linear-gradient(180deg,#ffb066,#ff8a38);border:none;border-radius:11px;padding:14px 34px;cursor:pointer}
 #landing .ld-btn:hover{filter:brightness(1.08)}
 #landing .ld-btn[disabled]{opacity:.6;cursor:wait}
 #landing .ld-stat{font:500 12px var(--mono);color:var(--steel-100);margin:14px 0 0;min-height:18px;white-space:pre-wrap}
 #landing .ld-man{font:500 11.5px var(--ui);color:var(--steel-300);margin-top:16px}
 #landing .ld-man code{color:var(--ink-soft)}
"""

_SK = []


def _skill(name, st, stlbl, purpose, enables, src, req, deps="", action=None):
    d = f'<p class="gmeta">{deps}</p>' if deps else ""
    a = (f'<button class="skact" data-action="{action[1]}">{action[0]}</button>'
         if action else "")
    _SK.append(
        f'<div class="gcard" data-st="{st}"><b>{name}<span class="st st--{st}">{stlbl}</span></b>'
        f'<p>{purpose}</p><p class="gmeta">enables: {enables}</p>'
        f'<p class="gmeta">source: {src} · {req}</p>{d}{a}</div>')


_skill("Graphify scan / read-model", "ext", "EXTERNAL", "Scans a repo into the structural graph + read-model this dashboard renders. This pre-mapping is what lets the model query targeted context instead of re-reading the whole repo (see context savings).",
       "nodes, edges, clusters, concepts — and big token savings", "graphify (uv tool, external dependency)", "required for install/use",
       "deps: python, uv; cmd: <code>graphify update .</code>", action=("Open Graphify settings", "set-graphify"))
_skill("3D Hivemind visualization", "imp", "IMPLEMENTED", "Molten-brain 3D view: region anatomy, pathway lighting, camera glide, motion controls, palettes.",
       "explore the whole graph spatially", "this repo (scripts/graphify_brain3d.py)", "core feature")
_skill("2D structural explorer", "imp", "IMPLEMENTED", "2D Brain + Structural slice views with search, inspector, slice chips and Tools drawer.",
       "slice-level structure + node inspection", "this repo (scripts/graphify_hivemind_explorer.py)", "core feature")
_skill("Local graph QA (Ask Console)", "imp", "IMPLEMENTED", "Two lanes: Graphify answers locally (natural phrasing OK; most-connected, find/jump, counts, concepts, slices); the Claude Code lane asks YOUR connected Claude and renders the answer right here (one real call per ask, STOP to cancel, CLR to clear). Answers selected/connected/concepts/slice/count questions from the local graph only.",
       "graph-aware answers without any agent", "this repo (dashboard generator)", "core feature")
_skill("Node lookup / jump", "imp", "IMPLEMENTED", "Ask \u201cfind &lt;name&gt;\u201d / \u201cjump to &lt;name&gt;\u201d \u2014 glides the 3D camera or focuses the 2D explorer on the best match (exact &gt; prefix &gt; contains, then degree).",
       "fast navigation to a named node", "this repo (G5P.1 + G5P.8)", "3D + 2D wired")
_skill("Hunter — project auditor", "imp", "LOCAL-FIRST", "Graph-first auditor: hunts orphan candidates, disconnected groups, possible missing links (same folder, no connections), single-link leaves, hotspots, and stale/incomplete graph signals — locally, from the selected project's own graph.",
       "actionable findings with jump-to-node; accept or ignore freely", "this repo (Reports section)", "local read-model only · no code edits · no remote scan · no model call",
       'findings stay conservative (\u201ccandidate / possible / inspect\u201d) \u2014 graph evidence, not proof of bugs · model enrichment stays gated',
       action=("Run Hunter", "run-hunter"))
_skill("Trace (path / chain)", "imp", "IMPLEMENTED", "\u201cTrace this node\u201d, \u201cshortest path A\u2192B\u201d, \u201cchain end\u201d over the local edge list (plain BFS); wired in the ask console.",
       "dependency walks without leaving the graph", "this repo (ask console, G5Q.1u)", "wired \u2014 BFS over local edges (no model call)")
_skill("Orphan / disconnect detection", "imp", "IMPLEMENTED", "\u201cWhat is orphaned / not connected?\u201d \u2014 answered by Hunter's connected-components + zero-degree passes over the local edges (ask console wired).",
       "graph health answers", "this repo (Hunter, G5P.9)", "wired via Hunter + ask console")
_skill("Dashboard visual QA", "imp", "IMPLEMENTED", "Browser verification battery: frame-sampled view switches, console-error sweeps, regression checks.",
       "every change ships visually verified", "operator process (doc 48 evidence)", "build/support skill")
_skill("Install / setup", "imp", "IMPLEMENTED", "Hook safe-installer + hygiene utilities exist; one-command product installer is planned.",
       "reproducible setup on a fresh machine", "this repo (scripts/install_graphify_hooks_safe.py)", "packaging planned")
_skill("Hook / process hygiene", "imp", "IMPLEMENTED", "Watchdogged hooks + stale-rebuild checker/cleaner so no process can pile up or hang.",
       "no stale CPU-burning processes", "this repo (scripts/cleanup_graphify_processes.py, 9/9 tests)", "support skill")
_skill("Local generate/rebuild bridge", "imp", "IMPLEMENTED", "Loopback-only bridge (127.0.0.1): allowlisted graphify update in a validated repo path, then read-model + per-project view generation. Honest manual command-pack fallback when not running.",
       "RUN GRAPHIFY from Settings \u2192 Repositories", "this repo (scripts/graphify_dashboard_bridge.py)", "optional \u00b7 manual fallback always works",
       "one rebuild at a time \u00b7 watchdog \u00b7 proof-checked \u00b7 manifest per project", action=("Open Repositories", "set-repos"))
_skill("Project graph switching", "imp", "IMPLEMENTED", "Selecting a ready project loads ITS graph: 3D/2D views, counts, Concepts and Ask Console all follow. Real output detection via the bridge scan; no project ever wears another project\u2019s graph.",
       "true multi-project local graphs", "this repo (G5P.4)", "needs the bridge for detection \u00b7 statuses honest without it")
_skill("Claude Code connector", "gate", "GATED", "THE connector: a real local MCP server SHIPS with this dashboard (scripts/graphify_mcp_server.py) and one click (REGISTER FOR ME) runs Claude Code\u2019s own <code>claude mcp add</code> for it. The wizard live-detects the claude CLI, the Graphify scanner, and the registration (it reads Claude Code\u2019s settings, never writes them). No call is ever made until you approve it inside Claude Code.",
       "ask Claude Code about your graphs \u2014 it reads them through the local server", "this repo + external (Claude Code)", "optional",
       "status ladder: setup required \u2192 registered \u2192 verified by you (claude mcp list) \u00b7 guided wizard", action=("Connect Claude Code", "set-claudecode"))
_skill("Token / context savings", "imp", "PROVEN", "Proves WHY Graphify helps: RUN SAVINGS CHECK estimates full-map vs focused-query tokens (chars/4, honestly labelled). MEASURED once for real (2026-06-11, two live claude -p calls on the graphify project): assisted 6,842 graph tokens / $0.64 vs full-graph-inlined 831,584 tokens / $8.39 \u2014 99.2% fewer tokens, 92% cheaper.",
       "a visible value metric: query structured context instead of re-reading the repo", "this repo (G5Q.1e)", "estimate now \u00b7 measured Claude-token mode is gated",
       "Claude-only = full read-model \u00b7 Graphify-assisted = top files + neighbors + concepts + slices + Hunter \u00b7 result stored locally", action=("Run savings check", "run-savings"))
_skill("Skills registry / packs", "imp", "MINIMAL", "A real LOCAL pack registry ships: the <b>Graph exporters</b> pack adds two ask commands — <code>export summary</code> (downloads a Markdown graph summary) and <code>copy stats</code> (clipboard). Install/remove with the button below; commands answer honestly when the pack is off. A remote/community registry is still planned.",
       "extensibility — commands ship as installable packs", "this repo (G5Q.1u)", "local packs now · remote registry planned",
       "1 pack ships: Graph exporters · state in this browser (graphify-packs-v1)", action=("Install / remove pack", "toggle-pack-exporters"))

SKILLS_CARDS = "".join(_SK)

SECTIONS_HTML = """
<div id="addmodal"><div class="am">
 <h4>Add a project</h4>
 <p class="am-sub">Two ways in &mdash; the project is named automatically, graphed, and loaded.</p>
 <button class="am-opt" id="am-pick"><b>&#128193;&nbsp; Select a project folder&hellip;</b><span>opens your file explorer (via the local bridge) &mdash; pick the repo folder and it is graphed &amp; loaded</span></button>
 <div class="am-or">or</div>
 <div class="am-optwrap">
  <b style="font:600 12px var(--ui);color:var(--ink)">&#128279;&nbsp; Import from a git repo link <span class="st st--imp" id="am-url-chip">LIVE via bridge</span></b>
  <div style="display:flex;gap:7px;margin-top:7px">
   <input class="rin" id="am-url" type="text" placeholder="https://github.com/owner/repo" spellcheck="false" style="flex:1;margin-top:0">
   <button class="rbtn" id="am-import" style="margin-top:0;flex:none">IMPORT</button>
  </div>
  <p class="am-note">clones with <code>graphify clone</code> (GitHub https), graphs it, loads it &mdash; the one flow that uses the network.</p>
 </div>
 <div id="am-paste" style="display:none">
  <div class="am-or">no bridge detected &mdash; paste a local path instead</div>
  <div style="display:flex;gap:7px">
   <input class="rin" id="am-path" type="text" placeholder="C:\\repos\\my-app  (absolute, or relative to this repo)" spellcheck="false" style="flex:1;margin-top:0">
   <button class="rbtn" id="am-save" style="margin-top:0;flex:none">ADD</button>
  </div>
 </div>
 <div class="am-status" id="am-status"></div>
 <div class="am-btns">
  <button class="rbtn" id="am-cancel">CANCEL</button>
 </div>
</div></div>
<div id="chatfly"><div class="cf-head"><b>Graph Chat</b><span class="gmeta" id="cf-ctx" style="margin:0"></span><button class="rbtn" id="cf-clr" style="margin-top:0" title="clear the chat — like /clear">CLR</button><button class="rbtn" id="cf-close" style="margin-top:0">CLOSE</button></div>
 <div id="cf-thread"></div>
 <div class="cf-foot"><input id="cf-in" type="text" spellcheck="false" placeholder="Ask &mdash; Graphify answers locally; the Claude Code lane asks your connected Claude">
  <div class="cf-lanes"><span class="gmeta" style="margin:0">lane:</span><button class="lane on" data-lane="graphify" id="cf-lane-graphify">Graphify</button><button class="lane" data-lane="claudecode" id="cf-lane-claudecode">Claude Code</button><button class="lane" id="cf-stop" style="display:none;border-color:rgba(248,113,113,.5);color:#f87171">STOP</button><span class="gmeta" style="margin:0;margin-left:auto">Claude lane = one real call per ask</span></div></div></div>
<div id="connmodal"><div class="cm">
 <h4 id="cm-title">Connect</h4>
 <span class="cm-led" id="cm-led">SETUP REQUIRED</span>
 <div class="cm-banner" id="cm-banner"></div>
 <div id="cm-steps"></div>
 <p class="gmeta" id="cm-extension" style="margin-top:10px"></p>
 <div class="am-btns"><button class="rbtn" id="cm-close">CLOSE</button></div>
</div></div>
<div id="sections">
 <span class="sec-close" id="sec-close" title="back to the Knowledge Graph">&larr; KNOWLEDGE GRAPH</span>

 <div class="sec" data-sec="skills">
  <h2>Skills</h2>
  <p class="sec-sub">The real inventory: skills used to build this dashboard and the skills it ships for using Graphify. Statuses are honest &mdash; nothing here claims to run unless it does.</p>
  <div id="skill-filter">
   <span class="skf on" data-f="all">All</span>
   <span class="skf" data-f="imp">Implemented</span>
   <span class="skf" data-f="part">Partial</span>
   <span class="skf" data-f="plan">Planned</span>
   <span class="skf" data-f="gate">Gated</span>
   <span class="skf" data-f="ext">External</span>
  </div>
  <div class="gcards">@@SKILLS@@</div>
 </div>

 <div class="sec hguide" data-sec="howto">
  <h2>How To Guide</h2>
  <p class="sec-sub">A first-time user&rsquo;s guide to the GraphiQuest. Everything here exists today; anything not built yet says so plainly. Everything runs locally &mdash; no cloud, no credentials.</p>

  <h3>1. What GraphiQuest is</h3>
  <ul><li>A local-first tool that maps any code repository into a knowledge graph and lets you explore it as a <b>3D molten-brain Hivemind</b> or a structural <b>2D Explorer</b>, filter it by concept, ask it questions, and audit it with <b>Hunter</b> &mdash; all answered from the local graph.</li></ul>

  <h3>Why Graphify saves context / tokens</h3>
  <ul>
   <li>Without a map, asking a model about a repo means feeding it large chunks of the code &mdash; and paying to re-read them every turn. Graphify <b>pre-maps</b> the repo into a structured graph, so the model (or you) can pull just the relevant slice: the most-connected files, a node&rsquo;s neighbors, the concept/slice summary, Hunter findings. That focused context is a tiny fraction of the whole.</li>
   <li><b>Run a token savings check:</b> click <b>RUN SAVINGS CHECK</b> in the right Graph panel (or Settings &rarr; Context Savings, or the Skills card). It computes a <b>Claude-only</b> estimate (the full structural map) vs a <b>Graphify-assisted</b> estimate (the focused query) and shows the % saved. It is logged in Activity and stored under Memory.</li>
   <li><b>Estimated vs measured:</b> the dashboard number is an <b>estimate</b> (<code>tokens &asymp; characters / 4</code>), clearly labelled. It has been <b>measured for real</b> (2026-06-11, two live Claude calls on the graphify project): Graphify-assisted used <b>6,842</b> graph tokens ($0.64); the same question with the full graph inlined used <b>831,584</b> tokens ($8.39) &mdash; <b>99.2% fewer tokens, 92% cheaper</b>. The estimate holds.</li>
  </ul>

  <h3>2. Start here &mdash; two ways in</h3>
  <ul>
   <li><b>Path A &mdash; you have Claude Code open (easiest):</b> paste this into Claude Code and it does the whole setup for you &mdash; clone, install the scanner, graph the repo, start this dashboard, and connect itself:</li>
  </ul>
  <div class="cpr" style="max-width:880px"><span class="cmd" id="cmd-claude-onboard">Set up the GraphiQuest from https://github.com/Bosheda/graphiquest :
1. Clone it (or cd into my existing clone).
2. Install the Graphify scanner CLI (open source by safishamsi - github.com/safishamsi/graphify): uv tool install graphifyy   (pipx install graphifyy also works)
3. Graph the repo: run "graphify update ." in the repo root.
4. Start the dashboard with "python scripts/start_graphify_dashboard.py", leave it running, and tell me the local URL it prints.
5. Register the dashboard's MCP server with yourself using ABSOLUTE paths on this machine: claude mcp add -s user graphify -- "&lt;absolute path to python&gt;" "&lt;repo&gt;/scripts/graphify_mcp_server.py" --repo "&lt;repo&gt;"
6. Run "claude mcp list", confirm graphify shows a health check, then use the graphify tools to summarize my graph.</span><button class="cpy" data-for="cmd-claude-onboard">COPY</button></div>
  <ul>
   <li><b>Path B &mdash; do it yourself:</b> <code>git clone https://github.com/Bosheda/graphiquest</code>, <code>cd DaForgeLayer-AI</code>, then one foreground command: <code>python scripts/start_graphify_dashboard.py</code>. It serves the views + the local bridge and prints the URL <code>http://127.0.0.1:8787/views/graphify-dashboard.html</code>. <kbd>Ctrl+C</kbd> stops it. Port busy? add <code>--port 8788</code>. Full step-by-step with copy buttons: <b>Settings &rarr; Setup &amp; Install</b>.</li>
   <li>Example paths in this guide use placeholders like <code>C:\\Users\\%USERNAME%\\&hellip;</code> &mdash; the wizard and the bridge always detect the <b>real</b> paths on your machine; nothing is hardcoded to anyone.</li>
  </ul>

  <h3>3. Install the Graphify scanner</h3>
  <ul><li>Graphify is the open-source scanner that turns a repo into the knowledge graph &mdash; built by <b>safishamsi</b>: <a href="https://github.com/safishamsi/graphify" target="_blank" rel="noopener">github.com/safishamsi/graphify</a> (MIT; full credit to the author). Install: <code>uv tool install graphifyy</code> (or <code>pipx install graphifyy</code>), check with <code>graphify --version</code>, update with <code>uv tool upgrade graphifyy</code>. Live detection: <b>Settings &rarr; Graphify CLI</b> &mdash; and the connect wizard checks it for you (step 2).</li></ul>

  <h3>4. Connect your first repo</h3>
  <ul><li>Click <b>+ Add a project</b> in the top strip. Either <b>pick a folder</b> (the native file explorer opens via the bridge) or <b>import a GitHub URL</b> (the bridge runs <code>graphify clone</code>). The project is created, graphed, and loaded automatically. You can also manage everything from <b>Settings &rarr; Repositories</b>.</li></ul>

  <h3>5. Run Graphify on a repo</h3>
  <ul><li>For a connected repo that isn&rsquo;t graphed yet, <b>RUN GRAPHIFY</b> (Settings &rarr; Repositories) runs the allowlisted <code>graphify update .</code> through the loopback bridge in your validated repo path &mdash; the browser never sends command text. Output lands in <code>&lt;repo&gt;/graphify-out/</code>, then the bridge builds the dashboard views and the project becomes <b>ready</b>. No bridge? the button becomes PREPARE COMMAND and shows the exact command to run yourself.</li></ul>

  <h3>6. Switch between project graphs</h3>
  <ul><li>Click any <b>ready</b> project card to load its own graph &mdash; the 3D/2D views, counts, Concepts, and Ask Console all follow it. No project ever shows another&rsquo;s graph. The top strip shows the active graph plus ready/pinned projects; Settings &rarr; Repositories is the full list.</li></ul>

  <h3>7. Use the 3D Hivemind</h3>
  <ul><li><kbd>left-drag</kbd> rotate &middot; <kbd>wheel</kbd> zoom &middot; <kbd>right-drag</kbd> pan &middot; click a glowing core to select it (the camera glides in and pathways light). <b>PAUSE</b> freezes the spin, <b>Reset View</b> re-frames, <b>Palette</b> cycles the molten color families. <b>Motion Controls</b> (right panel) scale spin/fly/drift and persist locally.</li></ul>

  <h3>8. Use the 2D Explorer</h3>
  <ul><li>The <b>2D Explorer</b> pill switches views. It boots in <b>2D Brain</b> (region overview); <b>Tools &rarr; View Mode</b> switches to <b>Structural</b> (slice-based). Slice chips scope the view; the search drawer finds nodes; the inspector shows a Connected list. find/jump works here too.</li></ul>

  <h3>9. Use Concepts filters</h3>
  <ul><li>The right-panel <b>CONCEPTS</b> checklist filters both views live; the header checkbox is select-all / deselect-all. Counts follow the active 2D slice when one is set.</li></ul>

  <h3>10. Ask graph questions</h3>
  <ul><li>Wired today (local, no model): <code>what is selected?</code> &middot; <code>what is connected to this node?</code> &middot; <code>what concepts are visible?</code> &middot; <code>what slice am I in?</code> &middot; <code>how many nodes?</code> &middot; <code>find &lt;name&gt;</code> / <code>jump to &lt;name&gt;</code> &middot; <code>run hunter</code> / <code>what did hunter find?</code> / <code>show orphans</code> &middot; <code>what are the most connected files?</code> &middot; <code>shortest path A to B</code> &middot; <code>trace &lt;name&gt;</code> &middot; <code>chain end &lt;name&gt;</code> &middot; <code>help</code>. <b>CLR</b> clears the responses (history stays in Activity); <b>STOP</b> cancels an in-flight Claude ask for real (the local call is killed). Every ask renders an evidence card and is logged in <b>Activity</b>. Natural phrasing is OK (&ldquo;can you jump to the auth module&rdquo; works) &mdash; extra words are stripped, and multi-word names fall back word-by-word. Unsupported questions answer honestly &mdash; nothing is faked. <b>Once Claude Code is connected, pick the Claude Code lane and any question is answered right here</b> &mdash; one real call per ask, never automatic. The EXPAND button opens the full chat window.</li></ul>

  <h3>11. Use Hunter (project auditor)</h3>
  <ul><li><b>Hunter</b> reads the selected project&rsquo;s graph locally and reports orphan candidates, disconnected groups, possible missing links (same folder, no connections), single-link leaves, hotspot files, and stale/incomplete-graph signals. Run it from <b>Reports &rarr; RUN HUNTER</b>, the Hunter card in Skills, or by asking <code>run hunter</code>. Findings are <b>graph evidence, not proof of bugs</b> &mdash; the wording stays &ldquo;candidate / possible / inspect&rdquo;. Then press <b>ENRICH WITH CLAUDE CODE</b>: one real call where Claude verifies the findings with the graph tools (incl. <code>run_hunter</code>) and returns prioritized recommendations &mdash; each with a JUMP that flies the view to the node. Re-running Hunter <b>archives</b> the previous report and shows the newest.</li></ul>

  <h3>12. Read Reports</h3>
  <ul><li><b>Reports</b> lists Hunter reports newest-first with severity counts; older runs are marked <b>ARCHIVED</b> and stay clickable. Open one to see its findings, Claude recommendations (if enriched), and summary. Reports persist in this browser only (<code>localStorage</code>, last 10).</li></ul>

  <h3>13. Click report findings to jump to the graph</h3>
  <ul><li>Each node-backed finding has a <b>JUMP</b> button that flies the 3D camera straight to that node (low-degree targets open in the 2D Explorer, where every node renders) and updates the Selected-node card. A finding with no graph location says so honestly.</li></ul>

  <h3>14. Connect Claude Code (the wizard does it with you)</h3>
  <ul>
   <li>Click the <b>CLAUDE CODE</b> pill in the left rail (or CONNECT in Settings / Skills). The wizard checks four things, in order, live: <b>(1)</b> is Claude Code installed? (if not: one COPY button + open a terminal and paste) &middot; <b>(2)</b> is the Graphify scanner installed? (open source by safishamsi &mdash; the wizard links and credits it, one COPY button to install) &middot; <b>(3)</b> connect &mdash; press <b>REGISTER FOR ME</b> and the bridge runs Claude Code&rsquo;s own <code>claude mcp add</code> command with the exact paths detected on your machine (or copy the same command and run it yourself) &middot; <b>(4)</b> check it worked with <code>claude mcp list</code> or <code>/mcp</code> inside Claude Code.</li>
   <li><b>Honesty rules it follows:</b> there is no browser sign-in for local servers (nothing can &ldquo;authorize&rdquo; Claude silently); the dashboard only ever <b>reads</b> Claude Code&rsquo;s settings file; &ldquo;connected&rdquo; is never claimed &mdash; the strongest status is <i>registered, verified by you</i>; and no call ever happens until you approve it inside Claude Code.</li>
  </ul>

  <h3>15. How the pieces talk (the simple mental model)</h3>
  <p class="gmeta" style="margin:0 0 6px"><b>GraphiQuest is built on top of Graphify.</b> Graphify scans the repo and generates the graph data; GraphiQuest visualizes, queries, audits, and navigates it. They are <b>separate projects</b> — GraphiQuest is not Graphify renamed, and the Graphify scanner is the work of <a href="https://github.com/safishamsi/graphify" target="_blank" rel="noopener">safishamsi</a> (MIT; full credit to the author).</p>
  <ul>
   <li><b>The Graphify scanner</b> (by safishamsi) BUILDS the graph from any repo: <code>graphify update .</code></li>
   <li><b>This dashboard</b> SHOWS the graph: 3D Hivemind, 2D Explorer, Hunter audits, Reports, token-savings proof. It runs entirely on your machine.</li>
   <li><b>Claude Code</b> THINKS about the graph: once connected, its <code>graphify</code> tools read the same data through a tiny read-only local server &mdash; and <b>its answers appear right here</b>: pick the <b>Claude Code lane</b> in the ask box (or the EXPAND chat window) and ask anything.</li>
   <li><b>Who talks to whom:</b> the Graphify lane is answered locally with no model. The Claude Code lane makes <b>one real call per ask</b> to YOUR Claude Code &mdash; only when you press ASK, never on its own, and only the read-only graph server is exposed to it.</li>
   <li><b>A normal session:</b> add a repo (<b>+ Add a project</b>) &rarr; it gets graphed &rarr; explore it in 3D, run <b>Hunter</b> from Reports &rarr; ask Claude Code (in its own window) to reason about what you are looking at &rarr; jump to nodes the answers mention.</li>
  </ul>

  <h3>16. Clear reports, activity &amp; memory</h3>
  <ul>
   <li><b>Reports</b>: CLEAR ALL REPORTS, or open a report to COPY its JSON / DELETE it.</li>
   <li><b>Activity</b>: COPY LOG (JSON), CLEAR ASK LOG, CLEAR EVENT LOG.</li>
   <li><b>Memory &rarr; Local data</b>: per-key CLEAR with live sizes, plus CLEAR ALL LOCAL DASHBOARD DATA.</li>
   <li>All of these are <b>this-browser <code>localStorage</code></b> only &mdash; they never touch your source repos or generated graph views.</li>
  </ul>

  <h3>17. Unload / reload the active graph</h3>
  <ul><li>The active project card has an <b>UNLOAD</b> chip that returns the viewport to a real <b>no-graph</b> state (the Ask Console, Hunter, and counts all say &ldquo;no graph loaded&rdquo;). Click the card again, or <b>RELOAD</b> in the viewport, to load it back. Even the default graph is unloadable; nothing is deleted.</li></ul>

  <h3>18. Clean up generated views (Maintenance)</h3>
  <ul><li><b>Settings &rarr; Maintenance</b> lists every generated project view with a CLEAN VIEWS button (bridge required). This deletes only <code>graphify-out/projects/&lt;id&gt;/</code> &mdash; source repos and design assets are structurally out of reach. This is <b>separate</b> from the localStorage clears above: Maintenance removes generated files on disk; Memory/Reports/Activity clears only remove browser data.</li></ul>

  <h3>19. Troubleshooting</h3>
  <ul>
   <li><b>Blank graph / flat spheres:</b> restart with <code>python scripts/start_graphify_dashboard.py</code> (it rebuilds missing views and seeds the molten atlas); check the browser console for an <code>atlas missing</code> warning.</li>
   <li><b>Bridge not detected:</b> start it with the command above; the page runs in a limited mode (no Add/RUN GRAPHIFY) until it is up.</li>
   <li><b>Graphify CLI missing:</b> <code>uv tool install graphifyy</code>, then <code>graphify --version</code>.</li>
   <li><b>&ldquo;not graphed yet&rdquo;:</b> connect a repo path in Settings &rarr; Repositories, then RUN GRAPHIFY.</li>
   <li><b>Stale processes:</b> <code>python scripts/cleanup_graphify_processes.py --kill-stale</code> (only ever touches Graphify rebuilds).</li>
   <li><b>Connector says gated:</b> expected &mdash; that is the honest no-call state, not an error.</li>
  </ul>

  <h3>20. Local-only vs gated, and what is not built yet</h3>
  <ul>
   <li><b>Local-only (works now):</b> graph views, concepts, ask console, find/jump, Hunter, reports, activity, memory. <b>Gated (never silent):</b> anything that would call Claude Code &mdash; that needs your setup and approval and the dashboard never calls them itself.</li>
   <li><b>Not built yet:</b> semantic/LLM graph answers &middot; a packaged OS-level installer (the first-run landing installs the scanner; the standalone repo split is planned) &middot; a remote/community skill-pack registry (a minimal LOCAL registry ships). Each appears in <b>Skills</b> with its honest status. (Path tracing, project switching, GitHub-URL import, 2D find/jump, Hunter + real Claude enrichment, savings proof, and graph unload/reload ARE built.)</li>
  </ul>
 </div>

 <div class="sec" data-sec="reports">
  <h2>Reports</h2>
  <p class="sec-sub">Hunter &mdash; the graph-first project auditor. Reports build locally from the selected project&rsquo;s own graph data. Findings are graph evidence (&ldquo;candidate / possible / inspect&rdquo;), never proof of bugs. Stored in this browser only (last 10).</p>
  <div class="gcard" style="max-width:880px">
   <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
    <button class="rbtn" id="hunt-run" style="margin-top:0">RUN HUNTER</button>
    <span class="gmeta" id="hunt-ctx" style="margin:0">analyzes the currently selected project</span>
   </div>
   <p class="gmeta" style="margin-bottom:0">the scan itself is local graph-only &middot; <b>ENRICH WITH CLAUDE CODE</b> on a report makes <b>one real call per click</b> &mdash; Claude verifies the findings with the graph tools (incl. <code>run_hunter</code>) and returns prioritized, jumpable recommendations &middot; never automatic</p>
  </div>
  <h3>Hunter reports (this browser)</h3>
  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;max-width:880px;margin:2px 0 6px">
   <button class="rbtn" id="hunt-clear-all" style="margin-top:0">CLEAR ALL REPORTS</button>
   <span class="gmeta" id="hunt-count" style="margin:0"></span>
   <span class="gmeta" style="margin:0;margin-left:auto">stored in this browser only (<code>localStorage</code>, last 10) &mdash; clearing never touches source repos or generated views</span>
  </div>
  <div id="hunt-list"><p class="gmeta">no reports yet &mdash; RUN HUNTER creates the first one</p></div>
  <div id="hunt-detail"></div>
 </div>

 <div class="sec" data-sec="activity">
  <h2>Activity</h2>
  <p class="sec-sub">Local evidence only &mdash; what this browser actually did. Nothing here is synthesized. Everything is <code>localStorage</code>; clearing it never touches source repos or generated views.</p>
  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;max-width:880px;margin:0 0 10px">
   <button class="rbtn" id="act-copy" style="margin-top:0">COPY LOG (JSON)</button>
   <button class="rbtn" id="act-clear-asks" style="margin-top:0">CLEAR ASK LOG</button>
   <button class="rbtn" id="act-clear-events" style="margin-top:0">CLEAR EVENT LOG</button>
   <span class="gmeta" id="act-counts" style="margin:0;margin-left:auto"></span>
  </div>
  <h3>Ask Console evidence (this browser, last 50)</h3>
  <div id="act-asks"><div class="aempty">No asks recorded yet in this browser.</div></div>
  <h3>Project / repo events (this browser)</h3>
  <div id="act-proj"><div class="aempty">No project events yet in this browser.</div></div>
  <h3>Graph build events</h3>
  <div class="aempty">Build events are not logged to the browser yet &mdash; the loaded graph was built at <code>@@BUILT@@</code> (read-model snapshot).</div>
  <h3>Connector attempts</h3>
  <div class="aempty" id="act-conn">Gated-lane asks appear in the evidence log above as <code>unsupported</code> &mdash; no connector call has ever been made from this dashboard.</div>
  <h3>Process / hook hygiene</h3>
  <div class="aempty">Run <code>python scripts/cleanup_graphify_processes.py</code> for a live check &mdash; results are not surfaced in-browser yet (planned for Settings &rarr; Maintenance).</div>
 </div>

 <div class="sec sec--settings" data-sec="settings">
  <h2>Settings</h2>
  <p class="sec-sub">Setup hub. Controls are honest: working, pending, or gated &mdash; never fake. Connector execution stays disabled until configured <b>and</b> explicitly approved.</p>
  <div id="setwrap">
  <nav id="setnav">
   <div class="sn on" data-card="set-setup">Setup &amp; Install</div>
   <div class="sn" data-card="set-dashboard">Dashboard</div>
   <div class="sn" data-card="set-savings">Context Savings</div>
   <div class="sn" data-card="set-graphify">Graphify CLI</div>
   <div class="sn" data-card="set-repos">Repositories</div>
   <div class="sn" data-card="set-claudecode">Claude Code</div>
   <div class="sn" data-card="set-skills">Skills</div>
   <div class="sn" data-card="set-privacy">Privacy / Local-first</div>
   <div class="sn" data-card="set-maint">Maintenance</div>
  </nav>
  <div id="setbody">
   <div class="gcard" id="set-setup"><b>Setup &amp; Install<span class="st st--imp">START HERE</span></b>
    <p class="gmeta">Everything runs locally on your machine. Four steps to a working dashboard; copy any command with its COPY button.</p>
    <div class="setup-step"><span class="n">1</span><div class="b"><b>Get the project</b>
     <p class="gmeta" style="margin:3px 0">Clone the repo (a standalone GraphiQuest repo split is planned; for now it lives inside DaForgeLayer-AI):</p>
     <div class="cpr"><span class="cmd" id="cmd-clone">git clone https://github.com/Bosheda/graphiquest
cd DaForgeLayer-AI</span><button class="cpy" data-for="cmd-clone">COPY</button></div></div></div>
    <div class="setup-step"><span class="n">2</span><div class="b"><b>Install the Graphify CLI</b>
     <p class="gmeta" style="margin:3px 0">Graphify scans a repo into the graph this dashboard renders. Install it with <b>uv</b> (or pipx), then verify:</p>
     <div class="cpr"><span class="cmd" id="cmd-gfy">uv tool install graphifyy        # or: pipx install graphifyy
graphify --version               # verify it is on PATH
uv tool upgrade graphifyy        # update later</span><button class="cpy" data-for="cmd-gfy">COPY</button></div>
     <p class="gmeta" style="margin:3px 0">detected at this page&rsquo;s build time: <code>@@GFYVER@@</code> &middot; live status: <span id="setup-gfy">checking the bridge…</span></p></div></div>
    <div class="setup-step"><span class="n">3</span><div class="b"><b>Start the dashboard</b>
     <p class="gmeta" style="margin:3px 0">One foreground command serves the views + the loopback bridge and seeds the molten-brain assets. <kbd>Ctrl+C</kbd> stops everything (nothing detaches):</p>
     <div class="cpr"><span class="cmd" id="cmd-start">python scripts/start_graphify_dashboard.py</span><button class="cpy" data-for="cmd-start">COPY</button></div>
     <p class="gmeta" style="margin:3px 0">It opens <code>http://127.0.0.1:8787/views/graphify-dashboard.html</code>. Port busy? add <code>--port 8788</code>. Already running? the starter says so and exits cleanly.</p></div></div>
    <div class="setup-step"><span class="n">4</span><div class="b"><b>Graph your first repo</b>
     <p class="gmeta" style="margin:3px 0">Two ways in &mdash; both from the top strip&rsquo;s <b>+ Add a project</b> (or Settings &rarr; Repositories):</p>
     <p class="gmeta" style="margin:3px 0">&bull; <b>Pick a folder</b> &mdash; the native file explorer opens (via the bridge); the folder is graphed and loaded automatically.<br>&bull; <b>Import a GitHub URL</b> &mdash; the bridge runs <code>graphify clone</code>, graphs it, loads it.</p>
     <p class="gmeta" style="margin:3px 0">When a project is <b>ready</b>, click its card to load its graph, then explore: <b>3D Hivemind</b> / <b>2D Explorer</b>, filter <b>Concepts</b>, <b>Ask</b> questions, and run <b>Hunter</b> (Reports).</p></div></div>
    <div class="setup-tip">Stuck? Troubleshooting: <b>blank graph</b> = restart the dashboard (it rebuilds missing views); <b>flat/glossy spheres</b> = the molten atlas did not load (check the console + asset path); <b>bridge not detected</b> = start it with the step-3 command; <b>graphify CLI missing</b> = step 2; <b>stale processes</b> = <code>python scripts/cleanup_graphify_processes.py --kill-stale</code>.</div>
   </div>
   <div class="gcard" id="set-dashboard"><b>Dashboard</b>
    <p class="gmeta">server: <code id="set-srv">&mdash;</code></p>
    <p class="gmeta">graph output: <code>graphify-out/</code> &middot; views: <code>graphify-out/views/</code> (generated, gitignored)</p>
    <p class="gmeta">build: <code>@@BUILT@@</code> &middot; 3D <code>@@H3D@@</code> &middot; 2D <code>@@H2D@@</code></p>
    <span class="cmd">python scripts/start_graphify_dashboard.py  # serve dashboard + bridge (foreground; Ctrl+C stops)
python scripts/graphify_dashboard_mock.py   # regenerate this page</span>
    <p class="gmeta">full product guide: <code>docs/GRAPHIFY_DASHBOARD_README.md</code></p>
   </div>
   <div class="gcard" id="set-savings"><b>Context Savings<span class="st st--imp">ESTIMATE</span></b>
    <p class="gmeta"><b>Why Graphify saves tokens:</b> instead of pasting a whole repo into the model and paying to re-read it every turn, Graphify pre-maps the code into a structured graph. The model (or you) can then pull just the relevant slice &mdash; the most-connected files, a node&rsquo;s neighbors, the concept/slice summary, Hunter findings &mdash; a tiny fraction of the full context.</p>
    <p class="gmeta"><b>Method (honest):</b> <code>tokens &asymp; characters / 4</code>. <b>Claude-only</b> = the full structural read-model serialized (a conservative baseline &mdash; the raw repo is larger, so real savings are higher). <b>Graphify-assisted</b> = the focused query payload. Savings % = (claude-only &minus; graphify) / claude-only &times; 100. This is an <b>estimate</b>, clearly labelled &mdash; it is not a measured Claude-token count.</p>
    <div style="display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin:6px 0">
     <button class="rbtn" id="sv-run2" style="margin-top:0">RUN SAVINGS CHECK</button>
     <span class="gmeta" id="sv-last2" style="margin:0">no check run yet in this browser</span>
    </div>
    <div class="setup-tip"><b>Estimated vs measured:</b> the panel number is an honest <code>chars/4</code> estimate. It was <b>measured for real once</b> (2026-06-11, two live Claude calls on the graphify project): assisted <b>6,842</b> graph tokens / $0.64 vs full-graph-inlined <b>831,584</b> tokens / $8.39 &mdash; <b>99.2% fewer tokens, 92% cheaper</b>. The dashboard never calls Claude on its own; the Claude Code lane calls only when you ask.</div>
   </div>
   <div class="gcard" id="set-graphify"><b>Graphify CLI<span class="st st--ext">EXTERNAL</span></b>
    <p class="gmeta">Graphify (by safishamsi) is the external tool that scans a repo into <code>graphify-out/graph.json</code> &mdash; the structural graph this dashboard renders. MIT-licensed. It is the one required external dependency.</p>
    <p class="gmeta">detected at this page&rsquo;s build time: <code>@@GFYVER@@</code> &middot; live: <span id="set-gfy-live">checking…</span></p>
    <div class="cpr"><span class="cmd" id="cmd-gfy2">uv tool install graphifyy        # install (or: pipx install graphifyy)
graphify --version               # verify on PATH
uv tool upgrade graphifyy        # update
graphify update .                # rebuild THIS repo's graph</span><button class="cpy" data-for="cmd-gfy2">COPY</button></div>
    <p class="gmeta">optional hooks (auto-rebuild on commit): <code>graphify hook install</code> then <code>python scripts/install_graphify_hooks_safe.py</code> (hygiene &mdash; see Maintenance).</p>
    <p class="gmeta">repo: <code>github.com/safishamsi/graphify</code> &middot; PyPI publish of the pinned version is operator-held; the dashboard works with 0.8.36+.</p>
   </div>
   <div class="gcard" id="set-repos"><b>Repositories<span class="st st--part">PARTIAL</span></b>
    <p class="gmeta">Registry: tracked <code>graphify.projects.json</code> (baked at generation). Repo-path edits and added projects below are <b>saved locally in this browser</b> (localStorage) until the CLI config-writer lands. A browser page cannot validate local paths &mdash; no scan, no generation, no network happens here.</p>
    <p class="gmeta" id="bridge-line">local bridge: checking…</p>
    <div id="repo-list"></div>
    <div class="rrow" id="repo-add"><b>Add a project</b>
     <p class="gmeta">One flow, same truth as the top strip.</p>
     <button class="rbtn" id="ra-open">OPEN ADD PROJECT…</button>
    </div>
    <p class="gmeta">RUN GRAPHIFY / REBUILD on each project runs the allowlisted <code>graphify update .</code> through the local bridge. Without the bridge the button becomes PREPARE COMMAND (manual, honest).</p>
   </div>
   <div class="gcard" id="set-claudecode"><b>Claude Code connector<span class="st st--gate">GATED</span></b>
    <div class="conn-panel" id="claudecode-panel">
     <div class="cp-status"><span class="cp-led" id="claudecode-led">NOT CONNECTED</span><span class="gmeta" id="claudecode-substatus" style="margin:0">no call has ever been made from this dashboard</span></div>
     <button class="conn-btn" id="claudecode-connect">CONNECT CLAUDE CODE</button>
     <div style="margin-top:7px">
      <button class="conn-btn2" data-cpy-for="cmd-cc-install">COPY INSTALL CMD</button>
      <button class="conn-btn2" data-cpy-for="cmd-cc-gfy">COPY SCANNER INSTALL</button>
      <button class="conn-btn2" data-cpy-for="cmd-cc-add">COPY REGISTER CMD</button>
      <button class="conn-btn2" data-cpy-for="cmd-cc-list">COPY CHECK CMD</button>
      <button class="conn-btn2" id="claudecode-check">CHECK SELF-TEST</button>
      <button class="conn-btn2" id="claudecode-steps">OPEN SETUP STEPS</button>
     </div>
     <div class="conn-banner">This dashboard never calls Claude Code automatically. You connect once, then approve any use inside Claude Code.</div>
    </div>
    <p class="gmeta">Status: <b>not connected</b> &middot; setup required &middot; <b>no call has ever been made from this dashboard</b>.</p>
    <p class="gmeta"><b>What it is:</b> Claude Code (terminal, or the terminal window inside Claude Desktop &mdash; same thing) reads your graphs through a tiny <b>read-only</b> local MCP server that ships with this dashboard (<code>scripts/graphify_mcp_server.py</code>). Tools: <code>graph_summary</code> &middot; <code>find_node</code> &middot; <code>node_neighbors</code> &middot; <code>list_concepts</code> &middot; <code>run_hunter</code> (the dashboard&rsquo;s skills, exposed to Claude). The easiest path is the <b>connect wizard</b> (CONNECT button above) &mdash; it checks everything and can register with one click.</p>
    <div class="setup-step"><span class="n">1</span><div class="b"><b>Install Claude Code (if you don&rsquo;t have it)</b>
     <div class="cpr"><span class="cmd" id="cmd-cc-install">@@CC_INSTALL@@</span><button class="cpy" data-for="cmd-cc-install">COPY</button></div>
     <p class="gmeta" style="margin:3px 0">Open a terminal, paste, run. Check it with <code>claude --version</code>.</p></div></div>
    <div class="setup-step"><span class="n">2</span><div class="b"><b>Install the Graphify scanner (if missing)</b>
     <div class="cpr"><span class="cmd" id="cmd-cc-gfy">uv tool install graphifyy    # or: pipx install graphifyy</span><button class="cpy" data-for="cmd-cc-gfy">COPY</button></div>
     <p class="gmeta" style="margin:3px 0">Graphify is the open-source scanner that builds the graph &mdash; by <b>safishamsi</b>: <a href="https://github.com/safishamsi/graphify" target="_blank" rel="noopener">github.com/safishamsi/graphify</a> (MIT; full credit to the author).</p></div></div>
    <div class="setup-step"><span class="n">3</span><div class="b"><b>Connect (one click in the wizard, or one command)</b>
     <div class="cpr"><span class="cmd" id="cmd-cc-add">claude mcp add -s user graphify -- "&lt;ABS-PYTHON&gt;" "&lt;ABS-REPO&gt;/scripts/graphify_mcp_server.py" --repo "&lt;ABS-REPO&gt;"</span><button class="cpy" data-for="cmd-cc-add">COPY</button></div>
     <p class="gmeta" style="margin:3px 0">The wizard&rsquo;s <b>REGISTER FOR ME</b> runs exactly this with the real paths detected on your machine (e.g. <code>&lt;ABS-PYTHON&gt;</code> &asymp; <code>C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Python\\Python313\\python.exe</code> on Windows &mdash; placeholders here on purpose, nothing is tied to any one user). Run it in PowerShell or CMD, <b>not Git Bash</b>. Claude Code stores it in <code>~/.claude.json</code>; this dashboard only reads that file.</p></div></div>
    <div class="setup-step"><span class="n">4</span><div class="b"><b>Check it worked</b>
     <div class="cpr"><span class="cmd" id="cmd-cc-list">claude mcp list</span><button class="cpy" data-for="cmd-cc-list">COPY</button></div>
     <p class="gmeta" style="margin:3px 0">graphify should appear with a health check (or type <code>/mcp</code> inside Claude Code). Server acting up? test it alone:</p>
     <div class="cpr"><span class="cmd" id="cmd-cc-self">python scripts/graphify_mcp_server.py --selftest</span><button class="cpy" data-for="cmd-cc-self">COPY</button></div></div></div>
    <p class="gmeta">docs: <code>@@CC_DOCS@@</code> (verified 2026-06-11). No browser sign-in exists for local MCP servers; &ldquo;connected&rdquo; is never claimable without a call &mdash; this card stays GATED until you approve a run inside Claude Code.</p>
    <div class="conn-warn">Connector execution is disabled until configured and explicitly approved.</div>
   </div>
   <div class="gcard" id="set-skills"><b>Skills &mdash; management<span class="st st--part">PARTIAL</span></b>
    <p class="gmeta">Every capability the dashboard ships, with honest status. There is <b>no installable skill-pack registry yet</b> (planned) &mdash; nothing here pretends to be installable. The visual Skills page (left nav) shows the same set as cards.</p>
    <div id="skill-mgmt"></div>
    <p class="gmeta" style="margin-top:9px">Legend: <span class="st st--imp">IMPLEMENTED</span> works now &middot; <span class="st st--part">PARTIAL</span> partly wired &middot; <span class="st st--plan">PLANNED</span> not built &middot; <span class="st st--gate">GATED</span> needs your setup + approval &middot; <span class="st st--ext">EXTERNAL</span> separate tool.</p>
   </div>
   <div class="gcard" id="set-privacy"><b>Privacy / Local-first</b>
    <p class="gmeta">&middot; graph data stays on disk (<code>graphify-out/</code>) &mdash; never uploaded</p>
    <p class="gmeta">&middot; no credentials stored &middot; no external calls by default &middot; connectors gated</p>
    <p class="gmeta">&middot; honest exception: view libraries + fonts load from public CDNs (jsdelivr / esm.sh / Google Fonts) on first load &mdash; a fully-offline bundle is on the packaging roadmap</p>
   </div>
   <div class="gcard" id="set-maint"><b>Maintenance</b>
    <p class="gmeta" id="clean-note">Generated project views live under <code>graphify-out/projects/&lt;id&gt;/</code> &mdash; cleanup deletes ONLY there (bridge-validated; source repos and design assets are structurally out of reach).</p>
    <div id="clean-list"><p class="gmeta">bridge not detected &mdash; cleanup needs the local bridge (views can also be deleted manually, they are disposable)</p></div>
    <span class="cmd">python scripts/cleanup_graphify_processes.py            # stale-rebuild check
python scripts/cleanup_graphify_processes.py --kill-stale
python scripts/install_graphify_hooks_safe.py           # hook hygiene (idempotent)</span>
    <p class="gmeta">generated views are disposable &mdash; delete <code>graphify-out/views/</code> and regenerate any time</p>
    <p class="gmeta">full hygiene details: the Maintenance section of <code>docs/GRAPHIFY_DASHBOARD_README.md</code></p>
   </div>
  </div>
  </div>
 </div>

 <div class="sec" data-sec="memory">
  <h2>Memory</h2>
  <p class="sec-sub">Local memory for this browser &mdash; saved graph sessions, node notes, ask history, and the data that backs them. Nothing leaves your machine.</p>

  <h3>Saved sessions</h3>
  <div class="gcard" style="max-width:880px">
   <p class="gmeta">A session captures the loaded project, 3D/2D mode, concept filters, selected node, and motion settings &mdash; restore puts you right back.</p>
   <div style="display:flex;gap:7px;align-items:center">
    <input class="rin" id="mem-sess-name" type="text" placeholder="session name (e.g. routing hot-spots)" spellcheck="false" style="flex:1;margin-top:0">
    <button class="rbtn" id="mem-sess-save" style="margin-top:0;flex:none">SAVE CURRENT SESSION</button>
   </div>
   <div id="mem-sess-list" style="margin-top:8px"><div class="aempty">No saved sessions yet in this browser.</div></div>
  </div>

  <h3>Node notes</h3>
  <div class="gcard" style="max-width:880px">
   <p class="gmeta" id="mem-note-ctx">Select a core in the Hivemind, then write a note &mdash; notes remember the node and project, and JUMP takes you back to it.</p>
   <div style="display:flex;gap:7px;align-items:center">
    <input class="rin" id="mem-note-text" type="text" placeholder="note for the selected node…" spellcheck="false" style="flex:1;margin-top:0">
    <button class="rbtn" id="mem-note-add" style="margin-top:0;flex:none">ADD NOTE</button>
   </div>
   <div id="mem-note-list" style="margin-top:8px"><div class="aempty">No node notes yet in this browser.</div></div>
  </div>

  <h3>Ask history</h3>
  <div class="gcard" style="max-width:880px">
   <div style="display:flex;gap:7px;align-items:center;margin-bottom:6px">
    <input class="rin" id="mem-ask-q" type="text" placeholder="search asks…" spellcheck="false" style="flex:1;margin-top:0">
    <select class="rin" id="mem-ask-proj" style="flex:none;width:200px;margin-top:0"><option value="">all projects</option></select>
   </div>
   <div id="mem-ask-list"><div class="aempty">No asks recorded yet in this browser.</div></div>
  </div>

  <h3>Local data (this browser)</h3>
  <div class="gcard" style="max-width:880px">
   <p class="gmeta">Everything Memory and the dashboard persist lives in plain <code>localStorage</code> &mdash; sizes below are live; clearing a key is immediate and only affects this browser.</p>
   <div id="mem-keys"></div>
   <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:10px">
    <button class="rbtn" id="mem-clear-all" style="margin-top:0;border-color:rgba(248,113,113,.45);color:#f87171">CLEAR ALL LOCAL DASHBOARD DATA</button>
    <span class="gmeta" style="margin:0">removes every key above (sessions, notes, ask history, Hunter reports, recents, edits) &mdash; <b>this browser only</b>. Source repos and generated views are never touched (those live under Settings &rarr; Maintenance).</span>
   </div>
  </div>

  <p class="gmeta" style="max-width:880px">Still planned (honest): semantic search over history, cross-browser sync, camera-exact restore. Everything above is real today.</p>
 </div>
</div>"""

SECTIONS_HTML = (SECTIONS_HTML
                 .replace("@@SKILLS@@", SKILLS_CARDS)
                 .replace("@@BUILT@@", html.escape(C["built_at"]))
                 .replace("@@NODES@@", html.escape(C["nodes"]))
                 .replace("@@CLUSTERS@@", html.escape(C["slices"]))
                 .replace("@@GFYVER@@", html.escape(GFY_VER))
                 .replace("@@H3D@@", H3D).replace("@@H2D@@", H2D)
                 # G5Q.1g: Claude Code connector facts -- research-verified 2026-06-11
                 # LIVE on this machine (claude 2.1.174) + code.claude.com/docs/en/{mcp,setup}
                 .replace("@@CC_INSTALL@@",
                          "PowerShell: irm https://claude.ai/install.ps1 | iex\n"
                          "winget:     winget install Anthropic.ClaudeCode\n"
                          "npm:        npm install -g @anthropic-ai/claude-code   (Node 18+)")
                 .replace("@@CC_DOCS@@", "code.claude.com/docs/en/mcp"))

SHELL_JS = """
/* ==== G5P.1 shell: real nav section switching (hero stays mounted underneath) */
(function() {
  const $ = id => document.getElementById(id);
  let CUR = 'graph';
  const setSection = name => {
    CUR = name;
    document.querySelectorAll('#rail .nav').forEach(n => n.classList.toggle('on', n.dataset.sec === name));
    document.querySelectorAll('#sections .sec').forEach(p => p.classList.toggle('on', p.dataset.sec === name));
    document.body.classList.toggle('sec-open', name !== 'graph');
    if (name === 'activity') renderActivity();
    if (name === 'settings') { const el = $('set-srv'); if (el) el.textContent = location.origin || 'local file'; if (window.__repoUI) window.__repoUI(); if (window.__maintUI) window.__maintUI(); if (window.__setupLive) window.__setupLive(); renderSkillMgmt(); if (window.__paintConnLeds) window.__paintConnLeds(); if (window.__paintSavings) window.__paintSavings(); }
    if (name === 'memory' && window.__memUI) window.__memUI();
  };
  document.querySelectorAll('#rail .nav').forEach(n => n.onclick = () => setSection(n.dataset.sec));
  $('sec-close').onclick = () => setSection('graph');
  // G5Q.1d: copy buttons -- copy the referenced element's textContent
  document.addEventListener('click', e => {
    const b = e.target.closest && e.target.closest('.cpy');
    if (!b) return;
    const src = b.dataset.for ? document.getElementById(b.dataset.for) : b.previousElementSibling;
    const txt = src ? src.textContent : '';
    const ok = () => { const t = b.textContent; b.classList.add('ok'); b.textContent = 'COPIED'; setTimeout(() => { b.textContent = t; b.classList.remove('ok'); }, 1200); };
    const fb = () => { try { const ta = document.createElement('textarea'); ta.value = txt; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); ok(); } catch (er) {} };
    try { navigator.clipboard.writeText(txt).then(ok, fb); } catch (er) { fb(); }
  });
  // G5Q.1d: Settings -> Skills management table (honest static inventory; no fake registry)
  const SKILLS_MGMT = [
    { s:'ext', sl:'EXTERNAL', n:'Graphify scan / read-model', w:'The external Graphify CLI scans a repo into graph.json -> the read-model this dashboard renders.', m:'required: YES (data source) · configured: install the CLI · deps: uv or pipx', x:'Settings -> Graphify CLI' },
    { s:'imp', sl:'IMPLEMENTED', n:'3D Hivemind visualization', w:'Molten-brain 3D view: regions, pathway lighting, camera glide, palettes, motion controls.', m:'required: core · source: scripts/graphify_brain3d.py', x:'' },
    { s:'imp', sl:'IMPLEMENTED', n:'2D Explorer', w:'2D Brain + Structural slice views with search, inspector, slice chips, find/jump.', m:'required: core · source: scripts/graphify_hivemind_explorer.py', x:'' },
    { s:'imp', sl:'IMPLEMENTED', n:'Local graph QA / Ask Console', w:'Two lanes: Graphify answers locally (natural phrasing, most-connected, paths, find/jump); the Claude Code lane answers right here -- one real call per ask, STOP/CLR wired.', m:'required: core · ask "help" for the wired commands', x:'' },
    { s:'imp', sl:'IMPLEMENTED', n:'Node lookup / jump', w:'find / jump-to a node by name -- glides the 3D camera or focuses the 2D explorer.', m:'required: optional · wired in 3D and 2D', x:'' },
    { s:'imp', sl:'IMPLEMENTED', n:'Project graph switching', w:'Selecting a ready project loads ITS graph: views, counts, concepts, ask all follow.', m:'required: optional · needs the bridge to detect generated views', x:'' },
    { s:'imp', sl:'IMPLEMENTED', n:'Local generate / rebuild bridge', w:'Loopback-only bridge runs the allowlisted graphify update in a validated repo path.', m:'required: for graphing repos · source: scripts/graphify_dashboard_bridge.py', x:'start it: python scripts/start_graphify_dashboard.py' },
    { s:'imp', sl:'IMPLEMENTED', n:'Hunter -- project auditor', w:'Graph-first audit: orphans, disconnected groups, missing-link candidates, hotspots, stale signals.', m:'required: optional · local scan + per-click Claude enrichment with jumpable recommendations', x:'run it from Reports' },
    { s:'imp', sl:'IMPLEMENTED', n:'Reports', w:'Stores Hunter reports (this browser), clickable findings jump to the graph, clear/export controls.', m:'required: optional · storage: localStorage (last 10)', x:'' },
    { s:'imp', sl:'IMPLEMENTED', n:'Orphan / disconnect detection', w:'Answered by Hunter via zero-degree + connected-components passes; ask "show orphans".', m:'required: optional · wired via Hunter + ask console', x:'' },
    { s:'imp', sl:'IMPLEMENTED', n:'Path / chain tracing', w:'Ask "shortest path A to B", "trace <name>" (depth layers), "chain end <name>" -- BFS over the selected project edges, honest no-path answers.', m:'required: optional · wired in the ask console (G5Q.1u)', x:'' },
    { s:'imp', sl:'IMPLEMENTED', n:'Hook / process hygiene', w:'Watchdogged hooks + stale-rebuild checker so no process piles up or hangs.', m:'required: optional · source: scripts/cleanup_graphify_processes.py', x:'Settings -> Maintenance' },
    { s:'imp', sl:'IMPLEMENTED', n:'Install / setup', w:'One-command start + first-run landing that detects the scanner and installs it on one click (uv -> pipx -> pip).', m:'required: to run · source: scripts/start_graphify_dashboard.py · standalone repo split planned', x:'Settings -> Setup & Install' },
    { s:'imp', sl:'IMPLEMENTED', n:'Asset seeding', w:'The bridge copies the tracked molten-brain design assets into the served path on startup.', m:'required: for the approved visual · seed_design_assets() in the bridge', x:'' },
    { s:'gate', sl:'GATED', n:'Claude Code MCP connector', w:'One-click REGISTER FOR ME wizard; once connected the Claude Code ask-lane answers IN the dashboard and Hunter enrich makes real recommendations -- one bounded call per explicit click, never automatic.', m:'required: no · status ladder ends LIVE after a real answered ask', x:'Settings -> Claude Code connector' },
    { s:'imp', sl:'MINIMAL', n:'Skills registry / packs', w:'A real LOCAL registry ships: the Graph exporters pack (export summary -> Markdown download; copy stats -> clipboard) with an install/remove toggle in Skills.', m:'required: no · local packs now · remote/community registry planned', x:'Skills -> Skills registry / packs' },
    { s:'imp', sl:'IMPLEMENTED', n:'Visual QA / screenshot gate', w:'Two-viewport browser verification with warning-inclusive console sweeps before any "done".', m:'required: build/support process · not a runtime feature', x:'' },
    { s:'imp', sl:'IMPLEMENTED', n:'Security -- CSRF / loopback bridge', w:'Bridge binds 127.0.0.1, checks the client address, and refuses cross-origin state-changing POSTs.', m:'required: always-on · source: scripts/graphify_dashboard_bridge.py', x:'' }
  ];
  function renderSkillMgmt() {
    const box = $('skill-mgmt'); if (!box) return;
    box.innerHTML = SKILLS_MGMT.map(k =>
      '<div class="skrow"><span class="st st--' + k.s + '" style="flex:none;margin-top:1px">' + k.sl + '</span>'
      + '<div class="skmain"><div class="skname">' + k.n + '</div>'
      + '<div class="skwhat">' + k.w + '</div>'
      + '<div class="skmeta">' + k.m + '</div>'
      + (k.x ? '<div class="sknext">next: ' + k.x + '</div>' : '') + '</div></div>').join('');
  }
  // G5Q.1d: Activity management (copy / clear -- localStorage only)
  function actLogs() {
    let a = [], p = [];
    try { a = JSON.parse(localStorage.getItem('graphify-ask-log') || '[]'); } catch (e) {}
    try { p = JSON.parse(localStorage.getItem('graphify-project-log') || '[]'); } catch (e) {}
    return { a: a, p: p };
  }
  function wireActivityMgmt() {
    const L = actLogs();
    const cc = $('act-counts'); if (cc) cc.textContent = L.a.length + ' ask(s) · ' + L.p.length + ' event(s)';
    const cpy = $('act-copy'); if (cpy) cpy.onclick = () => { try { navigator.clipboard.writeText(JSON.stringify({ asks: L.a, events: L.p }, null, 2)); cpy.textContent = 'COPIED'; setTimeout(() => cpy.textContent = 'COPY LOG (JSON)', 1200); } catch (e) {} };
    const ca = $('act-clear-asks'); if (ca) ca.onclick = () => { if (confirm('Clear the ask log in this browser?')) { try { localStorage.removeItem('graphify-ask-log'); } catch (e) {} renderActivity(); } };
    const ce = $('act-clear-events'); if (ce) ce.onclick = () => { if (confirm('Clear the project/repo event log in this browser?')) { try { localStorage.removeItem('graphify-project-log'); } catch (e) {} renderActivity(); } };
  }
  addEventListener('keydown', e => { if (e.key === 'Escape' && CUR !== 'graph' && !document.body.classList.contains('vpmax')) setSection('graph'); });
  const setCard = id => {
    document.querySelectorAll('#setnav .sn').forEach(n => n.classList.toggle('on', n.dataset.card === id));
    document.querySelectorAll('#setbody > .gcard').forEach(c => c.classList.toggle('on', c.id === id));
  };
  document.querySelectorAll('#setnav .sn').forEach(n => n.onclick = () => setCard(n.dataset.card));
  setCard('set-dashboard');
  const openConnector = id => {
    setSection('settings');
    setCard(id);
    const card = $(id);
    if (card) { card.classList.remove('gflash'); void card.offsetWidth; card.classList.add('gflash'); }
  };
  document.querySelectorAll('#agents .badge').forEach(b => b.onclick = () => openConnWizard(b.dataset.connector));
  // ==== G5Q.1f CONNECT WIZARD: a real setup/connect workflow. Honest ladder --
  // never 'connected' without verification; never a fake OAuth pop-up. ====
  const CW = { which: null, status: null, preview: null };
  const cwGet = k => { try { return JSON.parse(localStorage.getItem(k) || '{}'); } catch (e) { return {}; } };
  const cwSet = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} };
  const cwKey = w => 'graphify-' + w + '-setup-v1';
  const logEv = (ev, d) => { if (window.__logEvent) window.__logEvent(ev, d); };
  async function cwStatus() {
    try { const r = await fetch('/api/connectors/status'); if (r.ok) return await r.json(); } catch (e) {}
    return null;
  }
  function cwLadder(which, st, mem) {
    // returns [ledText, ledClass, shortPill] -- honest rungs only
    // LIVE requires CURRENT-SESSION evidence (sessionStorage) AND real registration
    // (read from ~/.claude.json) -- never a stale localStorage cache from a prior run.
    let live = null; try { live = JSON.parse(sessionStorage.getItem('graphify-cc-live-session') || 'null'); } catch (e) { live = null; }
    if (live && st && st.claudeCodeRegistered) return ['CONNECTED — ANSWERS IN THIS DASHBOARD', 'ok', 'LIVE'];
    if (st && st.claudeCodeRegistered && st.claudeCodeCurrent && mem.listVerified) return ['REGISTERED + VERIFIED BY YOU (CLAUDE MCP LIST)', 'ok', 'VERIFIED'];
    if (st && st.claudeCodeRegistered && st.claudeCodeCurrent) return ['GRAPHIFY IS REGISTERED IN CLAUDE CODE — CHECK IT (STEP 4)', 'mid', 'REGISTERED'];
    if (st && st.claudeCodeRegistered) return ['REGISTERED WITH AN OLD COMMAND — PRESS REGISTER FOR ME AGAIN', 'mid', 'RE-REGISTER'];
    if (mem.addCopied) return ['COMMAND COPIED — PASTE IT INTO A TERMINAL, THEN RE-CHECK', 'mid', 'ADD COPIED'];
    if (st && st.claudeCodeOnPath && !st.graphifyDetected) return ['CLAUDE CODE FOUND — INSTALL THE GRAPHIFY SCANNER (STEP 2)', 'mid', 'NEED SCANNER'];
    if (st && st.claudeCodeOnPath) return ['CLAUDE CODE DETECTED — PRESS REGISTER FOR ME (STEP 3)', 'mid', 'NOT REGISTERED'];
    if (st && !st.claudeCodeOnPath) return ['CLAUDE CODE NOT FOUND ON THIS MACHINE', '', 'NOT INSTALLED'];
    return ['SETUP REQUIRED', '', 'SETUP REQUIRED'];
  }
  function updatePills(st) {
    ['claudecode'].forEach(w => {
      const mem = cwGet(cwKey(w));
      const lad = cwLadder(w, st, mem);
      const el = $('pill-' + w + '-sub');
      if (el) el.textContent = lad[2];
    });
  }
  function cwStepHtml(n, ok, title, body) {
    return '<div class="cm-step"><span class="n' + (ok ? ' ok' : '') + '">' + (ok ? '&#10003;' : n) + '</span>'
      + '<div class="b"><b>' + title + '</b>' + body + '</div></div>';
  }
  function renderWizard() {
    const w = CW.which; if (!w) return;
    const st = CW.status, mem = cwGet(cwKey(w));
    $('cm-title').textContent = 'Connect Claude Code';
    const lad = cwLadder(w, st, mem);
    const led = $('cm-led'); led.textContent = lad[0]; led.className = 'cm-led' + (lad[1] ? ' ' + lad[1] : '');
    $('cm-banner').innerHTML = 'One-time setup, all on your machine. There is <b>no browser sign-in</b> — Claude Code connects to your graphs through a tiny read-only server that ships with this dashboard. The wizard can do every step for you. <b>This dashboard never calls Claude Code</b>; nothing runs until you approve it inside Claude Code.';
    const steps = [];
    const noBridge = st === null;
    {
      const cli = st ? (st.claudeCodeOnPath ? '<div class="res">claude CLI detected on this machine &#10003;</div>'
          : '<div class="res">not found.</div><div class="hint">Open a terminal (Windows: press the Windows key, type <b>terminal</b>, Enter &middot; Mac: search <b>Terminal</b>), paste the install command, run it, then press RE-CHECK in step 4.</div>')
        : '<div class="res">bridge offline — cannot detect the CLI</div>';
      steps.push(cwStepHtml(1, !!(st && st.claudeCodeOnPath), 'Is Claude Code installed?',
        cli + '<button class="conn-btn2" data-cpy-for="cmd-cc-install">COPY INSTALL CMD</button>'));
      const gfy = st ? (st.graphifyDetected ? '<div class="res">graphify detected &#10003;' + (st.graphifyVersion ? ' (' + st.graphifyVersion + ')' : '') + '</div>'
          : '<div class="res">not found — paste the install command into the same terminal.</div>')
        : '<div class="res">bridge offline — cannot detect</div>';
      steps.push(cwStepHtml(2, !!(st && st.graphifyDetected), 'Is the Graphify scanner installed?',
        '<div class="hint">Graphify turns any repo into the knowledge graph. Open source by <b>safishamsi</b> — <a href="https://github.com/safishamsi/graphify" target="_blank" rel="noopener">github.com/safishamsi/graphify</a> (MIT; full credit to the author).</div>'
        + gfy + '<button class="conn-btn2" data-cpy-for="cmd-cc-gfy">COPY INSTALL CMD</button>'));
      const reg = st ? (st.claudeCodeRegistered ? (st.claudeCodeCurrent
            ? '<div class="res">registered in Claude Code &#10003; (graphify found in your Claude Code settings)</div>'
            : '<div class="res">registered, but with an old command — press REGISTER FOR ME to update it.</div>')
          : '<div class="res">not registered yet.</div>')
        : '<div class="res">bridge offline — cannot read registration status</div>';
      const addcmd = st && st.claudeCodeAddCmd ? '<div class="cm-prev">' + st.claudeCodeAddCmd + '</div>' : '';
      const regDis = (noBridge || (st && !st.claudeCodeOnPath)) ? ' disabled title="needs the bridge + an installed Claude Code"' : '';
      steps.push(cwStepHtml(3, !!(st && st.claudeCodeRegistered && st.claudeCodeCurrent), 'Connect Claude Code to your graphs',
        '<div class="hint">One click. This runs Claude Code&rsquo;s own registration command (shown below with the exact paths <b>detected on this machine</b> — nothing is hardcoded). Prefer to do it yourself? Copy the command and paste it into PowerShell or CMD (not Git Bash).</div>'
        + addcmd
        + '<button class="conn-btn" id="cm-register"' + regDis + '>REGISTER FOR ME</button> '
        + '<button class="conn-btn2" id="cm-copyadd">COPY THE COMMAND INSTEAD</button>'
        + '<div id="cm-reg-out"></div>' + reg));
      const self = mem.selftestOk ? '<div class="res">PASS — ' + (mem.selftestSummary || 'local MCP server works') + ' (this proves the LOCAL server, not a Claude connection)</div>' : '<div class="res" id="cm-self-res"></div>';
      steps.push(cwStepHtml(4, !!mem.listVerified, 'Check it worked — then use it',
        '<div class="hint">Run <code>claude mcp list</code> in the terminal — <b>graphify</b> should appear with a health check. Or type <code>/mcp</code> inside Claude Code.</div>'
        + '<button class="conn-btn2" data-cpy-for="cmd-cc-list">COPY CHECK COMMAND</button> '
        + '<button class="conn-btn2" id="cm-recheck">RE-CHECK STATUS</button> '
        + '<button class="conn-btn2" id="cm-mark">IT WORKED — GRAPHIFY SHOWS IN THE LIST</button>'
        + '<div class="hint" style="margin-top:12px">You&rsquo;re set: keep this dashboard open to SEE your graphs (3D Hivemind &middot; Hunter &middot; Reports) and ask Claude Code to THINK about them — try <i>&ldquo;use the graphify tools to summarize this repo&rdquo;</i>. Problems? Test the server by itself:</div>'
        + '<button class="conn-btn2" id="cm-selftest">RUN SELF-TEST</button>' + self));
      $('cm-extension').innerHTML = '<b>How it fits:</b> the Graphify scanner BUILDS the graph &middot; this dashboard SHOWS it &middot; Claude Code THINKS about it. The dashboard never calls Claude Code — you are the link (full picture: How To Guide &sect;15).';
    }
    $('cm-steps').innerHTML = steps.join('');
    wireWizard();
    updatePills(st);
  }
  function wireWizard() {
    const w = CW.which, mem = cwGet(cwKey(w));
    const self = $('cm-selftest');
    if (self) self.onclick = async () => {
      const res = $('cm-self-res'); if (res) res.textContent = 'running…';
      try {
        const r = await fetch('/api/mcp/selftest', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
        const j = await r.json();
        mem.selftestOk = !!j.ok; mem.selftestSummary = j.summary || ''; cwSet(cwKey(w), mem);
        logEv('connector_selftest', { which: w, ok: !!j.ok });
        renderWizard();
        if (!j.ok && res) res.textContent = 'FAILED — ' + (j.summary || 'unknown');
      } catch (e) { if (res) res.textContent = 'bridge offline — copy the self-test command from Settings instead.'; }
    };
    const rg = $('cm-register');
    if (rg) rg.onclick = async () => {
      const out = $('cm-reg-out'); out.innerHTML = '<div class="res">registering… (runs: claude mcp add)</div>';
      try {
        const r = await fetch('/api/claudecode/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
        const j = await r.json();
        if (j.ok) {
          logEv('claudecode_registered', {});
          out.innerHTML = '<div class="res">REGISTERED &#10003; — Claude Code accepted it. Now check it in step 4.</div>';
        } else {
          out.innerHTML = '<div class="res">did not register: ' + (j.reason || j.output || 'unknown') + ' — you can copy the command and run it yourself instead.</div>';
        }
        CW.status = await cwStatus(); renderWizard();
      } catch (e) { out.innerHTML = '<div class="res">bridge offline — copy the command and run it yourself.</div>'; }
    };
    const ca = $('cm-copyadd');
    if (ca) ca.onclick = () => {
      const live = CW.status && CW.status.claudeCodeAddCmd;
      const src = document.getElementById('cmd-cc-add');
      try { navigator.clipboard.writeText(live || (src ? src.textContent : '')); } catch (e) {}
      mem.addCopied = true; cwSet(cwKey(w), mem);
      logEv('claudecode_add_copied', {}); renderWizard();
    };
    const mk = $('cm-mark');
    if (mk) mk.onclick = () => {
      mem.listVerified = true;
      cwSet(cwKey(w), mem);
      logEv('connector_setup_marked', { which: w }); renderWizard();
    };
    const rc = $('cm-recheck');
    if (rc) rc.onclick = async () => { CW.status = await cwStatus(); renderWizard(); };
  }
  async function openConnWizard(which) {
    CW.which = which;
    document.body.classList.add('connmodal');
    $('cm-led').textContent = 'CHECKING…'; $('cm-led').className = 'cm-led';
    $('cm-steps').innerHTML = '<div class="res" style="font:500 11px var(--mono);color:var(--steel-100)">reading live status…</div>';
    logEv('connector_wizard_opened', { which: which });
    CW.status = await cwStatus();
    renderWizard();
  }
  window.__openConnWizard = openConnWizard;
  $('cm-close').onclick = () => document.body.classList.remove('connmodal');
  addEventListener('keydown', e => { if (e.key === 'Escape' && document.body.classList.contains('connmodal')) document.body.classList.remove('connmodal'); });
  cwStatus().then(updatePills);
  // G5Q.1l: overlays must live at BODY level -- inside #main they are trapped
  // in its stacking context (z-index 1) and the LATER #side sibling paints
  // over them (caught live: the chat flyout rendered behind the right rail;
  // the wizard backdrop never covered it either).
  ['chatfly', 'connmodal'].forEach(id => {
    const el = document.getElementById(id);
    if (el && el.parentElement !== document.body) document.body.appendChild(el);
  });
  // G5Q.1q first-run landing: the scanner is the ONE required dependency.
  // Installed -> the dashboard auto-loads as normal (no landing at all).
  // Missing -> a setup page installs it on an explicit click, then loads in.
  (function firstRun() {
    fetch('/api/bridge/status').then(r => r.json()).then(st => {
      if (!st || st.graphifyDetected) return;            // installed -> auto-load
      const d = document.createElement('div');
      d.id = 'landing';
      d.innerHTML = '<div class="ld"><h1>GraphiQuest</h1>'
        + '<p class="ld-sub">One-time setup: this dashboard needs the <b>Graphify scanner</b> &mdash; the open-source tool that turns a repo into the knowledge graph. By <b>safishamsi</b>: <a href="https://github.com/safishamsi/graphify" target="_blank" rel="noopener">github.com/safishamsi/graphify</a> (MIT; full credit to the author). One click installs it; when the dashboard loads, you know it worked.</p>'
        + '<button class="ld-btn" id="ld-go">INSTALL &amp; START</button>'
        + '<div class="ld-stat" id="ld-stat"></div>'
        + '<p class="ld-man">prefer to do it yourself? run <code>uv tool install graphifyy</code> (or <code>pipx install graphifyy</code>), then reload this page</p></div>';
      document.body.appendChild(d);
      const btn = document.getElementById('ld-go'), stat = document.getElementById('ld-stat');
      btn.onclick = () => {
        btn.disabled = true; btn.textContent = 'INSTALLING…';
        stat.textContent = 'running the installer (uv → pipx → pip) — usually under a minute…';
        fetch('/api/setup/install-graphify', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
          .then(r => r.json()).then(j => {
            if (j.ok) {
              stat.textContent = 'graphify ' + (j.version || '') + ' detected ✓ — loading your dashboard…';
              if (window.__logEvent) window.__logEvent('first_run_setup_ok', { installer: j.installer || 'already' });
              setTimeout(() => location.reload(), 1400);
            } else {
              btn.disabled = false; btn.textContent = 'TRY AGAIN';
              stat.textContent = 'setup did not finish: ' + (j.reason || 'unknown') + '\\nYou can also run the manual command below.';
            }
          })
          .catch(() => { btn.disabled = false; btn.textContent = 'TRY AGAIN'; stat.textContent = 'the local bridge is not running — start it with: python scripts/start_graphify_dashboard.py'; });
      };
    }).catch(() => {});                                  // bridge down -> normal page
  })();
  // G5Q.1k: stale-page detector -- this is a static page, so an open tab keeps
  // running the OLD app after the file on disk changes. Instead of silently
  // misbehaving, HEAD-poll our own Last-Modified and say so.
  (function staleWatch() {
    var base = null, iv = null;
    var probe = function (first) {
      try {
        fetch(location.pathname, { method: 'HEAD', cache: 'no-store' }).then(function (r) {
          var lm = r.headers.get('Last-Modified') || '';
          if (first) { base = lm; return; }
          if (base && lm && lm !== base && !document.getElementById('stale-banner')) {
            var b = document.createElement('div');
            b.id = 'stale-banner';
            b.innerHTML = '<b>This dashboard was updated</b>&nbsp;— this tab is running the old version.<button id="stale-reload">RELOAD NOW</button>';
            document.body.appendChild(b);
            document.getElementById('stale-reload').onclick = function () { location.reload(); };
            if (iv) clearInterval(iv);
            if (window.__logEvent) window.__logEvent('stale_page_detected', {});
          }
        }).catch(function () {});
      } catch (e) {}
    };
    probe(true);
    iv = setInterval(function () { probe(false); }, 30000);
    window.__staleCheck = function () { probe(false); };
  })();
  // G5P.6: the top strip renders + wires itself (renderTopStrip); Add opens the modal
  window.__openRepoSettings = () => openConnector('set-repos');
  window.__openSection = setSection;
  window.__openConnector = openConnector;
  // G5Q.1e: connector action panels (status ladder + CHECK SELF-TEST + steps)
  const MCP_KEY = 'graphify-mcp-selftest-v1';
  function paintConnLed(which) {
    let live = null;
    // CURRENT-SESSION evidence only: a real answered ask this session sets a
    // sessionStorage marker. A fresh browser/session has none, so the LED never
    // shows a stale LIVE carried over from a previous session.
    try { live = JSON.parse(sessionStorage.getItem('graphify-cc-live-session') || 'null'); } catch (e) {}
    const led0 = $(which + '-led'), sub0 = $(which + '-substatus');
    if (live && led0) {
      led0.textContent = 'LIVE — ANSWERED IN THIS DASHBOARD'; led0.classList.add('ok');
      if (sub0) sub0.textContent = 'your Claude Code answered an ask from the response window (' + (live.durationS ? live.durationS + 's' : 'ok') + ') — calls happen ONLY when you ask in the Claude Code lane';
      return;
    }
    let st = null;
    try { st = JSON.parse(localStorage.getItem(MCP_KEY) || 'null'); } catch (e) {}
    const led = $(which + '-led'), sub = $(which + '-substatus');
    if (st && st.ok) {
      if (led) { led.textContent = 'SELF-TEST PASSED'; led.classList.add('ok'); }
      if (sub) sub.textContent = 'local MCP server works (' + (st.summary || '') + ') \u2014 now connect Claude Code below + approve. Still GATED: no call is made from here.';
    } else {
      if (led) { led.textContent = 'NOT CONNECTED'; led.classList.remove('ok'); }
      if (sub) sub.textContent = 'no call has ever been made from this dashboard';
    }
  }
  window.__paintConnLeds = () => { paintConnLed('claudecode'); cwStatus().then(updatePills); };
  async function checkSelftest(which) {
    const sub = $(which + '-substatus'); if (sub) sub.textContent = 'running the local MCP self-test\u2026';
    try {
      const r = await fetch('/api/mcp/selftest', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      const j = await r.json();
      try { localStorage.setItem(MCP_KEY, JSON.stringify({ ok: !!j.ok, summary: j.summary || '', ts: Date.now() })); } catch (e) {}
      paintConnLed(which);
      if (!j.ok && sub) sub.textContent = 'self-test did not pass: ' + (j.summary || 'unknown') + ' \u2014 or run the copied command yourself.';
    } catch (e) {
      if (sub) sub.textContent = 'local bridge not detected \u2014 copy the self-test command and run it yourself.';
    }
  }
  function focusSteps(which) {
    const card = $('set-' + which);
    const step = card && card.querySelector('.setup-step');
    if (step) { try { step.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (e) {} }
  }
  ['claudecode'].forEach(which => {
    const cn = $(which + '-connect');
    if (cn) cn.onclick = () => openConnWizard(which);   // G5Q.1f: CONNECT opens the real wizard
    const ck = $(which + '-check'); if (ck) ck.onclick = () => checkSelftest(which);
    const sp = $(which + '-steps'); if (sp) sp.onclick = () => focusSteps(which);
  });
  // copy-for buttons (connector panels reference a cmd block by id)
  document.addEventListener('click', e => {
    const b = e.target.closest && e.target.closest('[data-cpy-for]');
    if (!b) return;
    const src = document.getElementById(b.dataset.cpyFor);
    if (!src) return;
    const ok = () => { const t = b.textContent; b.classList.add('ok'); b.textContent = 'COPIED'; setTimeout(() => { b.textContent = t; b.classList.remove('ok'); }, 1200); };
    try { navigator.clipboard.writeText(src.textContent).then(ok, ok); } catch (er) {}
  });
  // skills filter chips + skill action routing
  document.addEventListener('click', e => {
    const f = e.target.closest && e.target.closest('.skf');
    if (f) {
      document.querySelectorAll('#skill-filter .skf').forEach(x => x.classList.toggle('on', x === f));
      const want = f.dataset.f;
      document.querySelectorAll('.sec[data-sec=skills] .gcards .gcard').forEach(c => {
        c.style.display = (want === 'all' || c.dataset.st === want) ? '' : 'none';
      });
      return;
    }
    const a = e.target.closest && e.target.closest('.skact');
    if (a) {
      const act = a.dataset.action;
      if (act === 'set-claudecode') openConnWizard('claudecode');   // Connect = the wizard
      else if (act === 'toggle-pack-exporters') {
        const on = window.__packToggle && window.__packToggle('graph-exporters');
        a.textContent = on ? 'REMOVE PACK (INSTALLED)' : 'INSTALL PACK';
      }
      else if (act && act.indexOf('set-') === 0) openConnector(act);
      else if (window.__skillAction) window.__skillAction(act);
    }
  });
  function renderActivity() {
    wireActivityMgmt();
    const pbox = $('act-proj');
    if (pbox) {
      let plog = [];
      try { plog = (window.__projLog ? window.__projLog() : []); } catch (e) {}
      pbox.innerHTML = plog.length ? plog.slice(0, 50).map(en => {
        const t = String(en.ts || '').replace('T', ' ').slice(0, 19);
        const d = en.detail || {};
        const txt = en.ev + ': ' + (d.id || '') + (d.status ? ' (' + d.status + ')' : '') + (d.path ? ' -> ' + d.path : '');
        const q = txt.replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[ch]);
        return '<div class="arow"><span class="at">' + t + '</span><span class="aq" title="' + q + '">' + q + '</span></div>';
      }).join('') : '<div class="aempty">No project events yet in this browser.</div>';
    }
    const box = $('act-asks');
    let log = [];
    try { log = (window.__askLog ? window.__askLog() : JSON.parse(localStorage.getItem('graphify-ask-log') || '[]')); } catch (e) {}
    if (!log.length) { box.innerHTML = '<div class="aempty">No asks recorded yet in this browser.</div>'; return; }
    box.innerHTML = log.slice(0, 50).map(en => {
      const t = String(en.ts || '').replace('T', ' ').slice(0, 19);
      const st = en.status === 'answered' ? 'imp' : en.status === 'error' ? 'gate' : 'plan';
      const q = String(en.q || '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[ch]);
      return '<div class="arow"><span class="at">' + t + '</span><span class="as st st--' + st + '">' + (en.status || '?') + '</span><span class="aq" title="' + q + '">' + q + '</span></div>';
    }).join('');
  }
})();
"""


# G5P.8: "most important files" is COMPUTED from the loaded read-model in the
# browser (top degree) -- a baked list was wrong for every non-default project.

def card(cid, name, chip, selected, desc, stats) -> str:
    sel = " card--sel" if selected else ""
    dot = '<span class="dot"></span>' if selected else ""
    return (f'<div class="card{sel}" id="card-{cid}" data-proj="{cid}"><div class="card__top"><b>{html.escape(name)}</b>'
            f'<span class="chip">{html.escape(chip)}</span></div>'
            f'<p class="card__desc">{html.escape(desc)}</p>'
            f'<p class="card__stats">{dot}{html.escape(stats)}</p></div>')


# ==== G5P.9 HUNTER CORE: pure analyzer, injected as plain JS (no backslashes --
# unit-tested standalone via a node harness in tests/test_graphify_hunter.py) ====
HUNTER_JS = """
// G5P.9 Hunter core: graph-first project auditor (local-only; conservative wording).
window.__huntAnalyze = function (rm, ctx) {
  ctx = ctx || {};
  const nodes = (rm && rm.nodes) || [];
  const edges = (rm && rm.edges) || [];
  const md = (rm && rm.metadata) || {};
  const F = [];
  let fid = 0;
  const add = (sev, kind, title, nodeIds, evidence, action, confidence) => F.push({
    id: 'f' + (++fid), sev: sev, kind: kind, title: title, nodeIds: nodeIds || [],
    evidence: evidence, action: action, confidence: confidence || 'medium',
    clickable: !!(nodeIds && nodeIds.length), localOnly: true });
  const byId = new Map(nodes.map(n => [n.id, n]));
  const vdeg = new Map();
  for (const e of edges) { vdeg.set(e.source, (vdeg.get(e.source) || 0) + 1); vdeg.set(e.target, (vdeg.get(e.target) || 0) + 1); }
  const rank = new Map(nodes.slice().sort((a, b) => (b.degree || 0) - (a.degree || 0)).map((n, i) => [n.id, i]));
  // 1) true graph orphans: degree is computed over the FULL filtered repo graph upstream
  const orphans = nodes.filter(n => (n.degree || 0) === 0);
  for (const n of orphans.slice(0, 12)) add('low', 'orphan', 'Orphan candidate: ' + n.label, [n.id],
    'graph evidence: no relationships were extracted anywhere in this repo for ' + (n.file_path || n.label) + '.',
    'Inspect the file - possible dead code, an entry point, or an extraction gap. Not proof of a bug.', 'medium');
  if (orphans.length > 12) add('low', 'orphan', orphans.length + ' orphan candidates in total',
    orphans.slice(12, 42).map(n => n.id),
    'graph evidence: ' + orphans.length + ' nodes have zero extracted relationships (first 12 listed individually above).',
    'Sweep these files together - many orphans in one area can suggest an unwired module.', 'medium');
  // 2) view-isolated vs real orphans (honesty split: caps can isolate connected nodes)
  const viewIso = nodes.filter(n => (n.degree || 0) > 0 && !vdeg.has(n.id));
  if (viewIso.length) add('info', 'view-isolated', viewIso.length + ' nodes look isolated in this view only', [],
    'these nodes have repo-level connections, but their edges fell outside this view (slice caps). They are not orphans.',
    'No action needed - switch slices if you need to see their links.', 'high');
  // 3) disconnected groups (union-find over the view edges; labeled view-scope)
  const par = new Map();
  const find = x => { while (par.get(x) !== x) { par.set(x, par.get(par.get(x))); x = par.get(x); } return x; };
  for (const n of nodes) par.set(n.id, n.id);
  for (const e of edges) { if (par.has(e.source) && par.has(e.target)) { const a = find(e.source), b = find(e.target); if (a !== b) par.set(a, b); } }
  const comp = new Map();
  for (const n of nodes) { if (!vdeg.has(n.id)) continue; const r = find(n.id); if (!comp.has(r)) comp.set(r, []); comp.get(r).push(n.id); }
  const comps = Array.from(comp.values()).sort((a, b) => b.length - a.length);
  if (comps.length > 1) {
    const heads = comps.slice(1, 6).map(ids => ids.slice().sort((a, b) => ((byId.get(b) || {}).degree || 0) - ((byId.get(a) || {}).degree || 0))[0]);
    add(comps[0].length / Math.max(1, nodes.length) < 0.5 ? 'medium' : 'low', 'component',
      comps.length + ' disconnected groups in this view (largest holds ' + comps[0].length + ' of ' + nodes.length + ' nodes)', heads,
      'graph evidence: union-find over the view edges found ' + comps.length + ' separate groups. View-scope: slice caps can split groups.',
      'Inspect the head node of each smaller group - check why it is isolated from the main structure.', 'medium');
  }
  // 4) low-connectivity leaves
  const lowdeg = nodes.filter(n => (n.degree || 0) === 1);
  if (lowdeg.length) add('info', 'low-degree', lowdeg.length + ' files with exactly one connection',
    lowdeg.slice(0, 8).map(n => n.id),
    'single-link files are leaves - normal for configs/docs, worth a look for source files.',
    'Skim the source-code entries; a leaf that should be load-bearing is a possible missing relationship.', 'low');
  // 5) missing-relationship candidates: same directory, zero internal links
  const SLASH = '/';
  const dirOf = p => { const f = String(p || '').split(String.fromCharCode(92)).join(SLASH); return f.includes(SLASH) ? f.slice(0, f.lastIndexOf(SLASH)) : '(root)'; };
  const byDir = new Map();
  for (const n of nodes) { const d2 = dirOf(n.file_path); if (!byDir.has(d2)) byDir.set(d2, []); byDir.get(d2).push(n); }
  const intra = new Map();
  for (const e of edges) { const a = byId.get(e.source), b = byId.get(e.target); if (a && b) { const da = dirOf(a.file_path), db = dirOf(b.file_path); if (da === db) intra.set(da, (intra.get(da) || 0) + 1); } }
  let mrCount = 0;
  const dirsBySize = Array.from(byDir.entries()).sort((x, y) => y[1].length - x[1].length);
  for (const pair of dirsBySize) {
    if (mrCount >= 5) break;
    const d2 = pair[0], list = pair[1];
    if (list.length >= 3 && list.length <= 40 && !intra.get(d2)) {
      mrCount++;
      add('low', 'missing-rel', 'Possible missing links inside ' + d2 + SLASH + ' (' + list.length + ' files, 0 internal connections)',
        list.slice(0, 5).map(n => n.id),
        'graph evidence: files sharing this directory have no extracted relationships between them.',
        'Candidate only - inspect whether these files should reference each other or are intentionally independent.', 'low');
    }
  }
  // 6) hotspots (review-critical hubs)
  const hot = nodes.slice().sort((a, b) => (b.degree || 0) - (a.degree || 0)).slice(0, 5).filter(n => (n.degree || 0) >= 5);
  if (hot.length) add('info', 'hotspot', 'Hotspots: ' + hot.map(n => n.label).join(', '), hot.map(n => n.id),
    'highest-degree nodes - changes here ripple widest: ' + hot.map(n => n.label + ' (deg ' + n.degree + ')').join(' | '),
    'Treat these as review-critical paths; good first stops when exploring the project.', 'high');
  // 7) build-state / coverage disclosures
  if ((md.emitted_edges || 0) >= 12000) add('info', 'coverage', 'Edge cap reached (12,000)', [],
    'the view keeps the top 12,000 edges by weight - connectivity findings describe the view, not the full repo.',
    'Treat component results as view-scope.', 'high');
  if (md.slice_mode === 'generic-structure' && (md.filtered_nodes || 0) > (md.emitted_nodes || 0))
    add('info', 'coverage', 'View holds the top ' + md.emitted_nodes + ' of ' + md.filtered_nodes + ' extracted nodes', [],
      'generic mode caps the view by degree for 3D performance; the lowest-degree nodes are not shown.',
      'Nothing to fix - disclosure so the counts read honestly.', 'high');
  const sevRank = { high: 0, medium: 1, low: 2, info: 3 };
  F.sort((a, b) => (sevRank[a.sev] !== undefined ? sevRank[a.sev] : 9) - (sevRank[b.sev] !== undefined ? sevRank[b.sev] : 9));
  const counts = { high: 0, medium: 0, low: 0, info: 0 };
  for (const f of F) counts[f.sev] = (counts[f.sev] || 0) + 1;
  return { counts: counts, findings: F.map(f => Object.assign({}, f, { in3d: f.nodeIds.length ? ((rank.get(f.nodeIds[0]) !== undefined ? rank.get(f.nodeIds[0]) : 99999) < 1200) : null })) };
};
"""

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>GraphiQuest — Knowledge Graph (local)</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600;700&family=Saira:wght@300;500;600&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
<style>
 /* ==== G5G: FORGE_DESIGN token contract (.docs/design/FORGE_DESIGN.md) + the
    proof.css glass-pop recipe (DAFORGELAYER_WEBSITE_VISUAL_ASSET_PIPELINE SS14).
    Canvas black -- glass charcoal translucent panels -- steel-ladder rims --
    ONE accent (molten amber; status colors stay muted) -- Orbitron display /
    Inter UI / JetBrains Mono telemetry. Panels are REAL glass: translucent
    fills + backdrop blur refracting the molten glow pools staged behind. ==== */
 :root{{
   --canvas:#000;--glass:#0a0a0a;--glass2:#121212;
   --steel-900:#161616;--steel-700:#262626;--steel-500:#3a3a3a;--steel-300:#8a8a8a;--steel-200:#b4b4b4;
   --ink:#f5f5f5;--ink-soft:#cfcfcf;--dim:#a8adb8;
   --molten:#ff7a18;--molten-hot:#ffae3c;--molten-deep:#c2410c;--glow:rgba(255,122,24,.35);
   --good:#4ea672;--warn:#d4a017;--missing:#b04a4a;--link:#9fb8d6;
   --line:rgba(255,255,255,.08);--line2:rgba(255,255,255,.14);
   --r-md:12px;--r-lg:14px;--pill:9999px;
   --display:'Orbitron',ui-sans-serif,system-ui,sans-serif;
   --ui:Inter,system-ui,'Segoe UI',sans-serif;
   --mono:'JetBrains Mono',ui-monospace,Consolas,monospace;
   /* G5I: TRUE BLACK glass (operator: panels were grey blocks) -- panels darkest,
      capsules slightly lighter so they sit ABOVE the glass */
   --glass-fill:linear-gradient(160deg,rgba(16,17,20,.62) 0%,rgba(6,7,9,.55) 100%);
   --capsule-fill:linear-gradient(180deg,rgba(44,32,18,.35) 0%,rgba(16,17,21,.50) 55%,rgba(8,9,11,.55) 100%);
   --capsule-rim:rgba(255,138,56,.32);          /* amber rim -- glass catching molten light */
   --display-thin:'Saira',var(--ui);            /* FORGE display: thin/cinematic (G5K) */
   --glass-blur:blur(16px) saturate(1.15);
   --bevel:inset 0 1px 0 rgba(255,255,255,.12);
   --bevel-molten:inset 0 -1px 0 rgba(255,138,56,.10);
   --depth:0 22px 44px -26px rgba(0,0,0,.85);
   --trim-amber:0 0 10px -4px rgba(255,122,24,.4);  /* slim outer trim glow */
 }}
 html,body{{margin:0;height:100%;background:var(--canvas);color:var(--ink);font:15.5px/1.55 var(--ui)}}
 body{{display:grid;grid-template-columns:296px 1fr 296px;grid-template-rows:1fr;gap:0;height:100vh;overflow:hidden}}
 /* G5H STAGE: crisp rich obsidian black -- NO smoke/haze imagery. Subtle radial
    depth + two FAINT edge lights (one warm, one cool) so the translucent glass
    panels still have something to refract, + a whisper reflection band. */
 body::before{{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;background:
   radial-gradient(115% 80% at 50% 42%, transparent 50%, rgba(0,0,0,.7) 100%),
   linear-gradient(168deg, rgba(255,255,255,.028) 0%, transparent 16%),
   radial-gradient(34% 26% at 4% 6%, rgba(255,122,24,.05), transparent 70%),
   radial-gradient(30% 24% at 98% 96%, rgba(120,160,255,.035), transparent 70%),
   radial-gradient(90% 70% at 50% 44%, #0b0c0f 0%, #060708 52%, #020203 100%)}}
 /* grain (~4%, mix-blend overlay) -- texture without smoke */
 body::after{{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
   background:url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><filter id="n"><feTurbulence baseFrequency="0.85" numOctaves="2"/><feColorMatrix values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0.55 0"/></filter><rect width="200" height="200" filter="url(%23n)"/></svg>');
   mix-blend-mode:overlay;opacity:.04}}
 #rail,#main,#side{{position:relative;z-index:1}}
 a{{color:var(--link);text-decoration:none}}
 /* left rail — glass sidebar (translucent over the molten stage, NOT flat black) */
 #rail{{background:var(--glass-fill);-webkit-backdrop-filter:var(--glass-blur);backdrop-filter:var(--glass-blur);border-right:1px solid var(--line);box-shadow:var(--bevel),var(--depth);padding:16px 14px 12px;display:flex;flex-direction:column;min-height:0}}
 #brand{{display:flex;gap:10px;align-items:center;margin:0 4px 20px}}
 /* G5H: NEW generated GraphiQuest mark (ignored staging; wordmark stays DOM).
    overflow-crop zooms to the emblem tile face; gradient fallback if missing */
 #brand .logo{{width:52px;height:52px;border-radius:14px;overflow:hidden;position:relative;flex:none;background:linear-gradient(135deg,#1a1a1f,#0a0a0c);border:1px solid var(--steel-700);box-shadow:0 0 16px -2px var(--glow),inset 0 1px 0 rgba(255,255,255,.18)}}
 #brand .logo img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
 #brand b{{font:700 21px var(--display);display:block;letter-spacing:.02em;white-space:nowrap}}
 #brand .sub{{font:600 11.5px var(--ui);color:var(--steel-300);letter-spacing:.28em;display:flex;align-items:center;gap:10px}}
 #brand .sub i{{flex:1;height:1px;background:linear-gradient(90deg,var(--steel-500),transparent);min-width:34px}}
 #brand > div:last-child{{flex:1;min-width:0}}
 .nav{{padding:9px 12px;border-radius:12px;margin:2px 0;font:500 14.5px var(--ui);color:var(--steel-200);cursor:default;transition:background .15s,color .15s}}
 .nav:hover{{background:rgba(255,255,255,.04);color:var(--ink)}}
 .nav.on{{background:linear-gradient(90deg,rgba(255,122,24,.14),rgba(18,18,18,.65));color:var(--molten-hot);border:1px solid rgba(255,138,56,.4);border-radius:var(--pill);padding:8px 12px;box-shadow:var(--bevel),0 0 12px -6px var(--glow);font-weight:600}}
 #agents{{margin-top:22px}} #agents .lbl{{font:600 11px var(--ui);color:var(--steel-300);letter-spacing:.15em;margin:0 4px 8px}}
 /* agent badges — FORGE status semantics: amber = ALIVE (the one accent);
    candidates use the muted warn/missing ladder (no second brand color) */
 .badge{{border:1px solid var(--capsule-rim);border-radius:var(--pill);padding:7px 10px;margin:3.5px 0;font:500 12.5px var(--mono);letter-spacing:.05em;text-align:center;background:var(--capsule-fill);box-shadow:inset 0 1px 0 rgba(255,255,255,.13),inset 0 -1px 0 rgba(0,0,0,.45);transition:border-color .15s,box-shadow .15s}}
 .badge:hover{{border-color:var(--steel-500)}}
 .badge.alive{{border-color:rgba(255,122,24,.55);color:var(--molten-hot);background:linear-gradient(180deg,rgba(80,42,10,.4),rgba(34,17,5,.46));box-shadow:inset 0 1px 0 rgba(255,210,160,.2),inset 0 -1px 0 rgba(0,0,0,.45),0 0 14px -4px var(--glow)}}
 .badge.warn{{color:var(--warn);border-color:rgba(212,160,23,.35)}}
 .badge.missing{{color:#cf7070;border-color:rgba(207,112,112,.35)}}
 #railfoot{{margin-top:auto;font:400 11px var(--mono);color:var(--steel-300);padding:0 4px}}
 /* top glass plate (G5M): the header + project cards sit ON one glass surface */
 #plate{{background:rgba(14,15,18,.42);-webkit-backdrop-filter:blur(12px) saturate(1.1);backdrop-filter:blur(12px) saturate(1.1);border:1px solid var(--line);border-radius:var(--r-lg);padding:9px 12px 10px;box-shadow:var(--bevel)}}
 /* main -- G5H compact header: the viewport reclaims the wasted vertical band */
 #main{{padding:10px 9px 10px;min-width:0;display:flex;flex-direction:column;overflow:hidden}}
 #hrow{{display:flex;align-items:baseline;gap:14px}}
 #crumb{{font:600 11px var(--ui);letter-spacing:.12em;color:var(--steel-300);text-transform:uppercase}} #crumb b{{color:var(--ink-soft)}}
 h1{{font:300 28px var(--display-thin);margin:0;letter-spacing:.04em}}
 #sub{{font:400 13px var(--ui);color:var(--dim);max-width:900px;margin:0 0 8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
 #cards{{display:flex;gap:8px;overflow-x:auto;padding-bottom:2px;flex:none;scrollbar-width:none}}
 #cards::-webkit-scrollbar{{display:none}}
 /* project cards — the pf-card glass-tile recipe (proof.css reference): translucent
    fill + blur refracting the stage pools + molten top-edge + lift/glow hover */
 .card{{flex:0 0 205px;position:relative;background:linear-gradient(160deg,rgba(26,29,35,.55) 0%,rgba(10,12,15,.48) 100%);-webkit-backdrop-filter:var(--glass-blur);backdrop-filter:var(--glass-blur);border:1px solid var(--capsule-rim);border-radius:var(--r-md);padding:7px 12px 8px;box-shadow:var(--bevel),var(--bevel-molten),var(--depth);transition:transform .2s ease,border-color .2s ease,box-shadow .25s ease}}
 .card::before{{content:'';position:absolute;left:16px;right:16px;top:-1px;height:1px;border-radius:2px;background:linear-gradient(90deg,transparent,rgba(255,122,0,.55),transparent);opacity:.65;transition:opacity .25s ease;pointer-events:none}}
 .card:hover{{transform:translateY(-3px);border-color:rgba(255,138,56,.45);box-shadow:inset 0 1px 0 rgba(255,255,255,.16),0 28px 56px -26px rgba(0,0,0,.9),0 0 40px -16px rgba(255,122,0,.35)}}
 .card:hover::before{{opacity:1}}
 .card--sel{{border-color:rgba(255,138,56,.6);box-shadow:var(--bevel),0 0 18px -7px var(--glow)}}
 .card__top{{display:flex;justify-content:space-between;align-items:center;gap:7px}}
 .card b{{font:600 14px var(--ui);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
 .chip{{border:1px solid var(--capsule-rim);color:#ded7cd;border-radius:var(--pill);padding:1px 9px;font:500 11px var(--mono);letter-spacing:.05em;flex:none;background:var(--capsule-fill);box-shadow:inset 0 1px 0 rgba(255,255,255,.14)}}
 .card__desc{{margin:3px 0 4px;font:400 12.5px/1.35 var(--ui);color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
 .card__stats{{margin:0;font:500 11.5px var(--mono);color:var(--ink-soft)}}
 .gen-live{{color:#fbbf24;animation:genPulse 1.4s ease-in-out infinite}}
 .gen-err{{color:#f87171}}
 @keyframes genPulse{{0%,100%{{opacity:.45}}50%{{opacity:1}}}}
 #bridge-banner{{margin:8px 0 0;padding:8px 13px;border:1px solid rgba(251,191,36,.35);border-radius:10px;background:rgba(251,191,36,.07);font:500 12px var(--ui);color:var(--ink-soft);display:flex;gap:10px;align-items:center}}
 #bridge-banner code{{color:var(--ink)}}
 #bb-x{{margin-left:auto;cursor:pointer;color:var(--steel-300);font-size:15px}}
 .dot{{display:inline-block;width:6px;height:6px;border-radius:3px;background:var(--good);margin-right:6px}}
 .card--add{{border-style:dashed;border-color:var(--steel-500);color:var(--steel-300);display:flex;align-items:center;justify-content:center;font:500 13px var(--ui)}}
 /* viewport — premium black-glass chamber: chamber plate at low presence, strong
    bevel + steel rim + molten edge glow + corner reflections; brain unobstructed */
 #vp{{position:relative;flex:1;min-height:0;border-radius:var(--r-lg);margin:8px 0 0;overflow:hidden;background:url('../design/agentic-os-visual-system/proofs-v4/proof_v4_hivemind_viewport_backing_i2i_seed309104.png') 0 0/100% 100% no-repeat;background-color:#020203;border:1px solid rgba(255,138,56,.26);box-shadow:inset 0 0 32px rgba(0,0,0,.5), var(--depth), 0 0 7px -5px rgba(255,122,24,.28)}}
 #vp iframe{{position:absolute;inset:4px;width:calc(100% - 8px);height:calc(100% - 8px);border:0;border-radius:10px;background:#000}}
 #vp .proj{{position:absolute;top:12px;left:14px;background:rgba(10,10,10,.65);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);border:1px solid var(--line);border-radius:var(--pill);padding:6px 13px;font:600 12.5px var(--ui);z-index:2;box-shadow:var(--bevel)}}
 #vp .proj .mono{{font:500 11.5px var(--mono);color:var(--dim)}}
 #vp .proj .dot{{vertical-align:1px}}
 #vp .ctl{{position:absolute;top:12px;right:14px;display:flex;gap:6px;z-index:2}}
 /* glass capsules v2 (G5H): LAYERED translucent fill + inner top highlight +
    bottom bevel + steel rim; ACTIVE = molten-rim (the one amber accent) */
 .pill{{background:var(--capsule-fill);-webkit-backdrop-filter:blur(12px) saturate(1.15);backdrop-filter:blur(12px) saturate(1.15);border:1px solid var(--capsule-rim);color:#ded7cd;border-radius:var(--pill);padding:6px 15px;font:600 13px var(--ui);cursor:pointer;box-shadow:inset 0 1px 0 rgba(255,255,255,.16),inset 0 -1px 0 rgba(0,0,0,.25);transition:border-color .15s,color .15s,box-shadow .15s,transform .15s}}
 .pill:hover{{border-color:rgba(255,138,56,.55);color:var(--ink);transform:translateY(-1px);box-shadow:inset 0 1px 0 rgba(255,255,255,.2),inset 0 -1px 0 rgba(0,0,0,.25),0 0 18px -6px var(--glow)}}
 .pill:focus-visible{{outline:none;box-shadow:inset 0 1px 0 rgba(255,255,255,.16),0 0 0 3px var(--glow)}}
 .pill.on{{background:linear-gradient(180deg,rgba(90,48,12,.42),rgba(40,20,6,.5));border-color:var(--molten);color:var(--molten-hot);font-weight:700;box-shadow:inset 0 1px 0 rgba(255,210,160,.25),inset 0 -1px 0 rgba(0,0,0,.25),0 0 16px -4px var(--glow)}}
 /* ONE unified left console (G5M): responses + ask in a single glass panel */
 #console{{flex:1;min-height:120px;display:flex;flex-direction:column;background:var(--glass-fill);-webkit-backdrop-filter:var(--glass-blur);backdrop-filter:var(--glass-blur);border:1px solid rgba(255,138,56,.30);border-radius:var(--r-md);padding:11px 12px 10px;margin-top:14px;box-shadow:var(--bevel),0 0 14px -9px var(--glow);min-width:0}}
 #console .k{{font:600 11px var(--ui);color:var(--steel-300);letter-spacing:.15em;margin:0 0 6px}}
 #resp-body{{flex:1;min-height:50px;overflow-y:auto}}
 #resp-body .dim{{font:400 12px var(--ui);color:var(--steel-300);line-height:1.5}}
 #ask{{flex:none;border-top:1px solid var(--line);margin-top:9px;padding-top:9px}}
 #ask-ctx{{display:flex;align-items:center;gap:7px;margin-bottom:7px;min-width:0}}
 #ask-proj{{display:inline-flex;align-items:center;font:600 11.5px var(--ui);color:var(--ink-soft);white-space:nowrap}}
 #ask-node{{font:500 10.5px var(--mono);color:var(--steel-300);min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
 #ask-node.live{{color:var(--molten-hot)}}
 #ask-in{{width:100%;box-sizing:border-box;background:rgba(0,0,0,.45);border:1px solid var(--line);border-radius:10px;color:var(--ink);font:400 12.5px var(--ui);padding:7px 11px;outline:none;transition:border-color .15s}}
 #ask-in::placeholder{{color:var(--steel-300)}}
 #ask-in:focus{{border-color:rgba(255,138,56,.5);box-shadow:0 0 0 3px rgba(255,122,24,.18)}}
 #ask-foot{{display:flex;align-items:center;gap:5px;row-gap:5px;margin-top:7px;flex-wrap:wrap;min-width:0}}  /* G5O.2c: never overflow the console trim */
 #ask-lanes{{display:inline-flex;gap:4px;flex:1 1 auto;min-width:0}}
 .lane{{background:rgba(18,18,18,.55);border:1px solid var(--steel-700);color:var(--steel-200);border-radius:var(--pill);padding:4px 8px;font:600 10.5px/1 var(--ui);cursor:pointer;transition:border-color .15s,color .15s}}  /* G5O.2c: same block padding as ASK = aligned bubbles */
 .lane:hover{{border-color:rgba(255,138,56,.45);color:var(--ink)}}
 .lane.on{{background:rgba(255,122,24,.10);border-color:var(--molten);color:var(--molten-hot)}}
 .lane.dim{{opacity:.45}}
 #ask-go{{margin-left:auto;flex:none;background:linear-gradient(180deg,rgba(90,48,12,.5),rgba(40,20,6,.55));border:1px solid var(--molten);color:var(--molten-hot);border-radius:var(--pill);padding:4px 11px;font:700 10.5px/1 var(--ui);letter-spacing:.08em;cursor:pointer;box-shadow:inset 0 1px 0 rgba(255,210,160,.2);transition:box-shadow .15s}}
 #ask-go:hover{{box-shadow:inset 0 1px 0 rgba(255,210,160,.2),0 0 0 3px var(--glow)}}
 /* G5P local-ask response cards -- same glass language as the right-panel scards */
 .rcard{{background:rgba(18,19,23,.55);border:1px solid rgba(255,255,255,.07);border-radius:10px;padding:8px 10px;margin:0 0 8px;box-shadow:var(--bevel)}}
 .rcard__q{{font:500 10.5px var(--mono);color:var(--steel-300);margin-bottom:4px;word-break:break-word}}
 .rcard__a{{font:400 12px var(--ui);color:var(--ink-soft);line-height:1.5;white-space:pre-wrap;word-break:break-word}}
 .rcard__m{{display:flex;justify-content:space-between;align-items:center;gap:6px;margin-top:6px;border-top:1px solid var(--line);padding-top:5px}}
 .rcard__s{{font:600 9px var(--ui);letter-spacing:.08em;text-transform:uppercase;border:1px solid;border-radius:var(--pill);padding:2px 8px}}
 .rcard__s--answered{{color:var(--good);border-color:rgba(78,166,114,.4)}}
 .rcard__s--unsupported{{color:var(--warn);border-color:rgba(212,160,23,.45)}}
 .rcard__s--error{{color:#cf7070;border-color:rgba(207,112,112,.45)}}
 .rcard__t{{font:400 9.5px var(--mono);color:var(--steel-300)}}
 #ask-note{{display:block;margin-top:6px;font:400 9.5px var(--mono);color:var(--steel-300);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
 /* right intelligence panel — glass instrument panel */
 #side{{background:var(--glass-fill);-webkit-backdrop-filter:var(--glass-blur);backdrop-filter:var(--glass-blur);border-left:1px solid var(--line);box-shadow:var(--bevel),var(--depth);padding:16px 15px 12px;font:400 13.5px var(--ui);display:flex;flex-direction:column;min-height:0}}
 #side-scroll{{flex:1;overflow-y:auto;overflow-x:hidden;min-height:0;margin-right:-6px;padding-right:6px}}  /* overflow-x: 1px child overshoot spawned a horizontal scrollbar at 1366 (G5O.0) */
 #side .k{{font:600 11px var(--ui);color:var(--steel-300);letter-spacing:.15em;margin:16px 0 5px}} #side .k:first-child{{margin-top:0}}
 #side .big{{font:500 24px var(--mono);color:var(--ink)}} #side .big small{{font:400 11px var(--ui);color:var(--steel-300);margin-left:7px}}
 .leg{{display:flex;gap:8px;align-items:baseline;margin:4px 0;color:var(--steel-200);font:400 13px var(--ui)}}
 .leg i{{width:7px;height:7px;border-radius:4px;flex:none;display:inline-block}}
 ol{{margin:5px 0 0 18px;padding:0}} li{{margin:4px 0;font:500 12.5px var(--mono);color:var(--ink-soft)}}
 /* Open-3D overlay (G5J): the SAME iframe expands fullscreen -- no reload, no lost
    state; Esc or Close returns. */
 body.vpmax #main{{z-index:70}}              /* lift the whole stacking context above #side/#foot */
 body.vpmax #vp{{position:fixed;inset:12px;z-index:60;margin:0}}
 /* right-panel glass sub-cards (G5K) */
 .scard{{position:relative;background:rgba(18,19,23,.55);border:1px solid rgba(255,255,255,.07);border-radius:var(--r-md);padding:12px 13px;margin-bottom:14px;box-shadow:var(--bevel)}}
 .scard .k{{margin:0 0 7px}}
 #statgrid{{display:grid;grid-template-columns:repeat(3,minmax(0,auto));justify-content:space-between;column-gap:16px;align-items:end}}
#statgrid > div{{text-align:center}}
#statgrid .big{{white-space:nowrap;line-height:1.05}}
 #statgrid small{{font:400 10.5px var(--ui);color:var(--steel-300)}}
 .scard__foot{{border-top:1px solid var(--line);margin-top:9px;padding-top:7px}}
 .scard--files{{background:#000;border-color:var(--steel-900);border-radius:6px}}
 #selcard.live::before{{content:'';position:absolute;left:14px;right:14px;top:-1px;height:1px;border-radius:2px;background:linear-gradient(90deg,transparent,rgba(255,122,0,.6),transparent)}}
 /* selected-node detail (G5J postMessage from the Hivemind iframe) */
 #selnode .sn-l{{font:600 14px/1.35 var(--ui);color:var(--ink);overflow-wrap:anywhere}}
 #selnode .sn-p{{font:500 11.5px/1.55 var(--mono);color:var(--dim);word-break:break-all;margin:2px 0 6px}}
 #selnode .sn-row{{display:flex;justify-content:space-between;gap:8px;font:400 12.5px var(--ui);color:var(--steel-200);margin:2px 0}}
 #selnode .sn-row b{{color:var(--ink);font-weight:600}}
 #selnode .sn-hint{{margin-top:7px;font:400 11px/1.55 var(--mono);color:var(--steel-300);border-top:1px solid var(--line);padding-top:6px;word-break:break-all}}
 #selnode .dim{{color:var(--steel-300)}}
 /* CONCEPTS card (G5O.0) -- always visible, filters BOTH views via postMessage */
 #conlist{{margin-right:-2px}}  /* G5O.0b: full list, no internal scrollbar (operator) */
 .crow{{display:flex;gap:8px;align-items:center;margin:3px 0;font:400 12.5px var(--ui);color:var(--steel-200);cursor:pointer}}
 .crow input{{accent-color:var(--molten);margin:0;flex:none;width:13px;height:13px}}
 .crow__n{{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
 .crow__c{{flex:none;font:500 11px var(--mono);color:var(--steel-300)}}
 .crow:hover .crow__n{{color:var(--ink)}}
 .k--row{{display:flex;justify-content:space-between;align-items:center}}
 #con-all{{accent-color:var(--molten);width:13px;height:13px;margin:0;cursor:pointer}}
 .crow--zero{{opacity:.4}}  /* concept absent from the current mission slice (G5O.2i) */
 /* MOTION CONTROLS card (G5O.2) -- operator multipliers for the 3D Hivemind */
 .mrow{{display:grid;grid-template-columns:1fr auto;align-items:center;margin:5px 0 1px;font:400 12.5px var(--ui);color:var(--steel-200);cursor:pointer}}
 .mrow__v{{font:500 11px var(--mono);color:var(--molten-hot)}}
 .mrow input[type=range]{{grid-column:1/-1;width:100%;height:14px;accent-color:var(--molten);background:transparent;cursor:pointer;margin:1px 0 3px}}
 #mot-reset{{cursor:pointer;flex:none;font:600 9.5px var(--ui);letter-spacing:.08em;text-transform:uppercase;color:var(--steel-200);border:1px solid rgba(255,122,24,.3);border-radius:var(--pill);padding:3px 10px;background:linear-gradient(180deg,rgba(60,32,8,.3),rgba(26,13,3,.35));box-shadow:inset 0 1px 0 rgba(255,210,160,.14);transition:border-color .15s,color .15s}}
 #mot-reset:hover{{border-color:var(--molten);color:var(--ink)}}
 #side-scroll::-webkit-scrollbar,#conlist::-webkit-scrollbar{{width:7px}}
 #side-scroll::-webkit-scrollbar-thumb,#conlist::-webkit-scrollbar-thumb{{background:rgba(255,255,255,.12);border-radius:4px}}
 #side-scroll::-webkit-scrollbar-track,#conlist::-webkit-scrollbar-track{{background:transparent}}
 /* powered-by — anchored at the bottom of the right panel (G5L) */
 #powered{{flex:none;margin-top:10px;text-align:center;display:flex;flex-direction:column;align-items:center;gap:4px}}
 #powered a{{display:inline-flex;align-items:center;gap:6px;font:600 11px var(--ui);letter-spacing:.12em;text-transform:uppercase;color:var(--steel-200);border:1px solid rgba(255,122,24,.3);border-radius:var(--pill);padding:5px 15px;background:linear-gradient(180deg,rgba(60,32,8,.3),rgba(26,13,3,.35));box-shadow:inset 0 1px 0 rgba(255,210,160,.14);transition:border-color .15s,color .15s,box-shadow .15s}}
 #powered a b{{color:var(--molten-hot);font-weight:700}}
 #powered a:hover{{border-color:var(--molten);color:var(--ink);box-shadow:0 0 0 3px var(--glow)}}
 #powered .built-on{{font:500 10px var(--ui);letter-spacing:.04em;text-transform:none;color:var(--steel-300);border:none;background:none;padding:2px 0;box-shadow:none}}
 #powered .built-on:hover{{color:var(--ink);border:none;box-shadow:none}}
 #powered .built-on b{{color:var(--steel-200);font-weight:600}}
{SECTIONS_CSS}
</style></head><body>
<nav id="rail">
 <div id="brand"><div class="logo"><img src="{MAT}/graphiquest_logo_mark_seed711002c.png" alt="" onerror="this.style.display='none'"></div><div><b>Graphi <span style="color:var(--molten)">Quest</span></b><span class="sub">LOCAL<i></i></span></div></div>
 <div class="nav on" data-sec="graph">Knowledge Graph</div><div class="nav" data-sec="skills">Skills</div><div class="nav" data-sec="reports">Reports</div><div class="nav" data-sec="howto">How To Guide</div>
 <div class="nav" data-sec="activity">Activity</div><div class="nav" data-sec="settings">Settings</div><div class="nav" data-sec="memory">Memory</div>
 <div id="agents"><div class="lbl">CONNECTORS</div>
  <div class="badge warn" data-connector="claudecode" style="cursor:pointer" title="open the Claude Code connect wizard"><svg width="11" height="11" viewBox="0 0 24 24" style="vertical-align:-1px;margin-right:6px" aria-hidden="true"><g stroke="#D97757" stroke-width="3.2" stroke-linecap="round"><line x1="12" y1="2.5" x2="12" y2="21.5"/><line x1="2.5" y1="12" x2="21.5" y2="12"/><line x1="5.3" y1="5.3" x2="18.7" y2="18.7"/><line x1="18.7" y1="5.3" x2="5.3" y2="18.7"/></g></svg>CLAUDE CODE — <span id="pill-claudecode-sub">SETUP REQUIRED</span></div></div>
 <div id="console">
  <div class="k">RESPONSES<button id="resp-expand" title="open the chat window">EXPAND &#x26F6;</button></div>
  <div id="resp-body"><span class="dim" id="resp-placeholder">Ask about the graph below — answered locally from the structural read-model. Try: "find &lt;name&gt;", "what is selected?", "how many nodes?", "help".</span></div>
  <div id="ask">
   <div id="ask-ctx"><span id="ask-proj"><span class="dot"></span>no graph loaded</span><span id="ask-node" class="mono" title="selected node context">no node selected</span></div>
   <input id="ask-in" type="text" spellcheck="false" placeholder="Ask about this graph — answered locally">
   <div id="ask-foot"><span id="ask-lanes"><button class="lane on" data-lane="graphify" title="answers locally from the structural graph">Graphify</button><button class="lane" data-lane="claudecode" title="asks YOUR connected Claude Code — the answer appears here (one real call per ask)">Claude Code</button></span><button id="ask-clr" title="clear the responses — like /clear (Activity history is kept)">CLR</button><button id="ask-stop" style="display:none" title="stop the in-flight ask">STOP</button><button id="ask-go" title="answers from the local structural graph only">ASK</button></div>
   <span id="ask-note">Graphify = local graph &middot; Claude Code = your Claude, on ask only</span>
  </div>
 </div>
</nav>
<main id="main">
 <div id="plate">
 <div id="hrow"><h1>Knowledge Graph</h1><div id="crumb"><b>Local-first</b> / this machine</div></div>
 <p id="sub">Every codebase you work in, mapped by Graphify — files and the relationships between them, grouped into clusters. Pick a project, explore its structure, and ask about it below.</p>
 <div id="cards"><!-- G5P.6: rendered by renderTopStrip() from the registry + display rules --></div>
 </div>
 <div id="vp"><iframe id="brain" src="about:blank" title="molten brain" allow="clipboard-write"></iframe>
  <div id="nograph"><div id="nograph-card"></div></div>
  <div class="proj"><span class="dot"></span><b>no graph loaded</b> &nbsp;<span class="mono">select a project to load a graph</span></div>
  <div class="ctl"><span class="pill on" id="pv3d">Brain 3D</span><span class="pill" id="pv2d">2D Explorer</span><span class="pill" id="ppause">PAUSE</span><span class="pill on" id="ptools" style="display:none">Tools</span><span class="pill" id="pmax">Open 3D</span></div>
 </div>
{SECTIONS_HTML}
</main>
<aside id="side">
 <div id="side-scroll">
 <div class="scard">
  <div class="k">GRAPH</div>
  <div id="statgrid">
   <div><div class="big">&mdash;</div><small>files</small></div>
   <div><div class="big">&mdash;</div><small>links</small></div>
   <div><div class="big">&mdash;</div><small>clusters</small></div>
  </div>
 </div>
 <div class="scard" id="savecard">
  <div class="k">GRAPHIFY CONTEXT SAVINGS</div>
  <div style="display:flex;align-items:baseline;gap:10px;margin:2px 0 6px"><span class="sv-pct" id="sv-pct">—</span><span class="sv-status" id="sv-status">not run</span></div>
  <div class="sv-row"><span>Claude-only (full graph)</span><b id="sv-claude">—</b></div>
  <div class="sv-row"><span>Graphify-assisted (query)</span><b id="sv-graphify">—</b></div>
  <button class="rbtn" id="sv-run" style="margin-top:8px;width:100%">RUN SAVINGS CHECK</button>
 </div>
 <div class="scard" id="selcard">
  <div class="k">SELECTED NODE</div><div id="selnode"><span class="dim">none — click a node in the 3D or 2D view</span></div>
 </div>
 <div class="scard scard--files">
  <div class="k">MOST CONNECTED FILES</div><ol id="imp-list"><li class="dim">computing from the loaded graph…</li></ol>
 </div>
 <div class="scard" id="concard">
  <div class="k k--row">CONCEPTS <input type="checkbox" id="con-all" checked title="select all / deselect all"></div>
  <div id="con-unavail">unavailable — no graph loaded for the selected project</div>
  <div id="conlist"><span class="dim" style="font:500 10.5px var(--ui);color:var(--steel-300)">unavailable &mdash; no graph loaded</span></div>
  <div class="scard__foot"><div class="leg" style="color:var(--steel-300)">filters the live view — 3D &amp; 2D</div></div>
 </div>
 <div class="scard" id="motcard">
  <div class="k">MOTION CONTROLS</div>
  <label class="mrow"><span>Brain Spin</span><span class="mrow__v" id="mv-spin">1.00&times;</span><input type="range" id="ms-spin" min="0.25" max="2" step="0.05" value="1"></label>
  <label class="mrow"><span>Node Fly</span><span class="mrow__v" id="mv-fly">1.00&times;</span><input type="range" id="ms-fly" min="0.25" max="2" step="0.05" value="1"></label>
  <label class="mrow"><span>Core Drift</span><span class="mrow__v" id="mv-drift">1.00&times;</span><input type="range" id="ms-drift" min="0.25" max="2" step="0.05" value="1"></label>
  <div class="scard__foot" style="display:flex;justify-content:space-between;align-items:center">
   <div class="leg" style="color:var(--steel-300);margin:0">applies to the 3D Hivemind</div>
   <span id="mot-reset" title="back to 1.00&times; defaults">Reset Motion</span>
  </div>
 </div>
 </div>
 <div id="powered"><a href="https://daforgelayer-ai.com/" target="_blank" rel="noopener">Powered by <b>DaForgeLayer-AI</b></a><a class="built-on" href="https://github.com/safishamsi/graphify" target="_blank" rel="noopener">Built on <b>Graphify</b> by safishamsi (MIT)</a></div>
</aside>
<script>
{HUNTER_JS}
(function() {{
  const iframe = document.getElementById('brain');
  const $ = id => document.getElementById(id);
  const SRC3D = 'brain-3d-prototype.html?b={H3D}#embed';
  const SRC2D = 'graph-explorer.html?b={H2D}#embed';
  // Defeat Chrome subframe session-restore: force the known-good 3D src at boot,
  // and keep the pill state in sync with what the iframe ACTUALLY loaded.
  iframe.src = SRC3D;
  addEventListener('beforeunload', () => {{               // G5O.2j: refresh paint-holding shows black, not the outgoing doc
    try {{ iframe.src = 'about:blank'; }} catch (e) {{}}
    document.documentElement.style.visibility = 'hidden';
  }});
  iframe.addEventListener('load', () => {{
    if (HIDDEN_CONCEPTS.size) {{ setTimeout(sendConcepts, 400); setTimeout(sendConcepts, 1600); }}  // re-apply filter to the freshly loaded view (G5O.0)
    setTimeout(motSend, 450); setTimeout(motSend, 1700);  // re-apply motion multipliers (G5O.2)
    if (mode3d) paintConceptCounts(null);                 // 3D shows the whole graph -> global counts (G5O.2i)
    try {{
      const is3d = iframe.contentWindow.location.pathname.indexOf('brain-3d') !== -1;
      if (mode3d !== is3d) {{ mode3d = is3d; paintMode(); }}
    }} catch (e) {{}}
  }});
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}})[c]);
  let mode3d = true;
  const paintMode = () => {{
    $('pv3d').classList.toggle('on', mode3d);
    $('pv2d').classList.toggle('on', !mode3d);
    $('ppause').style.opacity = mode3d ? '' : '.4';
    $('ppause').style.pointerEvents = mode3d ? '' : 'none';
    const ovl = document.body.classList.contains('vpmax');
    $('pmax').style.display = (mode3d || ovl) ? '' : 'none';  // Close must NEVER strand the overlay (G5M)
    $('ppause').style.display = mode3d ? '' : 'none';         // Pause is a 3D control (G5N contract)
    $('ptools').style.display = mode3d ? 'none' : '';         // Tools is a 2D control (G5N contract)
    const proj = document.querySelector('#vp .proj');
    if (proj) proj.style.display = mode3d ? '' : 'none';      // explorer has its own banner (G5M)
  }};
  // G5O.2j killed paint-holding by blanking first; G5P.0c: the fixed 30ms timer
  // could fire BEFORE the blank committed a frame on a busy main thread, so the
  // old doc still held. Now the blank's load + two rAFs (a painted compositor
  // frame) gate the heavy src; 150ms safety covers a missing onload.
  let swapSeq = 0;                                       // G5P.0c grill: stale go() from a superseded swap (rAF chain / 150ms timer) must no-op
  const swapView = src => {{
    const my = ++swapSeq;
    iframe.onload = null;
    let done = false;
    const go = () => {{ if (done || my !== swapSeq) return; done = true; iframe.onload = null; iframe.src = src; }};
    iframe.onload = () => requestAnimationFrame(() => requestAnimationFrame(go));
    iframe.src = 'about:blank';
    setTimeout(go, 150);
  }};
  $('pv2d').onclick = () => {{ if (!mode3d) return; mode3d = false; swapView((CURRENT_VIEWS || {{ src2d: SRC2D }}).src2d); paintMode(); renderSel(null); }};
  $('pv3d').onclick = () => {{ if (mode3d) return; mode3d = true; swapView((CURRENT_VIEWS || {{ src3d: SRC3D }}).src3d); $('ppause').textContent = 'PAUSE'; $('ppause').classList.remove('on'); paintMode(); }};
  $('ppause').onclick = () => {{ if (!mode3d) return; try {{ iframe.contentWindow.postMessage({{graphify: 'toggle-pause'}}, '*'); }} catch (e) {{}} }};
  $('ptools').onclick = () => {{ if (mode3d) return; try {{ iframe.contentWindow.postMessage({{graphify: 'toggle-tools'}}, '*'); }} catch (e) {{}} }};
  // G5O.2 MOTION CONTROLS: persisted multipliers -> the 3D Hivemind (2D ignores them)
  const MOT_DEF = {{ spin: 1, fly: 1, drift: 1 }};
  let MOT = {{ ...MOT_DEF }};
  try {{ MOT = {{ ...MOT_DEF, ...JSON.parse(localStorage.getItem('graphify-motion-v1') || '{{}}') }}; }} catch (e) {{}}
  const motSend = () => {{ try {{ iframe.contentWindow.postMessage({{ graphify: 'motion', spin: MOT.spin, fly: MOT.fly, drift: MOT.drift }}, '*'); }} catch (e) {{}} }};
  const motPaint = () => ['spin', 'fly', 'drift'].forEach(k => {{
    const sl = $('ms-' + k), vv = $('mv-' + k);
    if (sl) sl.value = MOT[k];
    if (vv) vv.textContent = (+MOT[k]).toFixed(2) + '\u00d7';
  }});
  ['spin', 'fly', 'drift'].forEach(k => {{ const sl = $('ms-' + k); if (sl) sl.oninput = () => {{
    MOT[k] = +sl.value;
    try {{ localStorage.setItem('graphify-motion-v1', JSON.stringify(MOT)); }} catch (e) {{}}
    motPaint(); motSend();
  }}; }});
  $('mot-reset').onclick = () => {{
    MOT = {{ ...MOT_DEF }};
    try {{ localStorage.setItem('graphify-motion-v1', JSON.stringify(MOT)); }} catch (e) {{}}
    motPaint(); motSend();
  }};
  motPaint();
  // G5O.0 CONCEPTS: dashboard owns the state; one bulk protocol for BOTH views
  const HIDDEN_CONCEPTS = new Set();
  const sendConcepts = () => {{ try {{ iframe.contentWindow.postMessage({{graphify: 'concepts', hidden: Array.from(HIDDEN_CONCEPTS)}}, '*'); }} catch (e) {{}} }};
  const CON_GLOBAL = {{}};                            // baked whole-graph counts (3D view + fallback)
  document.querySelectorAll('#conlist .crow').forEach(r => CON_GLOBAL[r.querySelector('input').dataset.key] = r.querySelector('.crow__c').textContent);
  const paintConceptCounts = counts => document.querySelectorAll('#conlist .crow').forEach(r => {{
    const k = r.querySelector('input').dataset.key, v = counts ? (counts[k] || 0) : CON_GLOBAL[k];
    r.querySelector('.crow__c').textContent = v;
    r.classList.toggle('crow--zero', !!counts && !counts[k]);
  }});
  const conAll = $('con-all');
  const syncConAll = () => {{ if (conAll) conAll.checked = HIDDEN_CONCEPTS.size === 0; }};
  if (conAll) conAll.onchange = () => {{
    const on = conAll.checked;
    document.querySelectorAll('#conlist input').forEach(cb => {{
      cb.checked = on;
      if (on) HIDDEN_CONCEPTS.delete(cb.dataset.key); else HIDDEN_CONCEPTS.add(cb.dataset.key);
    }});
    sendConcepts();
  }};
  const wireConcepts = () => document.querySelectorAll('#conlist input').forEach(cb => cb.onchange = () => {{
    if (cb.checked) HIDDEN_CONCEPTS.delete(cb.dataset.key); else HIDDEN_CONCEPTS.add(cb.dataset.key);
    syncConAll(); sendConcepts();
  }});
  wireConcepts();
  // G5P.4: rebuild the concepts card for a switched project graph
  const renderConcepts = list => {{
    HIDDEN_CONCEPTS.clear();
    N_CONCEPTS = list.length;
    $('conlist').innerHTML = list.map(en => '<label class="crow"><input type="checkbox" checked data-key="' + esc(en[0]) + '"/><span class="crow__n">' + esc(en[0]) + '</span><span class="crow__c">' + en[1] + '</span></label>').join('');
    Object.keys(CON_GLOBAL).forEach(k => delete CON_GLOBAL[k]);
    list.forEach(en => CON_GLOBAL[en[0]] = String(en[1]));
    wireConcepts(); syncConAll();
  }};
  window.__renderConcepts = renderConcepts;            // referenced by the switch core (defined earlier)
  $('pmax').onclick = () => {{
    const on = document.body.classList.toggle('vpmax');
    $('pmax').textContent = on ? 'Close' : 'Open 3D';
    paintMode();
  }};
  addEventListener('keydown', e => {{ if (e.key === 'Escape' && document.body.classList.contains('vpmax')) $('pmax').onclick(); }});
  addEventListener('message', e => {{
    if (e.origin !== location.origin) return;   // same-origin only (G5K security)
    const d = e.data || {{}};
    if (d.graphify === 'paused') {{
      $('ppause').textContent = d.value ? 'RESUME' : 'PAUSE';
      $('ppause').classList.toggle('on', !!d.value);
    }}
    if (d.graphify === 'selected') {{ LAST_SEL = d.node || null; renderSel(d.node); }}
    if (d.graphify === 'tools') $('ptools').classList.toggle('on', !!d.value);
    if (d.graphify === 'slice-concepts') {{ LAST_SLICE = {{ slice: d.slice, counts: d.counts }}; paintConceptCounts(d.counts); }}  // counts follow the mission slice (G5O.2i)
    if (d.graphify === 'mode2d') MODE2D = d.value;        // honest ask context (G5P)
    if (d.graphify === 'find-res' && FIND_PENDING) {{      // async find/jump answer (G5P.1 + G5Q.1i fallback)
      clearTimeout(FIND_PENDING.timer);
      if (d.hit) {{
        const via = FIND_PENDING.via ? ' — matched on "' + FIND_PENDING.via + '"' : '';
        renderResp(FIND_PENDING.q, 'Jumped to ' + d.hit.lbl + ' (' + d.hit.reg + ')' + via + (d.matches > 1 ? ' — best of ' + d.matches + ' matches (exact > prefix > contains, then degree).' : '.'), 'answered');
        FIND_PENDING = null;
      }} else if (FIND_PENDING.attempts.length) {{
        const next = FIND_PENDING.attempts.shift();        // multi-word miss: try each word, longest first
        FIND_PENDING.tried.push(next); FIND_PENDING.via = next;
        FIND_PENDING.timer = setTimeout(() => {{ if (FIND_PENDING) {{ renderResp(FIND_PENDING.q, 'The view did not answer the lookup (timeout).', 'error'); FIND_PENDING = null; }} }}, 1500);
        try {{ iframe.contentWindow.postMessage({{ graphify: 'find-req', q: next }}, '*'); }} catch (e) {{}}
        return;
      }} else {{
        renderResp(FIND_PENDING.q, 'No visible node matches "' + (FIND_PENDING.qq || d.q || '') + '"'
          + (FIND_PENDING.tried.length ? ' (also tried each word: ' + FIND_PENDING.tried.join(', ') + ')' : '')
          + ' — names match file/folder names, so part of a filename works best (e.g. "jump to extract.py"). A concept filter can also hide it.', 'unsupported');
        FIND_PENDING = null;
      }}
    }}
    if (d.graphify === 'neighbors' && NB_PENDING) {{       // async neighbor answer (G5P)
      clearTimeout(NB_PENDING.timer);
      const list = (d.items || []).map(n => '· ' + n.lbl + '  (' + n.reg + ', deg ' + n.deg + ')').join('\\n');
      renderResp(NB_PENDING.q, NB_PENDING.sel + ' has ' + d.total + ' direct connections.' + (list ? ' Top by degree:\\n' + list : ''), 'answered');
      NB_PENDING = null;
    }}
  }});
  // ---- G5P.2 project registry: honest source selection (tracked registry baked
  // at generation; browser-local overlay for repo-path edits + added projects) ----
  const REGISTRY = {REGISTRY_JS};
  const PSTATUS = {{ missing_repo_path: 'no repo path', not_graphed: 'not graphed yet', graph_missing: 'graph missing', rebuild_required: 'rebuild required', repo_path_configured: 'path configured — not generated', command_prepared: 'command prepared — run it manually', waiting_for_manual_run: 'waiting for manual run', generating: 'generating…', generated_pending_reload: 'generated — views not built yet', generated_incompatible: 'generated — incompatible output', views_missing: 'view files missing — rebuild', pending: 'pending setup', error: 'generation error', ready: 'ready' }};
  const lsGet = (k, d) => {{ try {{ return JSON.parse(localStorage.getItem(k) || JSON.stringify(d)); }} catch (e) {{ return d; }} }};
  const lsSet = (k, v) => {{ try {{ localStorage.setItem(k, JSON.stringify(v)); }} catch (e) {{}} }};
  const projLocal = () => lsGet('graphify-projects-local-v1', {{ edits: {{}}, added: [] }});
  const projLog = (ev, detail) => {{
    const log = lsGet('graphify-project-log', []);
    log.unshift({{ ts: new Date().toISOString(), ev, detail }});
    lsSet('graphify-project-log', log.slice(0, 50));
  }};
  window.__projLog = () => lsGet('graphify-project-log', []);
  window.__logEvent = (ev, detail) => projLog(ev, detail || {{}});
  const projAll = () => {{
    const loc = projLocal();
    const base = REGISTRY.map(p => {{
      const e = loc.edits[p.id] || {{}};
      const q = {{ ...p, ...e }};
      if (e.pinned !== undefined) q.pinned = e.pinned;
      if (q.graphStatus !== 'ready' && q.graphStatus !== 'graph_missing' && q.repoPath) q.graphStatus = 'repo_path_configured';
      if (q.graphStatus === 'repo_path_configured' && e.genStatus) {{ q.graphStatus = e.genStatus; if (e.genMsg) q.statusMessage = e.genMsg; }}
      applyScan(q);
      return q;
    }});
    return base.concat(loc.added.map(a => {{
      let st = a.repoPath ? 'repo_path_configured' : 'missing_repo_path';
      let sm = a.repoPath ? 'repo path configured — graph not generated yet (saved locally in this browser)' : 'no repo path connected yet';
      if (a.genStatus) {{ st = a.genStatus; if (a.genMsg) sm = a.genMsg; }}   // G5P.8: imports start with repoPath null -- genStatus must surface anyway
      const q = {{ ...a, kind: 'local', graphStatus: st, statusMessage: sm, local: true }};
      applyScan(q);
      return q;
    }}));
  }};
  const projGet = id => projAll().find(p => p.id === id);
  let PROJ = (REGISTRY.find(p => p.graphStatus === 'ready') || REGISTRY[0] || {{}}).id;   // G5Q.1o: no shipped default
  let UNLOADED = false;   // G5Q.1d: true after Unload Graph -> a real no-graph state
  const projReady = () => {{ const p = projGet(PROJ); return !UNLOADED && p && p.graphStatus === 'ready'; }};
  // ---- G5P.6 top strip display rules: default + ready + pinned + showInTopBar
  // + recent browser-local; everything else manages from Settings (never deleted).
  const RECENTS_KEY = 'graphify-recent-projects-v1';
  const recents = () => lsGet(RECENTS_KEY, []);
  const touchRecent = id => {{ const r = recents().filter(x => x !== id); r.unshift(id); lsSet(RECENTS_KEY, r.slice(0, 4)); }};
  // G5P.6b (operator): the strip is ONLY loaded-able things -- default, ready,
  // pinned, or the currently selected project. Recency/locals never admit
  // not-ready cards; everything else lives in Settings -> Repositories.
  const inTopStrip = p => p.isDefault || p.graphStatus === 'ready' || p.pinned === true
    || p.showInTopBar === true || p.id === PROJ
    || p.genStatus === 'generating' || p.graphStatus === 'generating'
    || p.genStatus === 'error';   // G5P.8: running imports/generates (and their failures) must be SEEN
  const KIND_CHIP = {{ monorepo: 'MONOREPO', 'monorepo-slice': 'SLICE', future: 'FUTURE', 'import-slot': 'IMPORT', local: 'LOCAL' }};
  const renderTopStrip = () => {{
    const wrap = $('cards');
    if (!wrap) return;
    const list = projAll().filter(inTopStrip);
    wrap.innerHTML = list.map(p => {{
      const sel = p.id === PROJ;
      const live = p.genStatus === 'generating' || p.graphStatus === 'generating';
      const stats = live
        ? '<span class="gen-live">' + esc(p.genMsg || p.statusMessage || 'working…') + '</span>'
        : p.genStatus === 'error'
          ? '<span class="gen-err">' + esc(p.genMsg || 'failed — open Settings → Repositories') + '</span>'
          : p.graphStatus === 'ready'
            ? (p.nodeCount != null ? esc(p.nodeCount) + ' nodes · ' + (p.conceptCount != null ? esc(p.conceptCount) + ' concepts' : '') : 'ready')
            : esc(PSTATUS[p.graphStatus] || p.graphStatus);
      const acts = sel ? ('<div class="card__act">'
          + (UNLOADED ? '<span class="ca ca-reload" title="reload this graph">RELOAD</span>'
                      : '<span class="ca ca-unload" title="unload the active graph to a no-graph state — click the card to reload">UNLOAD</span>')
          + (p.local ? '<span class="ca ca-remove" title="removes this browser-local project from the dashboard — the source repo is untouched">REMOVE</span>' : '')
          + '</div>') : '';
      return '<div class="card' + (sel ? ' card--sel' : '') + '" data-proj="' + esc(p.id) + '">'
        + '<div><div class="card__top"><b>' + esc(p.label) + '</b><span class="chip">' + esc(KIND_CHIP[p.kind] || 'PROJECT') + '</span></div>'
        + '<p class="card__stats">' + (sel ? '<span class="dot"></span>' : '') + stats + '</p></div>' + acts + '</div>';
    }}).join('') + '<div class="card card--add" title="add a project — pick a folder or paste a GitHub link">+ Add a project</div>';
    wrap.querySelectorAll('.card[data-proj]').forEach(c => c.onclick = e => {{
      if (e.target.classList.contains('ca')) return;     // action chips handle themselves
      selectProject(c.dataset.proj);
      if (window.__openSection) window.__openSection('graph');
    }});
    const selCard = wrap.querySelector('.card--sel');
    if (selCard) {{
      const u = selCard.querySelector('.ca-unload');
      if (u) u.onclick = () => unloadGraph();
      const rl = selCard.querySelector('.ca-reload');
      if (rl) rl.onclick = () => selectProject(PROJ);
      const rm = selCard.querySelector('.ca-remove');
      if (rm) rm.onclick = () => removeLocalProject(PROJ);
    }}
    const add = wrap.querySelector('.card--add');
    if (add) add.onclick = () => addProjectEntry();
  }};
  // G5P.6a operator flow: click +Add -> file explorer opens immediately; picking
  // a folder creates the project and graphs+loads it; cancel falls back to the
  // modal (paste a path / import a repo URL).
  const addProjectEntry = () => openAddModal();        // G5P.6b: the flyout IS the chooser (two options)
  const uniqueLocalId = base => {{
    let id = 'local-' + base.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    if (id === 'local-') id = 'local-project';
    let n = 2, out = id;
    while (projGet(out)) {{ out = id + '-' + n++; }}
    return out;
  }};
  let AUTO_LOAD_ID = null;                               // selected automatically once ready
  const createAndGraph = async (name, path) => {{
    const id = uniqueLocalId(name);
    const loc = projLocal();
    loc.added.push({{ id, label: name, description: 'added locally in this browser', repoPath: path, graphOutputPath: 'graphify-out/', isDefault: false }});
    lsSet('graphify-projects-local-v1', loc);
    touchRecent(id);
    projLog('project_added', {{ id, path }});
    renderTopStrip();
    await scanProjects();
    const sc = SCAN[id] || {{}};
    projLog('repo_path_validated', {{ id, status: sc.status }});
    if (sc.status === 'ready') {{ selectProject(id); return; }}
    if (sc.status === 'invalid_path') {{ openAddModal(); amStatus('picked path was refused: ' + (sc.reason || ''), '#fbbf24'); return; }}
    AUTO_LOAD_ID = id;
    const p = projGet(id);
    if (p && p.repoPath) runGenerate(p);                 // graph + build views now; auto-loads on ready
  }};
  const unloadProject = () => {{
    const prev = PROJ;
    const next = projAll().find(x => x.graphStatus === 'ready' && x.id !== prev);
    if (!next) return;
    projLog('project_unloaded', {{ id: prev }});
    selectProject(next.id);
  }};
  // G5Q.1d: unload the ACTIVE graph to a real no-graph state (works for the
  // default project too -- any loaded graph becomes unloadable). Reconnect by
  // clicking any project card, or RELOAD in the viewport / strip.
  const unloadGraph = () => {{
    UNLOADED = true;
    LAST_SEL = null; renderSel(null);
    try {{ swapView('about:blank'); }} catch (e) {{}}
    CURRENT_GRAPH = null;
    document.querySelectorAll('#statgrid .big').forEach(b => b.textContent = '\u2014');
    paintConceptCounts(null);
    paintProj(); paintNoGraph(); renderTopStrip();
    if (window.__renderHunt) window.__renderHunt();
    projLog('graph_unloaded', {{ id: PROJ }});
  }};
  const removeLocalProject = id => {{
    const p = projGet(id);
    if (!p || !p.local) return;                          // tracked registry entries are never browser-deletable
    if (PROJ === id) unloadProject();
    const loc = projLocal();
    loc.added = loc.added.filter(a => a.id !== id);
    lsSet('graphify-projects-local-v1', loc);
    lsSet(RECENTS_KEY, recents().filter(x => x !== id));
    projLog('local_project_removed', {{ id }});
    renderTopStrip();
    if ($('repo-list')) renderRepos();
  }};
  const paintProj = () => {{
    const p = projGet(PROJ) || {{}};
    renderTopStrip();
    const an = $('ask-proj');
    const badge = document.querySelector('#vp .proj');
    if (UNLOADED) {{
      if (an) an.innerHTML = '<span class="dot"></span>no graph loaded';
      if (badge) badge.innerHTML = '<span class="dot"></span><b>No graph loaded</b> &nbsp;<span class="mono">select a project to load a graph</span>';
      return;
    }}
    if (an) an.innerHTML = '<span class="dot"></span>' + esc(p.label || '?') + (p.graphStatus === 'ready' ? '' : ' · ' + esc(PSTATUS[p.graphStatus] || p.graphStatus));
    if (badge) badge.innerHTML = '<span class="dot"></span><b>' + esc(p.label || '?') + '</b> &nbsp;<span class="mono">' + (p.graphStatus === 'ready' ? esc(p.nodeCount + ' nodes · ' + (p.conceptCount != null ? p.conceptCount : '?') + ' concepts') : esc(PSTATUS[p.graphStatus] || p.graphStatus)) + '</span>';
  }};
  const paintNoGraph = () => {{
    const p = projGet(PROJ) || {{}};
    const ready = !UNLOADED && p.graphStatus === 'ready';
    document.body.classList.toggle('nograph', !ready);
    if (ready) return;
    // G5Q.1r: the empty state must not wear the BAKED placeholder graph --
    // blank the counts, concepts and bar so no stale concepts appear with no
    // graph loaded
    document.querySelectorAll('#statgrid .big').forEach(b => b.textContent = '—');
    try {{ if (window.__renderConcepts) window.__renderConcepts([]); }} catch (e) {{}}   // TDZ-safe: concepts IIFE may not have run yet at first paint
    const card = $('nograph-card');
    // G5Q.2b: clean first-run -- NO project at all (fresh browser, empty
    // registry). Show an honest "add your first project" state, never a broken
    // "?" card or a pretend default graph.
    const hasProject = !!projGet(PROJ);
    if (!hasProject) {{
      card.innerHTML = '<h4>Add your first project</h4>'
        + '<span class="ng-status">no graph yet</span>'
        + '<div>GraphiQuest has no graph loaded. Add a repository to scan it with Graphify and explore it as a 3D Hivemind. <b>Ask, Hunter, Reports and Context Savings activate once a graph is loaded.</b></div>'
        + '<span class="ng-cta" id="ng-add">+ ADD A PROJECT</span>'
        + '<span class="ng-cta" id="ng-howto0">HOW IT WORKS</span>';
      const ab = $('ng-add'); if (ab) ab.onclick = () => window.__openAddModal && window.__openAddModal();
      const hb0 = $('ng-howto0'); if (hb0) hb0.onclick = () => window.__openSection && window.__openSection('howto');
      return;
    }}
    if (UNLOADED) {{
      card.innerHTML = '<h4>No graph loaded</h4>'
        + '<span class="ng-status">unloaded</span>'
        + '<div>You unloaded the active graph. Select a project to load a graph &mdash; or reload the last one.</div>'
        + '<span class="ng-cta" id="ng-reload">RELOAD ' + esc((projGet(PROJ) || {{}}).label || 'GRAPH') + '</span>'
        + '<span class="ng-cta" id="ng-settings2">OPEN SETTINGS &rarr; REPOSITORIES</span>';
      const rb = $('ng-reload'); if (rb) rb.onclick = () => selectProject(PROJ);
      const sb = $('ng-settings2'); if (sb) sb.onclick = () => window.__openRepoSettings && window.__openRepoSettings();
      return;
    }}
    const readyElsewhere = REGISTRY.find(x => x.graphStatus === 'ready');
    card.innerHTML = '<h4>' + esc(p.label || '?') + '</h4>'
      + '<span class="ng-status">' + esc(PSTATUS[p.graphStatus] || p.graphStatus) + '</span>'
      + '<div>' + esc(p.statusMessage || 'no local graph data is loaded for this project') + '</div>'
      + (readyElsewhere ? '<div style="color:var(--steel-300);font-size:11.5px;margin-top:6px">The Hivemind behind this panel still shows the <b>' + esc(readyElsewhere.label) + '</b> graph — it is hidden rather than misrepresented.</div>' : '')
      + '<span class="ng-cta" id="ng-settings">OPEN SETTINGS → REPOSITORIES</span>'
      + (p.repoPath ? '' : '<span class="ng-cta" id="ng-howto">HOW TO CONNECT A REPO</span>');
    const sBtn = $('ng-settings'); if (sBtn) sBtn.onclick = () => window.__openRepoSettings && window.__openRepoSettings();
    const hBtn = $('ng-howto'); if (hBtn) hBtn.onclick = () => window.__openSection && window.__openSection('howto');
  }};
  const selectProject = (id, log) => {{
    if (!projGet(id)) return;
    const wasUnloaded = UNLOADED; UNLOADED = false;   // G5Q.1d: selecting always reconnects
    PROJ = id;
    touchRecent(id);
    const p = projGet(id);
    if (wasUnloaded) CURRENT_GRAPH = null;            // force loadGraphFor to re-swap the iframe
    if (p.graphStatus !== 'ready') renderSel(null);
    if (p.graphStatus === 'ready') {{
      const switched = loadGraphFor(p);
      if (switched) projLog('project_graph_switched', {{ id, from: null, nodes: p.nodeCount }});
    }}
    paintProj(); paintNoGraph();
    if (window.__renderHunt) window.__renderHunt();
    if (log !== false) projLog('project_selected', {{ id, status: p.graphStatus }});
  }};
  window.__selectProject = selectProject;
  // ---- G5P.4 real output detection + graph switching --------------------------
  let SCAN = {{}};                                      // id -> bridge scan result (runtime filesystem truth)
  const SCAN_LOGGED = new Set();
  const applyScan = q => {{
    if (q.isDefault && q.graphStatus === 'ready') return;   // baked default graph
    const sc = SCAN[q.id];
    if (!sc) return;
    if (sc.status === 'ready') {{
      q.graphStatus = 'ready';
      q.nodeCount = sc.nodes; q.edgeCount = sc.edges; q.conceptCount = (sc.concepts || []).length;
      q.lastGraphedAt = sc.generatedAt; q.graphOutputPath = sc.viewsBase;
      q.statusMessage = 'generated views ready — SELECT loads this graph' + (sc.sourceGone ? ' (source graph.json has since disappeared)' : '');
      q.scanReady = true;
    }} else if (sc.status === 'generated_pending_reload' || sc.status === 'views_missing' || sc.status === 'rebuild_required') {{
      q.graphStatus = sc.status; q.statusMessage = sc.reason || q.statusMessage;
      if (sc.status === 'rebuild_required' && sc.nodes != null) {{ q.nodeCount = sc.nodes; }}  // stale-but-real counts stay visible in the row
    }} else if (sc.status === 'generated_incompatible') {{
      q.graphStatus = 'generated_incompatible'; q.statusMessage = sc.reason || 'output incompatible';
    }} else if (sc.status === 'invalid_path' || sc.status === 'error') {{
      q.graphStatus = 'error'; q.statusMessage = sc.reason || 'scan error';
    }}
    if (sc.pathKind) q.pathKind = sc.pathKind;
    if (sc.resolvedPath) q.resolvedPath = sc.resolvedPath;
    // sc.status === 'no_output': derived state stands (nothing generated yet)
  }};
  const scanProjects = async () => {{
    if (!BRIDGE.available) return;
    try {{
      const list = projAll().filter(p => !(p.isDefault && p.graphStatus === 'ready'))
        .map(p => ({{ id: p.id, repoPath: p.repoPath || null }}));
      const r = await fetch('/api/projects/scan', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ projects: list }}) }});
      const j = await r.json();
      SCAN = (j && j.results) || {{}};
      Object.entries(SCAN).forEach(([id, sc]) => {{
        if (sc.status === 'ready' && !SCAN_LOGGED.has(id)) {{ SCAN_LOGGED.add(id); projLog('graph_output_detected', {{ id, nodes: sc.nodes }}); }}
        if (sc.status === 'generated_incompatible' && !SCAN_LOGGED.has(id + ':bad')) {{ SCAN_LOGGED.add(id + ':bad'); projLog('graph_output_invalid', {{ id, reason: (sc.reason || '').slice(0, 120) }}); }}
      }});
      paintProj(); paintNoGraph();
      if (document.body.classList.contains('sec-open') && $('repo-list')) renderRepos();
    }} catch (e) {{}}
  }};
  let CURRENT_GRAPH = null;                            // G5Q.1o: nothing pre-loaded; first ready project swaps in
  let CURRENT_VIEWS = null;                            // {{src3d, src2d}} of the LOADED graph (G5P.5: pills must follow the switch)
  const viewsFor = p => {{
    if (p.isDefault) return {{ src3d: SRC3D, src2d: SRC2D, totals: {{ ...TOTALS_BASE }}, concepts: BASE_CONCEPTS }};
    const sc = SCAN[p.id];
    if (sc && sc.status === 'ready' && sc.viewsBase) {{
      const b = encodeURIComponent(sc.generatedAt || '');
      return {{ src3d: sc.viewsBase + 'brain-3d-prototype.html?b=' + b + '#embed',
               src2d: sc.viewsBase + 'graph-explorer.html?b=' + b + '#embed',
               totals: {{ nodes: String(sc.nodes != null ? sc.nodes : '?'), edges: String(sc.edges != null ? sc.edges : '?'), clusters: String(sc.slices != null ? sc.slices : '?') }},
               concepts: sc.concepts || [] }};
    }}
    return null;
  }};
  // G5P.8: top-connected files come from the project's own read-model (fetched
  // same-origin from the static tree the bridge serves) -- never a baked list.
  const readModelUrl = p => (p && p.isDefault)
    ? '/hivemind/read-model.json'
    : (((SCAN[(p || {{}}).id] || {{}}).viewsBase || '/projects/' + ((p || {{}}).id || '') + '/') + 'read-model.json');
  const RM_TOP_CACHE = {{}};
  const refreshImportant = async () => {{
    const ol = $('imp-list'); if (!ol) return;
    const p = projGet(PROJ);
    if (!p || p.graphStatus !== 'ready') {{ ol.innerHTML = '<li class="dim">no graph loaded</li>'; return; }}
    try {{
      if (!RM_TOP_CACHE[p.id]) {{
        const rm = await (await fetch(readModelUrl(p))).json();
        RM_TOP_CACHE[p.id] = (rm.nodes || []).slice().sort((a, b) => (b.degree || 0) - (a.degree || 0)).slice(0, 5)
          .map(n => ({{ lbl: n.label, deg: n.degree }}));
      }}
      ol.innerHTML = RM_TOP_CACHE[p.id].map(n => '<li title="degree ' + n.deg + '">' + esc(n.lbl) + '</li>').join('') || '<li class="dim">no nodes</li>';
    }} catch (e) {{ ol.innerHTML = '<li class="dim">unavailable — needs the local server</li>'; }}
  }};
  window.__refreshImportant = refreshImportant;
  const loadGraphFor = p => {{
    const v = viewsFor(p);
    if (!v || CURRENT_GRAPH === p.id) return false;
    CURRENT_GRAPH = p.id;
    CURRENT_VIEWS = {{ src3d: v.src3d, src2d: v.src2d }};
    TOTALS = v.totals;
    if (window.__renderConcepts) window.__renderConcepts(v.concepts);
    renderSel(null); LAST_SLICE = null; MODE2D = 'brain';
    swapView(mode3d ? v.src3d : v.src2d);   // G5P.8: switching projects keeps your 3D/2D choice
    $('ppause').textContent = 'PAUSE'; $('ppause').classList.remove('on');
    paintMode();
    const bigs = document.querySelectorAll('#statgrid .big');
    if (bigs[0]) bigs[0].textContent = TOTALS.nodes;
    if (bigs[1]) bigs[1].textContent = TOTALS.edges;
    if (bigs[2]) bigs[2].textContent = TOTALS.clusters;
    refreshImportant();
    projLog('graph_loaded', {{ id: p.id, nodes: TOTALS.nodes }});
    return true;
  }};
  // ---- G5P.3 generate/rebuild: loopback bridge detection + honest fallback ----
  const BRIDGE = {{ available: null, graphify: false, logged: false }};
  const checkBridge = async () => {{
    try {{
      const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), 900);
      const r = await fetch('/api/bridge/status', {{ signal: ctl.signal }});
      clearTimeout(t);
      const j = await r.json();
      BRIDGE.available = j && j.bridge === 'graphify-dashboard-bridge';
      BRIDGE.graphify = !!(j && j.graphifyDetected);
      if (BRIDGE.available && !BRIDGE.logged) {{ BRIDGE.logged = true; projLog('bridge_detected', {{ version: j.version, graphify: BRIDGE.graphify }}); }}
      if (BRIDGE.available) await scanProjects();
    }} catch (e) {{ BRIDGE.available = false; }}
    updateSetupLive();
  }};
  // G5Q.1d: live Setup/Graphify status text (honest -- reflects bridge + CLI)
  const updateSetupLive = () => {{
    const txt = BRIDGE.available == null ? 'checking the bridge…'
      : !BRIDGE.available ? 'local bridge not running — start it with: python scripts/start_graphify_dashboard.py'
      : BRIDGE.graphify ? 'bridge up · graphify CLI detected on PATH ✓'
      : 'bridge up · graphify CLI NOT found on PATH — install it (uv tool install graphifyy)';
    ['setup-gfy', 'set-gfy-live'].forEach(id => {{ const el = $(id); if (el) el.textContent = txt; }});
  }};
  window.__setupLive = updateSetupLive;
  const setGen = (id, st, msg) => {{
    const loc = projLocal();
    const added = loc.added.find(a => a.id === id);
    if (added) {{ added.genStatus = st; added.genMsg = msg; }}
    else loc.edits[id] = {{ ...(loc.edits[id] || {{}}), genStatus: st, genMsg: msg }};
    lsSet('graphify-projects-local-v1', loc);
    paintProj(); paintNoGraph();
  }};
  let GEN_POLL = null;
  const pollRun = id => {{
    if (GEN_POLL) clearInterval(GEN_POLL);
    GEN_POLL = setInterval(async () => {{
      try {{
        const j = await (await fetch('/api/graphify/status')).json();
        const run = j.run || {{}};
        if (run.projectId !== id) return;
        if (run.state === 'success') {{
          clearInterval(GEN_POLL); GEN_POLL = null;
          setGen(id, 'generated_pending_reload', 'graph generated — verifying views…');
          projLog('generate_success', {{ id, exitCode: run.exitCode, manifest: (run.manifest || {{}}).status }});
          await scanProjects();                          // G5P.4: pick up the fresh manifest (ready/incompatible)
          if ($('repo-list')) renderRepos();
          if (AUTO_LOAD_ID === id && (SCAN[id] || {{}}).status === 'ready') {{ AUTO_LOAD_ID = null; selectProject(id); if (window.__openSection) window.__openSection('graph'); }}
        }} else if (run.state === 'error') {{
          clearInterval(GEN_POLL); GEN_POLL = null;
          setGen(id, 'error', 'generation failed: ' + (run.error || 'unknown') + ' — see bridge log');
          projLog('generate_error', {{ id, exitCode: run.exitCode, error: (run.error || '').slice(0, 160) }});
          await scanProjects();
          if ($('repo-list')) renderRepos();
        }}
      }} catch (e) {{}}
    }}, 1500);
  }};
  const runGenerate = async p => {{
    try {{
      const r = await fetch('/api/graphify/generate', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ projectId: p.id, repoPath: p.repoPath }}) }});
      const j = await r.json();
      if (r.status === 202) {{
        setGen(p.id, 'generating', 'graphify update running via the local bridge…');
        projLog('generate_started', {{ id: p.id }});
        pollRun(p.id);
      }} else {{
        setGen(p.id, 'error', 'bridge refused: ' + (j.error || j.message || r.status));
        projLog('generate_error', {{ id: p.id, refused: j.error || j.message }});
      }}
    }} catch (e) {{
      setGen(p.id, 'error', 'bridge unreachable — it may have stopped');
    }}
    renderRepos();
  }};
  const packCmd = p => 'cd "' + (p.repoPath || '') + '"' + String.fromCharCode(10) + 'graphify update .';
  const runBtn = (p, label) => '<button class="rbtn rbtn-run" title="loopback bridge pipeline: graphify update -> read-model -> views (the entire allowlist)">' + label + '</button>';
  // ---- G5P.2 repositories flow (Settings card; localStorage persistence) ----
  const renderRepos = () => {{
    const box = $('repo-list');
    if (!box) return;
    if (BRIDGE.available === null) {{ checkBridge().then(() => renderRepos()); }}
    const bline = $('bridge-line');
    if (bline) bline.innerHTML = BRIDGE.available
      ? 'local bridge: <b style="color:var(--good)">detected</b> — loopback-only (127.0.0.1), allowlisted to <code>graphify update</code> in a validated path; nothing else can run' + (BRIDGE.graphify ? '' : ' · <b style="color:#fbbf24">graphify not on PATH</b>')
      : BRIDGE.available === false
        ? 'local bridge: <b style="color:var(--steel-300)">not detected</b> — RUN GRAPHIFY falls back to an honest manual command pack. Start it with <code>python scripts/graphify_dashboard_bridge.py</code> and open the dashboard via <code>http://127.0.0.1:8787/views/graphify-dashboard.html</code>'
        : 'local bridge: checking…';
    box.innerHTML = projAll().map(p => {{
      const ready = p.graphStatus === 'ready';
      const sel = p.id === PROJ ? ' · <b style="color:var(--molten-hot)">selected</b>' : '';
      const onStrip = inTopStrip(p);
      return '<div class="rrow" data-proj="' + esc(p.id) + '">'
        + '<div class="rrow__h"><b>' + esc(p.label) + '</b>'
        + '<span class="st st--' + (ready ? 'imp' : p.graphStatus === 'repo_path_configured' ? 'part' : 'plan') + '">' + esc(PSTATUS[p.graphStatus] || p.graphStatus) + '</span>'
        + '<span class="st st--' + (onStrip ? 'imp' : 'plan') + '" title="display rule: default + ready + pinned + recent local — everything is managed here either way">' + (onStrip ? 'TOP STRIP' : 'SETTINGS ONLY') + '</span>'
        + (p.local ? '<span class="st st--ext">LOCAL</span>' : '') + sel
        + '<button class="rbtn rbtn-pin" title="pin/unpin to the top strip (saved locally in this browser)">' + (p.pinned ? 'UNPIN' : 'PIN') + '</button>'
        + (p.local ? '<button class="rbtn rbtn-rm" title="remove this browser-local project — the source repo is untouched; tracked registry projects cannot be deleted here">REMOVE</button>' : '')
        + '<button class="rbtn rbtn-sel">' + (p.id === PROJ ? 'SELECTED' : 'SELECT') + '</button></div>'
        + '<p class="gmeta">' + esc(p.statusMessage || '') + '</p>'
        + (p.pathKind ? '<p class="gmeta">path: ' + (p.pathKind === 'relative-resolved' ? 'relative — resolved by the bridge to <code>' + esc(p.resolvedPath || '?') + '</code>' : p.pathKind === 'absolute' ? 'absolute — validated by the bridge' : esc(p.pathKind)) + '</p>'
                          : (p.repoPath && !p.isDefault ? '<p class="gmeta">path: browser-local text — not validated (bridge ' + (BRIDGE.available ? 'has not scanned it yet' : 'not running') + ')</p>' : ''))
        + (ready ? '<p class="gmeta">repo: <code>' + esc(p.repoPath) + '</code> · output: <code>' + esc(p.graphOutputPath || '?') + '</code> · ' + esc(p.nodeCount) + ' nodes · graphed at <code>' + esc(p.lastGraphedAt || '?') + '</code></p>'
                   + (p.isDefault ? '' : '<div class="rrow__btns">' + runBtn(p, 'REBUILD GRAPH') + '</div><div class="gpack" style="display:none"></div>')
                 : '<input class="rin rin-path" type="text" placeholder="local repo path (absolute, or relative to the dashboard repo)" value="' + esc(p.repoPath || '') + '" spellcheck="false">'
                   + '<div class="rrow__btns">'
                   + '<button class="rbtn rbtn-save" title="saved locally in this browser (localStorage)">SAVE PATH</button>'
                   + (p.repoPath
                      ? (p.graphStatus === 'generating'
                         ? '<button class="rbtn" disabled>GENERATING…</button>'
                         : BRIDGE.available
                           ? runBtn(p, p.graphStatus === 'rebuild_required' ? 'REBUILD REQUIRED'
                                       : p.graphStatus === 'views_missing' || p.graphStatus === 'generated_pending_reload' ? 'BUILD VIEWS'
                                       : 'RUN GRAPHIFY')
                           : '<button class="rbtn rbtn-pack" title="no local bridge detected — prepare the exact manual command">PREPARE COMMAND</button>')
                      : '<button class="rbtn" disabled title="enter a repo path first">RUN GRAPHIFY</button>')
                   + '</div><div class="gpack" style="display:none"></div>')
        + '</div>';
    }}).join('');
    box.querySelectorAll('.rrow').forEach(row => {{
      const id = row.dataset.proj;
      const run = row.querySelector('.rbtn-run');
      if (run) run.onclick = () => {{ const p = projGet(id); if (p && p.repoPath) runGenerate(p); }};
      const packBtn = row.querySelector('.rbtn-pack');
      if (packBtn) packBtn.onclick = () => {{
        const p = projGet(id); if (!p || !p.repoPath) return;
        const pack = row.querySelector('.gpack');
        const cmd = packCmd(p);
        pack.style.display = 'block';
        pack.innerHTML = '<p class="gmeta" style="margin-top:7px">No local bridge detected — run this yourself in a terminal (the page cannot check your filesystem without the bridge, so it will not claim the graph exists):</p>'
          + '<span class="cmd">' + esc(cmd) + '</span>'
          + '<p class="gmeta">output: <code>' + esc(p.repoPath) + String.fromCharCode(92) + 'graphify-out' + String.fromCharCode(92) + '</code> (graph.json + GRAPH_REPORT.md) · next: start everything with <code>python scripts/start_graphify_dashboard.py</code> — ready projects then load with one click</p>'
          + '<button class="rbtn gp-copy">COPY COMMAND</button><button class="rbtn gp-mark">MARK STARTED — waiting for manual run</button>';
        if (p.graphStatus !== 'command_prepared' && p.graphStatus !== 'waiting_for_manual_run') {{
          setGen(id, 'command_prepared', 'command prepared — run it manually, then REBUILD once the bridge is up');
        }}
        projLog('command_pack_opened', {{ id }});
        pack.querySelector('.gp-copy').onclick = () => {{
          try {{ navigator.clipboard.writeText(cmd); projLog('command_copied', {{ id }}); }} catch (e) {{}}
        }};
        pack.querySelector('.gp-mark').onclick = () => {{
          setGen(id, 'waiting_for_manual_run', 'manual run marked started — the page cannot verify output without the bridge');
          projLog('manual_run_marked', {{ id }});
          renderRepos();
        }};
      }};
      const save = row.querySelector('.rbtn-save');
      if (save) save.onclick = () => {{
        const v = row.querySelector('.rin-path').value.trim();
        const loc = projLocal();
        const added = loc.added.find(a => a.id === id);
        if (added) added.repoPath = v; else loc.edits[id] = {{ ...(loc.edits[id] || {{}}), repoPath: v, statusMessage: v ? 'repo path configured — graph not generated yet (saved locally in this browser)' : undefined }};
        lsSet('graphify-projects-local-v1', loc);
        projLog('repo_path_set', {{ id, path: v }});
        renderRepos(); paintProj(); paintNoGraph();
      }};
      row.querySelector('.rbtn-sel').onclick = () => {{ selectProject(id); renderRepos(); }};
      const pin = row.querySelector('.rbtn-pin');
      if (pin) pin.onclick = () => {{
        const loc = projLocal();
        const added = loc.added.find(a => a.id === id);
        const cur = projGet(id);
        if (added) added.pinned = !cur.pinned;
        else loc.edits[id] = {{ ...(loc.edits[id] || {{}}), pinned: !cur.pinned }};
        lsSet('graphify-projects-local-v1', loc);
        renderRepos(); renderTopStrip();
      }};
      const rm = row.querySelector('.rbtn-rm');
      if (rm) rm.onclick = () => {{ removeLocalProject(id); renderRepos(); }};
    }});
    const go = $('ra-open');
    if (go && !go.dataset.wired) {{
      go.dataset.wired = '1';
      go.onclick = () => {{ if (window.__openAddModal) window.__openAddModal(); }};
    }}
  }};
  window.__repoUI = renderRepos;
  // ---- G5P.5 cleanup controls (Maintenance card) ----
  const renderMaint = () => {{
    const box = $('clean-list');
    if (!box) return;
    if (!BRIDGE.available) {{ box.innerHTML = '<p class="gmeta">bridge not detected — cleanup needs the local bridge (views can also be deleted manually, they are disposable)</p>'; return; }}
    const gen = Object.entries(SCAN).filter(([id, sc]) => ['ready', 'rebuild_required', 'views_missing', 'generated_incompatible'].includes(sc.status));
    box.innerHTML = (gen.length
      ? gen.map(([id, sc]) => '<div class="rrow"><div class="rrow__h"><b>' + esc(id) + '</b><span class="st st--' + (sc.status === 'ready' ? 'imp' : 'plan') + '">' + esc(PSTATUS[sc.status] || sc.status) + '</span>'
          + '<button class="rbtn rbtn-clean" data-clean="' + esc(id) + '" title="deletes graphify-out/projects/' + esc(id) + '/ only — the source repo is untouched">CLEAN VIEWS</button></div></div>').join('')
      : '<p class="gmeta">no generated project views on disk</p>')
      + (gen.length > 1 ? '<button class="rbtn" id="clean-all" title="deletes every graphify-out/projects/<id>/ directory — source repos untouched">CLEAN ALL GENERATED VIEWS</button>' : '');
    const doClean = async payload => {{
      try {{
        const r = await fetch('/api/projects/clean', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify(payload) }});
        const j = await r.json();
        (j.results || []).forEach(res => projLog('views_cleaned', {{ id: res.projectId, cleaned: res.cleaned }}));
        const cleanedIds = (j.results || []).filter(x => x.cleaned).map(x => x.projectId);
        if (cleanedIds.includes(CURRENT_GRAPH)) {{                 // the LOADED graph was cleaned -> fall back honestly
          const wb = REGISTRY.find(x => x.isDefault);
          if (wb) {{ PROJ = wb.id; loadGraphFor(projGet(wb.id)); }}
        }}
        await scanProjects();
        renderMaint(); renderRepos(); paintProj(); paintNoGraph();
      }} catch (e) {{}}
    }};
    box.querySelectorAll('.rbtn-clean').forEach(b => b.onclick = () => doClean({{ projectId: b.dataset.clean }}));
    const all = $('clean-all');
    if (all) all.onclick = () => doClean({{ all: true }});
  }};
  window.__maintUI = renderMaint;
  // ---- G5P.7 Memory: real local memory surfaces (sessions / notes / history / data) ----
  const SESS_KEY = 'graphify-sessions-v1';
  const NOTES_KEY = 'graphify-node-notes-v1';
  const fmtTs = ts => String(ts || '').replace('T', ' ').slice(0, 16);
  const memStatus = (msg) => {{ const el = $('mem-note-ctx'); if (el && msg) el.textContent = msg; }};
  const saveSession = () => {{
    const name = ($('mem-sess-name').value || '').trim() || ('session ' + new Date().toLocaleString());
    const sess = {{ name, ts: new Date().toISOString(), proj: PROJ, mode3d, mode2d: MODE2D,
      hidden: Array.from(HIDDEN_CONCEPTS), sel: LAST_SEL ? {{ id: LAST_SEL.id, lbl: LAST_SEL.lbl }} : null, motion: {{ ...MOT }} }};
    const all = lsGet(SESS_KEY, []);
    all.unshift(sess);
    lsSet(SESS_KEY, all.slice(0, 20));
    $('mem-sess-name').value = '';
    projLog('session_saved', {{ name, proj: PROJ }});
    renderMemory();
  }};
  const restoreSession = i => {{
    const sess = lsGet(SESS_KEY, [])[i];
    if (!sess) return;
    const p = projGet(sess.proj);
    if (!p || p.graphStatus !== 'ready') {{
      projLog('session_restore_blocked', {{ name: sess.name, proj: sess.proj, status: p ? p.graphStatus : 'gone' }});
      alertRow(i, 'project "' + (p ? p.label : sess.proj) + '" is not ready anymore — rebuild it first');
      return;
    }}
    selectProject(sess.proj);
    MOT = {{ ...MOT_DEF, ...(sess.motion || {{}}) }};
    try {{ localStorage.setItem('graphify-motion-v1', JSON.stringify(MOT)); }} catch (e) {{}}
    motPaint(); motSend();
    setTimeout(() => {{
      HIDDEN_CONCEPTS.clear();
      (sess.hidden || []).forEach(k => HIDDEN_CONCEPTS.add(k));
      document.querySelectorAll('#conlist input').forEach(cb => cb.checked = !HIDDEN_CONCEPTS.has(cb.dataset.key));
      syncConAll(); sendConcepts();
      if (sess.mode3d === false) {{
        $('pv2d').click();
        if (sess.sel && sess.sel.id) setTimeout(() => {{   // G5P.8: 2D find/jump parity
          try {{ iframe.contentWindow.postMessage({{ graphify: 'find-req', q: sess.sel.lbl || sess.sel.id }}, '*'); }} catch (e) {{}}
        }}, 1200);
      }} else if (sess.sel && sess.sel.id) {{
        try {{ iframe.contentWindow.postMessage({{ graphify: 'find-req', q: sess.sel.lbl || sess.sel.id }}, '*'); }} catch (e) {{}}
      }}
    }}, 1800);
    projLog('session_restored', {{ name: sess.name, proj: sess.proj }});
    if (window.__openSection) window.__openSection('graph');
  }};
  const alertRow = (i, msg) => {{
    const row = document.querySelectorAll('#mem-sess-list .mrow2')[i];
    if (row) {{ const m = row.querySelector('.mq'); if (m) m.innerHTML += ' <span style="color:#fbbf24">— ' + esc(msg) + '</span>'; }}
  }};
  const addNote = () => {{
    const text = ($('mem-note-text').value || '').trim();
    if (!text) return;
    if (!LAST_SEL) {{ memStatus('No node selected — click a node in the 3D or 2D view first, then add the note.'); return; }}
    const all = lsGet(NOTES_KEY, []);
    all.unshift({{ ts: new Date().toISOString(), proj: PROJ, projLbl: (projGet(PROJ) || {{}}).label, id: LAST_SEL.id, lbl: LAST_SEL.lbl, fp: LAST_SEL.fp, text }});
    lsSet(NOTES_KEY, all.slice(0, 100));
    $('mem-note-text').value = '';
    projLog('note_added', {{ node: LAST_SEL.lbl, proj: PROJ }});
    renderMemory();
  }};
  const jumpToNote = n => {{
    const p = projGet(n.proj);
    if (!p || p.graphStatus !== 'ready') {{ projLog('note_jump_blocked', {{ node: n.lbl, proj: n.proj }}); return; }}
    selectProject(n.proj);
    setTimeout(() => {{ try {{ iframe.contentWindow.postMessage({{ graphify: 'find-req', q: n.lbl || n.id }}, '*'); }} catch (e) {{}} }}, 1800);
    if (window.__openSection) window.__openSection('graph');
  }};
  const MEM_KEYS = [
    ['graphify-sessions-v1', 'saved sessions'],
    ['graphify-node-notes-v1', 'node notes'],
    ['graphify-ask-log', 'ask evidence log'],
    ['graphify-project-log', 'project/repo events'],
    ['graphify-projects-local-v1', 'browser-local projects + path edits'],
    ['graphify-recent-projects-v1', 'recent projects (top strip)'],
    ['graphify-motion-v1', 'motion slider preferences'],
    ['graphify-hunter-reports-v1', 'Hunter audit reports'],
    ['graphify-savings-v1', 'token/context savings history'],
    ['graphify-claudecode-setup-v1', 'Claude Code wizard progress'],
    ['graphify-mcp-selftest-v1', 'connector self-test result'],
    ['graphify-claudecode-live-v1', 'Claude Code last-answered (LIVE) cache'],
  ];
  const renderMemory = () => {{
    if (!document.querySelector('.sec[data-sec=memory]')) return;
    // sessions
    const sessBox = $('mem-sess-list');
    const sess = lsGet(SESS_KEY, []);
    if (sessBox) sessBox.innerHTML = sess.length ? sess.map((x, i) =>
      '<div class="mrow2"><span class="mt">' + fmtTs(x.ts) + '</span><span class="mq"><b>' + esc(x.name) + '</b> — ' + esc((projGet(x.proj) || {{}}).label || x.proj)
      + (x.sel ? ' · node ' + esc(x.sel.lbl) : '') + ((x.hidden || []).length ? ' · ' + x.hidden.length + ' concept(s) hidden' : '') + (x.mode3d === false ? ' · 2D' : ' · 3D') + '</span>'
      + '<button class="rbtn mem-restore" data-i="' + i + '">RESTORE</button><button class="rbtn mem-sess-del" data-i="' + i + '">DELETE</button></div>').join('')
      : '<div class="aempty">No saved sessions yet in this browser.</div>';
    // notes
    const noteBox = $('mem-note-list');
    const notes = lsGet(NOTES_KEY, []);
    if (noteBox) noteBox.innerHTML = notes.length ? notes.map((n, i) =>
      '<div class="mrow2"><span class="mt">' + fmtTs(n.ts) + '</span><span class="mq"><b>' + esc(n.lbl) + '</b> <span style="color:var(--steel-300)">(' + esc(n.projLbl || n.proj) + ')</span><br>' + esc(n.text) + '</span>'
      + '<button class="rbtn mem-jump" data-i="' + i + '">JUMP</button><button class="rbtn mem-note-del" data-i="' + i + '">REMOVE</button></div>').join('')
      : '<div class="aempty">No node notes yet in this browser.</div>';
    const ctx = $('mem-note-ctx');
    if (ctx) ctx.textContent = LAST_SEL ? ('Note will attach to: ' + LAST_SEL.lbl + ' (' + ((projGet(PROJ) || {{}}).label || PROJ) + ')')
      : 'Select a core in the Hivemind, then write a note — notes remember the node and project, and JUMP takes you back to it.';
    // ask history
    const projSel = $('mem-ask-proj');
    if (projSel && projSel.options.length <= 1) {{
      projAll().forEach(p => {{ const o = document.createElement('option'); o.value = p.label; o.textContent = p.label; projSel.appendChild(o); }});
    }}
    const q = (($('mem-ask-q') || {{}}).value || '').toLowerCase();
    const pf = (projSel || {{}}).value || '';
    const log = (window.__askLog ? window.__askLog() : []);
    const hits = log.filter(en => (!q || (en.q || '').toLowerCase().includes(q)) && (!pf || ((en.ctx || {{}}).project === pf)));
    const askBox = $('mem-ask-list');
    if (askBox) askBox.innerHTML = hits.length ? hits.slice(0, 50).map(en =>
      '<div class="mrow2"><span class="mt">' + fmtTs(en.ts) + '</span><span class="mq">' + esc(en.q) + ' <span style="color:var(--steel-300)">· ' + esc((en.ctx || {{}}).project || '?') + ' · ' + esc(en.status) + '</span></span></div>').join('')
      : '<div class="aempty">' + (log.length ? 'No asks match the filter.' : 'No asks recorded yet in this browser.') + '</div>';
    // local data keys
    const keysBox = $('mem-keys');
    if (keysBox) keysBox.innerHTML = MEM_KEYS.map(([k, label]) => {{
      let size = 0, count = '';
      try {{
        const raw = localStorage.getItem(k);
        size = raw ? raw.length : 0;
        const parsed = raw ? JSON.parse(raw) : null;
        if (Array.isArray(parsed)) count = parsed.length + ' item(s) · ';
      }} catch (e) {{}}
      return '<div class="mrow2"><span class="mq"><code>' + k + '</code> <span style="color:var(--steel-300)">— ' + label + '</span></span>'
        + '<span class="mt">' + count + (size ? (size / 1024).toFixed(1) + ' KB' : 'empty') + '</span>'
        + (size ? '<button class="rbtn mem-clear" data-k="' + k + '">CLEAR</button>' : '') + '</div>';
    }}).join('');
    // wire
    document.querySelectorAll('.mem-restore').forEach(b => b.onclick = () => restoreSession(+b.dataset.i));
    document.querySelectorAll('.mem-sess-del').forEach(b => b.onclick = () => {{ const a = lsGet(SESS_KEY, []); a.splice(+b.dataset.i, 1); lsSet(SESS_KEY, a); renderMemory(); }});
    document.querySelectorAll('.mem-jump').forEach(b => b.onclick = () => jumpToNote(lsGet(NOTES_KEY, [])[+b.dataset.i]));
    document.querySelectorAll('.mem-note-del').forEach(b => b.onclick = () => {{ const a = lsGet(NOTES_KEY, []); const n = a.splice(+b.dataset.i, 1)[0]; lsSet(NOTES_KEY, a); projLog('note_removed', {{ node: (n || {{}}).lbl }}); renderMemory(); }});
    document.querySelectorAll('.mem-clear').forEach(b => b.onclick = () => {{ try {{ localStorage.removeItem(b.dataset.k); }} catch (e) {{}} projLog('memory_key_cleared', {{ key: b.dataset.k }}); renderMemory(); }});
    const clrAll = $('mem-clear-all');
    if (clrAll) clrAll.onclick = () => {{ if (confirm('Clear ALL local dashboard data in this browser? Source repos and generated views are NOT affected.')) {{ MEM_KEYS.forEach(([k]) => {{ try {{ localStorage.removeItem(k); }} catch (e) {{}} }}); try {{ sessionStorage.removeItem('graphify-cc-live-session'); }} catch (e) {{}} projLog('all_local_data_cleared', {{}}); renderMemory(); renderTopStrip(); if (window.__paintConnLeds) window.__paintConnLeds(); if (window.__renderHunt) window.__renderHunt(); }} }};
  }};
  window.__memUI = renderMemory;
  const sBtn = $('mem-sess-save'); if (sBtn) sBtn.onclick = saveSession;
  const nBtn = $('mem-note-add'); if (nBtn) nBtn.onclick = addNote;
  const aq = $('mem-ask-q'); if (aq) aq.oninput = () => renderMemory();
  const ap = $('mem-ask-proj'); if (ap) ap.onchange = () => renderMemory();
  // ---- G5P.6 Add Project modal ----
  const amStatus = (msg, color) => {{ const el = $('am-status'); if (el) {{ el.textContent = msg; el.style.color = color || 'var(--steel-300)'; }} }};
  const openAddModal = () => {{
    document.body.classList.add('addmodal');
    ['am-path', 'am-url'].forEach(i => {{ const el = $(i); if (el) el.value = ''; }});
    amStatus('');
    const pickBtn = $('am-pick');
    if (pickBtn) pickBtn.disabled = !BRIDGE.available;
    const imp = $('am-import');
    if (imp) imp.disabled = !BRIDGE.available || !BRIDGE.graphify;
    const uchip = $('am-url-chip');
    if (uchip) {{
      const t = !BRIDGE.available ? 'needs the local bridge' : (!BRIDGE.graphify ? 'graphify CLI not installed' : 'LIVE via bridge');
      uchip.textContent = t;
      uchip.className = 'st ' + ((BRIDGE.available && BRIDGE.graphify) ? 'st--imp' : 'st--plan');
    }}
    const paste = $('am-paste');
    if (paste) paste.style.display = BRIDGE.available ? 'none' : 'block';
    projLog('add_project_opened', {{ bridge: !!BRIDGE.available }});
  }};
  window.__openAddModal = openAddModal;
  const closeAddModal = () => document.body.classList.remove('addmodal');
  const amWire = () => {{
    const c = $('am-cancel'); if (c) c.onclick = closeAddModal;
    const modal = $('addmodal'); if (modal) modal.onclick = e => {{ if (e.target === modal) closeAddModal(); }};
    const pick = $('am-pick');
    if (pick) pick.onclick = async () => {{
      if (!BRIDGE.available) {{ amStatus('folder picker needs the local bridge — paste a path below instead', '#fbbf24'); projLog('folder_picker_unavailable', {{}}); return; }}
      amStatus('opening your file explorer…');
      try {{
        const j = await (await fetch('/api/projects/pick-folder', {{ method: 'POST' }})).json();
        if (j.path) {{
          projLog('folder_picker_used', {{}});
          const base = String(j.path).replace(/[\\/]+$/, '').split(/[\\/]/).pop() || 'project';
          amStatus('graphing ' + base + '…');
          closeAddModal();
          await createAndGraph(base, j.path);
        }}
        else if (j.cancelled) amStatus('picker cancelled');
        else {{ amStatus(j.error || 'picker unavailable', '#fbbf24'); projLog('folder_picker_unavailable', {{ error: j.error }}); }}
      }} catch (e) {{ amStatus('bridge unreachable', '#fbbf24'); }}
    }};
    const imp = $('am-import');
    if (imp) imp.onclick = async () => {{
      const url = ($('am-url').value || '').trim();
      if (!url) {{ amStatus('paste a GitHub repo URL first', '#fbbf24'); return; }}
      const m = url.match(/^https:\\/\\/github\\.com\\/([A-Za-z0-9_.-]+)\\/([A-Za-z0-9_.-]+?)(?:\\.git)?\\/?$/);
      if (!m) {{ amStatus('only https://github.com/owner/repo URLs are supported', '#fbbf24'); return; }}
      const loc0 = projLocal();
      const prev = loc0.added.find(a => (a.description || '') === 'imported from ' + url);
      const id = prev ? prev.id : uniqueLocalId(m[2]);   // G5P.10: re-importing the same URL reuses the SAME project (no duplicate cards)
      amStatus(prev ? 're-importing — refreshing the existing clone…' : 'importing — cloning via the bridge…');
      try {{
        const r = await fetch('/api/projects/import-url', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ projectId: id, url }}) }});
        const j = await r.json();
        if (r.status !== 202) {{ amStatus('bridge refused: ' + (j.error || j.message || r.status), '#fbbf24'); return; }}
        projLog('repo_url_import_started', {{ id, url }});
        const loc = projLocal();
        const entry0 = loc.added.find(a => a.id === id);
        if (entry0) {{ entry0.genStatus = 'generating'; entry0.genMsg = 're-importing — refreshing via the bridge…'; }}
        else loc.added.push({{ id, label: m[2], description: 'imported from ' + url, repoPath: null, graphOutputPath: 'graphify-out/', isDefault: false, genStatus: 'generating', genMsg: 'cloning + graphing via the bridge…' }});
        lsSet('graphify-projects-local-v1', loc);
        touchRecent(id);
        closeAddModal();
        renderTopStrip();
        watchImport(id);
      }} catch (e) {{ amStatus('bridge unreachable', '#fbbf24'); }}
    }};
    const save = $('am-save');
    if (save) save.onclick = () => {{
      const path = ($('am-path').value || '').trim();
      if (!path) {{ amStatus('paste a local repo path first', '#fbbf24'); return; }}
      const base = path.replace(/[\\/]+$/, '').split(/[\\/]/).pop() || 'project';
      const id = uniqueLocalId(base);
      const loc = projLocal();
      loc.added.push({{ id, label: base, description: 'added locally in this browser', repoPath: path, graphOutputPath: 'graphify-out/', isDefault: false }});
      lsSet('graphify-projects-local-v1', loc);
      projLog('project_added', {{ id, path }});
      amStatus('saved — manage it in Settings → Repositories (start the bridge to graph it)', 'var(--good)');
      setTimeout(() => {{ closeAddModal(); renderTopStrip(); if ($('repo-list')) renderRepos(); }}, 900);
    }};
  }};
  amWire();
  paintProj(); paintNoGraph();
  setTimeout(() => {{ checkBridge(); }}, 300);          // boot detection -> scan -> honest live statuses
  // G5P.8: a reload mid-import must never leave a project stuck on 'generating'
  // forever -- reconcile against the bridge's actual run state once at boot.
  // G5P.10: ONE import watcher shared by the IMPORT click AND boot reconcile,
  // so a reload mid-import resumes polling instead of sticking on 'generating'.
  const watchImport = id => {{
    const poll = setInterval(async () => {{
      try {{
        const q = await (await fetch('/api/graphify/status')).json();
        const run = q.run || {{}};
        if (run.projectId !== id) return;
        if (!['success', 'error'].includes(run.state)) {{   // live stage on the strip chip
          const msg = 'import: ' + (run.stage || run.state || 'working') + '…';
          const locL = projLocal();
          const eL = locL.added.find(a => a.id === id);
          if (eL && eL.genMsg !== msg) {{ eL.genMsg = msg; lsSet('graphify-projects-local-v1', locL); renderTopStrip(); }}
          return;
        }}
        clearInterval(poll);
        const loc2 = projLocal();
        const entry = loc2.added.find(a => a.id === id);
        if (run.state === 'success') {{
          if (entry) {{ entry.repoPath = run.clonedPath || run.repoPath; delete entry.genStatus; delete entry.genMsg; }}
          lsSet('graphify-projects-local-v1', loc2);
          projLog('repo_url_import_done', {{ id, path: run.clonedPath }});
          await scanProjects();
          if ((SCAN[id] || {{}}).status === 'ready') {{ selectProject(id); if (window.__openSection) window.__openSection('graph'); }}
        }} else {{
          if (entry) {{ entry.genStatus = 'error'; entry.genMsg = 'import failed: ' + (run.error || 'unknown'); }}
          lsSet('graphify-projects-local-v1', loc2);
          projLog('repo_url_import_failed', {{ id, error: (run.error || '').slice(0, 140) }});
        }}
        renderTopStrip();
        if ($('repo-list')) renderRepos();
      }} catch (e) {{}}
    }}, 1500);
  }};
  const reconcileImports = async () => {{
    const loc = projLocal();
    const stuck = loc.added.filter(a => a.genStatus === 'generating');
    if (!stuck.length) return;
    let run = {{}};
    try {{ run = (await (await fetch('/api/graphify/status')).json()).run || {{}}; }} catch (e) {{}}
    let changed = false;
    for (const a of stuck) {{
      if (run.projectId === a.id && ['cloning', 'running'].includes(run.state)) {{ watchImport(a.id); continue; }}   // still live -> resume watching (G5P.10)
      if (run.projectId === a.id && run.state === 'success') {{
        a.repoPath = a.repoPath || run.clonedPath || run.repoPath || null;
        delete a.genStatus; delete a.genMsg; changed = true; continue;
      }}
      const sc = SCAN[a.id] || {{}};
      if (sc.status === 'ready') {{ delete a.genStatus; delete a.genMsg; }}
      else {{ a.genStatus = 'error'; a.genMsg = 'interrupted — import again (re-import resumes from the existing clone)'; }}
      changed = true;
    }}
    if (changed) {{
      lsSet('graphify-projects-local-v1', loc);
      projLog('import_reconciled_on_boot', {{ count: stuck.length }});
      await scanProjects(); renderTopStrip(); if ($('repo-list')) renderRepos();
    }}
  }};
  const bridgeBanner = () => {{
    if (BRIDGE.available || $('bridge-banner')) return;
    const d = document.createElement('div'); d.id = 'bridge-banner';
    d.innerHTML = 'Limited mode &mdash; the local server (bridge) is not running, so adding and graphing projects is off. Start it with <code>python scripts/start_graphify_dashboard.py</code> and open <code>http://127.0.0.1:8787/views/graphify-dashboard.html</code>.<span id="bb-x" title="dismiss">&times;</span>';
    const plate = $('plate'); if (plate) plate.appendChild(d);
    const x = $('bb-x'); if (x) x.onclick = () => d.remove();
  }};
  const guardSelection = () => {{
    // G5P.8: a project removed out-of-band must never leave a dangling
    // selection ("? (undefined)" answers) -- fall back to the default graph.
    if (!projGet(PROJ) || !projReady()) {{
      const first = projAll().find(p => p.graphStatus === 'ready');
      if (first) {{ selectProject(first.id); return; }}
      UNLOADED = true; paintNoGraph(); paintProj(); renderTopStrip();   // honest empty boot
    }}
  }};
  setTimeout(() => {{ guardSelection(); reconcileImports(); bridgeBanner(); refreshImportant(); }}, 2300);
  setTimeout(guardSelection, 6500);                       // G5Q.1q: scan may resolve after the first pass -- retry the auto-load once
  // ---- G5P ask console: LOCAL Graphify answer path (no agents, no network) ----
  const TOTALS_BASE = {{ nodes: '{html.escape(C['nodes'])}', edges: '{html.escape(C['edges'])}', clusters: '{html.escape(C['slices'])}' }};
  let TOTALS = {{ ...TOTALS_BASE }};
  const BASE_CONCEPTS = {CONCEPTS_JS};
  let N_CONCEPTS = {len(CONCEPTS)};
  let LAST_SEL = null, LAST_SLICE = null, MODE2D = 'brain', NB_PENDING = null, FIND_PENDING = null;
  const askCtx = () => {{
    const mode = mode3d ? '3D Hivemind' : ('2D Explorer · ' + (MODE2D === 'brain' ? '2D Brain' : 'Structural'));
    const pp = projGet(PROJ) || {{}};
    return {{ project: pp.label || '?', projectId: PROJ, projectStatus: pp.graphStatus, mode, sel: LAST_SEL ? LAST_SEL.lbl : null,
      hidden: Array.from(HIDDEN_CONCEPTS), slice: LAST_SLICE ? LAST_SLICE.slice : null }};
  }};
  const askLog = (q, status, ctx) => {{
    try {{
      const log = JSON.parse(localStorage.getItem('graphify-ask-log') || '[]');
      log.unshift({{ ts: new Date().toISOString(), q, status, ctx }});
      localStorage.setItem('graphify-ask-log', JSON.stringify(log.slice(0, 50)));
    }} catch (e) {{}}
  }};
  window.__askLog = () => {{ try {{ return JSON.parse(localStorage.getItem('graphify-ask-log') || '[]'); }} catch (e) {{ return []; }} }};
  window.__renderResp = (q, a, s) => renderResp(q, a, s);   // G5P.1 shell (project-card notices)
  const CHAT_HIST = [];
  let CF_LAST = null;
  const cfAppend = (q, a, s) => {{
    const th = $('cf-thread'); if (!th) return;
    const qd = document.createElement('div'); qd.className = 'cf-msg q'; qd.textContent = q;
    const ad = document.createElement('div'); ad.className = 'cf-msg a'; ad.textContent = a;
    const m = document.createElement('span'); m.className = 'cf-meta';
    m.textContent = s.toUpperCase() + ' · ' + new Date().toTimeString().slice(0, 8);
    ad.appendChild(m);
    th.appendChild(qd); th.appendChild(ad);
    th.scrollTop = th.scrollHeight;                        // auto-scroll: chat sticks to the newest
    CF_LAST = ad;
  }};
  const renderResp = (q, text, status) => {{
    const body = $('resp-body');
    const ph = $('resp-placeholder'); if (ph) ph.remove();
    const d = document.createElement('div'); d.className = 'rcard';
    const t = new Date().toTimeString().slice(0, 8);
    d.innerHTML = '<div class="rcard__q">' + esc(q) + '</div><div class="rcard__a">' + esc(text) + '</div>'
      + '<div class="rcard__m"><span class="rcard__s rcard__s--' + status + '">' + status + '</span><span class="rcard__t">' + t + ' · local graph</span></div>';
    body.insertBefore(d, body.firstChild);
    body.scrollTop = 0;                                    // auto-scroll: newest card visible
    CHAT_HIST.push({{ q, a: text, s: status, ts: Date.now() }});
    if (CHAT_HIST.length > 200) CHAT_HIST.shift();
    cfAppend(q, text, status);
    askLog(q, status, askCtx());
  }};
  const UNSUPPORTED = 'I can only answer from the local graph data wired in this build — no agents, no semantic search yet.';
  const ctxLine = () => {{
    const c = askCtx();
    return 'Available context: view ' + c.mode + (c.sel ? ' · selected ' + c.sel : ' · no node selected')
      + (c.slice ? ' · slice ' + c.slice : '') + ' · ' + (N_CONCEPTS - HIDDEN_CONCEPTS.size) + '/' + N_CONCEPTS + ' concepts visible'
      + ' · graph ' + TOTALS.nodes + ' files / ' + TOTALS.edges + ' links / ' + TOTALS.clusters + ' clusters.';
  }};
  const HELP = 'Local asks wired in this build:\\n· what is selected?\\n· what is connected to this node?\\n· what are the most connected files?\\n· what concepts are visible?\\n· what slice am I in?\\n· how many nodes are visible?\\n· shortest path A to B / trace <name> / chain end <name>\\n· find <name> / jump to <name>  (3D + 2D — natural phrasing OK: "can you jump to …" / "where is …"; multi-word names fall back word-by-word)\\n· run hunter / what did hunter find? / jump to first hunter finding / show orphans\\nPlanned (see How To Guide): what-changed (diff-aware queries).\\nClaude Code lane: ANY question — answered by your connected Claude Code right here (one real call per ask).';
  const answerAsk = q => {{
    // G5Q.1i: tolerate natural phrasing -- strip politeness/filler so
    // "can you jump to X?" reaches the same matchers as "jump to X".
    const t = q.toLowerCase().replace(/[?!.\\s]+$/, '')
      .replace(/^(?:(?:hey|hi|ok|okay|so|now|um|uh)[,!\\s]+)*/, '')
      .replace(/^(?:can|could|would|will)\\s+(?:you|we)\\s+(?:please\\s+)?/, '')
      .replace(/^use the graphify tools?[:,]?\\s+/, '')
      .replace(/^(?:please\\s+|i\\s+want\\s+to\\s+|i\\s+need\\s+to\\s+|i'd\\s+like\\s+to\\s+|lets\\s+|let's\\s+)/, '')
      .trim();
    if (/help|what can/.test(t)) return {{ s: 'answered', a: HELP }};
    if (/run hunter|hunter run/.test(t)) {{
      if (window.__openSection) window.__openSection('reports');
      runHunter();
      return {{ s: 'answered', a: 'Hunter is running against ' + ((projGet(PROJ) || {{}}).label || PROJ) + ' — the report opens in Reports.' }};
    }}
    if (/what did hunter|hunter report|show hunter/.test(t)) {{   // NOTE: must not swallow "first hunter finding"
      const r0 = huntAll()[0];
      return r0 ? {{ s: 'answered', a: huntSummaryText(r0) + ' Open Reports to click into findings.' }}
                : {{ s: 'answered', a: 'No Hunter reports yet — say "run hunter" or open Reports.' }};
    }}
    if (/first hunter finding/.test(t)) {{
      const r0 = huntAll()[0];
      if (!r0) return {{ s: 'unsupported', a: 'No Hunter reports yet — say "run hunter" first.' }};
      const fi = (r0.findings || []).findIndex(f => f.clickable);
      if (fi < 0) return {{ s: 'answered', a: 'The latest report has no node-backed finding to jump to.' }};
      openFinding(0, fi);
      return {{ s: 'answered', a: 'Jumping to: ' + r0.findings[fi].title }};
    }}
    if (/orphan|disconnected|not connected/.test(t)) {{
      const r0 = huntAll().find(x => x.proj === PROJ && x.status === 'complete');
      if (!r0) return {{ s: 'answered', a: 'Orphan/disconnect answers come from Hunter — say "run hunter" to analyze ' + ((projGet(PROJ) || {{}}).label || PROJ) + '.' }};
      const o = (r0.findings || []).filter(f => f.kind === 'orphan' || f.kind === 'component');
      return {{ s: 'answered', a: o.length ? ('From the last Hunter report: ' + o.slice(0, 3).map(f => f.title).join(' · ') + ' — open Reports for the full list.') : 'The last Hunter report found no orphan/disconnect candidates in this view.' }};
    }}
    if (/most connected|top (?:5 |five )?(?:files|nodes)|hubs?\\b|hotspots?|highest degree|depends on/.test(t)) {{
      // G5Q.1j: answered from the SAME read-model data as the right panel's
      // MOST CONNECTED FILES list -- local, no model.
      const p0 = projGet(PROJ);
      const fmtTop = list => 'Most connected files in this graph:\\n'
        + list.map((x, i) => (i + 1) + '. ' + x.lbl + ' — ' + x.deg + ' connections').join('\\n')
        + '\\nTo see what depends on one: "jump to ' + list[0].lbl + '", then ask "what is connected to this node?". (Same list: right panel.)';
      const cached = p0 && RM_TOP_CACHE[p0.id];
      if (cached && cached.length) return {{ s: 'answered', a: fmtTop(cached) }};
      refreshImportant().then(() => {{
        const l2 = p0 && RM_TOP_CACHE[p0.id];
        renderResp(q, l2 && l2.length ? fmtTop(l2) : 'The most-connected list is unavailable — load a graph (and start the local server) first.', l2 && l2.length ? 'answered' : 'unsupported');
      }});
      return null;                                       // async -- card renders after the read-model fetch
    }}
    if (/connect|neighbou?r/.test(t)) {{
      if (!LAST_SEL) return {{ s: 'unsupported', a: 'No node is selected. Click a node in the 3D or 2D view first — then I can list its connections.' }};
      try {{ iframe.contentWindow.postMessage({{ graphify: 'neighbors-req', id: LAST_SEL.id }}, '*'); }} catch (e) {{}}
      NB_PENDING = {{ q, sel: LAST_SEL.lbl, timer: setTimeout(() => {{ if (NB_PENDING) {{ renderResp(NB_PENDING.q, 'Neighbor data did not arrive from the view (timeout). ' + UNSUPPORTED, 'error'); NB_PENDING = null; }} }}, 1500) }};
      return null;                                       // async -- card renders on reply
    }}
    if (/select/.test(t)) {{
      if (!LAST_SEL) return {{ s: 'answered', a: 'No node is selected — click a node in the 3D or 2D view.' }};
      const n = LAST_SEL;
      return {{ s: 'answered', a: 'Selected: ' + n.lbl + '\\npath: ' + n.fp + '\\nregion: ' + n.reg + ' · degree ' + n.deg + ' · ' + n.nb + ' direct neighbors.' }};
    }}
    if (/concept/.test(t)) {{
      const visible = N_CONCEPTS - HIDDEN_CONCEPTS.size;
      let a = visible + ' of ' + N_CONCEPTS + ' concepts visible' + (HIDDEN_CONCEPTS.size ? ' — hidden: ' + Array.from(HIDDEN_CONCEPTS).join(', ') : ' (none hidden)') + '.';
      a += LAST_SLICE ? '\\nCounts follow the "' + LAST_SLICE.slice + '" slice (right panel shows per-slice membership).' : '\\nCounts show whole-graph totals (right panel).';
      return {{ s: 'answered', a }};
    }}
    if (/slice|mission/.test(t)) {{
      if (mode3d) return {{ s: 'answered', a: 'The 3D Hivemind shows the whole graph — slices apply in the 2D Structural view. Last 2D slice: ' + (LAST_SLICE ? LAST_SLICE.slice : 'none yet') + '.' }};
      if (MODE2D === 'brain') return {{ s: 'answered', a: '2D Brain mode is the region overview — it is not slice-based. Last structural slice: ' + (LAST_SLICE ? LAST_SLICE.slice : 'none yet') + '.' }};
      if (!LAST_SLICE) return {{ s: 'unsupported', a: 'No slice has reported yet in this session. Pick a mission slice (top chips or the drawer dropdown).' }};
      const total = Object.values(LAST_SLICE.counts).reduce((x, y) => x + y, 0);
      return {{ s: 'answered', a: 'Slice: ' + LAST_SLICE.slice + ' — ' + total + ' member nodes across ' + Object.keys(LAST_SLICE.counts).length + ' concepts.' }};
    }}
    // G5Q.1u: path/chain tracing -- BFS over the project's own edges (local)
    const mPath = t.match(/^(?:shortest path|path from|path)\\s+(.+?)\\s+(?:to|->|=>)\\s+(.+)$/);
    if (mPath) {{ tracePath(q, mPath[1].trim(), mPath[2].trim()); return null; }}
    const mTrace = t.match(/^trace\\s+(.+)$/);
    if (mTrace) {{ traceNode(q, mTrace[1].trim()); return null; }}
    if (/^(?:chain end|jump to chain end)\\b/.test(t)) {{
      const arg = t.replace(/^(?:jump to chain end|chain end)\\s*(?:of\\s+)?/, '').trim();
      chainEnd(q, arg || (LAST_SEL ? LAST_SEL.lbl : ''));
      return null;
    }}
    // G5Q.1u: skill-pack commands (gated on the pack being installed)
    if (/^export summary$/.test(t)) {{
      if (!packOn('graph-exporters')) return {{ s: 'unsupported', a: 'The Graph exporters pack is not installed — open Skills and press INSTALL PACK on "Skills registry / packs".' }};
      exportSummary(); return {{ s: 'answered', a: 'Graph summary downloaded as Markdown (graphify-summary.md).' }};
    }}
    if (/^copy stats$/.test(t)) {{
      if (!packOn('graph-exporters')) return {{ s: 'unsupported', a: 'The Graph exporters pack is not installed — open Skills and press INSTALL PACK on "Skills registry / packs".' }};
      const st = 'graph: ' + TOTALS.nodes + ' files / ' + TOTALS.edges + ' links / ' + TOTALS.clusters + ' clusters (' + ((projGet(PROJ) || {{}}).label || '?') + ')';
      try {{ navigator.clipboard.writeText(st); }} catch (e) {{}}
      return {{ s: 'answered', a: 'Copied: ' + st }};
    }}
    const mFind = t.match(/^(?:find|jump to|jump|go to|goto|locate|take me to|show me|open|navigate to|fly to|where is|where's)\\s+(.+)$/);
    if (mFind) {{                                        // G5P.1/G5Q.1i: local node lookup/jump (no LLM, no network)
      const raw = mFind[1].trim().replace(/^(?:the|a|an|node|file)\\s+/, '').replace(/\\s+(?:node|file|please)$/, '');
      const toks = raw.split(/\\s+/).filter(w => w.length > 2);
      const attempts = toks.length > 1 ? toks.slice().sort((x, y) => y.length - x.length) : [];
      try {{ iframe.contentWindow.postMessage({{ graphify: 'find-req', q: raw }}, '*'); }} catch (e) {{}}
      FIND_PENDING = {{ q, qq: raw, attempts, tried: [], via: null, timer: setTimeout(() => {{ if (FIND_PENDING) {{ renderResp(FIND_PENDING.q, 'The view did not answer the lookup (timeout).', 'error'); FIND_PENDING = null; }} }}, 1500) }};
      return null;                                       // async -- find-res retries word-by-word on miss
    }}
    if (/how many|node count|visible|count|edges|links/.test(t)) {{
      let a = 'Whole graph: ' + TOTALS.nodes + ' files · ' + TOTALS.edges + ' links · ' + TOTALS.clusters + ' clusters (structural read-model).';
      if (!mode3d && LAST_SLICE) {{ const total = Object.values(LAST_SLICE.counts).reduce((x, y) => x + y, 0); a += '\\nCurrent 2D slice "' + LAST_SLICE.slice + '": ' + total + ' member nodes.'; }}
      if (HIDDEN_CONCEPTS.size) a += '\\n' + HIDDEN_CONCEPTS.size + ' concept(s) are filtered out right now.';
      return {{ s: 'answered', a }};
    }}
    if (/jump|find|go to|take me|navigate|where is|fly to|show me|open/.test(t)) return {{ s: 'unsupported', a: 'That looks like a node search — the wired form is "find <name>" or "jump to <name>" (part of a file/folder name works best).\\n' + ctxLine() }};
    return {{ s: 'unsupported', a: UNSUPPORTED + '\\n' + ctxLine() + '\\nAsk "help" for the wired questions.' }};
  }};
  // G5Q.1l (operator-directed): the Claude Code lane ACTUALLY answers here.
  // One explicit ask = one bounded headless call via the local bridge; only
  // the read-only graphify server is exposed to it. Never automatic.
  let CC_BUSY = false, CC_ABORT = null;
  const setStops = show => ['ask-stop', 'cf-stop'].forEach(id => {{ const e = $(id); if (e) e.style.display = show ? '' : 'none'; }});
  const clearResponses = () => {{
    const body = $('resp-body');
    if (body) body.innerHTML = '<span class="dim" id="resp-placeholder">Ask about the graph below &mdash; answered locally from the structural read-model. Try: "find &lt;name&gt;", "what is selected?", "how many nodes?", "help".</span>';
    const th = $('cf-thread'); if (th) th.innerHTML = '';
    CHAT_HIST.length = 0;
    projLog('responses_cleared', {{}});
  }};
  if ($('ask-clr')) $('ask-clr').onclick = clearResponses;
  if ($('cf-clr')) $('cf-clr').onclick = clearResponses;
  const stopAsk = () => {{
    try {{ fetch('/api/claudecode/stop', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: '{{}}' }}); }} catch (e) {{}}
    if (CC_ABORT) CC_ABORT.abort();
  }};
  if ($('ask-stop')) $('ask-stop').onclick = stopAsk;
  if ($('cf-stop')) $('cf-stop').onclick = stopAsk;
  const askClaudeCode = q => {{
    if (CC_BUSY) {{ renderResp(q, 'Claude Code is still answering the previous ask — give it a moment.', 'unsupported'); return; }}
    CC_BUSY = true;
    renderResp(q, 'Asking your Claude Code… it reads the graph through the local server (usually 10–60 seconds).', 'pending');
    const myCard = $('resp-body').firstElementChild;
    const myMsg = CF_LAST;
    const finish = (text, status, extra) => {{
      CC_BUSY = false;
      if (myCard) {{
        myCard.querySelector('.rcard__a').textContent = text;
        const sEl = myCard.querySelector('.rcard__s'); sEl.textContent = status; sEl.className = 'rcard__s rcard__s--' + status;
        const tEl = myCard.querySelector('.rcard__t'); if (tEl) tEl.textContent = new Date().toTimeString().slice(0, 8) + ' · claude code' + (extra || '');
      }}
      if (myMsg) {{
        myMsg.childNodes[0].nodeValue = text;
        const meta = myMsg.querySelector('.cf-meta'); if (meta) meta.textContent = status.toUpperCase() + ' · claude code' + (extra || '');
        const th = $('cf-thread'); if (th) th.scrollTop = th.scrollHeight;
      }}
      askLog(q, status + '·claudecode', askCtx());
      setStops(false);
    }};
    setStops(true);
    CC_ABORT = new AbortController();
    fetch('/api/claudecode/ask', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, signal: CC_ABORT.signal, body: JSON.stringify((() => {{ const p = projGet(PROJ) || {{}}; return {{ q, projectId: p.isDefault ? null : PROJ, repoPath: p.repoPath || null, projectLabel: p.label || null }}; }})()) }})
      .then(r => r.json())
      .then(j => {{
        if (j.ok) {{
          // LIVE evidence is CURRENT-SESSION only: sessionStorage clears on browser
          // close, so a fresh browser can never show a stale LIVE from a prior run.
          try {{ const ev = JSON.stringify({{ ts: Date.now(), durationS: j.durationS }}); sessionStorage.setItem('graphify-cc-live-session', ev); localStorage.setItem('graphify-claudecode-live-v1', ev); }} catch (e) {{}}
          if (window.__paintConnLeds) window.__paintConnLeds();
          let text = j.answer;
          const mj = text.match(/^\\s*JUMP:\\s*(.+?)\\s*$/m);   // Claude names a node -> the camera goes there
          if (mj) {{
            text = text.replace(/^\\s*JUMP:.*$/m, '').trim();
            try {{ iframe.contentWindow.postMessage({{ graphify: 'find-req', q: mj[1] }}, '*'); }} catch (e) {{}}
          }}
          finish(text, 'answered', j.durationS ? ' · ' + j.durationS + 's' : '');
        }} else {{
          finish('Claude Code could not answer: ' + (j.reason || 'unknown'), 'error', '');
        }}
        if (window.__logEvent) window.__logEvent('claudecode_lane_ask', {{ ok: !!j.ok, durationS: j.durationS || null }});
      }})
      .catch(err => finish(err && err.name === 'AbortError'
        ? 'Stopped by you — the call was cancelled and no answer was used.'
        : 'The local bridge is not running — start it with python scripts/start_graphify_dashboard.py, then ask again.', err && err.name === 'AbortError' ? 'unsupported' : 'error', ''));
  }};
  // ---- G5Q.1u: full read-model loader + BFS helpers (all local) ----
  const RM_FULL = {{}};
  const loadFullRM = async () => {{
    const p = projGet(PROJ);
    if (!p || p.graphStatus !== 'ready') return null;
    if (RM_FULL[p.id]) return RM_FULL[p.id];
    try {{
      const rm = await (await fetch(readModelUrl(p))).json();
      const by = {{}}; (rm.nodes || []).forEach(n => {{ by[n.id] = n; }});
      const adj = {{}};
      (rm.edges || []).forEach(e => {{
        if (!by[e.source] || !by[e.target]) return;
        (adj[e.source] = adj[e.source] || []).push(e.target);
        (adj[e.target] = adj[e.target] || []).push(e.source);
      }});
      RM_FULL[p.id] = {{ by, adj, nodes: rm.nodes || [] }};
      return RM_FULL[p.id];
    }} catch (e) {{ return null; }}
  }};
  const rmBest = (g, query) => {{
    const qq = String(query || '').toLowerCase().trim();
    let best = null, bs = 0;
    for (const n of g.nodes) {{
      const lbl = String(n.label || '').toLowerCase(), nid = String(n.id || '').toLowerCase();
      let sc = 0;
      if (lbl === qq || nid === qq) sc = 3; else if (lbl.startsWith(qq)) sc = 2;
      else if (lbl.indexOf(qq) !== -1 || nid.indexOf(qq) !== -1) sc = 1;
      if (sc > bs || (sc === bs && sc > 0 && (n.degree || 0) > ((best || {{}}).degree || 0))) {{ best = n; bs = sc; }}
    }}
    return bs > 0 ? best : null;
  }};
  const lblOf = (g, id) => (g.by[id] || {{}}).label || id;
  const tracePath = (q, aq, bq) => {{
    loadFullRM().then(g => {{
      try {{
      if (!g) {{ renderResp(q, 'No graph loaded — load a project first.', 'unsupported'); return; }}
      const a = rmBest(g, aq), b = rmBest(g, bq);
      if (!a || !b) {{ renderResp(q, 'Could not match ' + (!a ? '"' + aq + '"' : '"' + bq + '"') + ' to a node — try part of a filename.', 'unsupported'); return; }}
      const prev = new Map(); prev.set(a.id, null);
      let frontier = [a.id], found = a.id === b.id, guard = 0;
      while (frontier.length && !found && guard < 60000) {{
        const next = [];
        for (const cur of frontier) {{
          for (const nb of (g.adj[cur] || [])) {{
            if (prev.has(nb)) continue;
            prev.set(nb, cur); guard++;
            if (nb === b.id) {{ found = true; break; }}
            next.push(nb);
          }}
          if (found) break;
        }}
        frontier = next;
      }}
      if (!found) {{ renderResp(q, 'No path: ' + a.label + ' and ' + b.label + ' are in disconnected parts of this view.', 'answered'); return; }}
      const path = [b.id]; let c = b.id, g2 = 0;
      while (prev.get(c) && g2++ < 10000) {{ c = prev.get(c); path.push(c); }}
      path.reverse();
      renderResp(q, 'Shortest path (' + (path.length - 1) + ' hops):\\n' + path.map(id => lblOf(g, id)).join('  →  ') + '\\nSay "jump to ' + b.label + '" to fly to the far end.', 'answered');
      }} catch (e) {{ renderResp(q, 'Path trace failed: ' + e.message, 'error'); }}
    }});
  }};
  const traceNode = (q, nq) => {{
    loadFullRM().then(g => {{
      if (!g) {{ renderResp(q, 'No graph loaded — load a project first.', 'unsupported'); return; }}
      const a = rmBest(g, nq);
      if (!a) {{ renderResp(q, 'Could not match "' + nq + '" to a node.', 'unsupported'); return; }}
      let seen = {{}}; seen[a.id] = true; let frontier = [a.id]; const lines = [];
      for (let d = 1; d <= 3; d++) {{
        const next = [];
        for (const cur of frontier) for (const nb of (g.adj[cur] || [])) if (!seen[nb]) {{ seen[nb] = true; next.push(nb); }}
        if (!next.length) break;
        const tops = next.map(id => g.by[id]).sort((x, y) => (y.degree || 0) - (x.degree || 0)).slice(0, 4).map(n => n.label).join(', ');
        lines.push('depth ' + d + ': ' + next.length + ' node(s) — ' + tops + (next.length > 4 ? ', …' : ''));
        frontier = next;
      }}
      renderResp(q, 'Trace from ' + a.label + ' (degree ' + (a.degree || 0) + '):\\n' + (lines.join('\\n') || 'no connections — orphan in this view.'), 'answered');
    }});
  }};
  const chainEnd = (q, nq) => {{
    loadFullRM().then(g => {{
      if (!g) {{ renderResp(q, 'No graph loaded — load a project first.', 'unsupported'); return; }}
      const a = nq ? rmBest(g, nq) : null;
      if (!a) {{ renderResp(q, 'Chain end needs a node — say "chain end <name>" or select a node first.', 'unsupported'); return; }}
      let cur = a.id, prev = null, hops = 0;
      while (hops < 200) {{
        const nbs = (g.adj[cur] || []).filter(x => x !== prev);
        if (nbs.length !== 1) break;
        prev = cur; cur = nbs[0]; hops++;
      }}
      const end = g.by[cur] || {{}};
      renderResp(q, hops === 0
        ? (a.label + ' is not on a single-link chain (it has ' + ((g.adj[a.id] || []).length) + ' connections).')
        : ('Chain end: ' + a.label + ' → ' + hops + ' hop(s) → ' + end.label + ' (degree ' + (end.degree || 0) + '). Say "jump to ' + end.label + '" to fly there.'), 'answered');
    }});
  }};
  // ---- G5Q.1u: minimal skill-pack registry (local, honest) ----
  const PACKS_KEY = 'graphify-packs-v1';
  const packOn = id => {{ try {{ return (JSON.parse(localStorage.getItem(PACKS_KEY) || '{{}}').installed || []).indexOf(id) !== -1; }} catch (e) {{ return false; }} }};
  const packToggle = id => {{
    let st; try {{ st = JSON.parse(localStorage.getItem(PACKS_KEY) || '{{}}'); }} catch (e) {{ st = {{}}; }}
    st.installed = st.installed || [];
    const i = st.installed.indexOf(id);
    if (i === -1) st.installed.push(id); else st.installed.splice(i, 1);
    try {{ localStorage.setItem(PACKS_KEY, JSON.stringify(st)); }} catch (e) {{}}
    projLog(i === -1 ? 'skillpack_installed' : 'skillpack_removed', {{ id }});
    return i === -1;
  }};
  window.__packToggle = packToggle; window.__packOn = packOn;
  const exportSummary = () => {{
    const p = projGet(PROJ) || {{}};
    const top = (RM_TOP_CACHE[p.id] || []).map((x, i) => (i + 1) + '. ' + x.lbl + ' — ' + x.deg + ' connections').join('\\n');
    const md = '# Graph summary — ' + (p.label || '?') + '\\n\\n' + TOTALS.nodes + ' files · ' + TOTALS.edges + ' links · ' + TOTALS.clusters + ' clusters\\n\\n## Most connected\\n' + (top || '(run a savings check or wait for the panel to compute)') + '\\n\\nGenerated locally by the GraphiQuest.';
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([md], {{ type: 'text/markdown' }}));
    a.download = 'graphify-summary.md';
    a.click();
    projLog('summary_exported', {{ id: p.id }});
  }};
  const submitAskQ = q => {{
    if (!projReady()) {{                               // G5P.2: honest per-project answers
      const p = projGet(PROJ) || {{}};
      const a = UNLOADED
        ? 'No graph is loaded — you unloaded the active graph. Click a project card (or RELOAD in the viewport) to load a graph, then ask again.'
        : p.graphStatus === 'repo_path_configured'
        ? 'Repo path is configured for ' + (p.label || '?') + ', but graph data has not been generated yet. Open Settings → Repositories and click RUN GRAPHIFY (or run graphify manually).'
        : 'No local graph data is loaded for ' + (p.label || '?') + ' (' + (PSTATUS[p.graphStatus] || p.graphStatus) + '). Open Settings → Repositories to connect a repo path, or run Graphify to generate graph data.';
      renderResp(q, a, 'unsupported');
      projLog('ask_blocked_no_graph', {{ id: PROJ, status: UNLOADED ? 'unloaded' : p.graphStatus }});
      return;
    }}
    const lane = document.querySelector('.lane.on');
    if (lane && lane.dataset.lane === 'claudecode') {{
      askClaudeCode(q);                                    // real answer renders right here
      return;
    }}
    const r = answerAsk(q);
    if (r) renderResp(q, r.a, r.s);
  }};
  const submitAsk = () => {{
    const inp = $('ask-in'), q = (inp.value || '').trim();
    if (!q) return;
    inp.value = '';
    submitAskQ(q);
  }};
  $('ask-go').onclick = submitAsk;
  $('ask-in').addEventListener('keydown', e => {{ if (e.key === 'Enter') submitAsk(); }});
  document.querySelectorAll('.lane:not(.dim)').forEach(b => b.onclick = () => {{
    const w = b.dataset.lane || 'graphify';
    document.querySelectorAll('.lane').forEach(x => x.classList.toggle('on', x.dataset.lane === w));
  }});
  // G5Q.1l chat flyout: same pipeline, bigger surface; CLOSE returns to compact
  const reOpen = $('resp-expand');
  if (reOpen) reOpen.onclick = () => {{
    document.body.classList.add('chatfly');
    const th = $('cf-thread'); if (th) th.scrollTop = th.scrollHeight;
    const i = $('cf-in'); if (i) i.focus();
    projLog('chat_flyout_opened', {{}});
  }};
  if ($('cf-close')) $('cf-close').onclick = () => document.body.classList.remove('chatfly');
  if ($('cf-in')) $('cf-in').addEventListener('keydown', e => {{
    if (e.key === 'Enter') {{ const q = ($('cf-in').value || '').trim(); if (!q) return; $('cf-in').value = ''; submitAskQ(q); }}
  }});
  // ==== G5P.9 HUNTER wiring: storage (capped), Reports UI, jump, gated enrich ====
  const HUNT_KEY = 'graphify-hunter-reports-v1';
  const huntAll = () => lsGet(HUNT_KEY, []);
  const huntSave = rep0 => {{
    const all = huntAll(); all.unshift(rep0);
    HUNT_OPEN = 0;                                       // G5Q.1t: a new run ARCHIVES the previous report -- newest is displayed
    let out = all.slice(0, 10);
    try {{ if (JSON.stringify(out).length > 200000) out = out.map((r, i) => i === 0 ? r : {{ ...r, findings: (r.findings || []).slice(0, 10), truncated: true }}); }} catch (e) {{}}
    lsSet(HUNT_KEY, out);
  }};
  const huntChip = sev => '<span class="hsev hsev--' + esc(sev) + '">' + esc(sev.toUpperCase()) + '</span>';
  const huntSummaryText = r => 'Hunter on ' + (r.projLbl || r.proj) + ' (' + new Date(r.ts).toLocaleString() + '): '
    + (r.findings || []).length + ' findings — ' + r.counts.high + ' high · ' + r.counts.medium + ' medium · '
    + r.counts.low + ' low · ' + r.counts.info + ' info. Local graph-only — no model call was made.';
  let HUNT_OPEN = 0;
  const renderHunt = () => {{
    const list = $('hunt-list'); if (!list) return;
    const all = huntAll();
    const ctxEl = $('hunt-ctx');
    if (ctxEl) {{ const p = projGet(PROJ) || {{}}; ctxEl.textContent = UNLOADED ? 'no graph loaded — load a project to run Hunter' : ('analyzes: ' + (p.label || PROJ) + ' (' + (PSTATUS[p.graphStatus] || p.graphStatus || '?') + ')'); }}
    const cntEl = $('hunt-count'); if (cntEl) cntEl.textContent = all.length + ' report(s) stored';
    const clrAll = $('hunt-clear-all');
    if (clrAll) clrAll.onclick = () => {{ if (!all.length) return; if (confirm('Clear ALL ' + all.length + ' Hunter report(s) from this browser?')) {{ lsSet(HUNT_KEY, []); HUNT_OPEN = 0; projLog('hunter_reports_cleared', {{ count: all.length }}); renderHunt(); }} }};
    if (!all.length) {{ list.innerHTML = '<p class="gmeta">no reports yet — RUN HUNTER creates the first one</p>'; const dd = $('hunt-detail'); if (dd) dd.innerHTML = ''; return; }}
    list.innerHTML = all.map((r, i) => '<div class="hrep' + (i === HUNT_OPEN ? ' hrep--on' : '') + '" data-i="' + i + '">'
      + '<b>' + esc(r.projLbl || r.proj) + '</b><span class="mono">' + esc(new Date(r.ts).toLocaleString()) + '</span>'
      + '<span class="hcounts">' + ['high', 'medium', 'low', 'info'].filter(k => r.counts[k]).map(k => huntChip(k) + '&nbsp;' + r.counts[k]).join(' ') + '</span>'
      + (i > 0 ? '<span class="st st--plan">ARCHIVED</span>' : '')
      + '<span class="st ' + (r.status === 'complete' ? 'st--imp' : 'st--plan') + '">' + esc((r.status === 'complete' ? 'local graph-only' : r.status).toUpperCase()) + '</span>'
      + '</div>').join('');
    list.querySelectorAll('.hrep').forEach(el => el.onclick = () => {{ HUNT_OPEN = +el.dataset.i; renderHunt(); }});
    renderHuntDetail(HUNT_OPEN);
  }};
  window.__renderHunt = () => renderHunt();
  const renderHuntDetail = i => {{
    const box = $('hunt-detail'); if (!box) return;
    const r = huntAll()[i]; if (!r) {{ box.innerHTML = ''; return; }}
    const hHead = '<div class="hth"><span>FINDING</span><span>GRAPH EVIDENCE</span><span>RECOMMENDED ACTION</span><span></span></div>';
    const rows = (r.findings || []).map((f, fi) => '<div class="htr">'
      + '<div class="htc">' + huntChip(f.sev) + ' <span class="hkind">' + esc(f.kind) + '</span><div class="htt">' + esc(f.title) + '</div></div>'
      + '<div class="htc">' + esc(f.evidence) + '</div>'
      + '<div class="htc">&rarr; ' + esc(f.action) + ' <span class="mono" style="opacity:.7">(' + esc(f.confidence) + ')</span></div>'
      + '<div class="htc htc-act">' + (f.clickable ? '<button class="rbtn hunt-jump" data-fi="' + fi + '" style="margin-top:0" title="' + (f.in3d === false ? 'low-degree target — opens in the 2D explorer' : 'jump to the node in the graph') + '">JUMP</button>' : '<span class="gmeta" style="margin:0">no target</span>')
      + '</div></div>').join('');
    box.innerHTML = '<h3 style="margin-top:18px">Report — ' + esc(r.projLbl || r.proj) + ' <span class="mono" style="font-weight:400">' + esc(r.id) + (r.graphSource ? ' · source ' + esc(r.graphSource) : '') + '</span></h3>'
      + '<div class="gcard" style="max-width:880px"><p class="gmeta" style="margin-top:0">' + esc(huntSummaryText(r)) + (r.truncated ? ' (stored copy truncated)' : '') + '</p>'
      + '<div style="display:flex;gap:8px;flex-wrap:wrap;margin:4px 0 10px">'
      + '<button class="rbtn hunt-enrich" data-c="claudecode" style="margin-top:0">ENRICH WITH CLAUDE CODE</button>'
      + '<button class="rbtn hunt-copy" style="margin-top:0">COPY REPORT JSON</button>'
      + '<button class="rbtn hunt-del" style="margin-top:0;border-color:rgba(248,113,113,.45);color:#f87171">DELETE REPORT</button>'
      + '<span class="gmeta" id="hunt-gate-note" style="margin:0;align-self:center">no call was made</span></div>'
      + (rows ? hHead + rows : '<p class="gmeta">no findings — the graph looks fully connected at this view</p>')
      + ((r.recommendations || []).length ? '<h3 style="margin:14px 0 6px;grid-column:1/-1">Claude recommendations <span class="mono" style="font-weight:400">(verified with the graph tools — silver-platter / grill-me / guess-what)</span></h3>'
        + '<div class="hth"><span>RECOMMENDATION</span><span>WHY (VERIFIED)</span><span>DO THIS</span><span></span></div>'
        + r.recommendations.map((c, ci) => '<div class="htr">'
          + '<div class="htc">' + huntChip(c.confidence === 'high' ? 'high' : c.confidence === 'medium' ? 'medium' : 'low') + '<div class="htt">' + esc(c.title) + '</div></div>'
          + '<div class="htc">' + esc(c.why) + '</div>'
          + '<div class="htc">&rarr; ' + esc(c.action) + '</div>'
          + '<div class="htc htc-act">' + ((c.nodeIds || []).length ? '<button class="rbtn rec-jump" data-ci="' + ci + '" style="margin-top:0" title="jump to the node in the 3D hivemind">JUMP</button>' : '<span class="gmeta" style="margin:0">no target</span>')
          + '</div></div>').join('') : '')
      + '</div>';
    const cp = box.querySelector('.hunt-copy');
    if (cp) cp.onclick = () => {{ try {{ navigator.clipboard.writeText(JSON.stringify(r, null, 2)); cp.textContent = 'COPIED'; setTimeout(() => cp.textContent = 'COPY REPORT JSON', 1200); }} catch (e) {{}} }};
    const dl = box.querySelector('.hunt-del');
    if (dl) dl.onclick = () => {{ const all = huntAll(); all.splice(i, 1); lsSet(HUNT_KEY, all); HUNT_OPEN = 0; projLog('hunter_report_deleted', {{}}); renderHunt(); }};
    box.querySelectorAll('.hunt-jump').forEach(btn => btn.onclick = () => openFinding(i, +btn.dataset.fi));
    box.querySelectorAll('.rec-jump').forEach(btn => btn.onclick = () => {{
      const c = (r.recommendations || [])[+btn.dataset.ci];
      if (!c || !(c.nodeIds || []).length) return;
      const nid = c.nodeIds[0];
      // low-degree/orphan targets only render in the 2D explorer -- inherit
      // the source finding's in3d flag (same logic as openFinding)
      const src = (r.findings || []).find(f => (f.nodeIds || []).indexOf(nid) !== -1);
      const go2d = src && src.in3d === false && mode3d;
      if (go2d) $('pv2d').click();
      projLog('recommendation_jump', {{ report: r.id, title: c.title }});
      if (window.__openSection) window.__openSection('graph');
      setTimeout(() => {{ try {{ iframe.contentWindow.postMessage({{ graphify: 'find-req', q: nid }}, '*'); }} catch (e) {{}} }}, go2d ? 1800 : 350);
    }});
    box.querySelectorAll('.hunt-enrich').forEach(btn => btn.onclick = async () => {{
      // G5Q.1m: REAL enrichment -- one bounded Claude Code call per click.
      const note = $('hunt-gate-note');
      btn.disabled = true; btn.textContent = 'ASKING CLAUDE CODE…';
      if (note) note.textContent = 'one real call — Claude verifies the findings with the graph tools (10–90s)';
      try {{
        const res = await fetch('/api/claudecode/enrich', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ report: r }}) }});
        const j = await res.json();
        if (j.ok) {{
          const all = huntAll();
          if (all[i]) {{ all[i].recommendations = j.recommendations; all[i].enriched = true; lsSet(HUNT_KEY, all); }}
          projLog('hunter_enriched', {{ report: r.id, count: (j.recommendations || []).length, durationS: j.durationS }});
          renderHunt();
        }} else {{
          btn.disabled = false; btn.textContent = 'ENRICH WITH CLAUDE CODE';
          if (note) note.textContent = 'could not enrich: ' + (j.reason || 'unknown') + (/(not registered|not on PATH)/.test(j.reason || '') ? ' — click the CLAUDE CODE pill to set it up' : '');
        }}
      }} catch (e) {{
        btn.disabled = false; btn.textContent = 'ENRICH WITH CLAUDE CODE';
        if (note) note.textContent = 'local bridge offline — start it with python scripts/start_graphify_dashboard.py';
      }}
    }});
  }};
  const openFinding = (ri, fi) => {{
    const r = huntAll()[ri]; if (!r) return;
    const f = (r.findings || [])[fi]; if (!f || !f.nodeIds || !f.nodeIds.length) return;
    projLog('report_finding_opened', {{ report: r.id, finding: f.id, kind: f.kind }});
    const switching = r.proj !== PROJ;
    if (switching) {{
      const p = projGet(r.proj);
      if (!p || p.graphStatus !== 'ready') {{ const note = $('hunt-gate-note'); if (note) note.textContent = 'project "' + (p ? p.label : r.proj) + '" is not ready anymore — rebuild it first'; return; }}
      selectProject(r.proj);
    }}
    if (f.in3d === false && mode3d) $('pv2d').click();   // low-degree targets render in the 2D explorer
    if (window.__openSection) window.__openSection('graph');
    setTimeout(() => {{ try {{ iframe.contentWindow.postMessage({{ graphify: 'find-req', q: f.nodeIds[0] }}, '*'); }} catch (e) {{}} }},
      (switching || f.in3d === false) ? 1800 : 350);
  }};
  const runHunter = async () => {{
    const p = projGet(PROJ) || {{}};
    projLog('hunter_run_started', {{ id: PROJ, status: p.graphStatus }});
    const base = {{ id: 'hunt-' + Date.now().toString(36), ts: new Date().toISOString(), proj: PROJ, projLbl: p.label, enriched: false }};
    if (UNLOADED || p.graphStatus !== 'ready') {{
      const reason = UNLOADED ? 'no graph loaded (you unloaded it)' : (PSTATUS[p.graphStatus] || p.graphStatus || 'unknown');
      huntSave({{ ...base, status: 'no-graph', graphSource: null, counts: {{ high: 0, medium: 1, low: 0, info: 0 }},
        findings: [{{ id: 'f1', sev: 'medium', kind: 'incomplete-project', title: 'No graph to audit — ' + reason,
          nodeIds: [], evidence: 'graph evidence: the selected project has no ready graph (status: ' + reason + '). No analysis ran.',
          action: 'Open Settings → Repositories and RUN GRAPHIFY (or fix the listed status), then run Hunter again.',
          confidence: 'high', clickable: false, localOnly: true }}] }});
      HUNT_OPEN = 0; renderHunt();
      projLog('hunter_blocked_no_graph', {{ id: PROJ, status: p.graphStatus }});
      return;
    }}
    let rm = null;
    try {{ rm = await (await fetch(readModelUrl(p))).json(); }} catch (e) {{}}
    if (!rm || !window.__huntAnalyze) {{
      huntSave({{ ...base, status: 'error', graphSource: readModelUrl(p), counts: {{ high: 0, medium: 1, low: 0, info: 0 }},
        findings: [{{ id: 'f1', sev: 'medium', kind: 'incomplete-project', title: 'Graph data could not be loaded',
          nodeIds: [], evidence: 'the read-model fetch failed — the local server may not be running.',
          action: 'Start it: python scripts/start_graphify_dashboard.py — then run Hunter again.',
          confidence: 'high', clickable: false, localOnly: true }}] }});
      HUNT_OPEN = 0; renderHunt(); return;
    }}
    const res = window.__huntAnalyze(rm, {{ scan: SCAN[PROJ] || {{}} }});
    const sc = SCAN[PROJ] || {{}};
    if (['rebuild_required', 'views_missing', 'generated_pending_reload'].includes(sc.status))
      res.findings.unshift({{ id: 'f0', sev: 'medium', kind: 'stale', title: 'Graph outputs are stale (' + sc.status + ')',
        nodeIds: [], evidence: 'the bridge scan reports ' + sc.status + ' — this report may describe an older build.',
        action: 'REBUILD in Settings → Repositories, then run Hunter again.', confidence: 'high', clickable: false, localOnly: true }});
    const cts = {{ high: 0, medium: 0, low: 0, info: 0 }};
    res.findings.forEach(f => cts[f.sev] = (cts[f.sev] || 0) + 1);
    huntSave({{ ...base, status: 'complete', graphSource: readModelUrl(p), sliceMode: (rm.metadata || {{}}).slice_mode,
      counts: cts, findings: res.findings.slice(0, 60), truncated: res.findings.length > 60 }});
    HUNT_OPEN = 0; renderHunt();
    projLog('hunter_report_created', {{ id: base.id, proj: PROJ, findings: Math.min(res.findings.length, 60) }});
  }};
  window.__runHunter = runHunter;
  const huntBtn = $('hunt-run'); if (huntBtn) huntBtn.onclick = runHunter;
  // ==== G5Q.1e Graphify Context Savings (honest chars/4 ESTIMATE) ====
  const SAVINGS_KEY = 'graphify-savings-v1';
  const TOK = n => Math.round((n || 0) / 4);                 // documented estimator: chars / 4
  const fmtTok = n => n >= 1000 ? (n / 1000).toFixed(n >= 10000 ? 0 : 1) + 'k' : String(n);
  const savingsHistory = () => lsGet(SAVINGS_KEY, []);
  const paintSavings = () => {{
    const last = savingsHistory()[0];
    const set = (id, v) => {{ const el = $(id); if (el) el.textContent = v; }};
    if (last) {{
      set('sv-pct', last.pct + '%'); set('sv-status', last.measured ? 'measured' : 'estimated');
      set('sv-claude', fmtTok(last.claudeOnly) + ' tok'); set('sv-graphify', fmtTok(last.graphify) + ' tok');
      set('sv-last2', 'last: ' + last.pct + '% saved on ' + (last.projLbl || last.proj) + ' (' + (last.measured ? 'measured' : 'estimated') + ' · ' + new Date(last.ts).toLocaleString() + ')');
    }} else {{
      set('sv-pct', '\u2014'); set('sv-status', 'not run'); set('sv-claude', '\u2014'); set('sv-graphify', '\u2014');
      set('sv-last2', 'no check run yet in this browser');
    }}
  }};
  window.__paintSavings = paintSavings;
  const runSavingsCheck = async () => {{
    const p = projGet(PROJ);
    if (UNLOADED || !p || p.graphStatus !== 'ready') {{
      renderResp('Run savings check', 'Load or graph a project first \u2014 savings are computed from a loaded project graph.', 'unsupported');
      return null;
    }}
    const query = 'What files are most connected and what should I inspect first?';
    let raw, rm;
    try {{ raw = await (await fetch(readModelUrl(p))).text(); rm = JSON.parse(raw); }}
    catch (e) {{ renderResp('Run savings check', 'Could not load the graph data \u2014 the local server may not be running.', 'error'); return null; }}
    const nodes = (rm.nodes || []).slice().sort((a, b) => (b.degree || 0) - (a.degree || 0));
    const top = nodes.slice(0, 25).map(n => ({{ label: n.label, file_path: n.file_path, concept: n.concept, degree: n.degree }}));
    const concepts = {{}}; (rm.nodes || []).forEach(n => concepts[n.concept] = (concepts[n.concept] || 0) + 1);
    const slices = (rm.slices || []).map(sl => ({{ label: sl.label, node_count: sl.node_count }}));
    const topId = (nodes[0] || {{}}).id;
    const nbr = (rm.edges || []).filter(e => e.source === topId || e.target === topId).slice(0, 20).map(e => e.source === topId ? e.target : e.source);
    const hunter = huntAll().find(r => r.proj === PROJ && r.status === 'complete');
    const payload = {{ query, project: p.label,
      totals: {{ nodes: (rm.metadata || {{}}).emitted_nodes, edges: (rm.metadata || {{}}).emitted_edges, slices: (rm.slices || []).length }},
      concepts, slices, topFiles: top, topNodeNeighbors: nbr, hunterSummary: hunter ? hunter.counts : null }};
    const claudeOnly = TOK((raw || '').length), graphify = TOK(JSON.stringify(payload).length);
    const pct = claudeOnly > 0 ? Math.round((claudeOnly - graphify) / claudeOnly * 1000) / 10 : 0;
    const result = {{ ts: new Date().toISOString(), proj: PROJ, projLbl: p.label, query, claudeOnly, graphify, pct,
      measured: false, method: 'chars/4 estimate; baseline=full read-model, graphify=targeted query payload' }};
    const h = savingsHistory(); h.unshift(result); lsSet(SAVINGS_KEY, h.slice(0, 20));
    projLog('savings_check_run', {{ id: PROJ, query, claudeOnly, graphify, pct }});
    paintSavings();
    renderResp('Run savings check',
      'Estimated token savings on ' + p.label + ': ' + pct + '%.\\n'
      + 'Claude-only (full structural context): ~' + fmtTok(claudeOnly) + ' tokens.\\n'
      + 'Graphify-assisted (targeted query): ~' + fmtTok(graphify) + ' tokens.\\n'
      + 'Estimate (chars/4) \u2014 measured Claude-token mode is gated until a connector is set up.', 'answered');
    return result;
  }};
  window.__runSavings = runSavingsCheck;
  window.__skillAction = act => {{
    if (act === 'run-hunter') {{ if (window.__openSection) window.__openSection('reports'); runHunter(); }}
    else if (act === 'run-savings') {{ if (window.__openConnector) window.__openConnector('set-savings'); runSavingsCheck(); }}
  }};
  const svB1 = $('sv-run'); if (svB1) svB1.onclick = runSavingsCheck;
  const svB2 = $('sv-run2'); if (svB2) svB2.onclick = runSavingsCheck;
  paintSavings();
  const skillHuntBtn = $('skill-hunt-run');
  if (skillHuntBtn) skillHuntBtn.onclick = () => {{ if (window.__openSection) window.__openSection('reports'); runHunter(); }};
  renderHunt();
  function renderSel(n) {{
    const el = $('selnode'), an = $('ask-node'), card = $('selcard');
    if (an) {{ an.textContent = n ? n.lbl : 'no node selected'; an.classList.toggle('live', !!n); }}
    if (card) card.classList.toggle('live', !!n);
    if (!n) {{ el.innerHTML = '<span class="dim">none — click a node in the 3D or 2D view</span>'; return; }}
    el.innerHTML = '<div class="sn-l">' + esc(n.lbl) + '</div>'
      + '<div class="sn-p">' + esc(n.fp) + '</div>'
      + '<div class="sn-row"><span>region</span><b>' + esc(n.reg) + '</b></div>'
      + '<div class="sn-row"><span>degree</span><b>' + esc(n.deg) + '</b></div>'
      + '<div class="sn-row"><span>direct neighbors</span><b>' + esc(n.nb) + '</b></div>'
      + '<div class="sn-hint">inspect (planned): ' + esc(n.fp) + '</div>';
  }}
}})();
{SHELL_JS}
</script>
</body></html>
"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(page, encoding="utf-8")
print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB) | {C['nodes']} nodes / {C['edges']} edges / {C['slices']} slices | built_at {C['built_at']}")
