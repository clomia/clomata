"""Tests for main module — subprocess invocation, markdown conversion, logging, orchestration, and prompt capture."""

import io
import json
import subprocess
from unittest.mock import patch

import pytest

from src.main import (
    capture_user_prompt,
    convert_actions_to_markdown,
    invoke_claude,
    run,
    write_log,
)
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
            assert "Follow the instructions in the input." in cmd

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

    def test_disallows_tools_when_allowed(self):
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr=""
        )
        with patch("src.main.subprocess.run", return_value=mock_result) as mock_run:
            invoke_claude("test", allow_tools=True)
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

    def test_returns_none_on_empty_stdout(self):
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="   \n", stderr=""
        )
        with patch("src.main.subprocess.run", return_value=mock_result):
            assert invoke_claude("test") is None


# ── convert_actions_to_markdown ──


class TestConvertActionsToMarkdown:
    def test_passes_raw_json_to_claude(self):
        actions = [{"role": "assistant", "content": "done"}]
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="# Actions\n\nThe agent responded.", stderr=""
        )
        with patch("src.main.subprocess.run", return_value=mock_result) as mock_run:
            result = convert_actions_to_markdown(actions, "claude-opus-4-6")
            assert result == "# Actions\n\nThe agent responded."
            stdin_prompt = mock_run.call_args[1]["input"]
            assert json.dumps(actions, ensure_ascii=False, indent=2) in stdin_prompt

    def test_falls_back_to_raw_json_on_failure(self):
        actions = [{"role": "assistant", "content": "hello"}]
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error"
        )
        with patch("src.main.subprocess.run", return_value=mock_result):
            result = convert_actions_to_markdown(actions, None)
            assert result == json.dumps(actions, ensure_ascii=False, indent=2)


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


# ── write_log ──


class TestWriteLog:
    def test_creates_header_and_sections(self, tmp_path):
        log = tmp_path / "test.log"
        write_log(log, 1, new_turn=True, prompt="the prompt", direction="go left")
        content = log.read_text()
        assert "# Round 1 — " in content
        assert "## prompt\n\nthe prompt\n\n" in content
        assert "## direction\n\ngo left\n\n" in content

    def test_new_turn_overwrites(self, tmp_path):
        log = tmp_path / "test.log"
        log.write_text("old content\n")
        write_log(log, 1, new_turn=True, note="fresh")
        content = log.read_text()
        assert "old content" not in content
        assert "# Round 1" in content

    def test_appends_without_new_turn(self, tmp_path):
        log = tmp_path / "test.log"
        write_log(log, 1, new_turn=True, note="round 1")
        write_log(log, 2, new_turn=False, note="round 2")
        content = log.read_text()
        assert "# Round 1" in content
        assert "# Round 2" in content


# ── run ──


class TestRun:
    def _make_state(self, tmp_path, *, user_input="fix bug", **overrides):
        defaults = dict(
            is_inside_recursion=False,
            is_disabled=False,
            stop_hook_active=False,
            continuing=False,
            current_round=0,
            direction_history=[],
        )
        defaults.update(overrides)
        return State(
            hook=HookInput(
                stop_hook_active=defaults["stop_hook_active"],
                last_assistant_message="done",
                session_id="s1",
                transcript_path=str(tmp_path / "t.jsonl"),
            ),
            env=PluginEnvironment(
                data_dir=tmp_path,
                is_inside_recursion=defaults["is_inside_recursion"],
                is_disabled=defaults["is_disabled"],
            ),
            continuing=defaults["continuing"],
            current_round=defaults["current_round"],
            direction_history=defaults["direction_history"],
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

    def test_exits_on_disabled(self, tmp_path):
        state = self._make_state(tmp_path, is_disabled=True)
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

    def test_exits_when_no_direction(self, tmp_path):
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

    def test_exits_when_direction_is_null_string(self, tmp_path):
        state = self._make_state(tmp_path)
        with (
            patch("src.main.build_state", return_value=state),
            patch("sys.stdin", io.StringIO("")),
            patch("src.main.save_initial_turn"),
            patch("src.main.convert_actions_to_markdown", return_value="md"),
            patch("src.main.invoke_claude", return_value="null"),
            pytest.raises(SystemExit) as exc,
        ):
            run()
        assert exc.value.code == 0

    def test_injects_direction_and_exits_2(self, tmp_path):
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
        mock_stderr.write.assert_called_once_with("Add error handling")
        mock_finish.assert_called_once_with(state, "Add error handling")

    @pytest.mark.parametrize(
        "user_input",
        ["/parallax", "/parallax on", "/parallax off", "/parallax log"],
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
