"""parallax — Stop hook that injects unexplored regions into the turn.

On each LLM stop:
1) Manage round counter (prevent runaway loops)
2) Review output via separate claude -p call (isolated context)
3) Block + inject region if unexplored paths remain, or allow stop
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.prompt import build_analysis_prompt, format_conversion_prompt, format_injection
from src.state import ROUND_LIMIT, build_state, finish_round, save_initial_turn

# ── claude -p invocation ──


TRIGGER_KEYWORD = "parallaxthink"
DISALLOWED_TOOLS = "Bash,Write,Edit,NotebookEdit"


def invoke_claude(
    prompt: str,
    model: str | None = None,
    *,
    tools: str | None = None,
    effort: str | None = None,
) -> str | None:
    """Run claude -p and return stdout. Returns None on failure.

    The prompt is piped via stdin to avoid OSError when the content exceeds
    the OS argument-list limit (ARG_MAX ~1 MB on macOS).

    tools:
      None (default) → --tools ""  (no tools)
      "Read"         → --tools "Read" --allowedTools "Read"  (whitelist + auto-approve)
      "*"            → --disallowedTools …  (all except dangerous)
    """
    cmd = ["claude", "-p", "--no-session-persistence"]
    if tools == "*":
        cmd.extend(["--disallowedTools", DISALLOWED_TOOLS])
    elif tools:
        cmd.extend(["--tools", tools, "--allowedTools", tools])
    else:
        cmd.extend(["--tools", ""])
    if model:
        cmd.extend(["--model", model])
    if effort:
        cmd.extend(["--effort", effort])
    env = {**os.environ, "PARALLAX_INSIDE_RECURSION": "1"}
    result = subprocess.run(cmd, input=prompt, capture_output=True, text=True, env=env)
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None


def convert_actions_to_markdown(
    actions: list[dict], model: str | None, data_dir: Path
) -> str:
    """Convert agent actions to a markdown document via claude -p.

    Saves the action record to a temporary file and instructs the
    conversion agent to read from it, avoiding input token limits
    for large transcripts.  Falls back to raw JSON on failure.
    """
    temp_file = data_dir / f"_conversion_{os.getpid()}.json"
    try:
        temp_file.write_text(json.dumps(actions, ensure_ascii=False, indent=2))
        prompt = format_conversion_prompt(str(temp_file))
        result = invoke_claude(prompt, model, tools="Read")
        return result or json.dumps(actions, ensure_ascii=False, indent=2)
    finally:
        temp_file.unlink(missing_ok=True)


# ── Logging ──


def write_log(log_file: Path, round_number: int, *, new_turn: bool, **sections: str):
    """Append a round's log to the session log file. Overwrites on new turn."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = f"[[ Round {round_number} - {timestamp} ]]\n\n"
    body = ""
    for title, content in sections.items():
        label = title.replace("_", " ").title()
        body += f"[[ Round {round_number} / {label} ]]\n\n{content}\n\n"
    mode = "w" if new_turn else "a"
    with open(log_file, mode) as f:
        f.write(header + body)


# ── Entry points ──


def run():
    """Stop hook entry point. Analyzes agent work and injects unexplored regions."""
    state = build_state(sys.stdin.read())

    if state.env.is_inside_recursion:
        sys.exit(0)

    activation_file = state.env.data_dir / f"{state.hook.session_id}_active"
    if not activation_file.exists():
        sys.exit(0)

    # Skip analysis when the user prompt is a /parallax-log skill command
    if state.turn.user_input.lstrip().startswith("/parallax-log"):
        sys.exit(0)

    new_turn = not state.continuing
    if new_turn:
        save_initial_turn(state)

    if state.current_round >= ROUND_LIMIT:
        sys.exit(0)

    log_file = state.env.data_dir / f"{state.hook.session_id}_parallax.log"

    action_history = convert_actions_to_markdown(
        state.turn.agent_actions, state.turn.agent_model, state.env.data_dir
    )
    mission = " ".join(state.turn.user_input.replace(TRIGGER_KEYWORD, "").split())
    prompt = build_analysis_prompt(mission, action_history, state.region_history)
    new_region = invoke_claude(prompt, state.turn.agent_model, tools="*", effort="max")

    write_log(
        log_file,
        state.current_round + 1,
        new_turn=new_turn,
        analysis_prompt=prompt,
        new_advice=new_region or "null",
    )

    if not new_region or new_region.strip().strip("`") == "null":
        sys.exit(0)

    finish_round(state, new_region)
    output = format_injection(new_region, mission=mission if state.compacted else None)
    sys.stderr.write(output)
    sys.exit(2)


def capture_user_prompt():
    """UserPromptSubmit hook entry point.

    Persists the raw user input to a file that the Stop hook reads later.
    This guarantees original-mission contains exactly what the user typed,
    regardless of skill expansions or system message injections.

    Also manages the activation marker: parallax only runs when the user
    prompt contains the trigger keyword.
    """
    data = json.loads(sys.stdin.read())
    data_dir = Path(os.environ["CLAUDE_PLUGIN_DATA"])
    session_id = data["session_id"]
    prompt = data.get("prompt", "")

    prompt_file = data_dir / f"{session_id}_last_user_prompt.txt"
    prompt_file.write_text(prompt)

    activation_file = data_dir / f"{session_id}_active"
    if TRIGGER_KEYWORD in prompt:
        activation_file.touch()
    elif activation_file.exists():
        activation_file.unlink()


if __name__ == "__main__":
    run()
