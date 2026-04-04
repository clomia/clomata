"""parallax — Stop hook that injects unexplored directions into the session.

On each LLM stop:
1) Manage round counter (prevent runaway loops)
2) Review output via separate claude -p call (isolated context)
3) Block + inject direction if unexplored paths remain, or allow stop
"""

import json
import os
import subprocess
import sys

from src.prompt import build_analysis_prompt, format_conversion_prompt
from src.state import ROUND_LIMIT, build_state, finish_round, save_initial_turn

# ── claude -p invocation ──


def invoke_claude(
    prompt: str,
    model: str | None = None,
    *,
    effort: str | None = None,
    timeout: int = 120,
) -> str | None:
    """Run claude -p and return stdout. Returns None on failure or timeout."""
    cmd = ["claude", "-p", prompt, "--no-session-persistence"]
    if model:
        cmd.extend(["--model", model])
    if effort:
        cmd.extend(["--effort", effort])
    env = {**os.environ, "PARALLAX_INSIDE_RECURSION": "1"}
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, env=env, timeout=timeout
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except subprocess.TimeoutExpired:
        pass
    return None


def convert_actions_to_markdown(actions: list[dict], model: str | None) -> str:
    """Convert agent actions to a markdown document via claude -p.

    Falls back to raw JSON on failure.
    """
    prompt = format_conversion_prompt(actions)
    result = invoke_claude(prompt, model)
    return result or json.dumps(actions, ensure_ascii=False, indent=2)


# ── Execution flow ──


def main():
    state = build_state(sys.stdin.read())

    if state.env.is_inside_recursion or state.env.is_disabled:
        sys.exit(0)

    if not state.hook.stop_hook_active:
        save_initial_turn(state)

    if state.current_round >= ROUND_LIMIT:
        sys.exit(0)

    action_history = convert_actions_to_markdown(
        state.turn.agent_actions, state.turn.agent_model
    )
    prompt = build_analysis_prompt(
        state.turn.user_input, action_history, state.direction_history
    )
    new_direction = invoke_claude(prompt, state.turn.agent_model, effort="max")

    if not new_direction or new_direction == "null":
        sys.exit(0)

    finish_round(state, new_direction)
    sys.stderr.write(new_direction)
    sys.exit(2)


if __name__ == "__main__":
    main()
