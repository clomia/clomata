"""Tests for the state module."""

import json
from pathlib import Path

from src.state import (
    HookInput,
    PluginEnvironment,
    State,
    Turn,
    build_state,
    extract_user_input,
    finish_round,
    load_last_user_prompt,
    load_turn_state,
    parse_turn,
    save_initial_turn,
    save_turn_state,
)


# ── Helpers ──


def write_jsonl(path: Path, messages: list[dict]):
    lines = [json.dumps({"message": msg}) for msg in messages]
    path.write_text("\n".join(lines))


def make_stdin(
    *,
    stop_hook_active=False,
    session_id="sess1",
    transcript_path="",
    **extra,
):
    return json.dumps(
        {
            "stop_hook_active": stop_hook_active,
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
            session_id="abc123",
            transcript_path="/tmp/t.jsonl",
        )
        hook = HookInput.model_validate_json(raw)
        assert hook.stop_hook_active is True
        assert hook.session_id == "abc123"

    def test_ignores_extra_fields(self):
        raw = make_stdin(cwd="/some/path", permission_mode="default")
        hook = HookInput.model_validate_json(raw)
        assert not hasattr(hook, "cwd")


# ── PluginEnvironment ──


class TestPluginEnvironment:
    def test_construction(self):
        env = PluginEnvironment(
            data_dir=Path("/plugin/data"),
            is_inside_recursion=False,
        )
        assert env.data_dir == Path("/plugin/data")
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


# ── load_last_user_prompt ──


class TestLoadLastUserPrompt:
    def test_returns_content_when_file_exists(self, tmp_path):
        f = tmp_path / "sess1_last_user_prompt.txt"
        f.write_text("/commit push")
        assert load_last_user_prompt(f) == "/commit push"

    def test_returns_none_when_file_missing(self, tmp_path):
        assert load_last_user_prompt(tmp_path / "nonexistent.txt") is None


# ── finish_round ──


class TestFinishRound:
    def test_increments_round_and_appends_region(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        save_turn_state(
            data_dir / "sess1.json",
            {"round": 0, "user_input": "fix bug", "regions": []},
        )
        state = State(
            hook=HookInput(
                stop_hook_active=False,
                session_id="sess1",
                transcript_path="",
            ),
            env=PluginEnvironment(
                data_dir=data_dir,
                is_inside_recursion=False,
            ),
            current_round=0,
            region_history=[],
            turn=Turn(user_input="fix bug", agent_actions=[], agent_model=None),
        )

        finish_round(state, "Add error handling")

        saved = load_turn_state(data_dir / "sess1.json")
        assert saved["round"] == 1
        assert saved["regions"] == ["Add error handling"]
        assert saved["user_input"] == "fix bug"

    def test_accumulates_regions_across_rounds(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        state = State(
            hook=HookInput(
                stop_hook_active=True,
                session_id="sess1",
                transcript_path="",
            ),
            env=PluginEnvironment(
                data_dir=data_dir,
                is_inside_recursion=False,
            ),
            current_round=2,
            region_history=["Add tests", "Handle edge cases"],
            turn=Turn(
                user_input="implement feature", agent_actions=[], agent_model=None
            ),
        )

        finish_round(state, "Add logging")

        saved = load_turn_state(data_dir / "sess1.json")
        assert saved["round"] == 3
        assert saved["regions"] == ["Add tests", "Handle edge cases", "Add logging"]


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

    def test_empty_content_list(self):
        msg = {"role": "user", "content": []}
        assert extract_user_input(msg) == ""


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

    def test_parallel_tool_calls(self, tmp_path):
        """Multiple tool_use in one assistant message, multiple tool_results in one user message."""
        t = tmp_path / "t.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "search and read"},
                {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "id": "t1", "name": "Glob"},
                        {"type": "tool_use", "id": "t2", "name": "Grep"},
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "t1", "content": "a.py"},
                        {
                            "type": "tool_result",
                            "tool_use_id": "t2",
                            "content": "match",
                        },
                    ],
                },
                {"role": "assistant", "content": "Found it."},
            ],
        )
        turn = parse_turn(str(t))
        assert turn.user_input == "search and read"
        assert len(turn.agent_actions) == 3

    def test_permission_denied(self, tmp_path):
        """Permission denied is a tool_result with is_error=True."""
        t = tmp_path / "t.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "read /etc/hosts"},
                {
                    "role": "assistant",
                    "content": [{"type": "tool_use", "id": "t1", "name": "Read"}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "t1",
                            "content": "Permission denied",
                            "is_error": True,
                        }
                    ],
                },
                {"role": "assistant", "content": "Access denied."},
            ],
        )
        turn = parse_turn(str(t))
        assert turn.user_input == "read /etc/hosts"
        assert len(turn.agent_actions) == 3

    def test_subagent_call(self, tmp_path):
        """Agent tool call appears as tool_use(Agent) → tool_result."""
        t = tmp_path / "t.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "find all TODO comments"},
                {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "id": "t1", "name": "Agent", "input": {}},
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "t1",
                            "content": "Found 5 TODOs",
                        }
                    ],
                },
                {"role": "assistant", "content": "Here are the results."},
            ],
        )
        turn = parse_turn(str(t))
        assert turn.user_input == "find all TODO comments"
        assert len(turn.agent_actions) == 3

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
    def test_uses_captured_prompt_over_transcript(self, tmp_path, monkeypatch):
        """Primary path: UserPromptSubmit hook saved the raw prompt to a file.
        build_state should use it instead of the transcript-parsed user_input."""
        t = tmp_path / "transcript.jsonl"
        write_jsonl(
            t,
            [
                # Transcript has the skill-expanded version
                {"role": "user", "content": "Full commit guide... 2500 chars..."},
                {
                    "role": "assistant",
                    "content": "Committed.",
                    "model": "claude-opus-4-6",
                },
            ],
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        # Captured prompt file written by capture_user_prompt hook
        (data_dir / "s1_last_user_prompt.txt").write_text("/commit push")

        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        state = build_state(
            make_stdin(
                stop_hook_active=False,
                session_id="s1",
                transcript_path=str(t),
            )
        )

        assert state.turn.user_input == "/commit push"
        assert state.turn.agent_actions == [
            {"role": "assistant", "content": "Committed.", "model": "claude-opus-4-6"}
        ]

    def test_falls_back_to_transcript_without_captured_prompt(
        self, tmp_path, monkeypatch
    ):
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
        assert state.region_history == []

    def test_save_initial_turn_persists_state(self, tmp_path, monkeypatch):
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

        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        state = build_state(
            make_stdin(
                stop_hook_active=False,
                session_id="s1",
                transcript_path=str(t),
            )
        )
        save_initial_turn(state)

        saved = json.loads((data_dir / "s1.json").read_text())
        assert saved["user_input"] == "original prompt"
        assert saved["round"] == 0
        assert saved["regions"] == []

    def test_captured_prompt_persists_through_save_initial_turn(
        self, tmp_path, monkeypatch
    ):
        """Captured prompt (not transcript) should be what gets saved to the state file."""
        t = tmp_path / "transcript.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "Expanded skill prompt... very long"},
                {"role": "assistant", "content": "Done."},
            ],
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "s1_last_user_prompt.txt").write_text("@file.md do the thing")

        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        state = build_state(
            make_stdin(
                stop_hook_active=False,
                session_id="s1",
                transcript_path=str(t),
            )
        )
        save_initial_turn(state)

        saved = json.loads((data_dir / "s1.json").read_text())
        assert saved["user_input"] == "@file.md do the thing"

    def test_fallback_uses_last_user_message_from_transcript(
        self, tmp_path, monkeypatch
    ):
        """Fallback path (no captured prompt file): parse_turn picks the last
        user(str) message in the transcript as user_input."""
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

    def test_compaction_before_first_stop_hook(self, tmp_path, monkeypatch):
        """If compaction happens within a turn before any Stop hook fires,
        the compaction summary becomes user_input (degraded but no crash).
        The original prompt text is lost from the transcript but included
        in the summary."""
        t = tmp_path / "transcript.jsonl"
        write_jsonl(
            t,
            [
                {
                    "role": "user",
                    "content": "This session is being continued from a previous conversation... the last task was: implement auth",
                },
                {
                    "role": "assistant",
                    "content": "Continuing.",
                    "model": "claude-opus-4-6",
                },
            ],
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        state = build_state(
            make_stdin(
                stop_hook_active=False,
                session_id="s1",
                transcript_path=str(t),
            )
        )

        # Compaction summary is the only user(str) → becomes user_input
        assert "This session is being continued" in state.turn.user_input
        assert len(state.turn.agent_actions) == 1
        # save_initial_turn persists for round 2+ recovery
        save_initial_turn(state)
        saved = json.loads((data_dir / "s1.json").read_text())
        assert "This session is being continued" in saved["user_input"]

    def test_new_turn_overwrites_previous_state_file(self, tmp_path, monkeypatch):
        """When a new turn starts (stop_hook_active=False, no compaction
        marker), save_initial_turn overwrites the stale state file."""
        t = tmp_path / "transcript.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "new task"},
                {"role": "assistant", "content": "ok"},
            ],
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        # Stale state file from previous turn — no compaction marker
        save_turn_state(data_dir / "s1.json", {"round": 5, "user_input": "old task"})

        prompt_path = data_dir / "s1_last_user_prompt.txt"
        prompt_path.write_text("new task")

        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        state = build_state(
            make_stdin(
                stop_hook_active=False,
                session_id="s1",
                transcript_path=str(t),
            )
        )

        assert state.compacted is False
        assert state.continuing is False
        assert state.current_round == 0
        assert state.turn.user_input == "new task"
        save_initial_turn(state)
        saved = json.loads((data_dir / "s1.json").read_text())
        assert saved["user_input"] == "new task"
        assert saved["round"] == 0

    def test_auto_compaction_preserves_round(self, tmp_path, monkeypatch):
        """PostCompact marker signals compaction. build_state must detect it
        and keep the existing round instead of resetting to 0."""
        t = tmp_path / "transcript.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "build feature"},
                {"role": "assistant", "content": "done"},
            ],
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        save_turn_state(
            data_dir / "s1.json",
            {
                "round": 3,
                "user_input": "build feature",
                "regions": ["d1", "d2", "d3"],
            },
        )

        # PostCompact marker (replaces mtime comparison)
        (data_dir / "s1_compacted").touch()

        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        state = build_state(
            make_stdin(
                stop_hook_active=False,
                session_id="s1",
                transcript_path=str(t),
            )
        )

        assert state.continuing is True
        assert state.compacted is True
        assert state.current_round == 3
        assert len(state.region_history) == 3
        assert state.turn.user_input == "build feature"

    def test_no_compaction_without_marker(self, tmp_path, monkeypatch):
        """Without PostCompact marker, compacted is False even when
        stop_hook_active is False and state file exists with round > 0."""
        t = tmp_path / "transcript.jsonl"
        write_jsonl(
            t,
            [
                {"role": "user", "content": "new task"},
                {"role": "assistant", "content": "done"},
            ],
        )
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        save_turn_state(
            data_dir / "s1.json",
            {"round": 3, "user_input": "old task", "regions": ["a", "b", "c"]},
        )
        prompt_path = data_dir / "s1_last_user_prompt.txt"
        prompt_path.write_text("new task")

        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        state = build_state(
            make_stdin(
                stop_hook_active=False,
                session_id="s1",
                transcript_path=str(t),
            )
        )

        assert state.compacted is False
        assert state.continuing is False
        assert state.current_round == 0
        assert state.turn.user_input == "new task"

    def test_save_initial_turn_cleans_stale_marker(self, tmp_path, monkeypatch):
        """save_initial_turn removes any leftover compaction marker."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        marker = data_dir / "s1_compacted"
        marker.touch()

        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        t = tmp_path / "transcript.jsonl"
        write_jsonl(t, [{"role": "user", "content": "task"}])

        state = build_state(
            make_stdin(
                stop_hook_active=False,
                session_id="s1",
                transcript_path=str(t),
            )
        )
        # Marker is detected → compacted=True, continuing=True
        assert state.compacted is True

        # But if this were a new turn, save_initial_turn cleans the marker
        # Simulate: force new_turn by building a non-continuing state
        state.continuing = False
        save_initial_turn(state)
        assert not marker.exists()


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
            {
                "round": 1,
                "user_input": "fix the bug",
                "regions": ["Add error handling"],
            },
        )

        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        state = build_state(
            make_stdin(
                stop_hook_active=True,
                session_id="s1",
                transcript_path=str(t),
            )
        )

        assert state.compacted is False
        assert state.turn.user_input == "fix the bug"
        assert state.current_round == 1
        assert state.region_history == ["Add error handling"]

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
            {
                "round": 1,
                "user_input": "fix the bug",
                "regions": ["Also add logging"],
            },
        )

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
            {
                "round": 2,
                "user_input": "implement feature",
                "regions": ["Add tests", "Handle edge cases"],
            },
        )

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
        assert state.region_history == ["Add tests", "Handle edge cases"]
        assert len(state.turn.agent_actions) == 1
        assert state.turn.agent_actions[0]["content"] == "Edge cases handled."

    def test_compaction_mid_loop(self, tmp_path, monkeypatch):
        """If compaction rewrites the transcript mid-loop while stop_hook_active
        remains True, the PostCompact marker still signals compaction."""
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
            {
                "round": 1,
                "user_input": "fix the bug",
                "regions": ["Add validation"],
            },
        )

        # PostCompact marker
        (data_dir / "s1_compacted").touch()

        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(data_dir))
        monkeypatch.delenv("PARALLAX_INSIDE_RECURSION", raising=False)

        state = build_state(
            make_stdin(
                stop_hook_active=True,
                session_id="s1",
                transcript_path=str(t),
            )
        )

        assert state.compacted is True
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
        assert state.turn.user_input == "Stop hook feedback:\n[hook]: more"


# ── build_state: environment ──


class TestBuildStateEnvironment:
    def test_recursion_guard(self, tmp_path, monkeypatch):
        t = tmp_path / "transcript.jsonl"
        write_jsonl(t, [{"role": "user", "content": "hi"}])

        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setenv("PARALLAX_INSIDE_RECURSION", "1")

        state = build_state(make_stdin(transcript_path=str(t)))
        assert state.env.is_inside_recursion is True
