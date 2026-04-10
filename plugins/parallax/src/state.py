"""State — all external inputs for a parallax run, assembled into one object.

Parses the session transcript, loads persisted turn state, and provides
save_initial_turn / finish_round for the caller to persist explicitly.
"""

import json
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict

ROUND_LIMIT = 30


# ── Input models ──


class HookInput(BaseModel):
    """Stop hook event data from stdin."""

    model_config = ConfigDict(extra="ignore")

    stop_hook_active: bool
    session_id: str
    transcript_path: str


class PluginEnvironment(BaseModel):
    """Plugin runtime environment from env vars and filesystem."""

    data_dir: Path
    is_inside_recursion: bool


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
    continuing: bool = False
    compacted: bool = False
    current_round: int = 0
    region_history: list[str] = []
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
    and splits the transcript at that point: agent_actions is everything
    after it.  user_input from this function is only used as a last resort;
    build_state prefers the captured prompt (round 1) or state file (round 2+).
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


def load_last_user_prompt(prompt_file: Path) -> str | None:
    """Load raw user prompt saved by the UserPromptSubmit hook."""
    if prompt_file.exists():
        return prompt_file.read_text()
    return None


def load_turn_state(state_file: Path) -> dict:
    """Load persisted turn state from JSON file. Returns empty dict on any failure."""
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text())
    except json.JSONDecodeError, OSError:
        return {}


def save_turn_state(state_file: Path, data: dict) -> None:
    """Save turn state to JSON file."""
    state_file.write_text(json.dumps(data))


def save_initial_turn(state: "State") -> None:
    """Persist user_input and empty regions for round 1. Called by run."""
    path = state.env.data_dir / f"{state.hook.session_id}.json"
    save_turn_state(
        path, {"round": 0, "user_input": state.turn.user_input, "regions": []}
    )
    # Clean up stale compaction marker from previous turn
    (state.env.data_dir / f"{state.hook.session_id}_compacted").unlink(missing_ok=True)


def finish_round(state: "State", new_region: str) -> None:
    """Persist round result: increment counter and append region. Called by run."""
    path = state.env.data_dir / f"{state.hook.session_id}.json"
    save_turn_state(
        path,
        {
            "round": state.current_round + 1,
            "user_input": state.turn.user_input,
            "regions": [*state.region_history, new_region],
        },
    )


# ── State assembly ──


def build_state(stdin_raw: str) -> State:
    """Collect all external inputs and assemble a State. No side effects.

    user_input source by round:
    - New turn (continuing=False): Raw user prompt captured by the
      UserPromptSubmit hook (capture_user_prompt).  Guaranteed to contain
      exactly what the user typed, free of skill expansions or system
      injections.
    - Continuing turn (continuing=True): Loaded from persisted state file.
      Compaction is detected via a marker file created by the PostCompact
      hook, independent of stop_hook_active.

    agent_actions always comes from parse_turn, which naturally scopes to
    work done since the last feedback injection.
    """
    hook = HookInput.model_validate_json(stdin_raw)

    data_dir = Path(os.environ["CLAUDE_PLUGIN_DATA"])
    env = PluginEnvironment(
        data_dir=data_dir,
        is_inside_recursion=os.environ.get("PARALLAX_INSIDE_RECURSION") == "1",
    )

    state_file = env.data_dir / f"{hook.session_id}.json"
    prompt_file = env.data_dir / f"{hook.session_id}_last_user_prompt.txt"
    turn_state = load_turn_state(state_file)
    turn = parse_turn(hook.transcript_path)

    compaction_marker = env.data_dir / f"{hook.session_id}_compacted"
    compacted = compaction_marker.exists()
    continuing = hook.stop_hook_active or compacted

    if continuing:
        current_round = turn_state.get("round", 0)
        region_history = turn_state.get("regions", [])
        saved_user_input = turn_state.get("user_input")
        if saved_user_input is not None:
            turn = Turn(
                user_input=saved_user_input,
                agent_actions=turn.agent_actions,
                agent_model=turn.agent_model,
            )
        else:
            # Fallback for first-round compaction: compaction happens before
            # save_initial_turn runs, so the state file has no user_input yet.
            # The prompt file (written by UserPromptSubmit) survives compaction
            # and holds the original mission.
            captured = load_last_user_prompt(prompt_file)
            if captured is not None:
                turn = Turn(
                    user_input=captured,
                    agent_actions=turn.agent_actions,
                    agent_model=turn.agent_model,
                )
    else:
        current_round = 0
        region_history = []
        captured = load_last_user_prompt(prompt_file)
        if captured is not None:
            turn = Turn(
                user_input=captured,
                agent_actions=turn.agent_actions,
                agent_model=turn.agent_model,
            )

    return State(
        hook=hook,
        env=env,
        continuing=continuing,
        compacted=compacted,
        current_round=current_round,
        region_history=region_history,
        turn=turn,
    )
