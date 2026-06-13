"""G5Q.1e: token/context savings + connector-UX + skills-completion guards.

Covers the savings formula/method, the no-fake-measured rule, the savings UI
surfaces, the connector action panels (CONNECT / COPY / CHECK SELF-TEST), the
safe MCP-selftest bridge endpoint, and the Skills filters + routed actions.
"""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GEN = (REPO / "scripts" / "graphify_dashboard_mock.py").read_text(encoding="utf-8")
BRIDGE = (REPO / "scripts" / "graphify_dashboard_bridge.py").read_text(encoding="utf-8")
OUT = REPO / "graphify-out" / "views" / "graphify-dashboard.html"
PAGE = OUT.read_text(encoding="utf-8") if OUT.exists() else ""


class SavingsFormulaTests(unittest.TestCase):
    def test_formula_present(self):
        # savings % = (claude-only - graphify) / claude-only * 100
        self.assertIn("(claudeOnly - graphify) / claudeOnly * 1000) / 10", GEN)

    def test_same_estimator_both_paths(self):
        # both estimates use the documented chars/4 TOK estimator
        self.assertIn("const TOK = n => Math.round((n || 0) / 4)", GEN)
        self.assertIn("TOK((raw || '').length)", GEN)        # claude-only
        self.assertIn("TOK(JSON.stringify(payload).length)", GEN)  # graphify

    def test_result_labelled_estimate_not_measured(self):
        self.assertIn("measured: false", GEN)
        self.assertIn("chars/4 estimate", GEN)

    def test_no_fake_measured_claude_tokens(self):
        # measured mode must be described as gated, never claimed
        self.assertIn("measured Claude-token mode is gated", GEN)

    def test_savings_history_key_and_event(self):
        self.assertIn("graphify-savings-v1", GEN)
        self.assertIn("savings_check_run", GEN)
        self.assertIn("['graphify-savings-v1',", GEN)  # in MEM_KEYS

    def test_no_graph_savings_is_honest(self):
        self.assertIn("Load or graph a project first", GEN)


class SavingsSurfacesTests(unittest.TestCase):
    def test_right_panel_widget(self):
        for m in ('id="savecard"', "GRAPHIFY CONTEXT SAVINGS", 'id="sv-pct"',
                  'id="sv-run"', 'id="sv-claude"', 'id="sv-graphify"'):
            self.assertIn(m, GEN, m)

    def test_settings_context_savings_card(self):
        self.assertIn('id="set-savings"', GEN)
        self.assertIn("Context Savings", GEN)
        self.assertIn("Why Graphify saves tokens", GEN)

    def test_skills_token_savings_card(self):
        self.assertIn("Token / context savings", GEN)
        self.assertIn('"run-savings"', GEN)          # the action wired in the generator
        self.assertIn('data-action="run-savings"', PAGE)  # rendered in the emitted page


class ConnectorUXTests(unittest.TestCase):
    def test_claudecode_action_panel(self):
        for m in ('id="claudecode-panel"', 'id="claudecode-connect"', "CONNECT CLAUDE CODE",
                  'data-cpy-for="cmd-cc-add"', 'id="claudecode-check"',
                  "never calls Claude Code automatically"):
            self.assertIn(m, GEN, m)

    def test_status_ladder_honest(self):
        # the LED only goes green on a real self-test pass; no "connected" from a snippet
        self.assertIn("SELF-TEST PASSED", GEN)
        self.assertIn("NOT CONNECTED", GEN)
        self.assertNotIn(">CONNECTED<", GEN)

    def test_check_selftest_calls_bridge(self):
        self.assertIn("/api/mcp/selftest", GEN)
        self.assertIn("graphify-mcp-selftest-v1", GEN)


class McpSelftestEndpointTests(unittest.TestCase):
    def test_endpoint_is_fixed_argv_readonly(self):
        self.assertIn('self.path == "/api/mcp/selftest"', BRIDGE)
        self.assertIn('"--selftest"', BRIDGE)
        # the only args are the server path, --repo DASHBOARD_ROOT, --selftest
        self.assertIn("graphify_mcp_server.py", BRIDGE)
        self.assertIn("DASHBOARD_ROOT", BRIDGE)

    def test_endpoint_is_csrf_guarded(self):
        # it lives inside do_POST which gates on _loopback_only + _csrf_ok
        post = BRIDGE.split("def do_POST", 1)[1]
        self.assertIn("self._csrf_ok()", post.split("def ", 1)[0])
        self.assertIn('self.path == "/api/mcp/selftest"', post)


class SkillsCompletionTests(unittest.TestCase):
    def test_filter_chips(self):
        for f in ("data-f=\"all\"", "data-f=\"imp\"", "data-f=\"part\"",
                  "data-f=\"plan\"", "data-f=\"gate\"", "data-f=\"ext\""):
            self.assertIn(f, GEN, f)

    def test_cards_carry_status_for_filtering(self):
        # the helper emits data-st on every card; check the rendered page
        self.assertTrue(PAGE, "emitted page must exist")
        self.assertIn('class="gcard" data-st="ext"', PAGE)
        self.assertIn('class="gcard" data-st="gate"', PAGE)

    def test_action_buttons_route(self):
        self.assertTrue(PAGE, "emitted page must exist")
        for act in ("set-graphify", "run-hunter", "set-repos",
                    "set-claudecode", "run-savings"):
            self.assertIn(f'data-action="{act}"', PAGE, act)

    def test_skill_action_router(self):
        self.assertIn("window.__skillAction", GEN)
        self.assertIn("act.indexOf('set-') === 0", GEN)


class WorkbenchUntouchedTests(unittest.TestCase):
    def test_apps_workbench_unchanged(self):
        out = subprocess.run(["git", "diff", "HEAD", "--name-only", "--", "apps/workbench"],
                             cwd=REPO, capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
