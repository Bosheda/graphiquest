# graphify_brain3d.py -- 3D MOLTEN BRAIN generator (G5D-corrected v2).
# TRACKED SOURCE (promoted G5P.0b from gitignored graphify-out/views/_make_brain3d.py so
# fixes like the G5P.0a loading-flash ready-gate live in the PR, not only in ignored
# output). Emits into gitignored graphify-out/ -- NEVER commit the generated HTML.
# PROTOTYPE-ONLY CDN build: 3d-force-graph PINNED 1.80.0 (bundles three r183, jsdelivr --
# unpkg has documented 429s) + esm.sh/three@0.183.0 UnrealBloomPass (revision-matched;
# never define window.THREE -- the UMD silently adopts it). Grill-verified pattern
# (doc 45 SS6): default Lambert spheres + Python-baked heat-ramp colors + bloom =
# molten cores; NO per-node THREE objects, NO glow sprites.
# Graphify mapping: clusters -> brain regions/nuclei; degree -> core size + white-hot
# center heat; edges -> two-tier molten bridges (magma rivers / ember crust);
# low-degree loose nodes -> dim peripheral cores.
# Run: python scripts/graphify_brain3d.py
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "graphify-out"
# G5P.4: env overrides let the bridge emit per-project views (defaults unchanged
# -- the default output stays byte-identical when the vars are absent)
RM_PATH = Path(os.environ.get("GRAPHIFY_READ_MODEL", str(ROOT / "hivemind" / "read-model.json")))
RM = json.load(open(RM_PATH, encoding="utf-8"))
OUT = Path(os.environ.get("GRAPHIFY_VIEW_OUT", str(ROOT / "views" / "brain-3d-prototype.html")))
CAP = 1200
HOT_FRACTION = 0.15  # top-degree share whose links render as bright magma rivers

# Molten-brain layout SLOTS: (x, y, |z| hemi-depth, legend-hue, atlas-cell).
# Distinct molten families (amber/gold, teal/cyan, magenta/pink, violet/purple,
# pale blue) on a flat wide hero-frame oval; the last slot is a separate satellite
# for the review/overflow region. Region NAMES are assigned GENERICALLY (top-level
# directories or concept buckets) or from an optional local config -- never a
# project-specific anatomy by default. Positions are reused per rank so the
# molten-brain layout is identical regardless of the names.
REGION_SLOTS = [
    (-510, 80, 110, "#8b2fff", 5),
    (-40, 120, 130, "#00e5ff", 3),
    (380, 110, 110, "#76ff03", 4),
    (-340, -120, 130, "#2f6bff", 1),
    (20, -60, 80, "#ffb300", 2),
    (270, -20, 100, "#76ff03", 4),
    (-40, -230, 120, "#ff2fa0", 6),
    (140, -250, 60, "#ffb300", 2),
    (290, -205, 110, "#ef7fae", 6),
    (760, -40, 200, "#76808c", 7),
]
WHITE_HOT = (255, 243, 198)  # #fff3c6 nucleus tint

GENERIC_MODE = RM.get("metadata", {}).get("slice_mode") == "generic-structure"
try:  # optional local view taxonomy (gitignored; never shipped)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from graphify_taxonomy_config import load_local_taxonomy
    _LOCAL_TAX = load_local_taxonomy()
except Exception:
    _LOCAL_TAX = {}
_CUSTOM_REGIONS = (_LOCAL_TAX.get("regions") or None) if not GENERIC_MODE else None
_CUSTOM_ROUTES = (_LOCAL_TAX.get("region_routes") or None) if not GENERIC_MODE else None

if _CUSTOM_REGIONS:
    _labels = [str(r.get("id")) for r in _CUSTOM_REGIONS][:9]
elif GENERIC_MODE:
    _labels = [s["label"] for s in RM.get("slices", []) if s.get("label") != "other directories"][:9]
else:
    _labels = sorted({n.get("concept", "other") for n in RM.get("nodes", []) if n.get("concept")})[:9]
REGIONS = {lbl: REGION_SLOTS[i] for i, lbl in enumerate(_labels)}
FALLBACK_REGION = "other directories" if GENERIC_MODE else "other"
REGIONS[FALLBACK_REGION] = REGION_SLOTS[min(len(_labels), 9)]
GENERIC_REGION_KEYS = [k for k in REGIONS if k != FALLBACK_REGION]


def region_of(n):
    f = n.get("file_path", "").replace(chr(92), "/")
    l, c = n.get("label", ""), n.get("concept", "")
    if GENERIC_MODE:
        # generic repo: region = the node's actual top-level dir (matches the
        # generic slice labels); everything else lands in the fallback.
        top = (f.split("/", 1)[0] if "/" in f else "(root)") or "(root)"
        return top if top in REGIONS else FALLBACK_REGION
    if _CUSTOM_ROUTES:
        for rt in _CUSTOM_ROUTES:
            if rt.get("concept") and c == rt["concept"]: return rt["region"]
            if rt.get("path") and re.search(str(rt["path"]), f, re.I): return rt["region"]
            if rt.get("label") and re.search(str(rt["label"]), l, re.I): return rt["region"]
    # generic fallback: a node's own concept IS its region when that's a region
    return c if c in REGIONS else FALLBACK_REGION


def h01(s: str, salt: str) -> float:
    """Deterministic [0,1) hash (NOT runtime random -- regens stay byte-identical)."""
    return int(hashlib.md5((s + salt).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def hex_to_rgb(hx):
    return tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5))


def boost_hex(hx, f):
    """Brighten WITHIN hue (multiply-clamp) -- keeps saturation, raises intensity."""
    r, g, b = hex_to_rgb(hx)
    return "#{:02x}{:02x}{:02x}".format(min(255, int(r * f)), min(255, int(g * f)), min(255, int(b * f)))


def lerp_hex(rim_hex, t):
    """t=0 -> rim region hue; t=1 -> white-hot nucleus."""
    r0, g0, b0 = hex_to_rgb(rim_hex)
    r1, g1, b1 = WHITE_HOT
    return "#{:02x}{:02x}{:02x}".format(int(r0 + (r1 - r0) * t), int(g0 + (g1 - g0) * t), int(b0 + (b1 - b0) * t))


nodes = sorted(RM["nodes"], key=lambda n: -n["degree"])[:CAP]
if not nodes:
    raise SystemExit("read-model contains 0 nodes - nothing to render")
keep = {n["id"] for n in nodes}
deg = {n["id"]: n["degree"] for n in nodes}
hot_cut = sorted((n["degree"] for n in nodes), reverse=True)[max(0, int(len(nodes) * HOT_FRACTION) - 1)]
white_cut = sorted((n["degree"] for n in nodes), reverse=True)[min(39, len(nodes) - 1)]  # top-40 true centers burn white-hot (G5P.4: clamped for small graphs)

by_region = {}
node_region = {}
for n in nodes:
    rr = region_of(n)
    by_region.setdefault(rr, []).append(n)
    node_region[n["id"]] = rr

# ---- G5S ADAPTIVE BRAIN LAYOUT (de-tuned from the DFL monorepo slot geometry) ----
# Problem: REGION_SLOTS are fixed absolute lobe centers hand-fit to the DFL monorepo's
# region balance, and they are assigned by LABEL order, not size. A generic/public repo
# with fewer or lopsided regions fills only the first few slots -> the dominant lobe is
# shoved to a corner and the rest scatter into islands with big empty gaps (and the
# camera, also DFL-fit, frames the wrong box). Fix: when there is NO local custom
# taxonomy override (i.e. the published/generic path), PACK the lobes into a brain-shaped
# mass sized to THIS graph and FRAME the camera from the resulting bbox. The DFL local
# custom view (a local taxonomy override is present) keeps the approved slots + camera.
ADAPTIVE = not _CUSTOM_REGIONS
LOBE_K = 15.0                     # lobe spatial radius = LOBE_K * sqrt(member count)
MEET = 0.55                       # tangent center dist = (rA+rB)*MEET -> ~45% overlap = fused mass (few-lobe graphs stay fused after the x-stretch instead of splitting into a dumbbell)
XSTRETCH, YSQUASH = 1.3, 1.0      # gentle side-profile widen (brain silhouette without pulling side-by-side lobes apart)
lobe_r = {r: LOBE_K * math.sqrt(len(m)) for r, m in by_region.items()}

