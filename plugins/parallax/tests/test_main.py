"""Tests for main module — subprocess invocation, markdown conversion, logging, orchestration, and prompt capture."""

import io
import json
import subprocess
from unittest.mock import patch

import pytest

from src.main import (
    TERMINATION_TOKEN,
    TRIGGER_KEYWORD,
    capture_user_prompt,
    convert_actions_to_markdown,
    invoke_claude,
    mark_compaction,
    run,
    write_log,
)
from src.prompt import format_injection
from src.state import ROUND_LIMIT, HookInput, PluginEnvironment, State, Turn


# ── invoke_claude ──


class TestInvokeClaude:
    def test_returns_stdout_on_success(self):
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="output text\n", stderr=""
        )
        with patch("src.main.subprocess.run", return_value=mock_result) as mock_run:
            result = invoke_claude("test prompt")
            assert result == "output text"
            cmd = mock_run.call_args[0][0]
            assert "claude" in cmd
            assert "-p" in cmd
            assert "--no-session-persistence" in cmd

    def test_pipes_prompt_via_stdin(self):
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr=""
        )
        with patch("src.main.subprocess.run", return_value=mock_result) as mock_run:
            invoke_claude("my prompt text")
            assert mock_run.call_args[1]["input"] == "my prompt text"
            cmd = mock_run.call_args[0][0]
            assert "my prompt text" not in cmd

    def test_returns_none_on_failure(self):
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error"
        )
        with patch("src.main.subprocess.run", return_value=mock_result):
            assert invoke_claude("test") is None

    def test_passes_model_flag(self):
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr=""
        )
        with patch("src.main.subprocess.run", return_value=mock_result) as mock_run:
            invoke_claude("test", "claude-opus-4-6")
            cmd = mock_run.call_args[0][0]
            assert "--model" in cmd
            assert "claude-opus-4-6" in cmd

    def test_passes_effort_flag(self):
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr=""
        )
        with patch("src.main.subprocess.run", return_value=mock_result) as mock_run:
            invoke_claude("test", effort="max")
            cmd = mock_run.call_args[0][0]
            assert "--effort" in cmd
            assert "max" in cmd

    def test_sets_recursion_guard_env(self):
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr=""
        )
        with patch("src.main.subprocess.run", return_value=mock_result) as mock_run:
            invoke_claude("test")
            env = mock_run.call_args[1]["env"]
            assert env["PARALLAX_INSIDE_RECURSION"] == "1"

    def test_wildcard_uses_disallowed_tools(self):
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr=""
        )
        with patch("src.main.subprocess.run", return_value=mock_result) as mock_run:
            invoke_claude("test", tools="*")
            cmd = mock_run.call_args[0][0]
            assert "--disallowedTools" in cmd
            assert "--tools" not in cmd

    def test_disables_all_tools_by_default(self):
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr=""
        )
        with patch("src.main.subprocess.run", return_value=mock_result) as mock_run:
            invoke_claude("test")
            cmd = mock_run.call_args[0][0]
            idx = cmd.index("--tools")
            assert cmd[idx + 1] == ""

    def test_uses_explicit_tools_whitelist(self):
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr=""
        )
        with patch("src.main.subprocess.run", return_value=mock_result) as mock_run:
            invoke_claude("test", tools="Read")
            cmd = mock_run.call_args[0][0]
            idx = cmd.index("--tools")
            assert cmd[idx + 1] == "Read"
            allowed_idx = cmd.index("--allowedTools")
            assert cmd[allowed_idx + 1] == "Read"
            assert "--disallowedTools" not in cmd

    def test_empty_string_disables_all_tools(self):
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr=""
        )
        with patch("src.main.subprocess.run", return_value=mock_result) as mock_run:
            invoke_claude("test", tools="")
            cmd = mock_run.call_args[0][0]
            idx = cmd.index("--tools")
            assert cmd[idx + 1] == ""

    def test_returns_none_on_empty_stdout(self):
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="   \n", stderr=""
        )
        with patch("src.main.subprocess.run", return_value=mock_result):
            assert invoke_claude("test") is None


# ── convert_actions_to_markdown ──


