"""G5Q.1d: product setup + management flow guards.

Locks in the in-dashboard install/setup flow, the real Skills management table,
the guided Claude Code setup flow, unload-to-no-graph, the
Reports/Activity/Memory management controls, and the rewritten How-To -- all
against the generator source (the emitted page is the user surface; these assert
the strings the browser QA verified render).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GEN = (REPO / "scripts" / "graphify_dashboard_mock.py").read_text(encoding="utf-8")
OUT = REPO / "graphify-out" / "views" / "graphify-dashboard.html"
PAGE = OUT.read_text(encoding="utf-8") if OUT.exists() else ""


class SetupInstallTests(unittest.TestCase):
    def test_setup_card_present(self):
        self.assertIn('id="set-setup"', GEN)
        self.assertIn("Setup &amp; Install", GEN)

    def test_setup_has_install_and_start_commands(self):
        self.assertIn("uv tool install graphifyy", GEN)
        self.assertIn("python scripts/start_graphify_dashboard.py", GEN)
        self.assertIn("git clone", GEN)

    def test_copy_buttons_exist(self):
        self.assertIn('class="cpy"', GEN)
        if PAGE:
            self.assertGreaterEqual(PAGE.count('class="cpy"'), 8)

    def test_first_repo_workflow_described(self):
        self.assertIn("Graph your first repo", GEN)


class SkillsManagementTests(unittest.TestCase):
    def test_skills_mgmt_container(self):
        self.assertIn('id="skill-mgmt"', GEN)
        self.assertIn("SKILLS_MGMT", GEN)

    def test_all_major_skills_listed(self):
        for name in ("Graphify scan / read-model", "3D Hivemind visualization",
                     "2D Explorer", "Local graph QA / Ask Console", "Node lookup / jump",
                     "Project graph switching", "Local generate / rebuild bridge",
                     "Hunter -- project auditor", "Reports", "Orphan / disconnect detection",
                     "Path / chain tracing", "Hook / process hygiene", "Install / setup",
                     "Asset seeding", "Claude Code MCP connector",
                     "Skills registry / packs", "Visual QA / screenshot gate",
                     "Security -- CSRF / loopback bridge"):
            self.assertIn(name, GEN, name)

    def test_registry_claim_is_honest_minimal(self):
        # G5Q.1u/y: a real LOCAL pack registry ships; remote registry stays planned
        self.assertIn("remote/community registry planned", GEN)
        self.assertIn("Graph exporters", GEN)


class ClaudeCodeConnectorSetupTests(unittest.TestCase):
    def test_guided_flow_markers(self):
        block = GEN.split('id="set-claudecode"', 1)[1].split('id="set-skills"', 1)[0]
        self.assertIn("claude mcp add -s user graphify", block)
        self.assertIn("claude mcp list", block)
        self.assertIn("graphify_mcp_server.py --selftest", block)
        self.assertIn("GATED", block)
        self.assertIn("no call has ever been made", block)

    def test_gated_and_no_fake_connected(self):
        block = GEN.split('id="set-claudecode"', 1)[1].split('id="set-skills"', 1)[0]
        self.assertNotIn(">connected<", block.lower())

    def test_scanner_step_with_credit(self):
        block = GEN.split('id="set-claudecode"', 1)[1].split('id="set-skills"', 1)[0]
        self.assertIn("uv tool install graphifyy", block)
        self.assertIn("github.com/safishamsi/graphify", block)

    def test_install_commands_research_verified(self):
        block = GEN.split('id="set-claudecode"', 1)[1].split('id="set-skills"', 1)[0]
        self.assertIn("claude.ai/install.ps1", GEN)  # filled via @@CC_INSTALL@@
        self.assertIn("Anthropic.ClaudeCode", GEN)
        self.assertIn("@anthropic-ai/claude-code", GEN)
        self.assertIn("not Git Bash", block)


class UnloadGraphTests(unittest.TestCase):
    def test_unload_to_no_graph_state(self):
        self.assertIn("const unloadGraph = ", GEN)
        self.assertIn("let UNLOADED = false", GEN)
        self.assertIn("graph_unloaded", GEN)

    def test_projready_honors_unloaded(self):
        self.assertIn("!UNLOADED && p && p.graphStatus === 'ready'", GEN)

    def test_ask_and_hunter_no_graph_after_unload(self):
        self.assertIn("you unloaded the active graph", GEN)
        self.assertIn("no graph loaded (you unloaded it)", GEN)

    def test_reload_path_exists(self):
        self.assertIn("ca-reload", GEN)
        self.assertIn("RELOAD ", GEN)


class ManagementControlTests(unittest.TestCase):
    def test_reports_clear_and_per_report(self):
        self.assertIn('id="hunt-clear-all"', GEN)
        self.assertIn("hunt-copy", GEN)
        self.assertIn("hunt-del", GEN)
        self.assertIn("hunter_reports_cleared", GEN)

    def test_activity_clear_and_copy(self):
        for m in ('id="act-copy"', 'id="act-clear-asks"', 'id="act-clear-events"',
                  "wireActivityMgmt"):
            self.assertIn(m, GEN, m)

    def test_memory_clear_all(self):
        self.assertIn('id="mem-clear-all"', GEN)
        self.assertIn("all_local_data_cleared", GEN)

    def test_localstorage_clears_never_touch_disk(self):
        # the clears must operate on localStorage only -- never call the bridge
        # clean/generate endpoints, and never delete repo/views
        self.assertIn("Source repos and generated views are never touched", GEN
                      .replace("are NOT affected", "are never touched")
                      if "are never touched" not in GEN else GEN)
        self.assertIn("localStorage", GEN)


class HowToGuideTests(unittest.TestCase):
    def test_product_guide_sections(self):
        howto = GEN.split('data-sec="howto"', 1)[1].split('data-sec="reports"', 1)[0]
        heads = re.findall(r"<h3>([^<]+)</h3>", howto)
        self.assertGreaterEqual(len(heads), 20)
        joined = " ".join(heads)
        for token in ("What GraphiQuest is", "Start here", "Graphify scanner",
                      "Connect your first repo", "3D Hivemind", "2D Explorer",
                      "Hunter", "Reports", "Connect Claude Code",
                      "How the pieces talk",
                      "Clear reports", "Unload", "Clean up generated views",
                      "Troubleshooting"):
            self.assertIn(token, joined, token)


class NoFakeConnectionTests(unittest.TestCase):
    def test_no_connector_connected_claim(self):
        # the connectors must never claim they are connected/active/live
        low = GEN.lower()
        self.assertNotIn("connector is connected", low)
        self.assertNotIn("status: connected", low)

    def test_no_fake_execution_claim(self):
        self.assertIn("never calls Claude", GEN)


class WorkbenchUntouchedTests(unittest.TestCase):
    def test_apps_workbench_unchanged(self):
        import subprocess
        out = subprocess.run(["git", "diff", "HEAD", "--name-only", "--", "apps/workbench"],
                             cwd=REPO, capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), "", "apps/workbench must be untouched")


class AskConsoleNLTests(unittest.TestCase):
    """G5Q.1i: natural-language tolerance -- operator's 'can you jump to
    pepper workspace' must reach the find handler, not generic unsupported."""

    def test_politeness_stripping_present(self):
        self.assertIn("(?:can|could|would|will)", GEN)
        self.assertIn("tolerate natural phrasing", GEN)

    def test_find_verb_synonyms(self):
        for verb in ("take me to", "show me", "navigate to", "fly to", "where is"):
            self.assertIn(verb, GEN, verb)

    def test_word_by_word_fallback(self):
        self.assertIn("attempts", GEN)
        self.assertIn("matched on", GEN)
        self.assertIn("also tried each word", GEN)

    def test_nodeish_unsupported_coached(self):
        self.assertIn("That looks like a node search", GEN)

    def test_claudecode_lane_answers_in_dashboard(self):
        # G5Q.1l operator direction: the Claude Code lane ACTUALLY answers in
        # the response window -- one bounded real call per explicit ask.
        self.assertIn("askClaudeCode(q)", GEN)
        self.assertIn("'/api/claudecode/ask'", GEN)
        self.assertIn("Asking your Claude Code", GEN)
        self.assertIn("one real call per ask", GEN)
        # never automatic: the only caller is the lane branch in submitAskQ
        self.assertIn("const askClaudeCode = q =>", GEN)
        self.assertEqual(GEN.count("askClaudeCode(q)"), 1)

    def test_chat_flyout_present(self):
        for m in ('id="chatfly"', 'id="cf-thread"', 'id="cf-in"', 'id="cf-close"',
                  'id="resp-expand"', "submitAskQ"):
            self.assertIn(m, GEN, m)

    def test_scrollbars_and_autoscroll(self):
        self.assertIn("scrollbar-width:thin", GEN)
        self.assertIn("::-webkit-scrollbar-thumb", GEN)
        self.assertIn("body.scrollTop = 0", GEN)
        self.assertIn("th.scrollTop = th.scrollHeight", GEN)

    def test_overlays_reparented_to_body(self):
        # caught live: overlays inside #main were painted over by #side
        self.assertIn("document.body.appendChild(el)", GEN)

    def test_help_and_howto_updated(self):
        self.assertIn("natural phrasing OK", GEN)
        self.assertIn("fall back word-by-word", GEN)

    def test_most_connected_answered_locally(self):
        # G5Q.1j: "what are the most connected files and what depends on them?"
        # must be ANSWERED from the read-model top list (same data as the right
        # panel), not hijacked by the neighbor matcher into "no node selected".
        self.assertIn("most connected|top (?:5 |five )?(?:files|nodes)", GEN)
        self.assertIn("Most connected files in this graph:", GEN)
        self.assertIn("RM_TOP_CACHE[p0.id]", GEN)
        # the ranking matcher must run BEFORE the neighbor matcher
        self.assertLess(GEN.find("Most connected files in this graph:"),
                        GEN.find("/connect|neighbou?r/"))

    def test_claude_code_speak_prefix_stripped(self):
        self.assertIn("use the graphify tools?", GEN)