if ADAPTIVE:
    # Greedy center-seeking pack of heterogeneous lobe disks: biggest lobe at the core,
    # each later lobe placed at the most-central tangent position that does not over-
    # overlap an already-placed lobe. Deterministic (sort by size then id; fixed 4deg
    # angular search), robust for ANY region count (1..N) and any balance -> a compact
    # coherent brain whether the repo is small/sparse or large/dense.
    order = sorted(by_region.keys(), key=lambda r: (-len(by_region[r]), r))
    placed = {}
    for r in order:
        ri = lobe_r[r]
        if not placed:
            placed[r] = (0.0, 0.0)
            continue
        best = None
        for pj, (px, py) in list(placed.items()):
            d_target = (ri + lobe_r[pj]) * MEET
            for a in range(0, 360, 4):
                ang = math.radians(a)
                x, y = px + d_target * math.cos(ang), py + d_target * math.sin(ang)
                ok = True
                for pk, (kx, ky) in placed.items():
                    if pk == pj:
                        continue
                    if math.hypot(x - kx, y - ky) < (ri + lobe_r[pk]) * MEET * 0.985:
                        ok = False
                        break
                if ok:
                    score = math.hypot(x, y)
                    if best is None or score < best[0] - 1e-6:
                        best = (score, x, y)
        placed[r] = (best[1], best[2]) if best else (0.0, 0.0)
    # member-weighted recenter to origin, then ellipse-stretch + per-lobe hemisphere depth
    _tw = sum(len(m) for m in by_region.values()) or 1
    _gx = sum(placed[r][0] * len(by_region[r]) for r in placed) / _tw
    _gy = sum(placed[r][1] * len(by_region[r]) for r in placed) / _tw
    region_center = {}
    for r, (x, y) in placed.items():
        cz = min(150.0, max(55.0, 0.42 * lobe_r[r]))   # depth ~ lobe size (hemisphere amplitude)
        region_center[r] = (round((x - _gx) * XSTRETCH, 1), round((y - _gy) * YSQUASH, 1), round(cz, 1))
    LAYOUT_MODE = "adaptive-pack"
else:
    region_center = {r: (REGIONS[r][0], REGIONS[r][1], REGIONS[r][2]) for r in by_region}
    LAYOUT_MODE = "custom-fixed"

out_nodes, counts = [], {}
for r, members in by_region.items():
    _slot = REGIONS[r]
    rim, fam_cell = _slot[3], _slot[4]
    cx, cy, cz = region_center[r]                       # packed (adaptive) or hand-tuned slot (custom)
    rmax = lobe_r[r] if ADAPTIVE else (16 if len(members) > 250 else 13) * math.sqrt(len(members))  # lobes meet: continuous hero mass
    peripheral = r == FALLBACK_REGION
    for i, n in enumerate(members):  # members arrive degree-sorted: low i = hub = hot center
        t = h01(n["id"], "r")
        rad = rmax * (0.12 + 0.88 * t ** 0.55)  # volumetric center-dense fill (no shell banding)
        th = math.acos(2 * h01(n["id"], "t") - 1)
        ph = 6.2831853 * h01(n["id"], "p")
        x = round(cx + rad * math.sin(th) * math.cos(ph), 1)
        y = round(cy + rad * math.sin(th) * math.sin(ph), 1)
        hemi = 1 if h01(n["id"], "h") > 0.5 else -1   # left/right hemisphere shells
        z = round(hemi * abs(cz) * 0.9 + rad * math.cos(th) * 0.8, 1)  # both hemispheres suggested
        heat = (1 - min(1.0, i / (len(members) * 0.35 + 1))) * (0.30 if peripheral else 0.62)
        is_hub = n["degree"] >= hot_cut  # (used by color + cell below)
        # atlas v2 cell: hubs -> white-hot 0; region family 1-5; dim peripherals -> 6/7
        low = 1 if (heat < 0.10 and not is_hub and not peripheral) else 0  # LOD tier, NEVER hidden
        cell = (0 if n["degree"] >= white_cut
                else 7 if peripheral
                else fam_cell)
        # quantized heat (3 buckets) keeps shared-material count <= ~30 (research verdict)
        qheat = round(heat * 3) / 3 * (0.30 if peripheral else 0.62) if not is_hub else heat
        out_nodes.append(dict(
            id=n["id"], name=f'{n["label"]}\n{n["file_path"]}\n[{r}] deg={n["degree"]}',
            lbl=n["label"], fp=n["file_path"], reg=r, deg=n["degree"],  # clean fields for the dashboard postMessage (G5J)
        con=n.get("concept", ""),                                 # G5O.0: right-panel concept filter
            color=lerp_hex(rim, heat), qcolor=lerp_hex(rim, round(heat * 3) / 3),
            val=max(1, min(n["degree"], 30)), hub=1 if is_hub else 0, cell=cell, low=low,
            ph=round(6.2831853 * h01(n["id"], "a"), 2),
            sp=round((0.05 + 0.10 * h01(n["id"], "s")) * (1 if h01(n["id"], "d") > 0.5 else -1), 3),
            x=x, y=y, z=z, fx=x, fy=y, fz=z,
        ))
    counts[r] = len(members)

def link_tier(e):
    a, b = e["source"], e["target"]
    if min(deg.get(a, 0), deg.get(b, 0)) >= hot_cut:
        return 2                                  # hub-to-hub molten bridge
    if max(deg.get(a, 0), deg.get(b, 0)) >= hot_cut and node_region.get(a) == node_region.get(b):
        return 1                                  # strongest intra-region bridge
    return 0                                      # cross-region bulk -> Full mode only


def link_rgba(e, w):
    hue = REGIONS[node_region.get(e["source"], FALLBACK_REGION)][3]
    r, g, b = hex_to_rgb(hue)
    if w == 0:
        rr, gg, bb = int(r * 0.5 + 30), int(g * 0.5 + 30), int(b * 0.5 + 30)
        return f"rgba({rr},{gg},{bb},0.04)"
    # keep the hue alive (mild lift, not grey-wash); alpha keeps them secondary
    rr, gg, bb = int(r * 0.7 + 55), int(g * 0.7 + 55), int(b * 0.7 + 55)
    return f"rgba({rr},{gg},{bb},{0.12 if w == 2 else 0.055})"


def link_highlight(e):
    """Saturated source-region color for the selected-node neighborhood."""
    r, g, b = hex_to_rgb(REGIONS[node_region.get(e["source"], FALLBACK_REGION)][3])
    return f"rgba({r},{g},{b},0.9)"


# ---- G5N micro-separation: welded/stacked cores = near-identical positions, which
# also z-fight (equal-depth opaque ties flicker during rotation). Deterministic pass:
# spatial-hash neighbors closer than MIN_D get pushed apart along a hash direction;
# displacement is small + capped so the brain silhouette holds.
# G5N.1 widened MIN_D 8->14 + multi-sweep: pushing a pair apart can create a NEW
# violation against a third neighbor, so re-scan until a sweep moves nothing
# (capped at 8 sweeps). Counts are printed per sweep for the mission report.
# G5N.2 H4 (workflow-verified): a fixed floor is SCALE-BLIND -- the operator's
# flashing pair (red hub scale 30 x amber scale 20.4) sat 15.0 wu apart, above the
# old floor but far under their 37.8 combined sprite radii, so they stayed ~67%
# screen-overlapped and the whole overlap flipped owner in one frame at each
# twice-per-orbit depth crossing. For pairs involving a HUB the floor is now
# scale-aware: (scaleA+scaleB)*0.45 -- visible disk radius is ~0.42x scale (atlas
# padding + alphaTest cut), so 0.45 guarantees the disks never overlap at the
# crossing instant with margin, while staying gentle enough to converge without
# reshaping the hub-clustered lobes (0.85 cascaded: 886 moves, no convergence).
# Small pairs keep the 14.0 floor so the dense texture is preserved.
def _render_scale(n):
    if n.get("hub") == 1:
        return min(30.0, 20.0 + n["val"] * 0.35)
    if n.get("low") == 1 or n["cell"] >= 7:
        return 12.0
    return 15.0 + n["val"] * 0.3


def _pair_floor(a, b):
    # any pair big enough that (sA+sB)*0.45 exceeds the base floor gets the
    # scale-aware floor (G5N.2 global audit: 3 non-hub large pairs also sat
    # inside disk-overlap-at-crossing range; hub-only left them flashing)
    return max(14.0, (_render_scale(a) + _render_scale(b)) * 0.45)


