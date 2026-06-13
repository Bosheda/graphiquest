# Graphify Dashboard — Required Asset Manifest

**Scope:** the minimum design assets a fresh clone needs to render the **current
approved** molten Hivemind / dashboard visual. Committed under
`graphify_assets/design/` (tracked) and seeded into the served
`graphify-out/design/` on bridge startup by `seed_design_assets()` in
`scripts/graphify_dashboard_bridge.py` (never overwrites existing files, so a
live operator's freshly-generated art is preserved). `graphify-out/` itself
stays gitignored.

**Gate (G5Q.1c):** this is the *only* design content committed. Every other file
under the local `graphify-out/design/` staging area — old atlas attempts
(v1/v2/v3), unused `_cool`/`_contrast` palettes, `cells/` source images, UI
material textures, earlier `proofs/` rounds, QA crops, guides, contact sheets,
generation logs — is **intentionally excluded** as dev-only/junk and remains
local + gitignored. The set was independently verified complete-and-minimal
(every runtime `/design/` and `../design/` path is backed; nothing unused is
included) before commit.

**Total committed:** 11 files · 26.78 MB (28,066,953 bytes).

## Committed assets

| File (under `graphify_assets/design/`) | Bytes | Used by | Why required |
| --- | --- | --- | --- |
| `agentic-os-visual-system/proofs-v4/proof_v4_hivemind_viewport_backing_i2i_seed309104.png` | 1,002,198 | dashboard `#vp` CSS `url()` (`../design/...`) | the molten viewport backing plate behind the 3D brain |
| `graphify-ui-materials/graphiquest_logo_mark_seed711002c.png` | 376,508 | dashboard `#brand` logo | the GraphiQuest mark v3: reference-faithful hexagon + molten 3-node network (ComfyUI Juggernaut img2img from the operator reference w/ text strip masked, seed 711002, denoise 0.52 — G5Q.1z; v2 style rejected + deleted) |
| `graphify-molten-cores-v4/molten_core_atlas_v4.png` | 2,852,464 | 3D brain `PALETTES.neon` (`/design/...`) | python-baked default ("Neon Brain") core texture atlas |
| `graphify-molten-cores-v4/molten_core_atlas_v4_obsidian.png` | 2,868,874 | 3D brain `PALETTES.obsidian` | **UI default palette** core atlas |
| `graphify-molten-cores-v4/molten_core_atlas_v4_forge.png` | 2,852,014 | 3D brain `PALETTES.forge` | "Molten Forge" palette atlas |
| `graphify-molten-cores-v4/molten_core_atlas_v4_ice.png` | 2,900,155 | 3D brain `PALETTES.ice` | "Cyber Ice" palette atlas |
| `graphify-molten-cores-v4/molten_core_atlas_v4_royal.png` | 2,887,905 | 3D brain `PALETTES.royal` | "Royal Plasma" palette atlas |
| `graphify-molten-cores-v4/molten_core_atlas_v4_enterprise.png` | 2,885,912 | 3D brain `PALETTES.enterprise` | "Toxic-Free Enterprise" palette atlas |
| `graphify-molten-cores-v4/molten_core_atlas_v4_access.png` | 2,710,195 | 3D brain `PALETTES.access` | "High Contrast (Accessibility)" palette atlas |
| `graphify-molten-cores-v4/molten_core_atlas_v4_space.png` | 2,904,481 | 3D brain `PALETTES.space` | "Deep Space" palette atlas |
| `graphify-molten-cores-v4/molten_core_atlas_v4_solar.png` | 2,887,765 | 3D brain `PALETTES.solar` | "Solar Storm" palette atlas |

The 9 atlases back the 9 palettes the approved **Palette** switcher offers; the
3D view loads the active palette's atlas on init and the others on swap, so all
9 are part of the shipped experience.

## Source, ownership & license

- **Generated, operator-owned.** All 11 are ComfyUI / Stable-Diffusion-XL
  (Juggernaut-XL_v9) outputs and deterministic PIL recolors thereof, produced by
  the operator during development. They are first-party project assets and fall
  under the repository's MIT `LICENSE`.
- **Hand-authored:** none. **Third-party:** none. (Fonts load from the Google
  Fonts CDN at runtime — no font file is bundled or committed.)

## How to regenerate / replace

- **9 molten-core atlases** — deterministic PIL recolors of one locked grayscale
  cell (`core_5_seed309216.png`) via `scripts/graphify_molten_core_atlas_plan.py
  --v4 --palettes`. That source cell is a build-time input, **not committed**
  (it is not a runtime render asset); it lives locally under the gitignored
  `graphify-out/design/graphify-molten-cores/cells/`. Re-deriving palettes
  requires it present locally. Pillow `LANCZOS` is visually identical but not
  guaranteed byte-identical across Pillow versions.
- **Viewport backing + logo mark** — ComfyUI + Juggernaut-XL_v9 at fixed seeds
  (309104 / 309310). Same-seed regeneration is not guaranteed pixel-identical
  across GPU/driver/ComfyUI versions, so these two committed binaries are the
  authoritative copies of the approved look.

## Fresh-clone contract

A clone with only the tracked files renders the approved visual: start the
dashboard (`python scripts/start_graphify_dashboard.py`), the bridge seeds these
11 into `graphify-out/design/`, and every `/design/` + `../design/` request
returns 200 with zero `atlas missing` console warnings. Verified at 1366×768 and
1920×1080 on a default project graph and an imported foreign-repo graph.
