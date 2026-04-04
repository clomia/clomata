"""Tests for main module — subprocess calls, direction parsing, and execution flow."""

import json
import subprocess
from unittest.mock import patch

from src.main import convert_actions_to_markdown, invoke_claude


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

    def test_returns_none_on_failure(self):
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error"
        )
        with patch("src.main.subprocess.run", return_value=mock_result):
            assert invoke_claude("test") is None

    def test_returns_none_on_timeout(self):
        with patch(
            "src.main.subprocess.run",
            side_effect=subprocess.TimeoutExpired("cmd", 120),
        ):
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
            prompt_arg = mock_run.call_args[0][0][2]
            assert json.dumps(actions, ensure_ascii=False, indent=2) in prompt_arg

    def test_falls_back_to_raw_json_on_failure(self):
        actions = [{"role": "assistant", "content": "hello"}]
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error"
        )
        with patch("src.main.subprocess.run", return_value=mock_result):
            result = convert_actions_to_markdown(actions, None)
            assert result == json.dumps(actions, ensure_ascii=False, indent=2)