class TestConvertActionsToMarkdown:
    def test_writes_temp_file_and_passes_path_to_claude(self, tmp_path):
        actions = [{"role": "assistant", "content": "done"}]
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="# Actions\n\nThe agent responded.", stderr=""
        )
        with patch("src.main.subprocess.run", return_value=mock_result) as mock_run:
            result = convert_actions_to_markdown(actions, tmp_path)
            assert result == "# Actions\n\nThe agent responded."
            stdin_prompt = mock_run.call_args[1]["input"]
            assert "Action record file:" in stdin_prompt
            assert str(tmp_path) in stdin_prompt
            cmd = mock_run.call_args[0][0]
            idx = cmd.index("--tools")
            assert cmd[idx + 1] == "Read"

    def test_falls_back_to_raw_json_on_failure(self, tmp_path):
        actions = [{"role": "assistant", "content": "hello"}]
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error"
        )
        with patch("src.main.subprocess.run", return_value=mock_result):
            result = convert_actions_to_markdown(actions, tmp_path)
            assert result == json.dumps(actions, ensure_ascii=False, indent=2)

    def test_cleans_up_temp_file(self, tmp_path):
        actions = [{"role": "assistant", "content": "done"}]
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr=""
        )
        with patch("src.main.subprocess.run", return_value=mock_result):
            convert_actions_to_markdown(actions, tmp_path)
        temp_files = list(tmp_path.glob("_conversion_*.json"))
        assert temp_files == []

    def test_cleans_up_temp_file_on_failure(self, tmp_path):
        actions = [{"role": "assistant", "content": "done"}]
        with patch("src.main.subprocess.run", side_effect=OSError("spawn failed")):
            with pytest.raises(OSError):
                convert_actions_to_markdown(actions, tmp_path)
        temp_files = list(tmp_path.glob("_conversion_*.json"))
        assert temp_files == []


# ── capture_user_prompt ──


class TestCaptureUserPrompt:
    def test_writes_prompt_to_file(self, tmp_path, monkeypatch):
        stdin_data = json.dumps(
            {
                "session_id": "sess1",
                "prompt": "/commit push",
                "hook_event_name": "UserPromptSubmit",
            }
        )
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))

        capture_user_prompt()

        written = (tmp_path / "sess1_last_user_prompt.txt").read_text()
        assert written == "/commit push"

    def test_writes_empty_string_when_prompt_missing(self, tmp_path, monkeypatch):
        stdin_data = json.dumps(
            {"session_id": "sess1", "hook_event_name": "UserPromptSubmit"}
        )
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))

        capture_user_prompt()

        written = (tmp_path / "sess1_last_user_prompt.txt").read_text()
        assert written == ""

    @pytest.mark.parametrize(
        "prompt",
        [
            f"implement auth system {TRIGGER_KEYWORD}",
            f"implement auth system\n{TRIGGER_KEYWORD}",
            f"  {TRIGGER_KEYWORD}  ",
            f"implement auth system {TRIGGER_KEYWORD}\n\n",
            TRIGGER_KEYWORD,
        ],
    )
    def test_activates_when_prompt_ends_with_keyword(
        self, tmp_path, monkeypatch, prompt
    ):
        stdin_data = json.dumps(
            {
                "session_id": "sess1",
                "prompt": prompt,
                "hook_event_name": "UserPromptSubmit",
            }
        )
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))

        capture_user_prompt()

        assert (tmp_path / "sess1_active").exists()

    @pytest.mark.parametrize(
        "prompt",
        [
            "fix the login bug",
            f"{TRIGGER_KEYWORD} implement auth system",
            f"refactor {TRIGGER_KEYWORD} module",
            f"<task-notification>{TRIGGER_KEYWORD} test</task-notification>",
            f"{TRIGGER_KEYWORD}.",
            f"see {TRIGGER_KEYWORD}-docs",
        ],
    )
    def test_does_not_activate_when_keyword_not_at_end(
        self, tmp_path, monkeypatch, prompt
    ):
        stdin_data = json.dumps(
            {
                "session_id": "sess1",
                "prompt": prompt,
                "hook_event_name": "UserPromptSubmit",
            }
        )
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))

        capture_user_prompt()

        assert not (tmp_path / "sess1_active").exists()

    def test_removes_stale_activation_file(self, tmp_path, monkeypatch):
        (tmp_path / "sess1_active").touch()

        stdin_data = json.dumps(
            {
                "session_id": "sess1",
                "prompt": "simple fix",
                "hook_event_name": "UserPromptSubmit",
            }
        )
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))

        capture_user_prompt()

        assert not (tmp_path / "sess1_active").exists()