MIN_D = 14.0
CELL_D = 28.0   # grid cell must cover the max scale-aware floor (2*30*0.45 = 27)
_sweep_counts = []
_hub_moved = 0
for _sweep in range(10):
    _grid = {}
    for _n in out_nodes:
        _grid.setdefault((int(_n["x"] // CELL_D), int(_n["y"] // CELL_D), int(_n["z"] // CELL_D)), []).append(_n)
    _moved = 0
    for _n in sorted(out_nodes, key=lambda q: q["id"]):
        _cx, _cy, _cz = int(_n["x"] // CELL_D), int(_n["y"] // CELL_D), int(_n["z"] // CELL_D)
        for _dx in (-1, 0, 1):
            for _dy in (-1, 0, 1):
                for _dz in (-1, 0, 1):
                    for _m in _grid.get((_cx + _dx, _cy + _dy, _cz + _dz), []):
                        if _m["id"] <= _n["id"]:
                            continue
                        _floor = _pair_floor(_n, _m)
                        ddx, ddy, ddz = _n["x"] - _m["x"], _n["y"] - _m["y"], _n["z"] - _m["z"]
                        d2 = ddx * ddx + ddy * ddy + ddz * ddz
                        if d2 >= _floor * _floor:
                            continue
                        th2 = math.acos(2 * h01(_n["id"] + _m["id"], "sx") - 1)
                        ph2 = 6.2831853 * h01(_n["id"] + _m["id"], "sy")
                        need = (_floor - math.sqrt(d2)) / 2 + 0.5
                        ux, uy, uz = math.sin(th2) * math.cos(ph2), math.sin(th2) * math.sin(ph2), math.cos(th2)
                        for _q, _sgn in ((_n, 1), (_m, -1)):
                            _q["x"] = round(_q["x"] + _sgn * ux * need, 1); _q["fx"] = _q["x"]
                            _q["y"] = round(_q["y"] + _sgn * uy * need, 1); _q["fy"] = _q["y"]
                            _q["z"] = round(_q["z"] + _sgn * uz * need, 1); _q["fz"] = _q["z"]
                        _moved += 1
                        if _floor > MIN_D:
                            _hub_moved += 1
    _sweep_counts.append(_moved)
    if _moved == 0:
        break
print(f"micro-separation: sweeps={_sweep_counts} (scale-aware hub-pair separations: {_hub_moved}; floor 14.0 / hub (sA+sB)*0.45)")

# ---- G5S adaptive camera + shell framing (computed from the FINAL node bbox) ----
# Same calibration constant for everyone: the approved DFL frame sat at distance 991
# from a view-plane bounding radius of ~717 -> ratio 1.38. Applying that to THIS graph's
# bbox makes the brain fill ~65-80% of a 16:9 viewport regardless of repo size. The DFL
# custom path keeps the exact approved literals (visually identical).
_xs = [n["x"] for n in out_nodes]; _ys = [n["y"] for n in out_nodes]; _zs = [n["z"] for n in out_nodes]
BB = dict(minx=min(_xs), maxx=max(_xs), miny=min(_ys), maxy=max(_ys), minz=min(_zs), maxz=max(_zs))


def _fmt(v):
    """Int-clean number formatting so the custom path stays byte-identical to the old literals."""
    return str(int(v)) if float(v) == int(v) else repr(round(float(v), 1))


if ADAPTIVE:
    _wsum = sum(max(1, n["deg"]) for n in out_nodes) or 1
    _dcx = sum(n["x"] * max(1, n["deg"]) for n in out_nodes) / _wsum    # degree-weighted centroid (dense hub mass)
    _dcy = sum(n["y"] * max(1, n["deg"]) for n in out_nodes) / _wsum
    _dcz = sum(n["z"] * max(1, n["deg"]) for n in out_nodes) / _wsum
    _bcx = (BB["minx"] + BB["maxx"]) / 2; _bcy = (BB["miny"] + BB["maxy"]) / 2; _bcz = (BB["minz"] + BB["maxz"]) / 2
    # 50/50 blend with the geometric center: lean toward the dense mass for an
    # interesting frame, but cap how far a hub-dominated region can pull the frame
    # off-center (adversarial-grill finding: pure degree-weighting drifted ~7% on a
    # hub-only graph; the blend halves that and stays robust for pathological balances).
    LOOK_X = round(0.5 * _bcx + 0.5 * _dcx, 1)
    LOOK_Y = round(0.5 * _bcy + 0.5 * _dcy, 1)
    LOOK_Z = round(0.5 * _bcz + 0.5 * _dcz, 1)
    _hw = (BB["maxx"] - BB["minx"]) / 2; _hh = (BB["maxy"] - BB["miny"]) / 2
    _Rview = math.hypot(_hw, _hh)
    CAM_DIST = max(420.0, _Rview * 1.38)
    _DIR = (0.1413, 0.0404, 0.9891)                       # approved 3/4 view direction (DFL pos-look, normalized)
    CAM_X = round(LOOK_X + _DIR[0] * CAM_DIST, 1); CAM_Y = round(LOOK_Y + _DIR[1] * CAM_DIST, 1); CAM_Z = round(LOOK_Z + _DIR[2] * CAM_DIST, 1)
    CAM_FAR = round(max(6000.0, CAM_DIST * 2.2 + _Rview))
    CAM_MAXD = round(CAM_DIST + _Rview * 2.0)
    SHELL_SX = round(max(_hw, 80) * 1.18, 1); SHELL_SY = round(max(_hh, 60) * 1.18, 1)
    SHELL_SZ = round(max(BB["maxz"] - BB["minz"], 180) / 2 * 1.3, 1)
    SHELL_PX = round((BB["minx"] + BB["maxx"]) / 2, 1); SHELL_PY = round((BB["miny"] + BB["maxy"]) / 2, 1); SHELL_PZ = round((BB["minz"] + BB["maxz"]) / 2, 1)
else:
    CAM_X, CAM_Y, CAM_Z = 80, 50, 980                     # exact approved DFL frame (byte-identical)
    LOOK_X, LOOK_Y, LOOK_Z = -60, 10, 0
    CAM_DIST = math.hypot(CAM_X - LOOK_X, CAM_Y - LOOK_Y, CAM_Z - LOOK_Z)
    CAM_FAR, CAM_MAXD = 6000, 4800
    SHELL_SX, SHELL_SY, SHELL_SZ = 660, 480, 440
    SHELL_PX, SHELL_PY, SHELL_PZ = -60, 15, 0

links = [dict(source=e["source"], target=e["target"], w=(w := link_tier(e)),
              c=link_rgba(e, w), hc=link_highlight(e),
              fam=REGIONS[node_region.get(e["source"], FALLBACK_REGION)][4],
              rot=round(6.2832 * h01(e["source"] + e["target"], "cr"), 2))
         for e in RM["edges"] if e["source"] in keep and e["target"] in keep]
tier_counts = {t: sum(1 for l in links if l["w"] == t) for t in (2, 1, 0)}
low_count = sum(1 for n in out_nodes if n["low"] == 1)
data = json.dumps(dict(nodes=out_nodes, links=links), separators=(",", ":"))
legend = " &middot; ".join(f'<span class="ldot" data-fam="{REGIONS[r][4]}" style="color:{REGIONS[r][3]}">&#9679;</span> {r} ({c})' for r, c in sorted(counts.items(), key=lambda kv: -kv[1]))
md = RM["metadata"]

html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Hivemind Molten Brain - PROTOTYPE</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
<style>html,body{{margin:0;height:100%;background:radial-gradient(ellipse at 50% 42%, #0a0a0c 0%, #040405 55%, #000 100%);color:#ddd;font:13.5px/1.5 Inter,system-ui,sans-serif;overflow:hidden}}
#g{{box-shadow:inset 0 0 140px #000, inset 0 1px 0 rgba(255,122,24,.18);opacity:0;transition:opacity .5s ease}}  /* G5P.0a: hidden until the atlas lands (pre-atlas default spheres = the operator's ghost flash) */
#g.ready{{opacity:1}}
/* black-glass chamber: EDGE-ONLY reflections + rims over the render -- the
   center stays fully transparent so the brain is unobstructed */
#glass{{position:fixed;inset:0;z-index:4;pointer-events:none;
  background:
    linear-gradient(115deg, rgba(255,255,255,.045) 0%, transparent 11%) no-repeat,
    linear-gradient(295deg, rgba(255,255,255,.03) 0%, transparent 9%) no-repeat,
    linear-gradient(180deg, rgba(255,122,24,.06) 0%, transparent 3.5%, transparent 96.5%, rgba(255,122,24,.045) 100%);
  box-shadow:inset 0 0 90px rgba(0,0,0,.78), inset 0 1px 0 rgba(255,255,255,.06), inset 0 -1px 0 rgba(255,122,24,.10)}}
/* HUD = FORGE glass-nav: rgba(10,10,10,.65) + blur(22px) + steel-700 hairline */
#hud{{position:fixed;top:0;left:0;right:0;z-index:5;background:rgba(10,10,10,.65);-webkit-backdrop-filter:blur(22px);backdrop-filter:blur(22px);border-bottom:1px solid #262626;box-shadow:inset 0 -1px 0 rgba(255,122,24,.08);padding:8px 13px}}
#hud b{{color:#f5f5f5;font:700 15px Orbitron,Inter,system-ui;letter-spacing:.02em}} .warn{{color:#8a8a8a;font:400 11.5px 'JetBrains Mono',ui-monospace,monospace}}
body.embed #hud{{display:none}}</style></head><body>
<div id="glass"></div>
<div id="hud"><a id="backdash" href="/views/graphify-dashboard.html" style="float:right;margin:2px 0 0 12px;font:600 11.5px Inter,system-ui;letter-spacing:.08em;text-transform:uppercase;color:#ffae3c;border:1px solid rgba(255,138,56,.4);border-radius:9999px;padding:4px 13px;text-decoration:none;background:linear-gradient(180deg,rgba(80,42,10,.4),rgba(34,17,5,.46));box-shadow:inset 0 1px 0 rgba(255,210,160,.2)">&larr; Back to Dashboard</a><b>Hivemind Molten Brain</b>
 <span style="border:1px solid rgba(255,138,56,.3);border-radius:9999px;padding:2px 10px;font:500 10px 'JetBrains Mono',monospace;margin-left:10px;color:#c8935a;letter-spacing:.04em">PROTOTYPE &middot; CDN pinned 3d-force-graph@1.80.0 + three@0.183.0 &middot; not production</span>
 <div class="warn">Molten structural map &mdash; NOT runtime truth &middot; clusters &rarr; brain nuclei &middot; degree &rarr; core size/heat &middot; loose nodes dim &middot; build {md["graph_build_mode"]} &middot; built_at {str(md["graph_built_at_commit"])[:10]} &middot; {len(out_nodes)}/{md["emitted_nodes"]} nodes &middot; {len(links)} bridges &middot; drag=rotate &middot; wheel=zoom &middot; click=fly</div>
 <div style="font-size:11.5px;margin-top:3px">{legend}</div></div>
<div id="g"></div>
<script src="https://cdn.jsdelivr.net/npm/3d-force-graph@1.80.0/dist/3d-force-graph.min.js"></script>
<script>const D = {data};</script>
<script type="module">
// Revision-matched bloom import (bundled three r183 <-> esm.sh three@0.183.0).
// NEVER define window.THREE here: the UMD bundle silently ADOPTS a pre-existing
// global THREE instead of its bundled copy (version-skew trap).
import {{ UnrealBloomPass }} from 'https://esm.sh/three@0.183.0/examples/jsm/postprocessing/UnrealBloomPass.js';
import {{ TextureLoader, Sprite, SpriteMaterial, SRGBColorSpace, Group, AdditiveBlending, Vector2 }} from 'https://esm.sh/three@0.183.0';

let MODE = 'full';   // G5M operator decision: Full always on -- everything connected (Brain/Full toggle removed)

// ---- palettes (G5E + G5F expansion): one atlas per palette (same LOCKED core_5 + v4
// LUT, family triplets only) + per-family neon hexes for links/legend.
// G5F: DEFAULT = 'obsidian' (Obsidian Neon -- the approved neon look minus acid green;
// molten orange is brand-aligned AND cyan's complement across the region boundary).
// 'neon' (classic) stays selectable; its link colors stay python-baked (l.c/l.hc).
// All other palettes compute link colors from family hues in JS using the same
// lift/alpha formulas the generator bakes. 'custom' = UI-only placeholder (disabled).
const AT = '/design/graphify-molten-cores-v4/molten_core_atlas_v4';  // absolute: per-project views live deeper than /views/ (G5P.4a operator catch)
const PALETTES = {{
  obsidian:   {{ label: 'Obsidian Neon',        atlas: AT + '_obsidian.png',
                fam: ['#ff4d5e','#2f6bff','#ffb300','#00e5ff','#ff7a18','#8b2fff','#ff2fa0','#6e7894'] }},
  neon:       {{ label: 'Neon Brain (classic)', atlas: AT + '.png',
                fam: ['#ff4d5e','#2f6bff','#ffb300','#00e5ff','#76ff03','#8b2fff','#ff2fa0','#6e7894'] }},
  forge:      {{ label: 'Molten Forge',         atlas: AT + '_forge.png',
                fam: ['#ff6a1a','#e8372f','#ffc23d','#ff9352','#5f8fe8','#9b4dff','#ff2f55','#6e635a'] }},
  ice:        {{ label: 'Cyber Ice',            atlas: AT + '_ice.png',
                fam: ['#ff4fd8','#2456ff','#9fb8ff','#3ae8ff','#6a5bff','#b44dff','#ff2f7a','#5c6880'] }},
  royal:      {{ label: 'Royal Plasma',         atlas: AT + '_royal.png',
                fam: ['#ffc63d','#2f6bff','#6a2fd8','#00b3ff','#ff2fd0','#7a1fff','#ff3f8e','#6e6480'] }},
  enterprise: {{ label: 'Toxic-Free Enterprise', atlas: AT + '_enterprise.png',
                fam: ['#ff6a5e','#3f7fe8','#ffb347','#00c8b4','#2fa8c8','#8a5cf0','#e8538e','#5c6470'] }},
  access:     {{ label: 'High Contrast (Accessibility)', atlas: AT + '_access.png',
                fam: ['#d55e00','#0072b2','#f0e442','#56b4e9','#009e73','#cc79a7','#e69f00','#999999'] }},
  space:      {{ label: 'Deep Space',           atlas: AT + '_space.png',
                fam: ['#ffb347','#4b3fd8','#f0c987','#22d3ee','#d946ef','#7c3aed','#fb7185','#64748b'] }},
  solar:      {{ label: 'Solar Storm',          atlas: AT + '_solar.png',
                fam: ['#ffd24a','#2456e8','#ff7a5e','#4ab8ff','#ff3fc8','#8b5cf6','#ff4060','#6e6a64'] }},
}};
let PALETTE = localStorage.getItem('graphify-palette') || 'obsidian';
if (!PALETTES[PALETTE]) PALETTE = 'obsidian';   // also migrates removed cool/contrast keys
const famRGB = f => {{ const h = PALETTES[PALETTE].fam[f] || '#888888';
  return [parseInt(h.slice(1,3),16), parseInt(h.slice(3,5),16), parseInt(h.slice(5,7),16)]; }};
const linkCol = l => {{
  if (PALETTE === 'neon') return l.c;                  // python-baked default (approved look)
  const [r,g,b] = famRGB(l.fam);
  if (l.w === 0) return `rgba(${{Math.round(r*.5+30)}},${{Math.round(g*.5+30)}},${{Math.round(b*.5+30)}},0.04)`;
  return `rgba(${{Math.round(r*.7+55)}},${{Math.round(g*.7+55)}},${{Math.round(b*.7+55)}},${{l.w === 2 ? 0.12 : 0.055}})`;
}};
const linkHi = l => {{
  if (PALETTE === 'neon') return l.hc;
  const [r,g,b] = famRGB(l.fam);
  return `rgba(${{r}},${{g}},${{b}},0.9)`;
}};

// ---- selection / 3D navigation state (operator: click a core -> light its pathways) ----
let SELECTED = null;
const NEIGHBORS = new Map();   // id -> Set(neighbor ids), built from raw D.links
for (const l of D.links) {{
  if (!NEIGHBORS.has(l.source)) NEIGHBORS.set(l.source, new Set());
  if (!NEIGHBORS.has(l.target)) NEIGHBORS.set(l.target, new Set());
  NEIGHBORS.get(l.source).add(l.target);
  NEIGHBORS.get(l.target).add(l.source);
}}
const lid = v => (v && v.id) || v;     // link endpoints become objects after graphData
const touchesSel = l => SELECTED && (lid(l.source) === SELECTED || lid(l.target) === SELECTED);

const HIDDEN_CON = new Set();                         // G5O.0: dashboard-driven concept filter
const CON_BY_ID = new Map(D.nodes.map(n => [n.id, n.con]));
const NODE_BY_ID = new Map(D.nodes.map(n => [n.id, n]));   // G5P: local ask-console lookups
const G = ForceGraph3D({{ controlType: 'orbit' }})(document.getElementById('g'))
  .graphData(D)
  .backgroundColor('#000000')                  // pure black glass -- neon cores pop (G5F)
  .nodeColor(n => n.color)            // python-baked heat ramp: white-hot nucleus -> region rim hue
  .nodeVal(n => n.val)
  .nodeVisibility(n => !HIDDEN_CON.has(n.con))        // G5O.0: concept filter (Group.visible)
  .nodeOpacity(1.0)
  .nodeResolution(10)
  .nodeLabel(n => n.name.replaceAll('\\n','<br>'))
  .linkWidth(l => touchesSel(l) ? 1.2 : 0)            // selected pathways gain body
  .linkCurvature(l => l.w === 2 ? 0.25 : l.w === 1 ? 0.14 : 0)  // neural arcs, not graph wires
  .linkCurveRotation(l => l.rot || 0)                            // organic spread of arc planes
  .linkOpacity(0.5)                   // global multiplier x rgba alpha = per-link tiers
  .linkVisibility(l => !HIDDEN_CON.has(CON_BY_ID.get(lid(l.source))) && !HIDDEN_CON.has(CON_BY_ID.get(lid(l.target))) && (touchesSel(l) || MODE === 'full' || l.w > 0))  // hidden-concept endpoints hide the link (G5O.0); selection reveals ALL its pathways
  .linkColor(l => touchesSel(l) ? linkHi(l) : linkCol(l))  // neighborhood = saturated region color (palette-aware)
  .cooldownTicks(0)                   // positions fixed in python; skip dead n-body burn
  .enableNodeDrag(false)
  .onNodeClick(n => selectNode(n))
  .onBackgroundClick(() => {{ console.log('[brain] onBackgroundClick'); SELECTED = null; refreshSelection(); postSelected(); }});

function selectNode(n) {{                              // shared by real clicks + the QA debug hook
  console.log('[brain] selectNode', n.id);
  SELECTED = (SELECTED === n.id) ? null : n.id;       // click again to deselect
  refreshSelection();
  postSelected();
  const dist = 220, ratio = 1 + dist / Math.hypot(n.fx, n.fy, n.fz || 1);
  flyTo(n.fx * ratio, n.fy * ratio, (n.fz || 1) * ratio, n.fx, n.fy, n.fz || 0, NODE_FLY_MIN_MS, NODE_FLY_MAX_MS);
}}
// QA-only hook (local prototype): synthetic CDP/JS clicks are classified as drags by
// three-render-objects' click recognizer, so automated visual QA drives selection here.
// Real-mouse clicks use the exact same selectNode path above.
window.__brainSelect = id => {{
  const n = G.graphData().nodes.find(n => n.id === id);
  if (n) selectNode(n); else {{ SELECTED = null; refreshSelection(); }}
  return SELECTED;
}};

function refreshSelection() {{
  G.linkColor(G.linkColor());          // re-evaluate accessors
  G.linkVisibility(G.linkVisibility());
  G.linkWidth(G.linkWidth());
  const nb = SELECTED ? NEIGHBORS.get(SELECTED) || new Set() : new Set();
  for (const [id, g] of GLOWS_BY_ID) {{
    g.sel = SELECTED === id ? 2 : nb.has(id) ? 1 : 0; // 2=selected, 1=neighbor, 0=normal
  }}
}}
const GLOWS_BY_ID = new Map();

// G5J jitter investigation fix: UnrealBloomPass with an undefined resolution uses a
// 256x256 internal buffer -- massively undersampled vs the canvas, so bright core
// halos shimmer/crawl during rotation (reads as stutter when nodes cross). Render
// the bloom chain at HALF CANVAS resolution instead.
// G5K jitter bundle (render-perf lane verdict): the bloom high-pass default
// smoothWidth (~0.01) is a BINARY luminance gate -- overlapping breathing glows
// sum past/below the threshold as rotation changes overlap, snapping local halos
// on/off (the center "flashing"). Soften the knee (threshold .38, smoothWidth .22,
// radius .55 smooths the half-res chain). Hub halos sit far above the knee, so the
// approved breathing look is unchanged.
const bloom = new UnrealBloomPass(
  new Vector2(Math.max(640, window.innerWidth >> 1), Math.max(360, window.innerHeight >> 1)),
  0.8, 0.55, 0.38);
if (bloom.highPassUniforms && bloom.highPassUniforms['smoothWidth']) bloom.highPassUniforms['smoothWidth'].value = 0.22;
G.postProcessingComposer().addPass(bloom);
// Composer path bypasses canvas MSAA entirely -> 1px alpha-cutout edges shimmer at
// dpr=1. Supersample at 1.25 (pixel cost ~1.56x; the dominant cost -- 2,400 sprite
// draw calls -- is unchanged). Also pushes sprites to shallower mips (less erosion).
G.renderer().setPixelRatio(1.25);
G.postProcessingComposer().setPixelRatio(1.25);
G.postProcessingComposer().setSize(window.innerWidth, window.innerHeight);

const c = G.controls();
const BRAIN_SPIN_DEFAULT = 0.5;                     // ~2 min/orbit = the 1.00x slider default
c.autoRotate = true; c.autoRotateSpeed = BRAIN_SPIN_DEFAULT;
// G5O.2 operator motion multipliers (dashboard MOTION CONTROLS sliders, postMessage).
// spin scales autoRotateSpeed only (autoRotate boolean stays pause-owned, so Pause
// overrides any slider value and a speed change while paused applies on resume);
// fly divides the G5O.1b glide duration; drift scales the glow-anim clock.
const MOTION = {{ spin: 1, fly: 1, drift: 1 }};
const applyMotion = m => {{
  if (m.spin !== undefined) {{ MOTION.spin = +m.spin || 1; c.autoRotateSpeed = BRAIN_SPIN_DEFAULT * MOTION.spin; }}
  if (m.fly !== undefined) MOTION.fly = +m.fly || 1;
  if (m.drift !== undefined) MOTION.drift = +m.drift || 1;
}};
window.__motion = () => ({{ spin: MOTION.spin, fly: MOTION.fly, drift: MOTION.drift, rotSpeed: c.autoRotateSpeed, auto: c.autoRotate, driftT: (window.__driftT ? window.__driftT() : -1), az: Math.atan2(cam ? 0 : 0, 1) }});  // QA probe (driftT wired below)

// ---- pause/resume (G5J): real product control. Grab = implicit pause (state
// reflected); interaction stays live while paused; reset/palette never touch it.
let PAUSED = false;
const notifyPause = () => {{ try {{ if (window.parent !== window) window.parent.postMessage({{graphify: 'paused', value: PAUSED}}, '*'); }} catch (e) {{}} }};
const setPaused = v => {{ PAUSED = !!v; c.autoRotate = !PAUSED; notifyPause(); if (typeof paintPause === 'function') paintPause(); }};
window.__brainPause = v => setPaused(v === undefined ? !PAUSED : v);
window.__brainOrbitSpeed = v => {{ c.autoRotateSpeed = v; }};   // QA: slow-orbit stress watch (G5N.1)
c.addEventListener('start', () => {{ if (!PAUSED) setPaused(true); }});  // pause on grab (state-honest)

// ---- selected-node channel (G5J): the dashboard right panel renders this.
const postSelected = () => {{ try {{
  if (window.parent === window) return;
  const n = SELECTED ? D.nodes.find(x => x.id === SELECTED) : null;
  window.parent.postMessage({{graphify: 'selected', node: n ? {{
    id: n.id, lbl: n.lbl, fp: n.fp, reg: n.reg, deg: n.deg,
    nb: (NEIGHBORS.get(n.id) || new Set()).size }} : null}}, '*');
}} catch (e) {{}} }};

window.addEventListener('message', e => {{
  if (e.origin !== location.origin) return;     // same-origin only (G5K security)
  const d = e.data || {{}};
  if (d.graphify === 'toggle-pause') setPaused(!PAUSED);
  if (d.graphify === 'set-pause') setPaused(!!d.value);
  if (d.graphify === 'reset') resetView();
  if (d.graphify === 'motion') applyMotion(d);        // G5O.2 dashboard sliders
  if (d.graphify === 'neighbors-req') {{               // G5P: ask console -- local neighbor listing
    const items = [];
    for (const l of D.links) {{
      const a = lid(l.source), b = lid(l.target);
      if (a === d.id || b === d.id) {{ const n = NODE_BY_ID.get(a === d.id ? b : a); if (n) items.push({{ lbl: n.lbl, reg: n.reg, deg: n.deg }}); }}
    }}
    items.sort((x, y) => y.deg - x.deg);
    try {{ if (window.parent !== window) window.parent.postMessage({{ graphify: 'neighbors', id: d.id, total: items.length, items: items.slice(0, 8) }}, '*'); }} catch (e) {{}}
  }}
  if (d.graphify === 'find-req') {{                   // G5P.1: local node lookup/jump (ask console)
    const q = String(d.q || '').toLowerCase().trim();
    let best = null, matches = 0;
    if (q) for (const n of D.nodes) {{
      if (HIDDEN_CON.has(n.con)) continue;            // filtered-out nodes are not jump targets
      const lbl = String(n.lbl || '').toLowerCase(), nid = String(n.id || '').toLowerCase();
      let score = 0;
      if (lbl === q || nid === q) score = 3; else if (lbl.startsWith(q)) score = 2; else if (lbl.includes(q) || nid.includes(q)) score = 1;
      if (!score) continue;
      matches++;
      if (!best || score > best.score || (score === best.score && (n.deg || 0) > (best.n.deg || 0))) best = {{ n, score }};
    }}
    if (best) {{ const gn = G.graphData().nodes.find(x => x.id === best.n.id); if (gn) selectNode(gn); }}
    try {{ if (window.parent !== window) window.parent.postMessage({{ graphify: 'find-res', q: d.q, matches, hit: best ? {{ id: best.n.id, lbl: best.n.lbl, reg: best.n.reg }} : null }}, '*'); }} catch (e) {{}}
  }}
  if (d.graphify === 'concepts') {{                   // G5O.0: dashboard right-panel filter
    HIDDEN_CON.clear(); (d.hidden || []).forEach(k => HIDDEN_CON.add(k));
    if (SELECTED && HIDDEN_CON.has(SELECTED.con)) {{ SELECTED = null; refreshSelection(); postSelected(); }}
    G.nodeVisibility(G.nodeVisibility()); G.linkVisibility(G.linkVisibility());
  }}
}});
// Hero first-frame: lookAt = dense-mass center of the side-profile oval (x ~-60),
// camera slightly right/above for 3/4 depth, distance tuned so the brain fills
// ~65-80% of the viewport (composition pass; not a random close-up).
G.cameraPosition({{x: {_fmt(CAM_X)}, y: {_fmt(CAM_Y)}, z: {_fmt(CAM_Z)}}}, {{x: {_fmt(LOOK_X)}, y: {_fmt(LOOK_Y)}, z: {_fmt(LOOK_Z)}}});
// G5N.2 H1 fix (workflow-verified): three-render-objects defaults are near=0.1 and
// far=skyRadius*2.5=125000, which quantize the 24-bit depth buffer to ~0.6 world
// units at orbit depth -- a depth crossing of two overlapping cores then sits in a
// multi-frame z-tie, and the glow polygonOffset band becomes +-2.3 wu wide (the
// sporadic halo-pops-in-front flash). near=5/far=6000 shrinks the quantum ~50x.
// maxDistance keeps wheel zoom-out short of the new far plane (4800+853 < 6000).
// G5O.1b custom camera glide. The lib's cameraPosition was the jump source
// (operator video, verified in the pinned artifact): its lookAt tween runs at
// duration/3 (view rotation -- the dominant screen motion at close zoom -- whipped
// in 500ms, Quadratic.Out = fastest at the start) and it never cancels a prior
// tween (rapid node clicks stack tweens that fight for the camera every frame).
// This glide: cubic EASE-IN-OUT, position + lookAt synchronized over the SAME
// duration, distance-aware timing, and one in-flight handle (new fly or a manual
// grab cancels cleanly).
const NODE_FLY_MIN_MS = 1600;   // floor for a neighbor hop
const NODE_FLY_MAX_MS = 3200;   // cap for a cross-brain hop
const NODE_FLY_RATE = 1.6;      // +ms per world-unit of camera travel
const RESET_FLY_MIN_MS = 1100;  // Reset View -- a touch quicker, still smooth
const RESET_FLY_MAX_MS = 2400;
const cam = G.camera();
const FLY = {{ id: null }};
function cancelFly() {{ if (FLY.id) {{ cancelAnimationFrame(FLY.id); FLY.id = null; }} }}
function flyTo(px, py, pz, lx, ly, lz, minMs, maxMs) {{
  cancelFly();
  const p0 = cam.position.clone(), t0 = c.target.clone();
  const travel = Math.hypot(px - p0.x, py - p0.y, pz - p0.z);
  const ms = Math.min(maxMs, Math.max(minMs, 700 + travel * NODE_FLY_RATE)) / (MOTION.fly || 1);  // G5O.2: fly-speed slider
  const start = performance.now();
  function step(now) {{
    const u = Math.min(1, (now - start) / ms);
    const e = u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2;  // cubic in-out
    cam.position.set(p0.x + (px - p0.x) * e, p0.y + (py - p0.y) * e, p0.z + (pz - p0.z) * e);
    c.target.set(t0.x + (lx - t0.x) * e, t0.y + (ly - t0.y) * e, t0.z + (lz - t0.z) * e);
    FLY.id = u < 1 ? requestAnimationFrame(step) : null;
  }}
  FLY.id = requestAnimationFrame(step);
}}
c.addEventListener('start', cancelFly);               // manual grab takes over instantly
const fixCam = () => {{ cam.near = 5; cam.far = {_fmt(CAM_FAR)}; cam.updateProjectionMatrix(); c.maxDistance = {_fmt(CAM_MAXD)}; }};
fixCam();
// three-render-objects assigns far=skyRadius*2.5 during ASYNC init AFTER this inline
// code (probed live: near=5 survived, far reverted to 125000) -- re-assert post-init.
setTimeout(fixCam, 800); setTimeout(fixCam, 2500);
window.__brainCam = () => ({{ near: cam.near, far: cam.far, dist: cam.position.distanceTo(c.target) }});  // QA probe
// G5S layout QA hook: active regions / displayed nodes / post-layout bbox / camera
// distance / chosen packing mode -- lets automated QA assert the brain is framed.
window.__brainLayoutDebug = () => ({{
  mode: '{LAYOUT_MODE}', adaptive: {str(ADAPTIVE).lower()},
  activeRegions: {len(counts)}, displayedNodes: {len(out_nodes)},
  bbox: {{ x: [{_fmt(BB["minx"])}, {_fmt(BB["maxx"])}], y: [{_fmt(BB["miny"])}, {_fmt(BB["maxy"])}], z: [{_fmt(BB["minz"])}, {_fmt(BB["maxz"])}] }},
  look: {{ x: {_fmt(LOOK_X)}, y: {_fmt(LOOK_Y)}, z: {_fmt(LOOK_Z)} }},
  bakedDist: {_fmt(round(CAM_DIST))}, camDist: Math.round(cam.position.distanceTo(c.target))
}});
c.target.set({_fmt(LOOK_X)}, {_fmt(LOOK_Y)}, {_fmt(LOOK_Z)});

// ---- premium backdrop + containment shell (G5D premium pass) ----
// Backdrop: the operator-APPROVED v2 obsidian plate (ignored staging; asset-commit
// gate pending) as scene background -- neon cores pop vs flat black.
// Shell: faint dark ellipsoid (BackSide) around the node mass so cores read as
// contained inside a brain-shaped volume; sits behind cores, never competes.
import('https://esm.sh/three@0.183.0').then(({{ SphereGeometry, Mesh, MeshBasicMaterial, BackSide }}) => {{
  // glass chamber treatment: NO pasted image backdrop (operator correction) --
  // the obsidian/glass asset is a MATERIAL/STYLE reference; the page carries a
  // CSS glass-depth vignette and the shell suggests the chamber.
  const shell = new Mesh(new SphereGeometry(1, 48, 32), new MeshBasicMaterial({{
    color: 0x06090e, transparent: true, opacity: 0.22, side: BackSide, depthWrite: false,
  }}));
  shell.scale.set({_fmt(SHELL_SX)}, {_fmt(SHELL_SY)}, {_fmt(SHELL_SZ)});   // wraps the (adaptive or DFL-fixed) brain bbox
  shell.position.set({_fmt(SHELL_PX)}, {_fmt(SHELL_PY)}, {_fmt(SHELL_PZ)});
  shell.renderOrder = -2;
  G.scene().add(shell);
}});

// ---- MOLTEN-CORE ATLAS SPRITES (G5D-molten-core-atlas-v1, research-verdict Path A) ----
// Juggernaut 4x2 grayscale atlas; region hue arrives via material.color multiplication.
// AdditiveBlending on black = transparent (no alpha cut); depthWrite:false preempts the
// known sprite depth artifacts (#214/#458/#430). Accessor set ONCE after texture load
// (one deliberate rebuild; never swapped again). Animation = own rAF loop (engine hooks
// are dead at cooldownTicks(0)); ALL cores: tiered scale/glow PULSE only (no spin),
// hash-deterministic phases baked in python. If the atlas fails to load, the default
// sphere cores remain (procedural placeholder fallback, labeled in the HUD).
const cells8 = base => [...Array(8)].map((_, i) => {{
  const t = base.clone();
  t.repeat.set(0.25, 0.5);
  t.offset.set((i % 4) * 0.25, i < 4 ? 0.5 : 0);     // PNG row 0 = top => offset.y 0.5
  t.needsUpdate = true;
  return t;
}});
const MAT_REG = [];                                   // every sprite material + its cell (palette swap)
window.__setPalette = name => {{                      // wired to the control bar below
  if (!PALETTES[name]) return;
  PALETTE = name;
  try {{ localStorage.setItem('graphify-palette', name); }} catch (e) {{}}
  new TextureLoader().load(PALETTES[name].atlas, b => {{
    b.colorSpace = SRGBColorSpace;
    const t8 = cells8(b);
    for (const r of MAT_REG) {{ r.m.map = t8[r.cell]; r.m.needsUpdate = true; }}
    G.linkColor(G.linkColor());                       // re-evaluate palette-aware link colors
    document.querySelectorAll('.ldot').forEach(d => d.style.color = PALETTES[name].fam[+d.dataset.fam]);
    if (typeof paintPal === 'function') paintPal();
    console.log('[brain] palette ->', name);
  }}, undefined, () => console.warn('[brain] palette atlas missing for ' + name + ' - kept current cores (design pack incomplete)'));
}};
new TextureLoader().load(PALETTES[PALETTE].atlas, base => {{
  base.colorSpace = SRGBColorSpace;
  const tex = cells8(base);
  if (PALETTE !== 'neon') document.querySelectorAll('.ldot').forEach(d => d.style.color = PALETTES[PALETTE].fam[+d.dataset.fam]);
  // G5F flicker fix: bodies are ALPHA-CUTOUT OPAQUE (transparent:false + alphaTest).
  // Transparent sprites are painter-sorted back-to-front EVERY frame -- when cores
  // cross during rotation their sort order swaps and the overlap POPS. Opaque-pass
  // sprites resolve per-pixel via the depth buffer (no sorting, no pop); alphaTest
  // still cuts the circular silhouette. Glow overlays stay additive (order-independent).
  const mat = (cell, color, opacity) => {{
    const m = new SpriteMaterial({{
      map: tex[cell], color, opacity,
      transparent: false, alphaTest: 0.38, depthWrite: true, depthTest: true,
    }});
    MAT_REG.push({{ m, cell }});
    return m;
  }};
  const shared = new Map();                            // <=~30 quantized statics
  const sharedMat = (cell, color, op) => {{
    const k = cell + '|' + color + '|' + op;
    if (!shared.has(k)) shared.set(k, mat(cell, color, op));
    return shared.get(k);
  }};
  // TWO-LAYER cores (operator: glow-only pulse, NO size pulse, NO spin):
  // layer 1 = STATIC opaque body (normal blending, depthWrite) -- never animated;
  // layer 2 = additive glow overlay of the SAME cell (dark body adds ~zero, neon
  // fissures double up) whose OPACITY breathes. Size and orientation stay fixed.
  const glows = [];
  G.nodeThreeObject(n => {{
    const hub = n.hub === 1;
    const op = 1.0;  // all bodies solid; dim tier dims via its cell colors
    const grp = new Group();
    const body = new Sprite(hub ? mat(n.cell, '#ffffff', 1.0) : sharedMat(n.cell, '#ffffff', op));
    const sc = hub ? Math.min(30, 20 + n.val * 0.35) : n.low === 1 ? 12 : n.cell >= 7 ? 12 : 15 + n.val * 0.3;
    body.scale.set(sc, sc, 1);
    body.renderOrder = n.cell + 1;
    grp.add(body);
    // G5N.1 root-cause fix: G5L's depthTest:false made glows X-RAY -- an occluded
    // node's halo still drew ON TOP of the nearer body (renderOrder 20 + no depth
    // test = every halo over every body), so during rotation a pair read "behind,
    // then in front" (the operator's orange-vs-red flash). Glows now DEPTH-TEST
    // (genuinely nearer bodies occlude them) and win the equal-depth tie against
    // their OWN body via polygonOffset pulled toward the camera -- the G5L
    // crossing-pop cannot return because ties resolve deterministically to the glow.
    const glowMat = new SpriteMaterial({{
      map: tex[n.cell], color: '#ffffff', transparent: true,
      blending: AdditiveBlending, depthWrite: false, depthTest: true,
      polygonOffset: true, polygonOffsetFactor: 0, polygonOffsetUnits: -2, opacity: 0,
    }});
    MAT_REG.push({{ m: glowMat, cell: n.cell }});      // palette swap covers glows too
    const glow = new Sprite(glowMat);
    glow.scale.set(sc * 1.04, sc * 1.04, 1);
    glow.renderOrder = 20;                              // glows after bodies
    grp.add(glow);
    const lo = hub ? 0.78 : (n.low === 1 || n.cell >= 7) ? 0.12 : 0.30;  // G5N.2 H3: hub breath damped (bloom-admitted energy swing ~1.9x -> ~1.3x; depth-blind bloom halo pulsing made the owner-flip conspicuous)
    const hi = hub ? 1.0 : (n.low === 1 || n.cell >= 7) ? 0.30 : 0.70;
    const rec = {{ m: glowMat, s: glow, base: sc * 1.04, ph: n.ph, lo, hi, sp: n.sp * 0.2, sel: 0, hub }};
    glows.push(rec);
    GLOWS_BY_ID.set(n.id, rec);
    return grp;
  }});
  let DRIFT_T = 0, _lastT = 0;                       // G5O.2: drift-scaled clock (accumulator => no phase jump on slider change)
  window.__driftT = () => DRIFT_T;                   // QA probe
  (function anim(t) {{                                 // ONLY glow opacity breathes
    requestAnimationFrame(anim);
    const _dt = ((t || 0) - _lastT) / 1000; _lastT = (t || 0);
    DRIFT_T += (_dt > 0 && _dt < 0.5 ? _dt : 0) * MOTION.drift;  // guard skips tab-suspend gaps
    const T = DRIFT_T;
    for (const g of glows) {{
      const w = 0.5 + 0.5 * Math.sin(T * 0.8 + g.ph * 5);
      // selection tiers: 2 = selected core (blazing, enlarged halo), 1 = neighbor
      // (boosted), 0 = normal breathing
      if (g.sel === 2) {{
        g.m.opacity = 0.95 + 0.05 * w;
        g.s.scale.set(g.base * 1.45, g.base * 1.45, 1);
      }} else if (g.sel === 1) {{
        g.m.opacity = 0.75 + 0.2 * w;
        g.s.scale.set(g.base * 1.15, g.base * 1.15, 1);
      }} else {{
        // G5M: only HUB glows breathe; std/low hold a steady mid-glow (temporal-shimmer fix)
        g.m.opacity = g.hub ? (g.lo + (g.hi - g.lo) * w) : (g.lo + (g.hi - g.lo) * 0.55);
        if (g.s.scale.x !== g.base) g.s.scale.set(g.base, g.base, 1);
      }}
      g.m.rotation = g.ph + T * g.sp;                  // subtle molten drift (glow only; body static)
    }}
  }})();
  console.log('core_5 v4 two-layer wired:', glows.length, 'glow-breathing cores (no spin, no size pulse),', shared.size, 'shared body materials');
  // G5P.0c: G5P.0a's single-rAF reveal raced the library's object digest -- on a
  // loaded CPU the fade-in started while default spheres still rendered (operator's
  // residual half-second flash). Reveal now waits until sprite groups VERIFIABLY
  // replaced the default sphere meshes; 4s fallback keeps a broken digest honest.
  const REVEAL_T0 = performance.now();
  const revealWhenSpritesLand = () => {{
    let verified = 0;
    const nodes = G.graphData().nodes;
    for (let i = 0; i < nodes.length && verified < 5; i++) {{
      const o = nodes[i].__threeObj;
      if (o && o.children && o.children.some(c => c.isSprite)) verified++;
    }}
    if (verified >= 5) {{
      document.getElementById('g').classList.add('ready');
    }} else if (performance.now() - REVEAL_T0 > 4000) {{
      console.warn('reveal fallback: sprite swap not verified within 4s - showing anyway');
      document.getElementById('g').classList.add('ready');
    }} else {{
      requestAnimationFrame(revealWhenSpritesLand);
    }}
  }};
  requestAnimationFrame(revealWhenSpritesLand);
}}, undefined, () => {{ console.warn('atlas missing - default cores kept (procedural placeholder)'); document.getElementById('g').classList.add('ready'); }});

// ---- premium control bar (G5E) -- visible in embed too (NOT part of the hidden HUD).
// Glass pills: Reset View | Brain | Full | Palette popover. Real DOM controls; the
// glass look is CSS layering (placement-only) per the material-treatment contract.
const ui = document.createElement('style');
ui.textContent = `
.cbar{{position:fixed;right:12px;bottom:12px;z-index:9;display:flex;gap:6px;align-items:center;
  font:600 12.5px Inter,system-ui;padding:6px 7px;border-radius:9999px;background:rgba(10,10,10,.65);
  -webkit-backdrop-filter:blur(16px) saturate(1.15);backdrop-filter:blur(16px) saturate(1.15);
  border:1px solid #262626;box-shadow:inset 0 1px 0 rgba(255,255,255,.12),
  inset 0 -1px 0 rgba(255,138,56,.10), 0 22px 44px -26px rgba(0,0,0,.85)}}
.cbar button{{background:linear-gradient(180deg,rgba(26,28,33,.78),rgba(12,13,16,.72) 55%,rgba(7,8,10,.78));
  border:1px solid rgba(255,138,56,.26);color:#b4b4b4;
  border-radius:9999px;padding:5px 14px;cursor:pointer;font:inherit;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.16),inset 0 -1px 0 rgba(0,0,0,.5);
  transition:border-color .15s,color .15s,box-shadow .15s,transform .15s}}
.cbar button:hover{{border-color:rgba(255,138,56,.5);color:#f5f5f5;transform:translateY(-1px);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.2),inset 0 -1px 0 rgba(0,0,0,.5),0 0 18px -6px rgba(255,122,24,.35)}}
.cbar button:focus-visible{{outline:none;box-shadow:0 0 0 3px rgba(255,122,24,.35)}}
.cbar button.on{{background:linear-gradient(180deg,rgba(90,48,12,.42),rgba(40,20,6,.5));border-color:#ff7a18;color:#ffae3c;font-weight:700;
  box-shadow:inset 0 1px 0 rgba(255,210,160,.25),inset 0 -1px 0 rgba(0,0,0,.5),0 0 16px -4px rgba(255,122,24,.35)}}
.cbar .sw{{display:inline-block;width:7px;height:7px;border-radius:4px;margin-right:3px}}
#palpop{{position:fixed;right:12px;bottom:56px;z-index:9;display:none;flex-direction:column;gap:3px;
  padding:9px;border-radius:14px;background:rgba(10,10,10,.78);border:1px solid #262626;
  -webkit-backdrop-filter:blur(18px) saturate(1.2);backdrop-filter:blur(18px) saturate(1.2);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.10), 0 22px 44px -22px rgba(0,0,0,.9)}}
#palpop.open{{display:flex}}
#palpop button{{display:flex;align-items:center;gap:8px;background:none;border:1px solid transparent;
  color:#b4b4b4;border-radius:9999px;padding:6px 13px;cursor:pointer;font:500 12.5px Inter,system-ui;text-align:left}}
#palpop button:hover{{background:rgba(255,255,255,.05);color:#f5f5f5}}
#palpop button.on{{border-color:rgba(255,122,24,.55);color:#ffae3c}}
#palpop button.off{{opacity:.42;cursor:default;font-weight:400}}
#palpop button.off:hover{{background:none;color:#b4b4b4}}`;
document.head.appendChild(ui);

const IS_EMBED = location.hash.includes('embed');
const bar = document.createElement('div'); bar.className = 'cbar';
const mkBtn = (label, fn) => {{ const b = document.createElement('button'); b.textContent = label; b.onclick = fn; return b; }};
const bReset = mkBtn('Reset View', () => resetView());
// Pause lives on the DASHBOARD pill when embedded (G5M: no duplicate pause buttons)
const bPause = mkBtn('Pause', () => setPaused(!PAUSED));
window.paintPause = () => {{ bPause.textContent = PAUSED ? 'Resume' : 'Pause'; bPause.classList.toggle('on', PAUSED); }};
const paint = () => {{}};
function resetView() {{                                // restore the hero first-load frame
  SELECTED = null; refreshSelection(); postSelected();
  G.linkVisibility(G.linkVisibility());
  flyTo({_fmt(CAM_X)}, {_fmt(CAM_Y)}, {_fmt(CAM_Z)}, {_fmt(LOOK_X)}, {_fmt(LOOK_Y)}, {_fmt(LOOK_Z)}, RESET_FLY_MIN_MS, RESET_FLY_MAX_MS);
  console.log('[brain] resetView');                    // NOTE: pause state intentionally untouched
}}
window.__brainReset = resetView;                       // QA hook (same path as the button)

// palette popover (4 palettes; swatch = family strip)
const pop = document.createElement('div'); pop.id = 'palpop';
const palBtns = {{}};
for (const [key, p] of Object.entries(PALETTES)) {{
  const b = document.createElement('button');
  b.innerHTML = [0,3,4,6].map(i => `<span class="sw" style="background:${{p.fam[i]}}"></span>`).join('') + p.label;
  b.onclick = () => {{ window.__setPalette(key); pop.classList.remove('open'); }};
  palBtns[key] = b; pop.appendChild(b);
}}
{{ // Operator Custom -- UI-only placeholder (G5F item D9; disabled until built)
  const b = document.createElement('button');
  b.className = 'off'; b.disabled = true;
  b.innerHTML = '<span class="sw" style="background:#3a3f4a"></span><span class="sw" style="background:#3a3f4a"></span><span class="sw" style="background:#3a3f4a"></span><span class="sw" style="background:#3a3f4a"></span>Operator Custom — coming soon';
  pop.appendChild(b);
}}
const bPal = mkBtn('Palette', () => pop.classList.toggle('open'));
window.paintPal = () => {{ for (const [k, b] of Object.entries(palBtns)) b.classList.toggle('on', k === PALETTE); }};
paintPal();
paintPause();
if (IS_EMBED) bar.append(bReset, bPal); else bar.append(bReset, bPause, bPal);
document.body.append(bar, pop);

if (location.hash.includes('embed')) document.body.classList.add('embed');
// G5M sizing fix: follow the iframe/window size (overlay expand, dashboard resize)
window.addEventListener('resize', () => {{
  G.width(window.innerWidth).height(window.innerHeight);
  G.postProcessingComposer().setSize(window.innerWidth, window.innerHeight);
}});
</script></body></html>"""
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(html, encoding="utf-8")
print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.1f} MB) - ALL {len(out_nodes)} cores visible in Brain mode ({low_count} low-LOD small cores) | links w2={tier_counts[2]}, w1={tier_counts[1]}, w0={tier_counts[0]} (hot cut deg>={hot_cut})")
print("regions:", {k: v for k, v in sorted(counts.items(), key=lambda kv: -kv[1])})
