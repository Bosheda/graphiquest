# GraphiQuest — Showcase Video Plan

A production plan for a short, polished demo of GraphiQuest. Public-safe: capture
only the GraphiQuest dashboard (no browser chrome, taskbar, usernames, or private
paths). GraphiQuest is built on top of [Graphify](https://github.com/safishamsi/graphify)
by safishamsi (MIT) — keep that attribution in the closing frame.

## Meta

- **Title:** *GraphiQuest — Find the needle in your codebase graph*
- **Target length:** 60–90 seconds
- **Audience:** developers and AI builders
- **Tone:** confident, fast, "show don't tell"
- **Resolution:** 1920×1080 (or higher), 30–60 fps
- **Output:** H.264 MP4 (and a short silent GIF/loop for the README/social)

## Voiceover script (~140 words ≈ 75s)

> This is GraphiQuest — your codebase as a living 3D brain.
> Every file is a node; every connection is real structure, scanned locally by the
> open-source Graphify engine. Nothing leaves your machine.
>
> Point it at a repo and the whole thing becomes a map you can fly through.
> Say *jump* — and you're there: the camera flies to the file, and everything it
> touches lights up.
>
> Flip to the 2D Explorer for the structural view. Then let Hunter audit the graph —
> orphans, dead ends, hotspots — every finding one click from the node itself.
>
> Ask through the graph instead of pasting your whole repo to a model, and watch the
> token savings. Connect your own Claude Code, read-only, and it reasons over the same
> map.
>
> GraphiQuest maps your repo with Graphify, visualizes it in Hivemind, and helps you
> hunt what matters.

## Scene list (12 shots)

> Capture order matters: **set the capture viewport size first, then reset/centre the
> Hivemind**, and only start recording once the brain is centered. Use a **large public
> repo** (e.g. `vercel/next.js`) for a dense Hivemind — caption it as an example public
> repo graph, never as GraphiQuest's own source.

| # | Scene | On-screen caption | Duration |
|---|-------|-------------------|----------|
| 1 | Open GraphiQuest (clean dashboard) | "GraphiQuest — local-first" | 3s |
| 2 | Load a repo | "Scan any repo with Graphify" | 5s |
| 3 | 3D Hivemind slow orbit (centered) | "Your codebase as a 3D brain" | 8s |
| 4 | Click a strong, central node and zoom in | "Jump to the node that matters" | 7s |
| 5 | Show the selected-node card + connected files | "Degree · neighbors · connected files" | 6s |
| 6 | Switch to 2D Explorer | "Structural 2D view" | 6s |
| 7 | Run Hunter | "Hunter audits the graph" | 6s |
| 8 | Open Reports (findings table) | "Orphans · leaves · hotspots" | 6s |
| 9 | Click a finding → jump back to the node | "One click from finding to node" | 6s |
| 10 | Run Context Savings | "~99% fewer tokens than dumping the whole repo (estimated)" | 6s |
| 11 | Show Claude Code connector (read-only) | "Optional, read-only, honest status" | 6s |
| 12 | Closing tagline + logo | **"Map the repo. Hunt the signal. Jump to the node that matters."** | 6s |

## On-screen captions (style)

- Lower-third, semi-transparent dark box, Inter/Segoe UI Semibold, ~28px.
- One caption per scene; keep ≤ 6 words where possible.
- Closing frame credit (required): **"Built on Graphify by safishamsi (MIT)"** + the
  repo URL `github.com/Bosheda/graphiquest`.

## Capture checklist (public-safe)

- [ ] Run the **standalone** GraphiQuest dashboard (not a monorepo copy).
- [ ] Graph a public-safe repo (GraphiQuest's own code, or a public OSS project).
- [ ] Capture page-only (headless/Playwright) — **no browser chrome, no taskbar**.
- [ ] No usernames / absolute home paths / private repos visible.
- [ ] Generic taxonomy only (no project-specific categories).
- [ ] Connector shown honestly (setup-required or current-session-true only).
- [ ] Savings labeled **estimated** (or measured) honestly.

## Recommended tools

- **Record:** **OBS Studio** (free) — use *Window Capture (WGC method)* so only the
  dashboard is captured, never the desktop/taskbar (avoid desktop/gdigrab capture — it
  leaks overlapping windows). Or **Playwright** (`page.video`, scripted) for clean,
  repeatable, chrome-free capture.
- **Edit:** **Clipchamp** (free, built into Windows), **CapCut** (free), or
  **DaVinci Resolve** (free) — trim, add the lower-third captions, and the closing frame.
- **Voiceover (optional):** Chatterbox (MIT, local) or your own recording.
- **Captions (optional auto):** whisper.cpp (`-osrt`) → burn in via ffmpeg or your editor.

## Export settings

- **Video:** H.264 (`libx264` or `h264_nvenc`), 1920×1080, 30–60 fps, CRF ~18–20
  (or `-cq 19` NVENC), `-pix_fmt yuv420p`, `+faststart`.
- **Audio:** AAC 192 kbps (if VO).
- **GIF (optional loop):** 800–1000px wide, 12–15 fps, palette-optimized
  (`ffmpeg -vf "fps=14,scale=960:-1:flags=lanczos,palettegen"` then `paletteuse`),
  keep under a few MB.
- **GitHub limits:** keep any committed video/GIF small (ideally < 10 MB); host larger
  videos externally and link them.