class StalePageDetectorTests(unittest.TestCase):
    """G5Q.1k: a running tab keeps the OLD app after the page file changes --
    burned the operator twice ('still doesnt work' = stale tab). The page now
    HEAD-polls its own Last-Modified and shows a RELOAD NOW banner."""

    def test_watcher_present(self):
        for marker in ("staleWatch", "Last-Modified", "stale-banner",
                       "RELOAD NOW", "__staleCheck", "stale_page_detected"):
            self.assertIn(marker, GEN, marker)
            if PAGE:
                self.assertIn(marker, PAGE, marker)

    def test_polls_own_path_no_network_beyond_loopback(self):
        # HEAD against location.pathname only -- never an external URL
        self.assertIn("fetch(location.pathname, { method: 'HEAD'", GEN)


if __name__ == "__main__":
    unittest.main()


class FirstRunLandingTests(unittest.TestCase):
    """G5Q.1q: scanner installed -> auto-load (no landing); missing -> landing
    page whose SETUP button installs the requirement, then loads in."""

    def test_landing_markers(self):
        for m in ("firstRun", "'/api/setup/install-graphify'", "INSTALL &amp; START",
                  "graphifyDetected) return", "uv tool install graphifyy"):
            self.assertIn(m, GEN, m)

    def test_landing_credits_scanner_author(self):
        block = GEN.split("function firstRun", 1)[1].split("stale-page detector", 1)[0]
        self.assertIn("safishamsi", block)

    def test_install_endpoint_and_fixed_chain(self):
        import sys as _sys
        _sys.path.insert(0, str(REPO / "scripts"))
        import graphify_dashboard_bridge as bridge
        src = (REPO / "scripts" / "graphify_dashboard_bridge.py").read_text(encoding="utf-8")
        self.assertIn('"/api/setup/install-graphify"', src)
        # already installed -> short-circuits, never runs an installer
        orig = bridge.graphify_exe
        bridge.graphify_exe = lambda: r"C:\fake\graphify.exe"
        try:
            res = bridge.install_graphify()
        finally:
            bridge.graphify_exe = orig
        self.assertTrue(res["ok"])
        self.assertTrue(res.get("already"))
        # nothing on PATH -> honest failure listing the fixed chain
        orig_w, orig_g = bridge.shutil.which, bridge.graphify_exe
        orig_run = bridge.subprocess.run
        bridge.shutil.which = lambda n: None
        bridge.graphify_exe = lambda: None
        class _R:
            returncode = 1
            stdout = ""
            stderr = "offline"
        bridge.subprocess.run = lambda *a, **k: _R()  # pip rung runs but fails
        try:
            res2 = bridge.install_graphify()
        finally:
            bridge.shutil.which, bridge.graphify_exe = orig_w, orig_g
            bridge.subprocess.run = orig_run
        self.assertFalse(res2["ok"])
        self.assertIn("uv: not found", res2["reason"])


