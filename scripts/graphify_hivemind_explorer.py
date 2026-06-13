#!/usr/bin/env python3
"""Local Graphify/Hivemind explorer generator (Mission G3).

Consumes the compact G2 read model (graphify-out/hivemind/read-model.json -- NOT the raw
graph.json) and emits ONE self-contained local HTML explorer to the gitignored path
graphify-out/views/graph-explorer.html. No CDN, no dependencies, file:// friendly.

Features: slice selector (8 G2 slices), search (label/path/concept), node inspector
(1-hop/2-hop/copy path, slice memberships), neighborhood isolation with hidden counts,
shortest-path tracing with readable path list, concept filters + hide-tests/generated/
low-degree toggles, metadata + standing warnings banner (Graphify first / repo truth
second; runtime truth not inferred), hash params for deterministic checks:
  #slice=<id>   #select=<query>   #trace=<query>=><query>

Usage:
  python scripts/graphify_hivemind_explorer.py
  python scripts/graphify_hivemind_explorer.py --read-model graphify-out/hivemind/read-model.json \
      --out graphify-out/views/graph-explorer.html --fixed-time 2026-06-09T00:00:00+00:00
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

DEFAULT_READ_MODEL = Path("graphify-out") / "hivemind" / "read-model.json"
DEFAULT_OUT = Path("graphify-out") / "views" / "graph-explorer.html"

# Optional LOCAL view taxonomy (gitignored; NEVER shipped). The published view
# uses generic, repo-agnostic regions/presets (derived from the read model's
# concepts + directories). A maintainer can overlay custom presets/regions/
# routes for their own repo via graphiquest.taxonomy.local.json.
try:
    from graphify_taxonomy_config import load_local_taxonomy
except ImportError:
    def load_local_taxonomy() -> Dict[str, Any]:  # type: ignore
        return {}


def _view_taxonomy_json() -> str:
    """JSON for the optional local view taxonomy (presets/regions/region_routes),
    or 'null' when no local config is present (the shipped default)."""
    cfg = load_local_taxonomy()
    keys = {k: cfg[k] for k in ("presets", "regions", "region_routes") if k in cfg}
    return json.dumps(keys, separators=(",", ":")) if keys else "null"


def load_read_model(path: Path) -> Dict[str, Any]:
    """Load the G2 read model JSON. Raises FileNotFoundError if absent."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def render_html(model: Dict[str, Any], generated_at: str) -> str:
    """Render the self-contained explorer HTML around the embedded read model."""
    data = json.dumps(model, separators=(",", ":"), sort_keys=True).replace("</", "<\\/")
    page = _TEMPLATE.replace("__GENERATED_AT__", generated_at)
    page = page.replace("__TAXONOMY__", _view_taxonomy_json())
    return page.replace("__DATA__", data)


