"""Captures all external inputs for a parallax run into a single State object."""

import json
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict

ROUND_LIMIT = 15


# ── Input models ──


class HookInput(BaseModel):
    """Stop hook event data from stdin."""

    model_config = ConfigDict(extra="ignore")

    stop_hook_active: bool
    last_assistant_message: str
    session_id: str
    transcript_path: str


class PluginEnvironment(BaseModel):
    """Plugin runtime environment from env vars and filesystem."""

    src_dir: Path
    data_dir: Path
    is_inside_recursion: bool
    is_disabled: bool


class Turn(BaseModel):
    """Most recent turn extracted from the session transcript."""

    user_input: str
    agent_actions: list[dict]
    agent_model: str | None


# ── Composite state ──


class State(BaseModel):
    """All external inputs for a parallax run, assembled into one object."""

    hook: HookInput
    env: PluginEnvironment
    current_round: int = 0
    turn: Turn


# ── Turn parsing ──


def extract_user_input(msg: dict) -> str | None:
    """Extract text from a user prompt. Returns None for non-prompt messages."""
    if msg.get("role") != "user":
        return None
    content = msg.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        if content and all(
            isinstance(item, dict) and item.get("type") == "tool_result"
            for item in content
        ):
            return None
        parts = [
            item["text"]
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        return "\n".join(parts)
    return None


def parse_turn(transcript_path: str) -> Turn:
    """Parse transcript JSONL and extract the most recent turn.

    Finds the last user message with string content (excluding tool results)
    and splits the transcript at that point: user_input is the prompt text,
    agent_actions is everything after it.

    When stop_hook_active is True, the "last user(str)" may be hook feedback
    rather than the real prompt. The caller (build_state) corrects user_input
    from the persisted state file in that case.
    """
    messages: list[dict] = []
    for line in Path(transcript_path).read_text().splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg := obj.get("message"):
            messages.append(msg)

    agent_model = None
    last_prompt_idx = 0
    user_input = ""

    for i, msg in enumerate(messages):
        if msg.get("role") == "assistant" and msg.get("model"):
            agent_model = msg["model"]
        if (text := extract_user_input(msg)) is not None:
            last_prompt_idx = i
            user_input = text

    return Turn(
        user_input=user_input,
        agent_actions=messages[last_prompt_idx + 1 :],
        agent_model=agent_model,
    )


# ── Turn state persistence ──


def load_turn_state(state_file: Path) -> dict:
    """Load persisted turn state from JSON file. Returns empty dict on any failure."""
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_turn_state(state_file: Path, data: dict) -> None:
    """Save turn state to JSON file."""
    state_file.write_text(json.dumps(data))


# ── State assembly ──


def build_state(stdin_raw: str) -> State:
    """Collect all external inputs and assemble a State.

    Uses stop_hook_active (documented in Hooks Reference) to decide whether
    to parse user_input from the transcript or load it from the state file:

    - stop_hook_active=False (round 1): No hook feedback exists in the
      transcript yet, so the last user(str) message is reliably the real
      prompt. Parsed user_input is saved to the state file.

    - stop_hook_active=True (round 2+): Hook feedback has been injected as
      a user(str) message, which would be misidentified as the prompt.
      Instead, user_input is loaded from the state file (saved in round 1).
      agent_actions naturally contains only the work done since the last
      feedback, which is the correct scope for each analysis round.
    """
    hook = HookInput.model_validate_json(stdin_raw)

    data_dir = Path(os.environ["CLAUDE_PLUGIN_DATA"])
    env = PluginEnvironment(
        src_dir=Path(os.environ["CLAUDE_PLUGIN_ROOT"]),
        data_dir=data_dir,
        is_inside_recursion=os.environ.get("PARALLAX_INSIDE_RECURSION") == "1",
        is_disabled=(data_dir / "disabled").exists(),
    )

    state_file = env.data_dir / f"{hook.session_id}.json"
    turn_state = load_turn_state(state_file)
    turn = parse_turn(hook.transcript_path)

    if hook.stop_hook_active:
        current_round = turn_state.get("round", 0)
        saved_user_input = turn_state.get("user_input")
        if saved_user_input is not None:
            turn = Turn(
                user_input=saved_user_input,
                agent_actions=turn.agent_actions,
                agent_model=turn.agent_model,
            )
    else:
        current_round = 0
        save_turn_state(state_file, {"round": 0, "user_input": turn.user_input})

    return State(hook=hook, env=env, current_round=current_round, turn=turn)