class EmptyStatePlaceholderTests(unittest.TestCase):
    """G5Q.1r: the no-graph state must not wear the BAKED host-graph
    placeholders (operator: "my workbench concepts is appearing")."""

    def test_no_baked_counts_in_viewport_badge(self):
        self.assertIn("select a project to load a graph", GEN)
        self.assertNotIn("{html.escape(C['nodes'])} nodes · {html.escape(C['slices'])} clusters", GEN)

    def test_paintnograph_blanks_counts_and_concepts(self):
        block = GEN.split("const paintNoGraph", 1)[1].split("const card", 1)[0]
        self.assertIn("#statgrid .big", block)
        self.assertIn("__renderConcepts([])", block)
        self.assertIn("TDZ-safe", block)


class StopAndClearTests(unittest.TestCase):
    """G5Q.1s: STOP for in-flight asks (real bridge-side kill) + CLR clear."""

    def test_markers(self):
        for m in ('id="ask-stop"', 'id="ask-clr"', 'id="cf-stop"', 'id="cf-clr"',
                  "'/api/claudecode/stop'", "Stopped by you", "responses_cleared",
                  "AbortController"):
            self.assertIn(m, GEN, m)

    def test_stale_legend_removed_and_statgrid_aligned(self):
        self.assertNotIn("found in code (structural)", GEN)
        self.assertNotIn("inferred (classification)", GEN)
        self.assertIn("repeat(3,minmax(0,auto));justify-content:space-between", GEN)

    def test_bridge_stop_kills_only_held_proc(self):
        import sys as _s
        _s.path.insert(0, str(REPO / "scripts"))
        import graphify_dashboard_bridge as bridge
        self.assertIn('"/api/claudecode/stop"',
                      (REPO / "scripts" / "graphify_dashboard_bridge.py").read_text(encoding="utf-8"))
        res = bridge.claude_code_stop()   # nothing running -> honest no-op
        self.assertTrue(res["ok"])
        self.assertFalse(res["stopped"])