class TestCaptureUserPromptTurnBoundaryCleanup:
    """capture_user_prompt cleans turn-scoped state at the turn boundary,
    preventing cross-turn contamination of round/regions/mission state."""

    def stdin(self, prompt: str) -> str:
        return json.dumps(
            {
                "session_id": "sess1",
                "prompt": prompt,
                "hook_event_name": "UserPromptSubmit",
            }
        )

    def test_cleans_stale_state_file(self, tmp_path, monkeypatch):
        (tmp_path / "sess1.json").write_text(
            json.dumps({"round": 5, "user_input": "old", "regions": ["a", "b"]})
        )
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setattr(
            "sys.stdin", io.StringIO(self.stdin("new task parallaxthink"))
        )

        capture_user_prompt()

        assert not (tmp_path / "sess1.json").exists()

    def test_cleans_stale_compaction_marker(self, tmp_path, monkeypatch):
        (tmp_path / "sess1_compacted").touch()
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setattr(
            "sys.stdin", io.StringIO(self.stdin("new task parallaxthink"))
        )

        capture_user_prompt()

        assert not (tmp_path / "sess1_compacted").exists()

    def test_no_op_when_files_absent(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setattr("sys.stdin", io.StringIO(self.stdin("task parallaxthink")))

        capture_user_prompt()

        assert not (tmp_path / "sess1.json").exists()
        assert not (tmp_path / "sess1_compacted").exists()

    def test_cleanup_runs_for_non_parallax_prompt_too(self, tmp_path, monkeypatch):
        """Cleanup is unconditional — applies even when the new prompt does
        not activate parallax.  This handles the leak path where a stale
        marker survives an inactive turn."""
        (tmp_path / "sess1.json").write_text(json.dumps({"round": 3}))
        (tmp_path / "sess1_compacted").touch()
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setattr("sys.stdin", io.StringIO(self.stdin("fix typo")))

        capture_user_prompt()

        assert not (tmp_path / "sess1.json").exists()
        assert not (tmp_path / "sess1_compacted").exists()
        assert not (tmp_path / "sess1_active").exists()


# ── write_log ──


class TestWriteLog:
    def test_creates_header_and_sections(self, tmp_path):
        log = tmp_path / "test.log"
        write_log(log, 1, new_turn=True, prompt="the prompt", region="go left")
        content = log.read_text()
        assert "[[ Round 1 - " in content
        assert "[[ Round 1 / Prompt ]]\n\nthe prompt\n\n" in content
        assert "[[ Round 1 / Region ]]\n\ngo left\n\n" in content

    def test_new_turn_overwrites(self, tmp_path):
        log = tmp_path / "test.log"
        log.write_text("old content\n")
        write_log(log, 1, new_turn=True, note="fresh")
        content = log.read_text()
        assert "old content" not in content
        assert "[[ Round 1" in content

    def test_appends_without_new_turn(self, tmp_path):
        log = tmp_path / "test.log"
        write_log(log, 1, new_turn=True, note="round 1")
        write_log(log, 2, new_turn=False, note="round 2")
        content = log.read_text()
        assert "[[ Round 1" in content
        assert "[[ Round 2" in content


# ── run ──


class TestRun:
    def _make_state(
        self, tmp_path, *, user_input="fix bug", activated=True, **overrides
    ):
        defaults = dict(
            is_inside_recursion=False,
            stop_hook_active=False,
            continuing=False,
            compacted=False,
            current_round=0,
            region_history=[],
        )
        defaults.update(overrides)
        activation_file = tmp_path / "s1_active"
        if activated:
            activation_file.touch()
        elif activation_file.exists():
            activation_file.unlink()
        return State(
            hook=HookInput(
                stop_hook_active=defaults["stop_hook_active"],
                session_id="s1",
                transcript_path=str(tmp_path / "t.jsonl"),
            ),
            env=PluginEnvironment(
                data_dir=tmp_path,
                is_inside_recursion=defaults["is_inside_recursion"],
            ),
            continuing=defaults["continuing"],
            compacted=defaults["compacted"],
            current_round=defaults["current_round"],
            region_history=defaults["region_history"],
            turn=Turn(
                user_input=user_input,
                agent_actions=[],
                agent_model="claude-opus-4-6",
            ),
        )

    def test_exits_on_recursion(self, tmp_path):
        state = self._make_state(tmp_path, is_inside_recursion=True)
        with (
            patch("src.main.build_state", return_value=state),
            patch("sys.stdin", io.StringIO("")),
            pytest.raises(SystemExit) as exc,
        ):
            run()
        assert exc.value.code == 0

    def test_exits_on_round_limit(self, tmp_path):
        state = self._make_state(
            tmp_path,
            stop_hook_active=True,
            continuing=True,
            current_round=ROUND_LIMIT,
        )
        with (
            patch("src.main.build_state", return_value=state),
            patch("sys.stdin", io.StringIO("")),
            pytest.raises(SystemExit) as exc,
        ):
            run()
        assert exc.value.code == 0

    def test_saves_initial_turn_on_new_turn(self, tmp_path):
        state = self._make_state(tmp_path, stop_hook_active=False)
        with (
            patch("src.main.build_state", return_value=state),
            patch("sys.stdin", io.StringIO("")),
            patch("src.main.save_initial_turn") as mock_save,
            patch("src.main.convert_actions_to_markdown", return_value="md"),
            patch("src.main.invoke_claude", return_value=None),
            pytest.raises(SystemExit),
        ):
            run()
        mock_save.assert_called_once_with(state)

    def test_skips_save_on_existing_turn(self, tmp_path):
        state = self._make_state(
            tmp_path, stop_hook_active=True, continuing=True, current_round=1
        )
        with (
            patch("src.main.build_state", return_value=state),
            patch("sys.stdin", io.StringIO("")),
            patch("src.main.save_initial_turn") as mock_save,
            patch("src.main.convert_actions_to_markdown", return_value="md"),
            patch("src.main.invoke_claude", return_value=None),
            pytest.raises(SystemExit),
        ):
            run()
        mock_save.assert_not_called()

    def test_exits_when_no_region(self, tmp_path):
        state = self._make_state(tmp_path)
        with (
            patch("src.main.build_state", return_value=state),
            patch("sys.stdin", io.StringIO("")),
            patch("src.main.save_initial_turn"),
            patch("src.main.convert_actions_to_markdown", return_value="md"),
            patch("src.main.invoke_claude", return_value=None),
            pytest.raises(SystemExit) as exc,
        ):
            run()
        assert exc.value.code == 0

    @pytest.mark.parametrize(
        "termination_output",
        [
            TERMINATION_TOKEN,
            f" {TERMINATION_TOKEN} ",
            f"No more unexplored regions. {TERMINATION_TOKEN}",
            f"{TERMINATION_TOKEN}\n\nAll relevant paths have been covered.",
            (
                "After analyzing the action-history and parallax-region-history,\n"
                "every candidate region has already been surfaced or covered by\n"
                "the main agent's work. Ending the turn.\n\n"
                f"{TERMINATION_TOKEN}"
            ),
        ],
    )
    def test_exits_when_output_contains_termination_token(
        self, tmp_path, termination_output
    ):
        """The advisory agent signals turn termination by including the
        sentinel token anywhere in its output.  Thinking-disabled models
        emit reasoning alongside the token, so the check must use `in`
        rather than equality."""
        state = self._make_state(tmp_path)
        with (
            patch("src.main.build_state", return_value=state),
            patch("sys.stdin", io.StringIO("")),
            patch("src.main.save_initial_turn"),
            patch("src.main.convert_actions_to_markdown", return_value="md"),
            patch("src.main.invoke_claude", return_value=termination_output),
            pytest.raises(SystemExit) as exc,
        ):
            run()
        assert exc.value.code == 0

    @pytest.mark.parametrize(
        "region_output",
        [
            "Consider handling null inputs explicitly",
            "Review the edge case where the result is null",
            "null",
            "`null`",
            "Examine what happens when the function returns None or null",
        ],
    )
    def test_injects_region_when_output_lacks_termination_token(
        self, tmp_path, region_output
    ):
        """Output containing the word 'null' but NOT the termination token
        must be treated as a region to surface.  This verifies the new
        check is strictly stricter than the old equality-based check and
        does not false-positive on region descriptions that mention null."""
        state = self._make_state(tmp_path)
        with (
            patch("src.main.build_state", return_value=state),
            patch("sys.stdin", io.StringIO("")),
            patch("src.main.save_initial_turn"),
            patch("src.main.convert_actions_to_markdown", return_value="md"),
            patch("src.main.invoke_claude", return_value=region_output),
            patch("src.main.finish_round") as mock_finish,
            patch("sys.stderr") as mock_stderr,
            pytest.raises(SystemExit) as exc,
        ):
            run()
        assert exc.value.code == 2
        mock_finish.assert_called_once_with(state, region_output)
        mock_stderr.write.assert_called_once_with(format_injection(region_output))

    def test_injects_region_and_exits_2(self, tmp_path):
        state = self._make_state(tmp_path)
        with (
            patch("src.main.build_state", return_value=state),
            patch("sys.stdin", io.StringIO("")),
            patch("src.main.save_initial_turn"),
            patch("src.main.convert_actions_to_markdown", return_value="md"),
            patch("src.main.invoke_claude", return_value="Add error handling"),
            patch("src.main.finish_round") as mock_finish,
            patch("sys.stderr") as mock_stderr,
            pytest.raises(SystemExit) as exc,
        ):
            run()
        assert exc.value.code == 2
        mock_finish.assert_called_once_with(state, "Add error handling")
        mock_stderr.write.assert_called_once_with(
            format_injection("Add error handling")
        )

    def test_injects_region_with_mission_on_compaction(self, tmp_path):
        state = self._make_state(tmp_path, compacted=True)
        with (
            patch("src.main.build_state", return_value=state),
            patch("sys.stdin", io.StringIO("")),
            patch("src.main.save_initial_turn"),
            patch("src.main.convert_actions_to_markdown", return_value="md"),
            patch("src.main.invoke_claude", return_value="Add error handling"),
            patch("src.main.finish_round") as mock_finish,
            patch("sys.stderr") as mock_stderr,
            pytest.raises(SystemExit) as exc,
        ):
            run()
        assert exc.value.code == 2
        mock_finish.assert_called_once_with(state, "Add error handling")
        mock_stderr.write.assert_called_once_with(
            format_injection("Add error handling", mission="fix bug")
        )

    @pytest.mark.parametrize(
        "user_input, expected_mission",
        [
            (f"implement auth {TRIGGER_KEYWORD}", "implement auth"),
            (f"build feature {TRIGGER_KEYWORD}", "build feature"),
            (f"# Task\nline2\n{TRIGGER_KEYWORD}", "# Task\nline2"),
            (f"  spaced  {TRIGGER_KEYWORD}  ", "spaced"),
            # Mid-prompt occurrences are preserved (only the trailing keyword is stripped)
            (
                f"see code: x = {TRIGGER_KEYWORD}; do {TRIGGER_KEYWORD}",
                f"see code: x = {TRIGGER_KEYWORD}; do",
            ),
        ],
    )
    def test_strips_trigger_keyword_from_mission(
        self, tmp_path, user_input, expected_mission
    ):
        state = self._make_state(tmp_path, user_input=user_input)
        with (
            patch("src.main.build_state", return_value=state),
            patch("sys.stdin", io.StringIO("")),
            patch("src.main.save_initial_turn"),
            patch("src.main.convert_actions_to_markdown", return_value="md"),
            patch(
                "src.main.build_analysis_prompt", return_value="prompt"
            ) as mock_prompt,
            patch("src.main.invoke_claude", return_value=None),
            pytest.raises(SystemExit),
        ):
            run()
        mock_prompt.assert_called_once_with(expected_mission, "md", [])

    def test_exits_when_not_activated(self, tmp_path):
        state = self._make_state(tmp_path, activated=False)
        with (
            patch("src.main.build_state", return_value=state),
            patch("sys.stdin", io.StringIO("")),
            pytest.raises(SystemExit) as exc,
        ):
            run()
        assert exc.value.code == 0

    @pytest.mark.parametrize(
        "user_input",
        ["/parallax-log"],
    )
    def test_exits_on_self_command(self, tmp_path, user_input):
        state = self._make_state(tmp_path, user_input=user_input)
        with (
            patch("src.main.build_state", return_value=state),
            patch("sys.stdin", io.StringIO("")),
            pytest.raises(SystemExit) as exc,
        ):
            run()
        assert exc.value.code == 0

    def test_cleans_compaction_marker(self, tmp_path):
        marker = tmp_path / "s1_compacted"
        marker.touch()
        state = self._make_state(tmp_path, compacted=True, continuing=True)
        with (
            patch("src.main.build_state", return_value=state),
            patch("sys.stdin", io.StringIO("")),
            patch("src.main.convert_actions_to_markdown", return_value="md"),
            patch("src.main.invoke_claude", return_value=None),
            pytest.raises(SystemExit),
        ):
            run()
        assert not marker.exists()


# ── mark_compaction ──


class TestMarkCompaction:
    def test_creates_marker_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        stdin_data = json.dumps(
            {
                "session_id": "s1",
                "trigger": "auto",
                "compact_summary": "...",
            }
        )
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
        mark_compaction()
        assert (tmp_path / "s1_compacted").exists()
