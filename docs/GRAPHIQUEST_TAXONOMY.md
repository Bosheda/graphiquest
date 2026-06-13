# GraphiQuest Taxonomy — generic default + optional local override

GraphiQuest groups the files in your graph into **concepts** (what kind of file)
and **slices/regions** (named groupings you can focus on in the 2D explorer and
the 3D Hivemind). How it groups them is the *taxonomy*.

## Generic default (what ships)

Out of the box, GraphiQuest classifies **any** repository with a generic,
repo-agnostic taxonomy — no project-specific vocabulary is baked into the
package. Concepts are derived from each file's kind and location:

| Concept | Examples |
|---|---|
| **frontend** | `*.jsx/tsx/vue/svelte`, `*.css/scss`, `*.html`, `components/`, `pages/`, `ui/` |
| **backend** | `api/`, `server/`, `routes/`, `services/`, `models/`, `*.go/rs/rb/java/php/cs/py` |
| **scripts** | `scripts/`, `bin/`, `tools/`, `*.sh/ps1/bat/cmd` |
| **tests** | `tests/`, `__tests__/`, `spec/`, `*.test.*`, `*.spec.*` |
| **docs** | `docs/`, `*.md/rst/txt`, `README`, `CHANGELOG`, `LICENSE` |
| **config** | `*.json/yaml/toml/ini/lock`, dotfiles, `*rc` |
| **data** | `data/`, `fixtures/`, `*.csv/sql/db/parquet/xml` |
| **assets** | `assets/`, `public/`, `static/`, images, fonts, media |
| **workflows** | `.github/workflows/`, `Dockerfile`, `Makefile`, CI files |
| **other** | anything else |

**Slices** default to your repo's **top-level directories** (e.g. `src`, `docs`,
`tests`). **3D Hivemind regions** are those same directories (or, when a custom
taxonomy is active, your named regions) laid out on the molten-brain canvas.

This is the only taxonomy in the shipped/published package. It works on every
repo and ships zero project-specific names.

## Optional local override (your own repo)

If you maintain a large repo with a meaningful internal vocabulary, you can
overlay a **custom taxonomy** that lives *only on your machine* and is never
part of the published package.

1. Copy the schema template:
   ```
   cp graphiquest.taxonomy.example.json graphiquest.taxonomy.local.json
   ```
2. Edit `graphiquest.taxonomy.local.json` to define your `concepts`, `slices`,
   `presets`, `regions`, and `region_routes` (every key is optional — see the
   example file for the full schema; patterns are case-insensitive regexes).
3. Rebuild your views (RUN GRAPHIFY in the dashboard, or
   `python scripts/start_graphify_dashboard.py`).

`graphiquest.taxonomy.local.json` is **gitignored** — it cannot be committed, so
your private vocabulary never leaks into the package. You can also point at a
different path with the `GRAPHIQUEST_TAXONOMY_CONFIG` environment variable.

### How a custom taxonomy is applied

The read model is built in **`auto`** mode by default:

- If **no** local config is present → **generic** taxonomy (the shipped default).
- If a local config **is** present → your custom concepts/slices are tried; if
  they genuinely cover the repo (≥4 slices with ≥5 matches), the custom taxonomy
  is used; otherwise GraphiQuest falls back to generic so a config written for
  one repo doesn't mislabel another.

Force a mode explicitly with
`python scripts/graphify_hivemind_readmodel.py --mode generic|custom|auto`.

## Guarantee

A guard test (`tests/test_graphify_package_clean.py`) fails the build if any
shipped/default source file contains project-specific taxonomy vocabulary, so
the public package stays generic by construction.
