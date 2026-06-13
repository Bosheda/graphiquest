#!/usr/bin/env python3
"""Optional LOCAL taxonomy override for GraphiQuest (clean-package boundary).

The shipped package classifies ANY repo with a GENERIC, repo-agnostic taxonomy
(file-kind + path categories: Frontend / Backend / Scripts / Docs / Tests /
Config / Data / Assets / Workflows / Other, plus top-level-directory slices).
NO project-specific vocabulary ships by default.

Power users can define their OWN concept / slice / region taxonomy in an
untracked local config file. It is loaded ONLY if present and is NEVER part of
the published package (it is gitignored). This is how a maintainer can keep a
bespoke "anatomy" view of their own repo without leaking that vocabulary into
the public tool.

See `graphiquest.taxonomy.example.json` (a generic, copy-me template) and
`docs/GRAPHIQUEST_TAXONOMY.md`.

Config file (repo root, gitignored): `graphiquest.taxonomy.local.json`
Schema (every key optional):
    {
      "concepts":      [ {"name","pattern","match_label"?} ],
      "slices":        [ {"id","label","purpose","concepts":[...], "extra"?} ],
      "hide":          [ {"name","pattern"} ],
      "presets":       { "<Button>": {"slice","hideTests","hideDocs","labels","hint","trace"?} },
      "regions":       [ {"id","x","y","tag","meaning"} ],
      "region_routes": [ {"concept"?,"path"?,"label"?,"region"} ]
    }

Standard library only. Never raises on a malformed/missing file -- a broken
local override silently degrades to the generic default (the package must never
fail because of an OPTIONAL local file).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

# Repo root = parent of scripts/. The local config lives at the repo root so a
# user drops it next to graphify.projects.json.
_ROOT = Path(__file__).resolve().parents[1]
LOCAL_CONFIG_NAME = "graphiquest.taxonomy.local.json"


def local_config_path() -> Path:
    """Absolute path to the (optional) local taxonomy override file.

    Honors GRAPHIQUEST_TAXONOMY_CONFIG for tests / non-default layouts.
    """
    override = os.environ.get("GRAPHIQUEST_TAXONOMY_CONFIG")
    if override:
        return Path(override)
    return _ROOT / LOCAL_CONFIG_NAME


def has_local_taxonomy() -> bool:
    try:
        return local_config_path().is_file()
    except OSError:
        return False


def load_local_taxonomy() -> Dict[str, Any]:
    """Return the parsed local taxonomy dict, or {} when absent/unreadable.

    A malformed override is treated as ABSENT (generic default) -- never an
    error, so the shipped tool cannot be broken by a bad optional local file.
    """
    p = local_config_path()
    try:
        if not p.is_file():
            return {}
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}
