"""Tests for State construction."""

import json
from pathlib import Path

from src.state import (
    HookInput,
    PluginEnvironment,
    build_state,
    extract_user_input,
    load_turn_state,
    parse_turn,
    save_turn_state,
)


# ── Helpers ──


def write_jsonl(path: Path, messages: list[dict]):
    lines = [json.dumps({"message": msg}) for msg in messages]
    path.write_text("\n".join(lines))


def make_stdin(
    *,
    stop_hook_active=False,
    last_assistant_message="",
    session_id="sess1",
    transcript_path="",
    **extra,
):
    return json.dumps(
        {
            "stop_hook_active": stop_hook_active,
            "last_assistant_message": last_assistant_message,
            "session_id": session_id,
            "transcript_path": transcript_path,
            **extra,
        }
    )


# ── HookInput ──


class TestHookInput:
    def test_parse_from_json(self):
        raw = make_stdin(
            stop_hook_active=True,
            last_assistant_message="Done",
            session_id="abc123",
            transcript_path="/tmp/t.jsonl",
        )
        hook = HookInput.model_validate_json(raw)
        assert hook.stop_hook_active is True
        assert hook.last_assistant_message == "Done"
        assert hook.session_id == "abc123"

    def test_ignores_extra_fields(self):
        raw = make_stdin(cwd="/some/path", permission_mode="default")
        hook = HookInput.model_validate_json(raw)
        assert not hasattr(hook, "cwd")


# ── PluginEnvironment ──


class TestPluginEnvironment:
    def test_construction(self):
        env = PluginEnvironment(
            src_dir=Path("/plugin/root"),
            data_dir=Path("/plugin/data"),
            is_inside_recursion=False,
            is_disabled=False,
        )
        assert env.src_dir == Path("/plugin/root")
        assert env.is_inside_recursion is False


# ── Turn state persistence ──


class TestTurnState:
    def test_load_existing(self, tmp_path):
        f = tmp_path / "state.json"
        f.write_text(json.dumps({"round": 3, "user_input": "hello"}))
        data = load_turn_state(f)
        assert data["round"] == 3
        assert data["user_input"] == "hello"

    def test_load_missing_file(self, tmp_path):
        data = load_turn_state(tmp_path / "nonexistent.json")
        assert data == {}

    def test_load_corrupt_file(self, tmp_path):
        f = tmp_path / "state.json"
        f.write_text("{broken json")
        data = load_turn_state(f)
        assert data == {}

    def test_load_empty_file(self, tmp_path):
        f = tmp_path / "state.json"
        f.write_text("")
        data = load_turn_state(f)
        assert data == {}

    def test_save_and_load_roundtrip(self, tmp_path):
        f = tmp_path / "state.json"
        save_turn_state(f, {"round": 2, "user_input": "test prompt"})
        data = load_turn_state(f)
        assert data == {"round": 2, "user_input": "test prompt"}


# ── extract_user_input ──


class TestExtractUserInput:
    def test_string_content(self):
        msg = {"role": "user", "content": "implement this"}
        assert extract_user_input(msg) == "implement this"

    def test_text_blocks(self):
        msg = {
            "role": "user",
            "content": [
                {"type": "text", "text": "first line"},
                {"type": "text", "text": "second line"},
            ],
        }
        assert extract_user_input(msg) == "first line\nsecond line"

    def test_mixed_blocks_extracts_only_text(self):
        msg = {
            "role": "user",
            "content": [
                {"type": "text", "text": "task request"},
                {"type": "image", "source": {"data": "..."}},
            ],
        }
        assert extract_user_input(msg) == "task request"

    def test_returns_none_for_assistant(self):
        assert extract_user_input({"role": "assistant", "content": "hi"}) is None

    def test_returns_none_for_tool_result(self):
        msg = {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}],
        }
        assert extract_user_input(msg) is None


# ── parse_turn ──


