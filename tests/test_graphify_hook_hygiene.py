"""Tests for the G5P.0d graphify process-hygiene mitigation (tracked).

Covers scripts/install_graphify_hooks_safe.py (template patcher: applies the
pidfile newest-wins guard + cross-platform watchdog to the graphify post-commit
hook, idempotently, with compile verification) and
scripts/cleanup_graphify_processes.py (strict rebuild fingerprint classifier --
must never match ComfyUI / Hermes / chat-proxy / dev servers).

Standard library unittest:
  python tests/test_graphify_hook_hygiene.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from install_graphify_hooks_safe import (  # noqa: E402
    ANCHOR_PRINT,
    ANCHOR_SIGALRM,
    SENTINEL,
    patch_hook_text,
    verify_embedded_script,
)
from cleanup_graphify_processes import classify, is_rebuild_cmdline  # noqa: E402

# Minimal synthetic hook reproducing the graphify 0.8.36 template structure the
# patcher anchors on: the embedded rebuild script with the per-commit print and
# the unix-only SIGALRM timeout block.
UNPATCHED_HOOK = f'''#!/bin/sh
# graphify-hook-start
echo "[graphify hook] launching background rebuild"
"$GRAPHIFY_PYTHON" -c "import os, subprocess, sys
_src = \'\'\'
import os, signal, sys
from pathlib import Path

changed = ['a.py']

{ANCHOR_PRINT}

try:
    from graphify.watch import _rebuild_code, _apply_resource_limits
    _apply_resource_limits()
{ANCHOR_SIGALRM}
    _rebuild_code(Path('.'), changed_paths=changed, force=False)
except Exception as exc:
    print(f'[graphify hook] Rebuild failed: {{exc}}')
    sys.exit(1)

\'\'\'
subprocess.Popen([sys.executable, '-c', _src])
"
# graphify-hook-end
'''


class PatcherTests(unittest.TestCase):
    def test_patch_applies_guard_and_watchdog(self):
        patched, status = patch_hook_text(UNPATCHED_HOOK)
        self.assertEqual(status, "patched")
        self.assertIn(SENTINEL, patched)
        self.assertIn("graphify-rebuild.pid", patched)
        self.assertIn("taskkill", patched)
        self.assertIn("IMAGENAME eq python.exe", patched)  # recycled-PID validation
        self.assertIn("threading", patched)                # cross-platform watchdog
        self.assertNotIn("hasattr(signal, 'SIGALRM')", patched)  # inert guard removed
        # the per-commit print survives (the guard is prepended, not replacing it)
        self.assertIn(ANCHOR_PRINT, patched)

    def test_patched_embedded_script_compiles(self):
        patched, status = patch_hook_text(UNPATCHED_HOOK)
        self.assertEqual(status, "patched")
        self.assertTrue(verify_embedded_script(patched))

    def test_idempotent_second_run(self):
        once, _ = patch_hook_text(UNPATCHED_HOOK)
        twice, status = patch_hook_text(once)
        self.assertEqual(status, "already-patched")
        self.assertEqual(once, twice)

    def test_unknown_template_is_untouched(self):
        alien = "#!/bin/sh\n# graphify-hook-start\necho hi\n# graphify-hook-end\n"
        out, status = patch_hook_text(alien)
        self.assertEqual(status, "anchor-missing")
        self.assertEqual(out, alien)

    def test_verify_rejects_broken_embedded_script(self):
        self.assertFalse(verify_embedded_script("_src = '''def broken(:'''"))
        self.assertFalse(verify_embedded_script("no embedded script here"))


class FingerprintTests(unittest.TestCase):
    REBUILD_SHIM = (
        'C:\\Users\\x\\AppData\\Roaming\\uv\\tools\\graphifyy\\Scripts\\python.exe -c "\n'
        "import os, signal, sys\nfrom pathlib import Path\n"
        "print(f'[graphify hook] rebuilding...')\n"
        "from graphify.watch import _rebuild_code, _apply_resource_limits\n\""
    )

    def test_matches_rebuild_processes(self):
        self.assertTrue(is_rebuild_cmdline(self.REBUILD_SHIM))

    def test_never_matches_unrelated_services(self):
        for cmd in (
            "C:\\ComfyUI\\.venv\\Scripts\\python.exe -s ComfyUI\\main.py --base-directory X",
            "python.exe -m hermes_cli.main dashboard --no-open --host 127.0.0.1 --port 9120",
            "python.exe scripts\\chat-proxy.py",
            "python.exe -m http.server 8077 --bind 127.0.0.1",
            "python.exe -m pytest tests/",
            "node.exe next dev -p 3010",
            "",
        ):
            self.assertFalse(is_rebuild_cmdline(cmd), cmd)

    def test_classify_newest_wins_and_hung(self):
        rebuilds = [
            {"pid": 1, "ppid": 0, "age_s": 12, "cmdline": "x"},    # newest generation
            {"pid": 2, "ppid": 1, "age_s": 13, "cmdline": "x"},    # its shim pair (within 5s)
            {"pid": 3, "ppid": 0, "age_s": 240, "cmdline": "x"},   # superseded
            {"pid": 4, "ppid": 0, "age_s": 9000, "cmdline": "x"},  # hung past watchdog budget
        ]
        healthy, stale = classify(rebuilds, max_age=600)
        self.assertEqual(sorted(p["pid"] for p in healthy), [1, 2])
        self.assertEqual(sorted(p["pid"] for p in stale), [3, 4])
        reasons = {p["pid"]: p["reason"] for p in stale}
        self.assertIn("superseded", reasons[3])
        self.assertIn("hung", reasons[4])

    def test_classify_empty(self):
        self.assertEqual(classify([], 600), ([], []))


if __name__ == "__main__":
    unittest.main()
