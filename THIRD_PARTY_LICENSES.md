# Third-Party Credits & Licenses

GraphiQuest is built on open-source work. This file credits every upstream
project GraphiQuest uses and records its license. GraphiQuest does **not** claim
ownership of any of these — full credit goes to their authors.

Verified against upstream sources on 2026-06-12.

---

## Graphify — the scanner / graph engine (external CLI, not bundled)

GraphiQuest is **built on top of Graphify**. **Graphify scans the repository and
generates the graph data; GraphiQuest visualizes, queries, audits, and navigates
it** (3D Hivemind, 2D explorer, Hunter, Reports, Trace, token-savings proof, the
read-only MCP server, and the UI).

**GraphiQuest and Graphify are separate projects.** GraphiQuest does not include,
modify, or rename Graphify — it calls the upstream Graphify CLI. Graphify is
authored and maintained by safishamsi; GraphiQuest claims no ownership of it and
is not Graphify renamed.

- **Project:** https://github.com/safishamsi/graphify
- **Package:** `graphifyy` (PyPI)
- **Author:** Safi Shamsi ([safishamsi](https://github.com/safishamsi))
- **License:** MIT — Copyright (c) 2026 Safi Shamsi

Graphify is used strictly as a **separately-installed CLI dependency** (invoked
via subprocess; its JSON output is read into GraphiQuest's own read model). Its
source is **not** vendored into this repository, so the MIT notice obligation
("include the copyright + permission notice in all copies or substantial
portions") does not attach to GraphiQuest's distribution.

> **Rule:** Graphify stays an external CLI — it is never vendored. If that ever
> changes, the full `safishamsi/graphify` LICENSE text (Copyright (c) 2026 Safi
> Shamsi) MUST be shipped verbatim in this file alongside the copied source.

---

## Bundled / loaded at runtime in the generated views

The 3D and 2D views load these from public CDNs (jsDelivr / esm.sh / Google
Fonts) on first paint. None are vendored into the repo today; when the planned
fully-offline bundle ships, their license texts will be included here.

| Component | Use | License | Author / Source |
|---|---|---|---|
| [3d-force-graph](https://github.com/vasturiano/3d-force-graph) (v1.80.0) | 3D graph rendering | MIT | Vasco Asturiano |
| [three.js](https://github.com/mrdoob/three.js) (incl. `UnrealBloomPass`) | WebGL + bloom | MIT | mrdoob & three.js authors |
| Orbitron, Inter, JetBrains Mono, Saira | UI typography | SIL OFL 1.1 | Google Fonts |
| jsDelivr / esm.sh | CDN delivery | free public CDNs (courtesy credit) | — |

The 2D explorer is a self-contained canvas renderer with **zero external
libraries** (inline in this repo).

---

## GraphiQuest's own license

GraphiQuest's own code and its committed design assets are **MIT** — see
[`LICENSE`](LICENSE) at the repo root. That grant covers GraphiQuest's code, not
the third-party engine/libraries above, which keep their own licenses.

---

## When the offline bundle lands

The planned offline bundle will vendor 3d-force-graph + three.js (MIT) and the
fonts (OFL 1.1). At that point their LICENSE / OFL texts MUST be included in this
file (or a `licenses/` directory). This vendoring does **not** include Graphify,
which remains an external CLI.
