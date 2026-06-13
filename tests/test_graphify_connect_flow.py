"""G5Q.1f-h: real connector connect-flow guards (single Claude Code connector).

Locks in the CONNECT wizard (no-browser-sign-in truth, honest status ladder,
self-test distinct from "connected", graphify-scanner credit), the read-only
Claude Code registration detection (~/.claude.json -- the bridge NEVER writes
it), and the fixed-argv one-click register endpoint. Detection tests
monkeypatch bridge.claude_code_config_path to a temp file so they never touch
a real config; the register test monkeypatches subprocess so nothing executes.

Standard library unittest:
  python tests/test_graphify_connect_flow.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import graphify_dashboard_bridge as bridge  # noqa: E402

GEN = (REPO_ROOT / "scripts" / "graphify_dashboard_mock.py").read_text(encoding="utf-8")
BRIDGE_SRC = (REPO_ROOT / "scripts" / "graphify_dashboard_bridge.py").read_text(encoding="utf-8")
OUT = REPO_ROOT / "graphify-out" / "views" / "graphify-dashboard.html"
PAGE = OUT.read_text(encoding="utf-8") if OUT.exists() else ""


class WizardMarkupTests(unittest.TestCase):
    def test_wizard_modal_present(self):
        for marker in ('id="connmodal"', 'id="cm-led"', 'id="cm-banner"',
                       'id="cm-steps"', 'id="cm-close"'):
            self.assertIn(marker, GEN, marker)
            if PAGE:
                self.assertIn(marker, PAGE, marker)

    def test_modal_overlays_sections(self):
        # G5Q.1h dry-run catch: #sections is z-index 60 -- the wizard opened
        # from How-To/Settings rendered BEHIND it until raised.
        self.assertIn("#connmodal{display:none;position:fixed;inset:0;z-index:140", GEN)

    def test_single_pill_with_logo_routes_to_wizard(self):
        self.assertIn('id="pill-claudecode-sub"', GEN)
        self.assertNotIn('id="pill-claude-sub"', GEN)
        self.assertIn("openConnWizard", GEN)
        # the pill carries the inline starburst mark
        pill = GEN.split('data-connector="claudecode"', 1)[1].split("</div>", 1)[0]
        self.assertIn("<svg", pill)

    def test_openclaw_fully_removed(self):
        self.assertNotIn("openclaw", GEN.lower())
        if PAGE:
            self.assertNotIn("openclaw", PAGE.lower())

    def test_claude_desktop_removed_single_explainer_left(self):
        # G5Q.1h operator decision: one connector. The ONLY allowed mention is
        # the "terminal window inside Claude Desktop -- same thing" explainer.
        self.assertEqual(GEN.count("Claude Desktop"), 1)
        self.assertIn("terminal window inside Claude Desktop", GEN)
        for gone in ('id="set-claude"', 'id="claude-panel"', "CONNECT CLAUDE DESKTOP",
                     "claude_desktop_config.json", 'data-lane="claude"',
                     "ENRICH WITH CLAUDE DESKTOP"):
            self.assertNotIn(gone, GEN, gone)

    def test_wizard_has_real_primary_actions(self):
        for action in ("cm-selftest", "cm-register", "cm-copyadd", "cm-mark",
                       "cm-recheck", "cmd-cc-install", "cmd-cc-gfy", "cmd-cc-list"):
            self.assertIn(action, GEN, action)

    def test_scanner_credit_in_wizard_and_settings(self):
        self.assertGreaterEqual(GEN.count("github.com/safishamsi/graphify"), 3)
        self.assertIn("full credit to the author", GEN)


class HonestyLadderTests(unittest.TestCase):
    def test_no_browser_sign_in_truth_stated(self):
        self.assertIn("no browser sign-in", GEN)

    def test_no_fake_oauth_claim(self):
        for fake in ("Sign in with Claude", "Authorize with Claude",
                     "OAuth flow will open", "browser authorization window"):
            self.assertNotIn(fake, GEN, fake)

    def test_selftest_distinct_from_connected(self):
        self.assertIn("proves the LOCAL server, not a Claude connection", GEN)

    def test_connected_never_claimed_without_verification(self):
        self.assertIn("REGISTERED + VERIFIED BY YOU (CLAUDE MCP LIST)", GEN)
        for fake in ("CLAUDE CONNECTED", "CONNECTED TO CLAUDE",
                     "Connected ✓", "CLAUDE CODE CONNECTED"):
            self.assertNotIn(fake, GEN, fake)

    def test_ladder_has_scanner_rung(self):
        self.assertIn("INSTALL THE GRAPHIFY SCANNER (STEP 2)", GEN)

    def test_no_stale_mcpb_or_writer_claims(self):
        for gone in (".mcpb", "WRITE CONFIG FOR ME", "cm-write", "cm-copycfg"):
            self.assertNotIn(gone, GEN, gone)

    def test_paste_into_claude_onboarding_prompt(self):
        self.assertIn('id="cmd-claude-onboard"', GEN)
        block = GEN.split('id="cmd-claude-onboard"', 1)[1].split("</span>", 1)[0]
        for marker in ("uv tool install graphifyy", "graphify update",
                       "start_graphify_dashboard.py", "claude mcp add -s user graphify",
                       "claude mcp list", "safishamsi"):
            self.assertIn(marker, block, marker)

    def test_generic_placeholders_not_personal_paths(self):
        # operator rule: examples use %USERNAME%-style placeholders; the only
        # "Boshe" hits allowed are the repo's own GitHub org URL (Bosheda).
        self.assertIn("%USERNAME%", GEN)
        import re
        personal = [m for m in re.findall(r"Boshe[^d]", GEN)]
        self.assertEqual(personal, [], "personal user dir leaked into the generator")


class ConnectorStatusTests(unittest.TestCase):
    def test_endpoints_wired(self):
        self.assertIn('"/api/connectors/status"', BRIDGE_SRC)
        self.assertIn('"/api/claudecode/register"', BRIDGE_SRC)
        self.assertIn('"/api/claudecode/ask"', BRIDGE_SRC)
        self.assertNotIn("write-config", BRIDGE_SRC)

    def test_status_shape_and_honesty(self):
        st = bridge.connectors_status()
        for key in ("claudeCodeOnPath", "claudeCodeConfigPath",
                    "claudeCodeRegistered", "claudeCodeCurrent",
                    "claudeCodeConfigMalformed", "claudeCodeAddCmd",
                    "graphifyDetected", "graphifyVersion", "serverPath"):
            self.assertIn(key, st, key)
        self.assertNotIn("connected", {k.lower() for k in st})

    def test_mcp_entry_is_absolute_and_server_side(self):
        entry = bridge.graphify_mcp_entry()
        self.assertEqual(set(entry), {"command", "args"})
        self.assertTrue(Path(entry["command"]).is_absolute())
        self.assertTrue(Path(entry["args"][0]).is_absolute())
        self.assertIn("--repo", entry["args"])


class ClaudeCodeDetectionTests(unittest.TestCase):
    """Registration detected by READING ~/.claude.json (live-verified shape
    2026-06-11: top-level mcpServers, entries carry extra type/env keys)."""

    def _with_cc_config(self, payload):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                          encoding="utf-8")
        tmp.write(payload if isinstance(payload, str) else json.dumps(payload))
        tmp.close()
        orig = bridge.claude_code_config_path
        bridge.claude_code_config_path = lambda: Path(tmp.name)
        try:
            return bridge.connectors_status()
        finally:
            bridge.claude_code_config_path = orig
            Path(tmp.name).unlink(missing_ok=True)

    def test_add_cmd_doc_canonical_and_absolute(self):
        cmd = bridge.claude_code_add_cmd()
        self.assertTrue(cmd.startswith("claude mcp add -s user graphify -- "))
        entry = bridge.graphify_mcp_entry()
        self.assertIn(entry["command"], cmd)
        self.assertIn(entry["args"][0], cmd)
        self.assertIn("--repo", cmd)

    def test_registered_and_current(self):
        entry = bridge.graphify_mcp_entry()
        st = self._with_cc_config({"mcpServers": {"graphify": {
            "type": "stdio", "command": entry["command"],
            "args": entry["args"], "env": {}}}})
        self.assertTrue(st["claudeCodeRegistered"])
        self.assertTrue(st["claudeCodeCurrent"])

    def test_registered_but_outdated(self):
        st = self._with_cc_config({"mcpServers": {"graphify": {
            "type": "stdio", "command": "python", "args": ["old.py"], "env": {}}}})
        self.assertTrue(st["claudeCodeRegistered"])
        self.assertFalse(st["claudeCodeCurrent"])

    def test_not_registered(self):
        st = self._with_cc_config({"mcpServers": {"other": {"command": "x"}}})
        self.assertFalse(st["claudeCodeRegistered"])

    def test_malformed_config_flagged_not_fatal(self):
        st = self._with_cc_config("{not json")
        self.assertFalse(st["claudeCodeRegistered"])
        self.assertTrue(st["claudeCodeConfigMalformed"])

    def test_bridge_never_writes_claude_code_config(self):
        cc_block = BRIDGE_SRC.split("def claude_code_config_path")[1].split(
            "def claude_code_add_cmd")[0]
        self.assertIn("NEVER writes", cc_block)
        connect_src = BRIDGE_SRC.split("def claude_code_config_path")[1].split(
            "def seed_design_assets")[0]
        self.assertNotIn("workbench", connect_src)
        for w in ("write_text", "with open(", "shutil.copy"):
            self.assertNotIn(w, connect_src, w)


class RegisterEndpointTests(unittest.TestCase):
    """The one-click connect: FIXED argv, zero client input, nothing executed
    in tests (subprocess + which are monkeypatched)."""

    def test_refuses_without_cli(self):
        orig = bridge.shutil.which
        bridge.shutil.which = lambda name: None
        try:
            res = bridge.claude_code_register()
        finally:
            bridge.shutil.which = orig
        self.assertFalse(res["ok"])
        self.assertIn("not on PATH", res["reason"])

    def test_fixed_argv_shape(self):
        captured = {}

        class _R:
            returncode = 0
            stdout = "Added stdio MCP server graphify"
            stderr = ""

        def fake_run(argv, **kw):
            captured["argv"] = argv
            return _R()

        orig_run, orig_which = bridge.subprocess.run, bridge.shutil.which
        bridge.subprocess.run = fake_run
        bridge.shutil.which = lambda name: r"C:\fake\claude.exe" if name == "claude" else orig_which(name)
        try:
            bridge.claude_code_register()
        finally:
            bridge.subprocess.run, bridge.shutil.which = orig_run, orig_which
        entry = bridge.graphify_mcp_entry()
        self.assertEqual(captured["argv"][:7],
                         [r"C:\fake\claude.exe", "mcp", "add", "-s", "user",
                          "graphify", "--"])
        self.assertEqual(captured["argv"][7], entry["command"])
        self.assertEqual(captured["argv"][8:], entry["args"])

    def test_ok_requires_real_registration_not_just_exit_zero(self):
        # exit 0 alone is not success -- the status re-read must show the entry
        class _R:
            returncode = 0
            stdout = ""
            stderr = ""

        orig_run, orig_which = bridge.subprocess.run, bridge.shutil.which
        orig_path = bridge.claude_code_config_path
        tmp = Path(tempfile.mkdtemp()) / "claude.json"
        tmp.write_text("{}", encoding="utf-8")  # no graphify entry appears
        bridge.subprocess.run = lambda *a, **k: _R()
        bridge.shutil.which = lambda name: r"C:\fake\claude.exe"
        bridge.claude_code_config_path = lambda: tmp
        try:
            res = bridge.claude_code_register()
        finally:
            bridge.subprocess.run, bridge.shutil.which = orig_run, orig_which
            bridge.claude_code_config_path = orig_path
            tmp.unlink(missing_ok=True)
        self.assertFalse(res["ok"])


class AskEndpointTests(unittest.TestCase):
    """G5Q.1l (operator-directed): one explicit ask = one bounded headless
    Claude Code call. Nothing executes in these tests (monkeypatched)."""

    def test_refuses_empty_and_oversize(self):
        self.assertFalse(bridge.claude_code_ask("")["ok"])
        self.assertFalse(bridge.claude_code_ask("x" * 4001)["ok"])

    def test_refuses_without_cli(self):
        orig = bridge.shutil.which
        bridge.shutil.which = lambda name: None
        try:
            res = bridge.claude_code_ask("hello")
        finally:
            bridge.shutil.which = orig
        self.assertFalse(res["ok"])
        self.assertIn("not on PATH", res["reason"])

    def test_argv_is_bounded_and_strict(self):
        captured = {}

        class _P:
            returncode = 0
            pid = 4242

            def communicate(self, timeout=None):
                captured["timeout"] = timeout
                return json.dumps({"result": "graph answer", "total_cost_usd": 0.01}), ""

            def poll(self):
                return 0

        orig_popen = bridge.subprocess.Popen
        orig_which = bridge.shutil.which
        orig_status = bridge.connectors_status
        bridge.subprocess.Popen = lambda argv, **kw: captured.update(argv=argv, kw=kw) or _P()
        bridge.shutil.which = lambda name: r"C:\fake\claude.exe"
        bridge.connectors_status = lambda: {"claudeCodeRegistered": True}
        try:
            res = bridge.claude_code_ask("what are the hubs?")
        finally:
            bridge.subprocess.Popen = orig_popen
            bridge.shutil.which = orig_which
            bridge.connectors_status = orig_status
        self.assertTrue(res["ok"])
        self.assertEqual(res["answer"], "graph answer")
        argv = captured["argv"]
        self.assertEqual(argv[:3], [r"C:\fake\claude.exe", "-p", "what are the hubs?"])
        self.assertIn("--strict-mcp-config", argv)        # ONLY our server loads
        self.assertIn("--allowedTools", argv)
        self.assertIn("mcp__graphify", argv)
        self.assertNotIn("--dangerously-skip-permissions", argv)
        self.assertEqual(captured["timeout"], 180)        # bound lives on communicate now
        # the mcp-config JSON pins exactly the graphify entry
        cfg = json.loads(argv[argv.index("--mcp-config") + 1])
        self.assertEqual(list(cfg["mcpServers"]), ["graphify"])

    def test_refuses_when_not_registered(self):
        orig_which = bridge.shutil.which
        orig_status = bridge.connectors_status
        bridge.shutil.which = lambda name: r"C:\fake\claude.exe"
        bridge.connectors_status = lambda: {"claudeCodeRegistered": False}
        try:
            res = bridge.claude_code_ask("hello")
        finally:
            bridge.shutil.which = orig_which
            bridge.connectors_status = orig_status
        self.assertFalse(res["ok"])
        self.assertIn("not registered", res["reason"])


if __name__ == "__main__":
    unittest.main()


class EnrichEndpointTests(unittest.TestCase):
    """G5Q.1m: REAL Hunter enrichment -- bounded, data-in-prompt, JSON out.
    Nothing executes (claude_code_ask monkeypatched)."""

    def test_prompt_encodes_disciplines_and_verbatim_ids(self):
        self.assertIn("silver-platter", bridge.ENRICH_PROMPT)
        self.assertIn("grill-me", bridge.ENRICH_PROMPT)
        self.assertIn("guess-what", bridge.ENRICH_PROMPT)
        self.assertIn("run_hunter", bridge.ENRICH_PROMPT)
        self.assertIn("character-for-character", bridge.ENRICH_PROMPT)

    def test_enrich_parses_recommendations(self):
        orig = bridge.claude_code_ask
        bridge.claude_code_ask = lambda q, max_len=4000: {
            "ok": True, "durationS": 1.0,
            "answer": '{"recommendations":[{"title":"t","why":"w","action":"a",'
                      '"confidence":"high","nodeIds":["n1"]}]}'}
        try:
            res = bridge.claude_code_enrich({"findings": [{"kind": "orphan"}]})
        finally:
            bridge.claude_code_ask = orig
        self.assertTrue(res["ok"])
        self.assertEqual(res["recommendations"][0]["nodeIds"], ["n1"])

    def test_enrich_prose_fallback_is_honest(self):
        orig = bridge.claude_code_ask
        bridge.claude_code_ask = lambda q, max_len=4000: {"ok": True, "answer": "just prose"}
        try:
            res = bridge.claude_code_enrich({"findings": []})
        finally:
            bridge.claude_code_ask = orig
        self.assertTrue(res["ok"])
        self.assertIn("JSON parse failed", res["recommendations"][0]["title"])

    def test_enrich_endpoint_wired_and_page_real(self):
        self.assertIn('"/api/claudecode/enrich"', BRIDGE_SRC)
        self.assertIn("rec-jump", GEN)
        self.assertIn("recommendation_jump", GEN)
        self.assertIn("Claude recommendations", GEN)
        self.assertNotIn("ENRICH WITH CLAUDE CODE — GATED", GEN)
        # orphan-class rec targets inherit the 2D fallback like openFinding
        self.assertIn("src.in3d === false && mode3d", GEN)