class TestParseTurn:
    def test_simple_turn(self, tmp_path):
        t = tmp_path / "t.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "implement this"},
                {"role": "assistant", "content": "done"},
            ],
        )
        turn = parse_turn(str(t))
        assert turn.user_input == "implement this"
        assert len(turn.agent_actions) == 1

    def test_agent_actions_excludes_user_prompt(self, tmp_path):
        t = tmp_path / "t.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "do it"},
                {"role": "assistant", "content": "step 1"},
                {"role": "assistant", "content": "step 2"},
            ],
        )
        turn = parse_turn(str(t))
        assert len(turn.agent_actions) == 2
        assert turn.agent_actions[0]["content"] == "step 1"

    def test_extracts_agent_model(self, tmp_path):
        t = tmp_path / "t.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi", "model": "claude-sonnet-4-6"},
                {"role": "user", "content": "bye"},
                {"role": "assistant", "content": "ok", "model": "claude-opus-4-6"},
            ],
        )
        turn = parse_turn(str(t))
        assert turn.agent_model == "claude-opus-4-6"

    def test_multi_turn_uses_last_prompt(self, tmp_path):
        t = tmp_path / "t.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "task 1"},
                {"role": "assistant", "content": "task 1 done"},
                {"role": "user", "content": "task 2"},
                {"role": "assistant", "content": "task 2 done"},
            ],
        )
        turn = parse_turn(str(t))
        assert turn.user_input == "task 2"
        assert len(turn.agent_actions) == 1

    def test_tool_result_does_not_split_turn(self, tmp_path):
        t = tmp_path / "t.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "implement feature"},
                {
                    "role": "assistant",
                    "content": [{"type": "tool_use", "id": "t1", "name": "Edit"}],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}
                    ],
                },
                {"role": "assistant", "content": "done"},
            ],
        )
        turn = parse_turn(str(t))
        assert turn.user_input == "implement feature"
        assert len(turn.agent_actions) == 3

    def test_realistic_session(self, tmp_path):
        """Full Claude Code session: multi-turn, mixed content, consecutive tool calls."""
        t = tmp_path / "t.jsonl"
        prev_turn = [
            {"role": "user", "content": "set up project"},
            {"role": "assistant", "content": "done", "model": "claude-opus-4-6"},
        ]
        assistant_read = {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Reading file"},
                {"type": "tool_use", "id": "t1", "name": "Read", "input": {}},
            ],
            "model": "claude-opus-4-6",
        }
        tool_result_read = {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": "file data"}
            ],
        }
        assistant_edit = {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "t2", "name": "Edit", "input": {}},
            ],
            "model": "claude-opus-4-6",
        }
        tool_result_edit = {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "t2", "content": "applied"}
            ],
        }
        assistant_final = {
            "role": "assistant",
            "content": "All done.",
            "model": "claude-opus-4-6",
        }
        current_actions = [
            assistant_read,
            tool_result_read,
            assistant_edit,
            tool_result_edit,
            assistant_final,
        ]
        write_jsonl(
            t,
            [*prev_turn, {"role": "user", "content": "fix the bug"}, *current_actions],
        )
        turn = parse_turn(str(t))
        assert turn.user_input == "fix the bug"
        assert turn.agent_model == "claude-opus-4-6"
        assert len(turn.agent_actions) == len(current_actions)
        for actual, expected in zip(turn.agent_actions, current_actions):
            assert actual == expected

    def test_truncated_last_line_skipped(self, tmp_path):
        """Partial JSONL line from concurrent write is safely skipped."""
        t = tmp_path / "t.jsonl"
        full = json.dumps({"message": {"role": "assistant", "content": "final"}})
        t.write_text(
            json.dumps({"message": {"role": "user", "content": "prompt"}})
            + "\n"
            + full[:20]
        )
        turn = parse_turn(str(t))
        assert turn.user_input == "prompt"
        assert turn.agent_actions == []


# ── build_state: round 1 (stop_hook_active=False) ──


