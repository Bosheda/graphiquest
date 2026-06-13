# GraphiQuest

**GraphiQuest** — a local-first knowledge-graph dashboard for your codebases.
Scan a repo with the open-source [Graphify](https://github.com/safishamsi/graphify)
scanner (by [safishamsi](https://github.com/safishamsi), MIT — full credit), then
explore it as a living **3D molten-brain Hivemind** or a structural **2D explorer**,
audit it with **Hunter**, read findings in **Reports**, **Trace** paths between
files, and ask it questions — all answered from the local graph, with no cloud,
no credentials, and no agent calls.

> Status: working pre-release. A standalone **graphiquest** repo is planned. It is
> built to be **independently usable** and is not tied to any host application.

> **Note:** the public `graphiquest` repository is **pending release** — clone
> URLs below point at the intended location and will work once it is published.

## Built on Graphify

GraphiQuest is **built on top of [Graphify](https://github.com/safishamsi/graphify)**,
the open-source repo scanner and knowledge-graph engine by
**Safi Shamsi ([safishamsi](https://github.com/safishamsi))**, released under the
**MIT License**.

**Graphify scans the repository and generates the graph data; GraphiQuest
visualizes, queries, audits, and navigates it** — the 3D Hivemind, the 2D explorer,
Hunter, Reports, Trace, the token-savings proof, the read-only MCP server, and the UI.

> **GraphiQuest and Graphify are separate projects.** GraphiQuest does not include,
> modify, or rename Graphify — it is a distinct dashboard/product layer that calls
> the upstream Graphify CLI. Graphify is authored and maintained by **safishamsi**;
> full credit for the scanning/graph engine goes to them. GraphiQuest is not
> Graphify renamed, and claims no ownership of it.

- Engine: <https://github.com/safishamsi/graphify> · Package: `graphifyy` (PyPI) · License: MIT
- Graphify is used as an **external CLI dependency** — its source is not bundled here,
  so no Graphify license text needs to ship with GraphiQuest. Full credit for the
  scanning/graph engine goes to its author. See [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

---

## What this is

- **GraphiQuest** — a generated, dependency-light HTML
  dashboard (black-glass / obsidian UI) served over loopback.
- **3D Hivemind** — your repo as a molten brain: clusters map to brain regions,
  hot files burn white-hot, edges are magma pathways; camera glide, palettes,
  motion controls, pathway lighting on select.
- **2D Explorer** — structural slice view + 2D brain overview with search,
  node inspector, and a Tools drawer.
- **Concepts** — live checklist filtering both views.
- **Ask Console** — local graph Q&A (`how many nodes?`, `what is connected to
  this node?`, `find <name>` / `jump to <name>` …). Every ask is logged locally
  as evidence.
- **Project registry + bridge** — connect local repo paths, run Graphify
  safely through a loopback-only bridge, and switch between generated project
  graphs.
- **Hunter + Reports** — a graph-first project auditor: orphan candidates,
  disconnected groups, possible missing links (same folder, no connections),
  hotspots, and stale-graph signals — local-only, conservative wording, with
  clickable jump-to-node findings.
- **Claude Code** — *the one gated connector, with a REAL local MCP server*
  (`scripts/graphify_mcp_server.py`, stdlib-only, read-only) and a wizard that
  can register it with one click. Nothing connects until YOU approve — it
  **never makes a call** on its own.

## What this is not

- Not a hosted runtime — it never hosts inside another application.
- Not a cloud service — nothing leaves your machine by default.
- Not an arbitrary command runner — the bridge allowlists exactly one
  operation pipeline.
- Not an agent execution system — the MCP server is read-only and
  connectors stay gated until you configure them.
- Not a general remote importer — the ONE network flow for *your data* is the
  explicit "import from GitHub URL" action (it runs `graphify clone`). The only
  other network use is loading view libraries + Google Fonts from public CDNs on
  first paint (see Privacy below); a fully-offline bundle is on the roadmap.

## Current status (honest)

Working: dashboard shell with real navigation (Knowledge Graph / Skills /
How-To / Activity / Settings / Memory), tracked project registry, Add Project,
loopback bridge with RUN GRAPHIFY, full generate → read-model → per-project
2D/3D view pipeline, generated-graph **switching**, staleness detection
(`rebuild_required` via a generator contract), `views_missing`, sandboxed
cleanup, relative repo-path resolution, find/jump command (3D + 2D),
evidence/activity logging, GitHub-URL import with live progress on the top
strip, Hunter graph audits with a Reports section, and a local MCP server for
Claude Code. In-dashboard product flows: a **Settings → Setup &
Install** step-by-step (clone → install Graphify CLI → start → first repo, with
copy buttons + live CLI detection), a **Skills** management table (16 honest
status rows), **guided Claude Code connect wizard** (live checks, one-click
REGISTER FOR ME, never auto-calling), **Unload/Reload** of the
active graph to a real no-graph state, and **Reports/Activity/Memory**
management (clear/copy/export, localStorage-only — never touches repos or
generated views). **Graphify Context Savings** proves the value: RUN SAVINGS
CHECK estimates the tokens for the full structural context vs a focused graph
query and shows the % saved (an honest `chars/4` estimate, shown in the right
panel + Settings + Skills; measured Claude-token mode is gated). The connector
is a **usable flow**: a CONNECT wizard with live install/scanner/registration
detection, one-click **REGISTER FOR ME**, and a real **CHECK SELF-TEST** that
runs the shipped MCP server's `--selftest` via the bridge — never a fake
"connected".

Limitations: one graph generation/import at a time; staleness is file-based
(graph vs views — repo source changes are not watched); connectors never call
out until you configure them yourself (the MCP server ships at
`scripts/graphify_mcp_server.py`); URL import is GitHub-https only; views load
CDN libraries + Google Fonts on first paint (a fully-offline bundle is on the
packaging roadmap). **Trace** (shortest-path / trace / chain-end over the local
edges) is built and wired in the ask console; `what-changed` (diff-aware
queries) is still planned.

## Requirements

| Requirement | Notes |
| --- | --- |
| Python 3.10+ | developed/tested on 3.11/3.13; stdlib only — no pip installs for the dashboard itself |
| uv (or pipx) | only to install the Graphify CLI |
| Graphify CLI | `uv tool install graphifyy` (developed against 0.8.36–0.8.37); must be on PATH as `graphify` |
| A modern browser | developed against Chromium; WebGL required for the 3D view |
| Loopback port | bridge defaults to `127.0.0.1:8787` |
| Tk (tkinter) | *optional* — only for the native "Select a project folder" picker. Bundled with python.org Windows/macOS builds; on Linux install `python3-tk`. Without it, use Add Project → paste a path / import a GitHub URL (the picker degrades honestly). |

## Quick start

> Have Claude Code open? Skip all of this — paste the prompt from
> [Using it with Claude Code](#using-it-with-claude-code-the-one-connector)
> and Claude does every step for you.

```bash
# 1. install the Graphify CLI (one time; uv -- or use: pipx install graphifyy)
uv tool install graphifyy

# 2. from the repo root: graph this repo once (creates graphify-out/graph.json)
graphify update .

# 3. start the dashboard -- it builds the read-model + all views itself if
#    missing, then serves them + the safe local bridge in the foreground
python scripts/start_graphify_dashboard.py          # add --port 8788 if 8787 is busy

# 4. open the printed URL
#    http://127.0.0.1:8787/views/graphify-dashboard.html
```

Then, in the dashboard:

1. Click **+ Add a project** (top strip) — the native file explorer opens (via
   the bridge): pick a folder and it is graphed and loaded automatically. Or
   cancel into the modal to paste a path / **import from a GitHub URL**
   (`graphify clone` → graph → load; this is the one flow that uses the
   network). Settings → Repositories manages everything afterwards.
2. Click **RUN GRAPHIFY** — the bridge runs the allowlisted pipeline and the
   project becomes **ready** when real output exists.
3. Click the project card (or **SELECT**) — the dashboard switches to that
   project's own 3D/2D graph, counts, and concepts.
4. Ask things: `how many nodes?` · `what concepts are visible?` ·
   `jump to <file>`.

## Manual fallback (no bridge)

If the bridge is not running, RUN GRAPHIFY becomes **PREPARE COMMAND** and shows
the exact manual command:

```bash
cd "<your repo path>"
graphify update .
```

The page tracks an honest `waiting for manual run` status — without the bridge
it cannot check your filesystem, so it never claims the graph exists. Start the
bridge for verified runs and automatic view generation.

## Project registry

- Tracked baseline: [`graphify.projects.json`](graphify.projects.json)
  (ids, labels, repo paths, honest statuses; counts are **never stored** — they
  come from real output at generation/scan time).
- Browser overlay: repo-path edits and added projects persist in
  `localStorage` and are labeled *"saved locally in this browser"* until a CLI
  config-writer lands.
- Status meanings: `ready` (views exist and load) · `repo_path_configured` ·
  `generated — views not built yet` · `rebuild_required` (graph or generator
  contract newer than the views) · `views_missing` · `generated — incompatible
  output` (exact reason shown) · `graph_missing` · `no repo path`.

## Generated outputs (never committed)

```
graphify-out/                      # gitignored
  views/                           # default dashboard views (the graph of whatever repo the dashboard runs from; gitignored — nothing pre-baked ships)
  projects/<project-id>/           # per-project generated views
    manifest.json                  # truth: paths, counts, versions, contract
    read-model.json
    brain-3d-prototype.html        # 3D Hivemind
    graph-explorer.html            # 2D explorer
```

`<your repo>/graphify-out/graph.json` (+ `GRAPH_REPORT.md`) is Graphify's own
output inside the scanned repo. Everything generated is disposable —
**Settings → Maintenance** can clean per-project views safely.

## Safety model

- **Loopback only** — the bridge binds `127.0.0.1` and additionally verifies
  the client address on every request. No LAN, no remote.
- **Cross-site request defense** — state-changing POSTs additionally require a
  same-origin `Origin`/`Sec-Fetch-Site` (browser-issued cross-origin requests
  are refused), so a web page you visit cannot drive the local bridge even while
  it is running. Non-browser clients (the tests, the MCP selftest) send no
  `Origin` and are unaffected.
- **Allowlisted pipeline only** — the browser sends `{projectId, repoPath}` as
  data; the bridge runs a fixed argv (`graphify update .` in a validated
  directory, then this repo's own view generators). There is **no command-text
  channel**; injection strings are simply invalid paths.
- **Path validation** — absolute/existing/directory required; drive roots,
  system directories, and bare home are refused.
- **One rebuild at a time** (HTTP 409), 600s watchdog, **proof-based success**
  (a real `graph.json` must exist and the view pipeline must complete — exit 0
  alone is never success; an unchanged graph is honestly treated as current).
- **Sandboxed cleanup** — deletes only `graphify-out/projects/<sanitized-id>`
  (realpath-guarded); source repos and design assets are structurally out of
  reach.
- **No credentials, no external calls by default** — two honest exceptions:
  view libraries/fonts load from public CDNs on first paint, and the explicit
  "import from GitHub URL" action clones over the network (strictly
  `https://github.com/<owner>/<repo>` — validated as data, fixed argv).
- **First-paint third-party note (privacy):** on first load the views fetch JS
  from jsDelivr/esm.sh and Google Fonts, which discloses your IP and referer to
  those hosts. Nothing else leaves your machine. A fully-offline vendored bundle
  (zero third-party requests) is on the roadmap — needed before fully-private
  use on sensitive code.

## Troubleshooting / visual QA

- **Glossy/plain spheres instead of molten cores** = the texture atlas did not
  load. The view logs a console **warning** (`atlas missing — default cores
  kept`); warnings matter here — check the browser console and the asset path.
- **Blank graph** — no read-model: run `graphify update .` in the repo, then
  regenerate views (or RUN GRAPHIFY via the bridge).
- **`rebuild_required`** — the graph or the generator contract is newer than
  the views; click REBUILD.
- **Stale processes** — `python scripts/cleanup_graphify_processes.py`
  (add `--kill-stale` to remove hung/superseded Graphify rebuilds; it can never
  touch other python processes). Hook hygiene:
  `python scripts/install_graphify_hooks_safe.py` (idempotent).
- **Port already in use** — the bridge prints a clear message; re-run with
  `python scripts/start_graphify_dashboard.py --port 8788`.
- **Stop the dashboard** — Ctrl+C in the terminal running the start script.

## Using it with Claude Code (the one connector)

> G5Q.1h operator decision: **Claude Code is the only connector** — whether you
> run it as a terminal app or as the terminal window inside Claude Desktop, it
> is the same thing. The old separate Claude-Desktop config flow and OpenClaw
> were removed.

**You have Claude Code open and this repo link — now what?** Paste this into
Claude Code and it does the whole setup (the same prompt ships in the
dashboard's How-To §2 with a COPY button):

```text
Set up the Graphify Dashboard from https://github.com/Bosheda/graphiquest :
1. Clone it (or cd into my existing clone).
2. Install the Graphify scanner CLI (open source by safishamsi -
   github.com/safishamsi/graphify): uv tool install graphifyy
3. Graph the repo: run "graphify update ." in the repo root.
4. Start the dashboard with "python scripts/start_graphify_dashboard.py",
   leave it running, and tell me the local URL it prints.
5. Register the dashboard's MCP server with yourself using ABSOLUTE paths:
   claude mcp add -s user graphify -- "<abs python>" "<repo>/scripts/graphify_mcp_server.py" --repo "<repo>"
6. Run "claude mcp list", confirm graphify shows a health check, then use the
   graphify tools to summarize my graph.
```

**How the pieces talk (simple):** the Graphify scanner (by
[safishamsi](https://github.com/safishamsi/graphify), MIT — full credit) BUILDS
the graph · this dashboard SHOWS it (3D Hivemind, Hunter, Reports, token
savings) · Claude Code THINKS about it through a tiny **read-only** local MCP
server that ships here (`scripts/graphify_mcp_server.py`; 5 tools:
`graph_summary` · `find_node` · `node_neighbors` · `list_concepts` · `run_hunter`). The
dashboard never calls Claude Code; Claude Code never changes the dashboard —
you are the link.

**The connect wizard** (CLAUDE CODE pill in the left rail, or CONNECT in
Settings/Skills) walks four live-checked steps: **(1)** is Claude Code
installed? (COPY install command if not) · **(2)** is the Graphify scanner
installed? (live version detection + credit link + COPY install) · **(3)**
connect — **REGISTER FOR ME** runs Claude Code's own registration command via
the local bridge with a **fixed argv** and zero client input
(`POST /api/claudecode/register`; the bridge never writes `~/.claude.json`
itself — the claude CLI does), or COPY the same command and run it in
PowerShell/CMD (not Git Bash, which mangles paths) · **(4)** check it worked
with `claude mcp list` (live health check) or `/mcp` inside Claude Code.

Honesty rules: there is **no browser sign-in** for local MCP servers (nothing
can "authorize" Claude silently); registration status is detected by
**reading** `~/.claude.json`; the strongest claim is *registered, verified by
you* — **"connected" is never claimed**. Doc examples use
`C:\Users\%USERNAME%\…`-style placeholders; the wizard always detects the real
paths on **your** machine. Facts live-verified 2026-06-11 on Claude Code
v2.1.174 + code.claude.com/docs/en/mcp.

**No connector call ever happens from the dashboard itself**; the in-page lane
stays gated and answers honestly: *"gated — no call was made."* The server
makes no network calls and never writes anything.

## License (this project)

**MIT License** — see [`LICENSE`](LICENSE) at the repo root (Copyright (c) 2026
DaForgeLayer-AI contributors). This dashboard's own code and its committed design
assets are MIT. The dependency licenses below are separate and verified.

> Public-release note: the MIT grant currently covers the whole monorepo it lives
> in; a scoped/standalone license boundary will be set at the repo-split step. The
> code being open-source does not mean the release is *done* — the public release
> still needs the G5Q.2 checklist (screenshots/README polish), connector execution
> stays gated, and the Graphify CLI PyPI publish (0.8.37) is a separate operator step.

## Dependency Credits & Licenses

Verified against upstream sources 2026-06-11 (license audit; final pass needed
before any public release):

| Dependency | Use | License | Delivery |
| --- | --- | --- | --- |
| [3d-force-graph](https://github.com/vasturiano/3d-force-graph) (v1.80.0) by Vasco Asturiano | 3D graph rendering | MIT (verified) | CDN (jsDelivr), pinned |
| [three.js](https://github.com/mrdoob/three.js) incl. examples `UnrealBloomPass` | WebGL + bloom | MIT (verified) | CDN (jsDelivr / esm.sh), pinned |
| [Graphify](https://github.com/safishamsi/graphify) (`graphifyy`) | repo scanning / graph build | MIT (verified) | external CLI tool |
| Fonts: Orbitron, Inter, JetBrains Mono, Saira | UI typography | SIL OFL 1.1 (verified) | Google Fonts CSS API |
| jsDelivr / esm.sh | delivery | free public CDNs (courtesy credit) | — |
| 2D explorer | 2D rendering | this repo — self-contained canvas, **zero external libraries** | inline |
| Claude Code MCP docs | connector documentation only | referenced, not bundled | — |

Still needed before public release: re-verify the OFL/Google-Fonts FAQ
interpretation live, and include MIT/OFL license texts if any library or font
is ever vendored locally (CDN loading creates no notice obligation today).

## Roadmap

- Standalone **graphiquest** repo split (currently ships inside the DaForgeLayer-AI monorepo)
- Packaging installer + fully-offline vendored bundle (license texts included)
- Repo import hardening (GitHub-https clone exists; other hosts/auth are future)
- Graph commands: `what-changed` diff-aware queries (Trace — shortest-path /
  trace / chain-end — and orphan/disconnect detection are already built)
- Connector bridge execution (explicitly gated + approved)
- Public release assets: screenshots / GIFs / video, final README polish