def write_explorer(model: Dict[str, Any], out_path: Path, generated_at: str) -> Path:
    """Write the explorer HTML; creates the output directory. Returns the path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    html = render_html(model, generated_at)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    return out_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Graphify/Hivemind local explorer generator (G3)")
    ap.add_argument("--read-model", default=str(DEFAULT_READ_MODEL))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--fixed-time", default=None,
                    help="ISO timestamp for deterministic output (tests/diffing)")
    args = ap.parse_args(argv)

    rm_path = Path(args.read_model)
    if not rm_path.exists():
        print(f"[graphify-hivemind-explorer] read model not found: {rm_path}")
        print("Run `python scripts/graphify_hivemind_readmodel.py` first (or pass --read-model).")
        return 1

    model = load_read_model(rm_path)
    generated_at = args.fixed_time or datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = write_explorer(model, Path(args.out), generated_at)

    md = model.get("metadata", {})
    print("[graphify-hivemind-explorer] OK")
    print(f"  read model : {rm_path} ({md.get('emitted_nodes', '?')} nodes / "
          f"{md.get('emitted_edges', '?')} edges, {len(model.get('slices', []))} slices)")
    print(f"  build mode : {md.get('graph_build_mode', '?')}")
    print(f"  built at   : {md.get('graph_built_at_commit', '?')}")
    print(f"  output     : {out}  (gitignored; never commit)")
    print(f"  open with  : start {out}")
    return 0


# ---------------------------------------------------------------------------
# Self-contained template (no CDN; data + app inline). Placeholders:
#   __GENERATED_AT__   __DATA__
# ---------------------------------------------------------------------------
_TEMPLATE = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Graphify Hivemind Explorer</title>
<style>
 html,body{margin:0;height:100%;background:#060709;color:#d8d8de;font:13px/1.45 system-ui,'Segoe UI',sans-serif;overflow:hidden}
 #top{position:fixed;top:0;left:0;right:0;z-index:5;background:#15151bee;border-bottom:1px solid #26262e;padding:6px 10px}
 #top b{color:#fff;font-size:14px}
 #slices{display:flex;flex-wrap:wrap;gap:4px;margin-top:5px}
 .pb{background:#23232c;border:1px solid #34343f;color:#cfcfd8;border-radius:6px;padding:3px 9px;cursor:pointer;font-size:12px}
 .pb:hover{background:#2e2e3a}.pb.active{background:#3c5a86;border-color:#5a82b8;color:#fff}
 #meta{color:#9a9aa5;font-size:11px;margin-top:4px}
 #warn{color:#e8c468;font-size:11px;margin-top:2px}
 #left{position:fixed;top:96px;left:8px;bottom:8px;width:260px;z-index:4;background:#15151bee;border:1px solid #26262e;border-radius:10px;padding:10px;overflow-y:auto}
 #right{position:fixed;top:96px;right:8px;bottom:8px;width:300px;z-index:4;background:#15151bee;border:1px solid #26262e;border-radius:10px;padding:10px;overflow-y:auto;display:none}
 h4{margin:10px 0 5px;color:#bdbdc8;font-size:12px;text-transform:uppercase;letter-spacing:.06em}
 input[type=text]{width:100%;box-sizing:border-box;background:#0e0e12;border:1px solid #34343f;color:#e8e8ee;border-radius:6px;padding:5px 8px;font-size:12px}
 .res{padding:4px 6px;border-radius:6px;cursor:pointer;border:1px solid transparent;margin:1px 0;font-size:12px}
 .res:hover{background:#23232c;border-color:#34343f}
 .res .p{color:#8d8d98;font-size:10.5px;word-break:break-all}
 .dot{display:inline-block;width:8px;height:8px;border-radius:3px;margin-right:5px;vertical-align:1px}
 label.g{display:flex;align-items:center;gap:6px;margin:2px 0;font-size:12px;cursor:pointer}
 label.g input{accent-color:#5a82b8}
 .muted{color:#77777f;font-size:11px}
 button.act{background:#23232c;border:1px solid #34343f;color:#cfcfd8;border-radius:6px;padding:4px 8px;cursor:pointer;font-size:12px;margin:2px 4px 2px 0}
 button.act:hover{background:#2e2e3a}
 #insp .fld{margin:3px 0}#insp .path{word-break:break-all;color:#a9c4e8;font-size:11.5px}
 #tip{position:fixed;pointer-events:none;background:#000d;border:1px solid #3a3a44;border-radius:6px;padding:5px 8px;font-size:12px;display:none;z-index:7;max-width:430px}
 #note{position:fixed;left:284px;bottom:8px;color:#6b6b75;font-size:11px;z-index:3}
 #banner{background:transparent;border:none;color:#6b7280;border-radius:0;padding:0;margin-left:8px;font-weight:500;font-size:10px;letter-spacing:.06em;display:inline-block}
 .chip{display:inline-block;background:#23232c;border:1px solid #34343f;border-radius:10px;padding:1px 8px;margin-left:6px;font-size:11px;color:#e8a0a0}
 .gh{color:#9fb6d4;font-size:11px;text-transform:uppercase;letter-spacing:.05em;margin:6px 0 2px}
 /* ---- #embed mode (G5K): dashboard-native skin; activated by hash token 'embed' ---- */
 body.embed{background:#020203;font-family:Inter,system-ui,'Segoe UI',sans-serif}
 body.embed #top{background:rgba(10,10,10,.72);border-bottom:1px solid rgba(255,138,56,.28);box-shadow:inset 0 1px 0 rgba(255,255,255,.08);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}
 body.embed #top>b,body.embed #meta,body.embed #warn,body.embed #note{display:none}
 body.embed #presets,body.embed #brainPresets{display:none !important}  /* G5L dedupe (G5M: !important beats the inline display:flex) */
 body.embed #brainWarn{display:none}
 /* G5O.2h: slice chips are a first-class top row (operator) -- round pills matching
    the Brain 3D / 2D Explorer / Tools capsules, centered in the header panel */
 body.embed #slices{display:flex !important;justify-content:center;flex-wrap:wrap;gap:5px;margin-top:6px}
 body.embed #slices .pb{border-radius:9999px;padding:4px 13px;font-size:12px;line-height:1.1}
 body.embed #left #modeBtns{display:flex;gap:4px;margin:0 0 8px}  /* G5O.2g: view-mode toggle lives in the drawer (operator: the switch was lost) */
 body.embed #left #modeBtns .pb{flex:none;padding:3px 9px;font-size:11.5px;line-height:1}
 body.embed #conceptsHdr,body.embed #concepts{display:none}  /* G5O.0: Concepts lives on the dashboard right panel (no duplication) */
 body.embed #smode{display:flex;gap:4px;align-items:center}  /* G5O.2d: kills whitespace-gap raggedness */
 body.embed #smode .pb{flex:none;padding:3px 9px;font-size:11.5px;line-height:1}
 #sliceSel{display:none}
 body.embed #sliceSel{display:block;width:100%;margin:4px 0 8px}
 body.embed #top{padding:5px 10px}
 body.embed input[type=text]{background:rgba(0,0,0,.45);border:1px solid rgba(255,255,255,.1);color:#f0ede8;border-radius:9999px;padding:5px 11px}
 body.embed h4{color:#c8935a;letter-spacing:.08em}
 body.embed button.act{background:linear-gradient(180deg,rgba(34,26,16,.6),rgba(12,13,16,.6));border:1px solid rgba(255,138,56,.26);color:#ded7cd;border-radius:9999px}
 body.embed button.act:hover{border-color:rgba(255,138,56,.5)}
 body.embed #mm,body.embed #mmBrain{background:rgba(20,16,10,.5);border:1px solid rgba(255,138,56,.22);border-radius:10px}
 body.embed .res:hover{background:rgba(40,30,18,.5);border-color:rgba(255,138,56,.3)}
 body.embed select{background:rgba(0,0,0,.55);border:1px solid rgba(255,255,255,.12);color:#f0ede8;border-radius:8px;padding:3px 7px}
 body.embed select option{background:#0b0c10;color:#e8e8ee}  /* G5O.2h: black drop menu (native list cannot blur, color matches the glass system) */
 body.embed label.g input{accent-color:#ff7a18}
 body.embed h4,body.embed .gh{color:#c8935a}
 body.embed #left,body.embed #right{bottom:54px}  /* G5O.2f: inspector matches the search drawer extent (operator: heights must align) */
 body.embed #drawerBtn{z-index:8}
 body.embed #banner{color:#ffae3c;border:1px solid rgba(255,138,56,.4);border-radius:9999px;padding:4px 13px;font:600 12px Inter,system-ui,sans-serif;letter-spacing:.04em;background:linear-gradient(180deg,rgba(60,30,8,.45),rgba(26,13,3,.5));box-shadow:inset 0 1px 0 rgba(255,210,160,.16)}  /* G5O.2h: matches the top pill capsules */
 body.embed .pb{background:linear-gradient(180deg,rgba(34,26,16,.6),rgba(12,13,16,.6));border:1px solid rgba(255,138,56,.26);color:#ded7cd;border-radius:4px;padding:5px 12px;font-size:12.5px;box-shadow:inset 0 1px 0 rgba(255,255,255,.12)}
 body.embed .pb:hover{background:rgba(40,30,18,.7);border-color:rgba(255,138,56,.5)}
 body.embed .pb.active{background:rgba(255,122,24,.12);border-color:#ff7a18;color:#ffae3c}
 body.embed #left,body.embed #right{background:rgba(10,11,14,.82);border:1px solid rgba(255,138,56,.28);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px)}
 body.embed #left{display:none}
 body.embed.drawer-open #left{display:block}
 body.embed #counts{font-family:'JetBrains Mono',Consolas,monospace}
 #drawerBtn{display:none}
 body.embed #drawerBtn{display:block;position:fixed;left:10px;bottom:10px;z-index:6;background:linear-gradient(180deg,rgba(44,32,18,.7),rgba(12,13,16,.7));border:1px solid rgba(255,138,56,.4);color:#ffae3c;border-radius:9999px;padding:6px 16px;font:600 12px Inter,system-ui;cursor:pointer;box-shadow:inset 0 1px 0 rgba(255,210,160,.2)}
 #mm{background:#101820;border:1px solid #24364a;border-radius:8px;padding:8px;margin-top:6px;font-size:12px}
 #mm ol{margin:4px 0 4px 18px;padding:0}
 select{background:#0e0e12;border:1px solid #34343f;color:#e8e8ee;border-radius:6px;padding:3px 6px;font-size:12px}
 canvas{display:block}
 ::-webkit-scrollbar{width:8px}::-webkit-scrollbar-thumb{background:#2c2c36;border-radius:4px}
</style></head><body>
<canvas id="cv"></canvas>
<div id="top">
 <b>Graphify Hivemind Explorer</b>
 <span style="margin-left:8px" id="modeBtns"><button class="pb active" id="modeGraph">Structural Graph Mode</button><button class="pb" id="modeBrain">Brain Mode</button></span>
 <span id="banner">STRUCTURAL GRAPH ONLY &mdash; NOT RUNTIME TRUTH</span> <span class="muted" id="counts"></span>
 <div id="presets" style="display:flex;flex-wrap:wrap;gap:4px;margin-top:5px"></div>
 <div id="brainPresets" style="display:none;flex-wrap:wrap;gap:4px;margin-top:5px"></div>
 <div id="slices"></div>
 <div id="meta"></div>
 <div id="warn"></div>
 <div id="brainWarn" style="display:none;color:#e8c468;font-size:11px;margin-top:2px">Brain Mode is a metaphorical structural map. It is not runtime truth. Disconnected nodes are review signals, not automatic defects.</div>
</div>
<div id="left">
 <h4>Search</h4>
 <div id="smode"><span class="pb active" data-m="label">label</span> <span class="pb" data-m="path">path</span> <span class="pb" data-m="concept">concept</span></div>
 <input type="text" id="q" placeholder="search nodes..."/>
 <div id="results"></div>
 <h4>Shortest path</h4>
 <input type="text" id="src" placeholder="source..."/><div id="srcR"></div>
 <input type="text" id="dst" placeholder="target..." style="margin-top:4px"/><div id="dstR"></div>
 <div><button class="act" id="traceBtn">Trace</button><button class="act" id="traceClr">Clear</button><button class="act" id="copyPath" style="display:none">Copy path</button></div>
 <div id="traceOut" class="muted"></div>
 <h4>Mission Mode</h4>
 <select id="sliceSel" title="mission area / slice"></select>
 <div id="mm">
  <b>Start with Graphify</b>
  <ol><li>Pick a preset / slice for the mission area.</li><li>Search or trace the structures involved.</li><li><b>Repo truth required:</b> verify every load-bearing claim with Read/Grep before editing.</li></ol>
  <div class="gh">Suggested for this preset</div>
  <div id="mmHints" class="muted">(pick a preset)</div>
  <div class="gh">Prompt snippet</div>
  <div class="muted" id="mmSnippet">Use Graphify first for structural context, then verify load-bearing claims with Read/Grep before editing.</div>
  <button class="act" id="copySnippet">Copy prompt snippet</button><span class="muted" id="mmMsg"></span>
 </div>
 <h4>Density</h4>
 <label class="g">labels <select id="labelDensity"><option value="12" selected>low</option><option value="26">medium</option><option value="60">high</option></select></label>
 <label class="g"><input type="checkbox" id="edgesOn" checked/>show edges</label>
 <label class="g">max nodes <select id="maxNodes"><option>200</option><option selected>400</option><option>800</option></select></label>
 <h4>Filters</h4>
 <label class="g"><input type="checkbox" id="hideTests" checked/>hide tests</label>
 <label class="g"><input type="checkbox" id="hideGen" checked/>hide generated/unknown</label>
 <label class="g"><input type="checkbox" id="hideDocs"/>hide docs</label>
 <label class="g"><input type="checkbox" id="hideLow"/>hide degree&le;1</label>
 <h4>Share</h4>
 <div><button class="act" id="copyView">Copy view link</button><button class="act" id="copyNodes">Copy visible nodes (JSON)</button></div>
 <div class="muted" id="shareMsg"></div>
 <div id="brainPanel" style="display:none">
  <h4>Connectedness</h4>
  <div id="connSummary" class="muted"></div>
  <h4>Brain regions</h4>
  <div id="regionCards"></div>
  <h4>Disconnected / loose nodes</h4>
  <div id="mmBrain" style="margin-top:0">
   <b>Disconnected does not automatically mean broken.</b>
   <div class="gh">Normal causes</div>
   <div class="muted">docs/evidence artifacts &middot; planned systems &middot; tests/proofs &middot; semantic layer absent (code-only build) &middot; slice/cap filter hides bridge nodes</div>
   <div class="gh">Suspicious causes</div>
   <div class="muted">orphaned source file &middot; stale plan &middot; system not wired &middot; naming/path drift</div>
   <div class="gh">Recommended action</div>
   <div class="muted">Graphify first, then repo Read/Grep before treating it as a bug.</div>
  </div>
  <h4>Loose-neuron review queue <span class="muted" id="looseCount"></span></h4>
  <div><button class="act" id="copyLoose">Copy review list</button><span class="muted" id="looseMsg"></span></div>
  <div id="looseQueue"></div>
 </div>
 <h4 id="conceptsHdr">Concepts</h4><div id="concepts"></div>
</div>
<div id="right"><div id="insp"></div><h4>Connected</h4><div id="conn"></div></div>
<div id="tip"></div>
<div id="note">click = inspect &middot; dbl-click = 1-hop &middot; drag = pan &middot; wheel = zoom &middot; esc = slice view &middot; generated __GENERATED_AT__</div>
<script id="data" type="application/json">__DATA__</script>
<script>
"use strict";
const RM=JSON.parse(document.getElementById('data').textContent);
const NODES=RM.nodes, EDGES=RM.edges, SLICES=RM.slices, MD=RM.metadata;
const TAX=__TAXONOMY__;   // optional local view taxonomy; null in the shipped package
const byId=new Map(NODES.map(n=>[n.id,n]));
const adj=new Map();
for(const e of EDGES){
 if(!adj.has(e.source))adj.set(e.source,[]); if(!adj.has(e.target))adj.set(e.target,[]);
 adj.get(e.source).push(e.target); adj.get(e.target).push(e.source);
}
for(const[,v]of adj)v.sort();
const sliceOf=new Map();
for(const s of SLICES)for(const id of s.node_ids){if(!sliceOf.has(id))sliceOf.set(id,[]);sliceOf.get(id).push(s.id);}
const CONCEPTS=[...new Set(NODES.map(n=>n.concept))].sort();
const PALETTE=['#e4572e','#f3a712','#a8c686','#669bbc','#9b5de5','#00b4d8','#90e0ef','#f15bb5','#ffd166','#06d6a0','#c77dff','#48cae4','#b5838d','#e0aaff','#8d99ae'];
const colorOf=c=>PALETTE[Math.max(0,CONCEPTS.indexOf(c))%PALETTE.length];

// ---- state ----
let conceptOn=Object.fromEntries(CONCEPTS.map(c=>[c,true]));
let curSlice=SLICES[0]?SLICES[0].id:null, selected=null, hovered=null, tracePath=null;
let view={ids:[],edges:[],title:''}, pos=new Map(), scale=1, ox=0, oy=0;
const dpr=window.devicePixelRatio||1;
const cv=document.getElementById('cv'), ctx=cv.getContext('2d');

function eligible(n){
 if(!conceptOn[n.concept])return false;
 if(document.getElementById('hideTests').checked && /(^|\/)(tests?|__tests__)\/|\.test\.|\.spec\.|_test\.(go|py|rb)$/i.test(n.file_path))return false;
 if(document.getElementById('hideGen').checked && (n.concept==='unknown'))return false;
 if(document.getElementById('hideDocs').checked && n.concept==='docs')return false;
 if(document.getElementById('hideLow').checked && n.degree<=1)return false;
 return true;
}
function nodeKind(n){
 if(/(^|\/)(tests?|__tests__)\/|\.test\.|\.spec\.|_test\.(go|py|rb)$/i.test(n.file_path))return 'test';
 if(n.concept==='unknown')return 'generated/unknown';
 if(n.concept==='docs')return 'doc/derived';
 return 'runtime-ish source';
}
// ---- presets: generic by default (one Overview); a local config may overlay custom presets ----
function buildGenericPresets(){
 const p={'Overview':{slice:null,hideTests:true,hideDocs:false,labels:'26',hint:'Pick any slice button below; search across the whole read model.',trace:null}};
 for(const s of SLICES){if(s.id&&!p[s.label])p[s.label]={slice:s.id,hideTests:true,hideDocs:false,labels:'26',hint:'Slice: '+s.label+' ('+(s.purpose||'')+')',trace:null};}
 return p;
}
const PRESETS=(TAX&&TAX.presets)?TAX.presets:buildGenericPresets();
function applyPreset(name){
 const p=PRESETS[name];if(!p)return;
 document.getElementById('hideTests').checked=p.hideTests;
 document.getElementById('hideDocs').checked=p.hideDocs;
 document.getElementById('labelDensity').value=p.labels;
 document.getElementById('mmHints').innerHTML=esc(p.hint)+(p.trace?('<br>suggested trace: <b>'+esc(p.trace[0])+'</b> &rarr; <b>'+esc(p.trace[1])+'</b>'):'');
 if(p.trace){const s=topHit(p.trace[0]),d=topHit(p.trace[1]);
  if(s){srcSel=s.id;document.getElementById('src').value=s.label;}
  if(d){dstSel=d.id;document.getElementById('dst').value=d.label;}}
 [...document.getElementById('presets').children].forEach(b=>b.classList.toggle('active',b.textContent===name));
 showSlice(p.slice||curSlice);
}

// ==================== BRAIN MODE ====================
let mode='graph', brainRegion=null;
const GENERIC2D=(MD.slice_mode==='generic-structure');
// Deterministic anatomy-style positions reused across taxonomies so the brain
// layout reads the same regardless of region NAMES.
const REGION_POS=[{x:-560,y:-300},{x:-40,y:-380},{x:520,y:-360},{x:-640,y:60},{x:-60,y:-20},{x:380,y:-60},{x:-420,y:380},{x:60,y:340},{x:520,y:300},{x:900,y:0}];
function buildGenericRegions(){
 // Generic, repo-agnostic regions: top-level directories (generic-structure
 // mode) or concept buckets otherwise. No project-specific anatomy names.
 const labels=(GENERIC2D
   ? SLICES.map(x=>x.label).filter(l=>l!=='other directories')
   : CONCEPTS.slice()).slice(0,9);
 const out=labels.map((l,i)=>({id:l,x:REGION_POS[i].x,y:REGION_POS[i].y,tag:'structural',
   meaning:(GENERIC2D?'top-level directory "':'concept group "')+l+'" (generic structure)'}));
 out.push({id:GENERIC2D?'other directories':'other',x:REGION_POS[9].x,y:REGION_POS[9].y,tag:'review',
   meaning:'other / low-degree nodes (review signals, not automatic defects)'});
 return out;
}
// Custom regions only apply when a local config supplies them AND a custom
// taxonomy is active; otherwise everything is generic.
let REGIONS=(!GENERIC2D&&TAX&&TAX.regions&&TAX.regions.length)?TAX.regions.slice():buildGenericRegions();
const REGION_IDS=new Set(REGIONS.map(r=>r.id));
const _OTHER_REGION=REGIONS[REGIONS.length-1]?REGIONS[REGIONS.length-1].id:'other';
function regionOf(n){
 const f=(n.file_path||'').replace(/\\/g,'/'),l=n.label||'',c=n.concept;
 if(GENERIC2D){const top=f.includes('/')?f.split('/')[0]:'(root)';return REGION_IDS.has(top)?top:'other directories';}
 if(TAX&&TAX.region_routes){
  for(const rt of TAX.region_routes){
   if(rt.concept&&c===rt.concept)return rt.region;
   if(rt.path&&new RegExp(rt.path,'i').test(f))return rt.region;
   if(rt.label&&new RegExp(rt.label,'i').test(l))return rt.region;
  }
 }
 // generic fallback: a node's own concept IS its region when that concept is a region
 return REGION_IDS.has(c)?c:_OTHER_REGION;
}
function unionFind(ids,edges){
 const pa=new Map(ids.map(i=>[i,i]));
 const find=x=>{while(pa.get(x)!==x){pa.set(x,pa.get(pa.get(x)));x=pa.get(x);}return x;};
 for(const[a,b]of edges){const ra=find(a),rb=find(b);if(ra!==rb)pa.set(ra,rb);}
 const sizes=new Map();
 for(const i of ids){const r=find(i);sizes.set(r,(sizes.get(r)||0)+1);}
 const comps=[...sizes.values()];
 return{count:comps.length,largest:Math.max(0,...comps),isolated:comps.filter(s=>s===1).length};
}
function looseClass(n,viewDeg){
 const kind=nodeKind(n);
 if(kind==='test'||kind==='doc/derived')return 'likely normal';
 if(n.degree===0&&kind==='runtime-ish source')return 'suspicious candidate';
 if(viewDeg===0&&n.degree>1)return 'likely normal (hidden bridges)';
 return 'review';
}
function brainView(){
 mode='brain';tracePath=null;selected=null;hideInsp();
 const eligibleIds=NODES.filter(n=>eligible(n)).map(n=>n.id);
 const byRegion=new Map(REGIONS.map(r=>[r.id,[]]));
 for(const id of eligibleIds){const n=byId.get(id);byRegion.get(regionOf(n)).push(id);}
 let ids=brainRegion?byRegion.get(brainRegion).slice():eligibleIds.slice();
 const cap=parseInt(document.getElementById('maxNodes').value,10)||400;
 const capTotal=brainRegion?cap:Math.max(cap*3,1200);
 let capped=0;
 if(ids.length>capTotal){ids.sort((a,b)=>byId.get(b).degree-byId.get(a).degree);capped=ids.length-capTotal;ids=ids.slice(0,capTotal);}
 const idSet=new Set(ids);
 const edges=[];for(const e of EDGES)if(idSet.has(e.source)&&idSet.has(e.target))edges.push([e.source,e.target]);
 // deterministic region layout: degree-sorted phyllotaxis orbit per region
 pos=new Map();
 const viewDeg=new Map(ids.map(i=>[i,0]));
 for(const[a,b]of edges){viewDeg.set(a,viewDeg.get(a)+1);viewDeg.set(b,viewDeg.get(b)+1);}
 window.brainStats={regions:[],viewDeg};
 for(const r of REGIONS){
  const members=(byRegion.get(r.id)||[]).filter(i=>idSet.has(i)).sort((a,b)=>byId.get(b).degree-byId.get(a).degree||(a<b?-1:1));
  members.forEach((id,i)=>{const a=i*2.39996,rad=16*Math.sqrt(i+0.5);pos.set(id,{x:r.x+rad*Math.cos(a),y:r.y+rad*Math.sin(a)});});
  window.brainStats.regions.push({region:r,members});
 }
 view={ids,edges,title:'Brain Mode: '+(brainRegion||'Whole Brain Overview')+' ('+ids.length+' nodes'+(capped?', '+capped+' over cap':'')+')'};
 fit();draw();caption();renderBrainPanel(ids,edges,viewDeg);
}
function renderBrainPanel(ids,edges,viewDeg){
 const uf=unionFind(ids,edges);
 const loose=[];
 for(const id of ids){const n=byId.get(id);if((viewDeg.get(id)||0)===0||n.degree<=1)loose.push(n);}
 loose.sort((a,b)=>a.degree-b.degree||(a.id<b.id?-1:1));
 document.getElementById('connSummary').innerHTML=
  'visible nodes: <b>'+ids.length+'</b> &middot; visible edges: <b>'+edges.length+'</b><br>'
  +'connected components: <b>'+uf.count+'</b> &middot; largest: <b>'+uf.largest+'</b> &middot; isolated: <b>'+uf.isolated+'</b><br>'
  +'loose/review queue: <b>'+loose.length+'</b> &middot; region: '+esc(brainRegion||'whole brain')
  +'<br>filters: tests '+(document.getElementById('hideTests').checked?'hidden':'shown')+', docs '+(document.getElementById('hideDocs').checked?'hidden':'shown')+', generated '+(document.getElementById('hideGen').checked?'hidden':'shown');
 const cards=document.getElementById('regionCards');cards.innerHTML='';
 for(const{region,members}of window.brainStats.regions){
  const top=members.slice(0,3).map(i=>esc(byId.get(i).label)).join(', ');
  const d=document.createElement('div');d.className='res';
  d.innerHTML='<b>'+esc(region.id)+'</b> ('+members.length+') <span class="muted">['+region.tag+']</span><div class="p">'+esc(region.meaning)+' runtime-live is NOT inferred.</div>'+(top?'<div class="p">top: '+top+'</div>':'');
  d.onclick=()=>{brainRegion=region.id;brainView();markBrainPreset(region.id);};
  cards.appendChild(d);}
 const lq=document.getElementById('looseQueue');lq.innerHTML='';
 document.getElementById('looseCount').textContent='('+loose.length+')';
 const groups=new Map();
 for(const n of loose.slice(0,200)){const cls=looseClass(n,viewDeg.get(n.id)||0);if(!groups.has(cls))groups.set(cls,[]);groups.get(cls).push(n);}
 window.lastLoose=loose.map(n=>looseClass(n,viewDeg.get(n.id)||0)+'\t'+n.label+'\t'+n.file_path+'\tdeg='+n.degree).join('\n');
 for(const[cls,arr]of[...groups.entries()].sort()){
  const h=document.createElement('div');h.className='gh';h.textContent=cls+' ('+arr.length+')';lq.appendChild(h);
  for(const n of arr.slice(0,25)){const d=document.createElement('div');d.className='res';
   d.innerHTML='<span class="dot" style="background:'+colorOf(n.concept)+'"></span>'+esc(n.label)+' <span class="muted">deg '+n.degree+'</span><div class="p">'+esc(n.file_path)+'</div>';
   d.onclick=()=>{selected=n.id;showInsp(n.id);if(pos.has(n.id)){center(n.id);draw();}};
   lq.appendChild(d);}}
}
const BRAIN_PRESETS=['Whole Brain Overview'].concat(REGIONS.map(r=>r.id));
function markBrainPreset(name){[...document.getElementById('brainPresets').children].forEach(b=>b.classList.toggle('active',b.dataset.r===(name==='Whole Brain Overview'?'':name)));}
function setMode(m){
 mode=m;
 document.getElementById('modeGraph').classList.toggle('active',m==='graph');
 document.getElementById('modeBrain').classList.toggle('active',m==='brain');
 document.getElementById('presets').style.display=m==='graph'?'flex':'none';
 document.getElementById('slices').style.display=m==='graph'?'flex':'none';
 document.getElementById('brainPresets').style.display=m==='brain'?'flex':'none';
 document.getElementById('brainPanel').style.display=m==='brain'?'block':'none';
 document.getElementById('brainWarn').style.display=m==='brain'?'block':'none';
 if(EMBED){try{if(window.parent!==window)window.parent.postMessage({graphify:'mode2d',value:m},'*');}catch(e){}}  // G5P: honest ask-console context
 if(m==='brain')brainView();else showSlice(curSlice);
}
document.getElementById('modeGraph').onclick=()=>setMode('graph');
document.getElementById('modeBrain').onclick=()=>setMode('brain');
{const bp=document.getElementById('brainPresets');
 for(const name of BRAIN_PRESETS){const b=document.createElement('button');b.className='pb';b.textContent=name;
  b.dataset.r=name==='Whole Brain Overview'?'':name;
  b.onclick=()=>{brainRegion=name==='Whole Brain Overview'?null:name;
   brainView();markBrainPreset(name);};
  bp.appendChild(b);}}
document.getElementById('copyLoose').onclick=()=>{if(window.lastLoose)clip(window.lastLoose,'looseMsg');};
// ==================== END BRAIN MODE ====================
function induced(ids){const s=new Set(ids),out=[];for(const e of EDGES)if(s.has(e.source)&&s.has(e.target))out.push([e.source,e.target]);return out;}

// ---- layout (small force sim; <=800 nodes) ----
function layout(ids,edges){
 const n=ids.length,idx=new Map(ids.map((d,i)=>[d,i]));
 const px=new Float32Array(n),py=new Float32Array(n);
 for(let i=0;i<n;i++){const a=i*2.39996,r=14*Math.sqrt(i+0.5);px[i]=r*Math.cos(a);py[i]=r*Math.sin(a);}
 const es=edges.map(([a,b])=>[idx.get(a),idx.get(b)]);
 const k=34,iters=n>500?120:200;
 for(let it=0;it<iters;it++){
  const t=1-it/iters,step=9*t+0.6,fx=new Float32Array(n),fy=new Float32Array(n);
  for(let i=0;i<n;i++)for(let j=i+1;j<n;j++){
   let dx=px[i]-px[j],dy=py[i]-py[j],d2=dx*dx+dy*dy+0.01;if(d2>90000)continue;
   const f=(k*k)/d2;dx*=f;dy*=f;fx[i]+=dx;fy[i]+=dy;fx[j]-=dx;fy[j]-=dy;}
  for(const[a,b]of es){let dx=px[a]-px[b],dy=py[a]-py[b];const d=Math.sqrt(dx*dx+dy*dy)+0.01,f=d*0.045;dx*=f/d;dy*=f/d;
   fx[a]-=dx*d;fy[a]-=dy*d;fx[b]+=dx*d;fy[b]+=dy*d;}
  for(let i=0;i<n;i++){const m=Math.sqrt(fx[i]*fx[i]+fy[i]*fy[i])+0.01,c=Math.min(m,step)/m;
   px[i]+=fx[i]*c-px[i]*0.004;py[i]+=fy[i]*c-py[i]*0.004;}
 }
 pos=new Map();ids.forEach((d,i)=>pos.set(d,{x:px[i],y:py[i]}));
}

// ---- views ----
function showSlice(id){
 // validate before mutating -- a missing slice id (e.g. a custom preset on a
 // generic graph) must not brick every later filter/Escape redraw.
 const s=SLICES.find(x=>x.id===id)||SLICES[0];
 if(!s){const c=document.getElementById('counts');if(c)c.textContent=' no graph data (0 slices)';return;}
 id=s.id;
 curSlice=id;tracePath=null;selected=null;hideInsp();
 let ids=s.node_ids.filter(i=>byId.has(i)&&eligible(byId.get(i)));
 const cap=parseInt(document.getElementById('maxNodes').value,10)||400;
 const capped=Math.max(0,ids.length-cap);
 if(capped)ids=ids.slice().sort((a,b)=>byId.get(b).degree-byId.get(a).degree).slice(0,cap);
 const hidden=s.node_ids.length-ids.length-capped;
 view={ids,edges:induced(ids),title:'Slice: '+s.label+' ('+ids.length+' shown'+(hidden>0?', '+hidden+' hidden by filters':'')+(capped?', '+capped+' over cap':'')+(s.warnings&&s.warnings.length?' - '+s.warnings.join('; '):'')+')'};
 [...document.getElementById('slices').children].forEach(b=>b.classList.toggle('active',b.dataset.id===id));
 const _ss=document.getElementById('sliceSel');if(_ss&&_ss.value!==id)_ss.value=id;
 if(EMBED){try{const _cc={};for(const _i of s.node_ids){const _n=byId.get(_i);if(_n)_cc[_n.concept]=(_cc[_n.concept]||0)+1;}
  if(window.parent!==window)window.parent.postMessage({graphify:'slice-concepts',slice:s.label,counts:_cc},'*');}catch(e){}}  // G5O.2i: right-panel counts follow the mission slice
 layout(view.ids,view.edges);fit();draw();caption();
}
function neighborhood(id,hops){
 const lim1=150,lim2=500;
 const n1=(adj.get(id)||[]).filter(i=>byId.has(i)&&eligible(byId.get(i)));
 const r1=n1.slice().sort((a,b)=>byId.get(b).degree-byId.get(a).degree).slice(0,lim1);
 let ids=[id,...r1],hiddenC=n1.length-r1.length;
 if(hops===2){const seen=new Set(ids);
  for(const m of r1){for(const x of(adj.get(m)||[])){if(seen.has(x))continue;const nn=byId.get(x);if(!nn||!eligible(nn))continue;seen.add(x);ids.push(x);if(ids.length>=lim2)break;}if(ids.length>=lim2)break;}}
 selected=id;tracePath=null;
 view={ids,edges:induced(ids),title:hops+'-hop of "'+byId.get(id).label+'" ('+ids.length+' nodes'+(hiddenC>0?', '+hiddenC+' capped/hidden':'')+')'};
 layout(view.ids,view.edges);fit();draw();caption();showInsp(id);
}
function bfs(a,b,allowed){
 if(a===b)return[a];
 const prev=new Map([[a,null]]);const q=[a];let qi=0;
 while(qi<q.length){const u=q[qi++];
  for(const v of(adj.get(u)||[])){if(prev.has(v))continue;if(allowed&&!allowed.has(v)&&v!==b)continue;
   prev.set(v,u);if(v===b){const p=[v];let c=v;while(prev.get(c)!==null){c=prev.get(c);p.push(c);}return p.reverse();}q.push(v);}}
 return null;
}

// ---- UI builders ----
const slicesDiv=document.getElementById('slices');
for(const s of SLICES){const b=document.createElement('button');b.className='pb';b.dataset.id=s.id;b.textContent=s.label+' ('+s.node_count+')';b.title=s.purpose;b.onclick=()=>showSlice(s.id);slicesDiv.appendChild(b);}
const sliceSel=document.getElementById('sliceSel');
for(const s of SLICES){const o=document.createElement('option');o.value=s.id;o.textContent=s.label+' ('+s.node_count+')';sliceSel.appendChild(o);}
sliceSel.onchange=()=>showSlice(sliceSel.value);
document.getElementById('meta').innerHTML='build: '+esc(MD.graph_build_mode)+' <span class="chip">semantic layer: ABSENT</span> | built_at_commit: <b>'+esc(String(MD.graph_built_at_commit).slice(0,10))+'</b> | source: '+esc(MD.source_graph_path)+' | generated_at: __GENERATED_AT__ | read model: '+MD.emitted_nodes+' nodes / '+MD.emitted_edges+' edges (source '+MD.total_source_nodes+'/'+MD.total_source_edges+') | hidden at build: '+esc(JSON.stringify(MD.hidden_noise_counts));
document.getElementById('warn').textContent='Graphify first, repo truth second - structural memory, not source of truth. Runtime truth is NOT inferred from this graph. '+(RM.warnings||[]).join(' ');
const presetsDiv=document.getElementById('presets');
for(const name of Object.keys(PRESETS)){const b=document.createElement('button');b.className='pb';b.textContent=name;b.onclick=()=>applyPreset(name);presetsDiv.appendChild(b);}
const conceptsDiv=document.getElementById('concepts');
for(const c of CONCEPTS){const l=document.createElement('label');l.className='g';
 const cb=document.createElement('input');cb.type='checkbox';cb.checked=true;cb.onchange=()=>{conceptOn[c]=cb.checked;mode==='brain'?brainView():showSlice(curSlice);};
 l.appendChild(cb);const sw=document.createElement('span');sw.className='dot';sw.style.background=colorOf(c);l.appendChild(sw);
 l.appendChild(document.createTextNode(c+' ('+NODES.filter(n=>n.concept===c).length+')'));conceptsDiv.appendChild(l);}
for(const id of['hideTests','hideGen','hideDocs','hideLow','maxNodes'])document.getElementById(id).onchange=()=>{mode==='brain'?brainView():showSlice(curSlice);};
document.getElementById('labelDensity').onchange=()=>draw();
document.getElementById('edgesOn').onchange=()=>draw();
async function clip(t,msgId){try{await navigator.clipboard.writeText(t);document.getElementById(msgId).textContent='copied.';}
 catch(e){document.getElementById(msgId).textContent='copy blocked (browser permission).';}}
document.getElementById('copySnippet').onclick=()=>clip(document.getElementById('mmSnippet').textContent,'mmMsg');
document.getElementById('copyView').onclick=()=>{
 let h='#slice='+curSlice;
 if(tracePath&&srcSel&&dstSel)h='#trace='+encodeURIComponent(byId.get(srcSel).label)+'=>'+encodeURIComponent(byId.get(dstSel).label);
 else if(selected)h='#select='+encodeURIComponent(byId.get(selected).label);
 clip(location.origin+location.pathname+h,'shareMsg');};
document.getElementById('copyNodes').onclick=()=>{
 const list=view.ids.map(i=>{const n=byId.get(i);return{id:n.id,label:n.label,file:n.file_path,concept:n.concept,degree:n.degree};});
 clip(JSON.stringify(list,null,1),'shareMsg');};

// search
let smode='label';
document.getElementById('smode').onclick=e=>{if(!e.target.dataset.m)return;smode=e.target.dataset.m;
 [...e.currentTarget.children].forEach(c=>c.classList.toggle('active',c===e.target));runSearch();};
function findNodes(q){q=q.trim().toLowerCase();if(!q)return[];
 const hay=n=>smode==='path'?n.file_path:smode==='concept'?n.concept:n.label;
 return NODES.filter(n=>hay(n).toLowerCase().includes(q)).sort((a,b)=>b.degree-a.degree).slice(0,50);}
function renderResults(el,hits,pick){el.innerHTML='';for(const n of hits){const d=document.createElement('div');d.className='res';
 d.innerHTML='<span class="dot" style="background:'+colorOf(n.concept)+'"></span><b>'+esc(n.label)+'</b> <span class="muted">deg '+n.degree+'</span><div class="p">'+esc(n.file_path)+'</div>';
 d.onclick=()=>pick(n);el.appendChild(d);}}
function runSearch(){renderResults(document.getElementById('results'),findNodes(document.getElementById('q').value),n=>{focusNode(n.id);document.getElementById('results').innerHTML='';});}  // G5O.2d: menu minimizes on pick (matches the trace pickers)
document.getElementById('q').oninput=runSearch;
function focusNode(id){if(pos.has(id)){selected=id;showInsp(id);center(id);draw();}else neighborhood(id,1);}

// trace
let srcSel=null,dstSel=null;
function bindPick(inp,list,set){const i=document.getElementById(inp);i.oninput=()=>{const prev=smode;smode='label';let h=findNodes(i.value);if(!h.length){smode='path';h=findNodes(i.value);}smode=prev;
 renderResults(document.getElementById(list),h.slice(0,6),n=>{set(n.id);i.value=n.label;document.getElementById(list).innerHTML='';});};}
bindPick('src','srcR',v=>srcSel=v);bindPick('dst','dstR',v=>dstSel=v);
document.getElementById('traceBtn').onclick=()=>{
 const out=document.getElementById('traceOut');
 if(!srcSel||!dstSel){out.textContent='pick both source and target from the dropdowns.';return;}
 const visible=new Set(view.ids);let scope='current view';let p=bfs(srcSel,dstSel,visible);
 if(!p){p=bfs(srcSel,dstSel,null);scope='whole read model';}
 if(!p){out.textContent='No path exists between these nodes in the read model.';tracePath=null;draw();return;}
 tracePath=p;
 const ctxN=[];const inP=new Set(p);
 for(const x of p)for(const nb of(adj.get(x)||[]))if(!inP.has(nb)&&byId.has(nb)&&ctxN.length<100)ctxN.push(nb);
 const ids=[...p,...ctxN];view={ids,edges:induced(ids),title:'Path: '+(p.length-1)+' hops ('+scope+')'};
 pos=new Map();const sp=170;
 p.forEach((id,i)=>pos.set(id,{x:i*sp,y:0}));
 ctxN.forEach((id,j)=>{let anchor=0;for(let i=0;i<p.length;i++)if((adj.get(id)||[]).includes(p[i])){anchor=i;break;}
  pos.set(id,{x:anchor*sp+((j%3)-1)*46,y:((j%2)?1:-1)*(90+38*Math.floor(j/2))});});
 fit();draw();caption();
 const sN=byId.get(srcSel),dN=byId.get(dstSel);
 out.innerHTML='<b>'+esc(sN.label)+'</b> &rarr; <b>'+esc(dN.label)+'</b><br>path length: <b>'+(p.length-1)+' hops</b> ('+scope+')<br>'
  +p.map((id,i)=>{const n=byId.get(id);return i+'. <span class="dot" style="background:'+colorOf(n.concept)+'"></span>'+esc(n.label)+' <span class="muted">'+esc(tail(n.file_path))+'</span>';}).join('<br>');
 window.lastTrace=p.map(id=>{const n=byId.get(id);return n.label+'  ['+n.file_path+']';}).join('\n');
 document.getElementById('copyPath').style.display='inline-block';
 selected=dstSel;showInsp(dstSel);};
document.getElementById('copyPath').onclick=async()=>{if(!window.lastTrace)return;
 try{await navigator.clipboard.writeText(window.lastTrace);document.getElementById('shareMsg').textContent='path copied.';}
 catch(e){document.getElementById('shareMsg').textContent='copy blocked (browser permission).';}};
document.getElementById('traceClr').onclick=()=>{tracePath=null;window.lastTrace=null;document.getElementById('copyPath').style.display='none';document.getElementById('traceOut').textContent='';showSlice(curSlice);};

// inspector
function showInsp(id){const n=byId.get(id);if(!n)return;
 document.getElementById('right').style.display='block';
 const kind=nodeKind(n);
 const reminder=(kind==='doc/derived'||kind==='generated/unknown')?'<div class="fld" style="color:#e8c468">repo-truth verify: derived/doc node - confirm with Read/Grep before relying on it.</div>':'';
 document.getElementById('insp').innerHTML='<h4>Node inspector</h4>'
  +'<div class="fld"><b>'+esc(n.label)+'</b></div>'
  +'<div class="fld path">'+esc(n.file_path)+'</div>'
  +'<div class="fld"><span class="dot" style="background:'+colorOf(n.concept)+'"></span>'+esc(n.concept)+' &nbsp; degree <b>'+n.degree+'</b> &nbsp; community <b>'+(n.community==null?'-':n.community)+'</b></div>'
  +'<div class="fld muted">kind: '+kind+' &nbsp;|&nbsp; slices: '+(sliceOf.get(id)||['(none)']).join(', ')+'</div>'+reminder
  +'<div class="fld"><button class="act" id="b1">1-hop</button><button class="act" id="b2">2-hop</button><button class="act" id="bc">Copy file path</button></div><div class="muted" id="cm"></div>';
 document.getElementById('b1').onclick=()=>neighborhood(id,1);
 document.getElementById('b2').onclick=()=>neighborhood(id,2);
 document.getElementById('bc').onclick=async()=>{try{await navigator.clipboard.writeText(n.file_path);document.getElementById('cm').textContent='copied.';}
  catch(e){const t=document.createElement('textarea');t.value=n.file_path;document.body.appendChild(t);t.select();document.execCommand('copy');t.remove();document.getElementById('cm').textContent='copied (fallback).';}};
 // connected, grouped by concept
 const connEl=document.getElementById('conn');connEl.innerHTML='';
 const groups=new Map();
 for(const x of(adj.get(id)||[])){const m=byId.get(x);if(!m)continue;
  if(!groups.has(m.concept))groups.set(m.concept,[]);groups.get(m.concept).push(m);}
 const ordered=[...groups.entries()].sort((a,b)=>b[1].length-a[1].length);
 for(const[concept,arr]of ordered){
  const h=document.createElement('div');h.className='gh conn-group';
  h.innerHTML='<span class="dot" style="background:'+colorOf(concept)+'"></span>'+esc(concept)+' ('+arr.length+')';
  connEl.appendChild(h);
  arr.sort((a,b)=>b.degree-a.degree);
  const frag=document.createElement('div');
  renderResults(frag,arr.slice(0,40),m=>focusNode(m.id));
  connEl.appendChild(frag);}
 // G5P.8: 2D selection parity -- the dashboard right panel/notes follow 2D too
 if(typeof EMBED!=='undefined'&&EMBED){try{if(window.parent!==window)window.parent.postMessage({graphify:'selected',node:{id:n.id,lbl:n.label,fp:n.file_path,reg:n.concept,deg:n.degree,nb:(adj.get(id)||[]).length}},'*');}catch(e){}}}
function hideInsp(){document.getElementById('right').style.display='none';
 if(typeof EMBED!=='undefined'&&EMBED){try{if(window.parent!==window)window.parent.postMessage({graphify:'selected',node:null},'*');}catch(e){}}}

// ---- render ----
function caption(){document.getElementById('counts').textContent=' '+view.title+' | showing '+view.ids.length+' nodes / '+view.edges.length+' edges';}
function fit(){let mnx=1e9,mxx=-1e9,mny=1e9,mxy=-1e9;
 for(const id of view.ids){const p=pos.get(id);if(!p)continue;mnx=Math.min(mnx,p.x);mxx=Math.max(mxx,p.x);mny=Math.min(mny,p.y);mxy=Math.max(mxy,p.y);}
 const W=innerWidth,H=innerHeight,pad=90;
 const _sw=(typeof EMBED!=='undefined'&&EMBED&&!document.body.classList.contains('drawer-open'))?40:580,_sh=(typeof EMBED!=='undefined'&&EMBED)?60:120,_sx=(typeof EMBED!=='undefined'&&EMBED&&!document.body.classList.contains('drawer-open'))?20:290,_sy=(typeof EMBED!=='undefined'&&EMBED)?48:104;scale=Math.min((W-_sw-pad)/Math.max(mxx-mnx,1),(H-_sh-pad)/Math.max(mxy-mny,1));scale=Math.min(Math.max(scale,0.05),6);
 ox=_sx+(W-_sw)/2-(mnx+mxx)/2*scale;oy=_sy+(H-_sh)/2-(mny+mxy)/2*scale;}
function center(id){const p=pos.get(id);if(!p)return;ox=innerWidth/2-p.x*scale;oy=innerHeight/2-p.y*scale;}
const sx=p=>p.x*scale+ox,sy=p=>p.y*scale+oy;
const maxDeg=Math.max(...NODES.map(n=>n.degree),1);
function rOf(n){return Math.min(3+5*Math.sqrt(byId.get(n).degree/maxDeg*8),16);}
function draw(){
 const W=innerWidth,H=innerHeight;cv.width=W*dpr;cv.height=H*dpr;cv.style.width=W+'px';cv.style.height=H+'px';
 ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
 if(mode==='brain'){
  ctx.font='13px system-ui';ctx.textBaseline='middle';
  for(const{region,members}of(window.brainStats?window.brainStats.regions:[])){
   if(brainRegion&&region.id!==brainRegion)continue;
   const cx=region.x*scale+ox,cy=region.y*scale+oy,rr=(16*Math.sqrt(Math.max(members.length,1))+46)*scale;
   ctx.strokeStyle='#3a4a5e';ctx.globalAlpha=0.55;ctx.lineWidth=1.4;
   ctx.beginPath();ctx.arc(cx,cy,rr,0,7);ctx.stroke();
   ctx.globalAlpha=0.95;ctx.fillStyle='#9fb6d4';
   ctx.fillText(region.id+' ('+members.length+')',cx-rr*0.7,cy-rr-12);
  }
  ctx.globalAlpha=1;
 }
 const inP=tracePath?new Set(tracePath):null;const pE=new Set();
 if(tracePath)for(let i=0;i+1<tracePath.length;i++){const a=tracePath[i],b=tracePath[i+1];pE.add(a<b?a+'|'+b:b+'|'+a);}
 const edgesOn=document.getElementById('edgesOn').checked;
 for(const[a,b]of view.edges){const pa=pos.get(a),pb=pos.get(b);if(!pa||!pb)continue;
  const on=pE.has(a<b?a+'|'+b:b+'|'+a);
  if(!edgesOn&&!on)continue;
  ctx.strokeStyle=on?'#ffd166':'#7e93ac';ctx.globalAlpha=on?0.95:(inP?0.05:0.12);ctx.lineWidth=on?2.4:0.7;
  const x1=sx(pa),y1=sy(pa),x2=sx(pb),y2=sy(pb),mx=(x1+x2)/2+(y2-y1)*0.08,my=(y1+y2)/2-(x2-x1)*0.08;
  ctx.beginPath();ctx.moveTo(x1,y1);ctx.quadraticCurveTo(mx,my,x2,y2);ctx.stroke();}
 ctx.globalAlpha=1;
 for(const id of view.ids){const p=pos.get(id);if(!p)continue;const n=byId.get(id);
  ctx.globalAlpha=(inP&&!inP.has(id))?0.14:1;
  ctx.fillStyle=colorOf(n.concept);ctx.shadowColor=ctx.fillStyle;ctx.shadowBlur=9;ctx.beginPath();ctx.arc(sx(p),sy(p),rOf(id),0,7);ctx.fill();ctx.shadowBlur=0;
  if(id===selected){ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.stroke();}}
 ctx.globalAlpha=1;ctx.font='11.5px system-ui';ctx.textBaseline='middle';
 const nLbl=parseInt(document.getElementById('labelDensity').value,10)||26;
 const top=new Set(view.ids.slice().sort((a,b)=>byId.get(b).degree-byId.get(a).degree).slice(0,nLbl));
 const zoomed=scale>1.7;
 for(const id of view.ids){
  const show=id===selected||id===hovered||(inP&&inP.has(id))||top.has(id)||zoomed;
  if(!show)continue;if(inP&&!inP.has(id)&&id!==selected)continue;
  const p=pos.get(id);const x=sx(p),y=sy(p);if(x<-80||y<-40||x>W+80||y>H+40)continue;
  const t=byId.get(id).label,w=ctx.measureText(t).width;
  ctx.fillStyle='#000a';ctx.fillRect(x+rOf(id)+3,y-8,w+6,16);ctx.fillStyle='#ecedf2';ctx.fillText(t,x+rOf(id)+6,y);}
}
// interaction
let drag=null,moved=false;
cv.addEventListener('mousedown',e=>{drag={x:e.clientX,y:e.clientY};moved=false;});
addEventListener('mouseup',()=>drag=null);
addEventListener('mousemove',e=>{
 if(drag){ox+=e.clientX-drag.x;oy+=e.clientY-drag.y;drag={x:e.clientX,y:e.clientY};moved=true;draw();return;}
 const id=hit(e.clientX,e.clientY);if(id!==hovered){hovered=id;draw();}
 const tip=document.getElementById('tip');
 if(id){const n=byId.get(id);tip.style.display='block';tip.style.left=(e.clientX+14)+'px';tip.style.top=(e.clientY+10)+'px';
  tip.innerHTML='<b>'+esc(n.label)+'</b><br>'+esc(n.file_path)+'<br><span class="muted">'+esc(n.concept)+' - deg '+n.degree+'</span>';}
 else tip.style.display='none';});
cv.addEventListener('click',e=>{if(moved)return;const id=hit(e.clientX,e.clientY);
 if(!id){selected=null;hideInsp();draw();return;}selected=id;showInsp(id);draw();});
cv.addEventListener('dblclick',e=>{const id=hit(e.clientX,e.clientY);if(id)neighborhood(id,1);});
cv.addEventListener('wheel',e=>{e.preventDefault();const f=e.deltaY<0?1.16:0.86;
 ox=e.clientX-(e.clientX-ox)*f;oy=e.clientY-(e.clientY-oy)*f;scale*=f;draw();},{passive:false});
addEventListener('keydown',e=>{if(e.key==='Escape')showSlice(curSlice);});
addEventListener('resize',()=>draw());
function hit(mx,my){let best=null,bd=1e9;
 for(const id of view.ids){const p=pos.get(id);if(!p)continue;const dx=sx(p)-mx,dy=sy(p)-my,d2=dx*dx+dy*dy,r=rOf(id)+4;
  if(d2<r*r&&d2<bd){bd=d2;best=id;}}return best;}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');}
function tail(f){const p=f.split('/');return p.length>2?'.../'+p.slice(-2).join('/'):f;}

// ---- boot (hash params for deterministic checks) ----
let _htokens=[];try{_htokens=location.hash.slice(1).split('&').map(t=>{try{return decodeURIComponent(t);}catch(e){return t;}});}catch(e){_htokens=[];}  // G5P.8: malformed hash must not kill boot
const EMBED=_htokens.includes('embed');
if(EMBED)document.body.classList.add('embed');
const hash=_htokens.filter(t=>t!=='embed').join('&');
function topHit(q){const prev=smode;smode='label';let h=findNodes(q);if(!h.length){smode='path';h=findNodes(q);}smode=prev;return h[0]||null;}
if(EMBED){
document.body.classList.add('drawer-open');   // G5N: Tools drawer open by default in 2D
// G5O.2g: the Structural/Brain view-mode toggle moves INTO the drawer (real DOM,
// original handlers) -- top bar stays clean, the 2D Brain view stays reachable.
(function(){
 const mb=document.getElementById('modeBtns'), left=document.getElementById('left');
 if(mb&&left){
  const h=document.createElement('h4'); h.textContent='View Mode';
  left.insertBefore(mb,left.firstChild); left.insertBefore(h,mb);
  const g=document.getElementById('modeGraph'), b=document.getElementById('modeBrain');
  if(g)g.textContent='Structural'; if(b)b.textContent='2D Brain';
  if(g&&b)mb.insertBefore(b,g);                       // G5O.2k: 2D Brain listed first (operator)
 }
 // G5O.2k: 2D Brain is the embed DEFAULT view; deferred past the hash boot so
 // deep-links (slice=/select=/trace=) still open in structural mode.
 setTimeout(function(){ if(!/(trace=|select=|slice=)/.test(location.hash)) setMode('brain'); },0);
 // slice chips stay visible in embed even in brain mode (G5O.2h !important) --
 // clicking one must switch modes coherently, not just repaint the canvas.
 [...document.querySelectorAll('#slices .pb')].forEach(function(ch){
  const orig=ch.onclick;
  ch.onclick=function(){ if(mode==='brain'){ curSlice=ch.dataset.id; setMode('graph'); } else orig(); };
 });
})();
window.addEventListener('message',ev=>{
  if(ev.origin!==location.origin)return;
  const d=ev.data||{};
  if(d.graphify==='toggle-tools'){
    const open=document.body.classList.toggle('drawer-open');
    try{draw();}catch(e){}  // G5O.2e: drawer is an overlay -- redraw only, NEVER re-fit (operator: Tools must not reset the view)
    try{if(window.parent!==window)window.parent.postMessage({graphify:'tools',value:open},'*');}catch(e){}
  }
  else if(d.graphify==='concept'){              // single toggle: drive the real checkbox (byte-identical path)
    const idx=CONCEPTS.indexOf(d.key);
    if(idx>=0){const cb=document.querySelectorAll('#concepts input[type=checkbox]')[idx];
      if(cb&&cb.checked!==!!d.value){cb.checked=!!d.value;cb.onchange();}}
  }
  else if(d.graphify==='concepts'){             // bulk from the dashboard right panel: one redraw
    const hid=new Set(d.hidden||[]);
    document.querySelectorAll('#concepts input[type=checkbox]').forEach((cb,i)=>{const k=CONCEPTS[i];cb.checked=!hid.has(k);});
    Object.keys(conceptOn).forEach(k=>conceptOn[k]=!hid.has(k));
    mode==='brain'?brainView():showSlice(curSlice);
  }
  else if(d.graphify==='find-req'){            // G5P.8: 2D node jump parity (3D-identical scoring)
    const q=String(d.q||'').toLowerCase().trim();
    let best=null,matches=0;
    if(q)for(const n of NODES){
     if(!eligible(n))continue;                   // filtered-out nodes are not jump targets
     const lbl=String(n.label||'').toLowerCase(),nid=String(n.id||'').toLowerCase();
     let score=0;
     if(lbl===q||nid===q)score=3;else if(lbl.startsWith(q))score=2;else if(lbl.includes(q)||nid.includes(q))score=1;
     if(!score)continue;matches++;
     if(!best||score>best.score||(score===best.score&&n.degree>best.n.degree))best={n,score};
    }
    if(best){if(mode==='brain')setMode('graph');focusNode(best.n.id);}
    try{if(window.parent!==window)window.parent.postMessage({graphify:'find-res',q:d.q,matches,hit:best?{id:best.n.id,lbl:best.n.label,reg:best.n.concept}:null},'*');}catch(e){}
  }
  else if(d.graphify==='neighbors-req'){       // G5P.8: 2D neighbor listing parity
    const items=[];
    for(const x of(adj.get(d.id)||[])){const m=byId.get(x);if(m)items.push({lbl:m.label,reg:m.concept,deg:m.degree});}
    items.sort((a,b)=>b.deg-a.deg);
    try{if(window.parent!==window)window.parent.postMessage({graphify:'neighbors',id:d.id,total:items.length,items:items.slice(0,8)},'*');}catch(e){}
  }
  else if(d.graphify==='concepts-state'){
    try{window.parent.postMessage({graphify:'concepts-state',concepts:CONCEPTS.map(c=>({key:c,count:NODES.filter(n=>n.concept===c).length,checked:!!conceptOn[c]}))},'*');}catch(e){}
  }
});
try{if(window.parent!==window)window.parent.postMessage({graphify:'tools',value:true},'*');}catch(e){}
}
if(hash.startsWith('trace=')){const[a,b]=hash.slice(6).split('=>');showSlice(curSlice);
 const s=topHit(a),d=topHit(b);
 if(s&&d){srcSel=s.id;dstSel=d.id;document.getElementById('src').value=s.label;document.getElementById('dst').value=d.label;document.getElementById('traceBtn').click();}}
else if(hash.startsWith('select=')){const n=topHit(hash.slice(7));showSlice(curSlice);if(n)neighborhood(n.id,1);}
else if(hash.startsWith('slice=')){const id=hash.slice(6);showSlice(SLICES.some(s=>s.id===id)?id:curSlice);}
else if(hash.startsWith('brain')){const r=hash.includes('=')?hash.slice(hash.indexOf('=')+1):'';
 brainRegion=REGIONS.some(x=>x.id===r)?r:null;setMode('brain');markBrainPreset(brainRegion||'Whole Brain Overview');}
else showSlice(curSlice);
</script></body></html>
"""


if __name__ == "__main__":
    sys.exit(main())