class TestBuildStateRound1:
    def test_parses_user_input_from_transcript(self, tmp_path, monkeypatch):
        t = tmp_path / "transcript.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "fix the login bug"},
                {"role": "assistant", "content": "Fixed.", "model": "claude-opus-4-6"},
            ],
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        state = build_state(
            make_stdin(
                stop_hook_active=False,
                session_id="s1",
                transcript_path=str(t),
            )
        )

        assert state.turn.user_input == "fix the login bug"
        assert state.current_round == 0

    def test_saves_user_input_to_state_file(self, tmp_path, monkeypatch):
        t = tmp_path / "transcript.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "original prompt"},
                {"role": "assistant", "content": "ok"},
            ],
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        build_state(
            make_stdin(
                stop_hook_active=False,
                session_id="s1",
                transcript_path=str(t),
            )
        )

        saved = json.loads((data_dir / "s1.json").read_text())
        assert saved["user_input"] == "original prompt"
        assert saved["round"] == 0

    def test_system_injections_before_prompt_do_not_interfere(
        self, tmp_path, monkeypatch
    ):
        """Slash commands, doc injection, compaction summary all come before the
        real prompt. The last user(str) is always the real prompt in round 1."""
        t = tmp_path / "transcript.jsonl"
        write_jsonl(
            t,
            [
                # Compaction summary
                {
                    "role": "user",
                    "content": "This session is being continued from a previous conversation...",
                },
                # Slash command
                {"role": "user", "content": "<command-name>/effort</command-name>..."},
                # Command stdout
                {
                    "role": "user",
                    "content": "<local-command-stdout>Set effort level to max</local-command-stdout>",
                },
                # Real prompt (LAST user(str))
                {"role": "user", "content": "now fix the tests"},
                {"role": "assistant", "content": "On it.", "model": "claude-opus-4-6"},
            ],
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        state = build_state(
            make_stdin(
                stop_hook_active=False,
                session_id="s1",
                transcript_path=str(t),
            )
        )

        assert state.turn.user_input == "now fix the tests"
        assert len(state.turn.agent_actions) == 1


# ── build_state: round 2+ (stop_hook_active=True) ──


class TestBuildStateRound2:
    def test_loads_user_input_from_state_file(self, tmp_path, monkeypatch):
        """Hook feedback in transcript does NOT override the saved user_input."""
        t = tmp_path / "transcript.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "fix the bug"},
                {"role": "assistant", "content": "Fixed it."},
                # Stop hook feedback injected by parallax
                {
                    "role": "user",
                    "content": "Stop hook feedback:\n[hook.sh]: Add error handling.",
                },
                {"role": "assistant", "content": "Added try-except."},
            ],
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        save_turn_state(
            data_dir / "s1.json",
            {"round": 1, "user_input": "fix the bug"},
        )
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        state = build_state(
            make_stdin(
                stop_hook_active=True,
                session_id="s1",
                transcript_path=str(t),
            )
        )

        assert state.turn.user_input == "fix the bug"
        assert state.current_round == 1

    def test_agent_actions_contains_work_since_last_feedback(
        self, tmp_path, monkeypatch
    ):
        """agent_actions should contain only the work done after the last
        hook feedback — the correct scope for each analysis round."""
        t = tmp_path / "transcript.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "fix the bug"},
                {"role": "assistant", "content": "Fixed it."},
                # Hook feedback (last user(str) in transcript)
                {
                    "role": "user",
                    "content": "Stop hook feedback:\n[hook.sh]: Also add logging.",
                },
                # New work after feedback
                {
                    "role": "assistant",
                    "content": [{"type": "tool_use", "id": "t1", "name": "Edit"}],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}
                    ],
                },
                {"role": "assistant", "content": "Added logging."},
            ],
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        save_turn_state(
            data_dir / "s1.json",
            {"round": 1, "user_input": "fix the bug"},
        )
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        state = build_state(
            make_stdin(
                stop_hook_active=True,
                session_id="s1",
                transcript_path=str(t),
            )
        )

        # 3 actions after hook feedback: tool_use, tool_result, final text
        assert len(state.turn.agent_actions) == 3
        assert state.turn.agent_actions[2]["content"] == "Added logging."

    def test_multiple_hook_rounds(self, tmp_path, monkeypatch):
        """Three rounds of parallax feedback: user_input stays original,
        agent_actions scopes to the latest round's work."""
        t = tmp_path / "transcript.jsonl"
        write_jsonl(
            t,
            [
                # Round 1
                {"role": "user", "content": "implement feature"},
                {"role": "assistant", "content": "Done v1."},
                # Round 1 feedback
                {"role": "user", "content": "Stop hook feedback:\n[hook]: Add tests."},
                # Round 2
                {"role": "assistant", "content": "Tests added."},
                # Round 2 feedback
                {
                    "role": "user",
                    "content": "Stop hook feedback:\n[hook]: Handle edge cases.",
                },
                # Round 3 (current)
                {"role": "assistant", "content": "Edge cases handled."},
            ],
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        save_turn_state(
            data_dir / "s1.json",
            {"round": 2, "user_input": "implement feature"},
        )
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        state = build_state(
            make_stdin(
                stop_hook_active=True,
                session_id="s1",
                transcript_path=str(t),
            )
        )

        assert state.turn.user_input == "implement feature"
        assert state.current_round == 2
        assert len(state.turn.agent_actions) == 1
        assert state.turn.agent_actions[0]["content"] == "Edge cases handled."

    def test_compaction_mid_loop(self, tmp_path, monkeypatch):
        """If compaction rewrites the transcript mid-loop, user_input comes from
        the state file and agent_actions degrades to post-compaction work."""
        t = tmp_path / "transcript.jsonl"
        write_jsonl(
            t,
            [
                # After compaction: summary replaces everything before
                {
                    "role": "user",
                    "content": "This session is being continued from a previous conversation...",
                },
                {"role": "assistant", "content": "Continuing work."},
            ],
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        save_turn_state(
            data_dir / "s1.json",
            {"round": 1, "user_input": "fix the bug"},
        )
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        state = build_state(
            make_stdin(
                stop_hook_active=True,
                session_id="s1",
                transcript_path=str(t),
            )
        )

        assert state.turn.user_input == "fix the bug"
        assert len(state.turn.agent_actions) == 1

    def test_fallback_when_state_file_missing_user_input(self, tmp_path, monkeypatch):
        """Old state file format without user_input: fall back to transcript parsing."""
        t = tmp_path / "transcript.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "fix the bug"},
                {"role": "assistant", "content": "Fixed."},
                {
                    "role": "user",
                    "content": "Stop hook feedback:\n[hook]: Add tests.",
                },
                {"role": "assistant", "content": "Tests added."},
            ],
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        # Old format: no user_input key
        save_turn_state(data_dir / "s1.json", {"round": 1})

        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        state = build_state(
            make_stdin(
                stop_hook_active=True,
                session_id="s1",
                transcript_path=str(t),
            )
        )

        # Falls back to transcript parsing — gets hook feedback as user_input
        # (degraded but no crash)
        assert state.turn.user_input == "Stop hook feedback:\n[hook]: Add tests."
        assert state.current_round == 1

    def test_corrupt_state_file_does_not_crash(self, tmp_path, monkeypatch):
        """Corrupt state file: falls back to defaults."""
        t = tmp_path / "transcript.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "prompt"},
                {"role": "assistant", "content": "ok"},
                {"role": "user", "content": "Stop hook feedback:\n[hook]: more"},
                {"role": "assistant", "content": "done"},
            ],
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "s1.json").write_text("{corrupt")

        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        state = build_state(
            make_stdin(
                stop_hook_active=True,
                session_id="s1",
                transcript_path=str(t),
            )
        )

        # Corrupt file → empty dict → round=0, no saved user_input → transcript fallback
        assert state.current_round == 0


# ── build_state: environment ──


class TestBuildStateEnvironment:
    def test_recursion_guard(self, tmp_path, monkeypatch):
        t = tmp_path / "transcript.jsonl"
        write_jsonl(t, [{"role": "user", "content": "hi"}])
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setenv("PARALLAX_INSIDE_RECURSION", "1")

        state = build_state(make_stdin(transcript_path=str(t)))
        assert state.env.is_inside_recursion is True

    def test_disabled_flag(self, tmp_path, monkeypatch):
        t = tmp_path / "transcript.jsonl"
        write_jsonl(t, [{"role": "user", "content": "hi"}])
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "disabled").touch()
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        state = build_state(make_stdin(transcript_path=str(t)))
        assert state.env.is_disabled is True
