"""parallax — Stop hook that injects unexplored directions into the session.

On each LLM stop:
1) Manage round counter (prevent runaway loops)
2) Review output via separate claude -p call (isolated context)
3) Block + inject direction if unexplored paths remain, or allow stop
"""

import sys

from pydantic import BaseModel

from src.state import build_state

MESSAGE_TRUNCATE_LENGTH = 2000


# ── Analysis result ──


class Decision(BaseModel):
    """ok=True allows stop. ok=False injects reason via stderr and continues."""

    ok: bool
    reason: str = ""


# ── Execution flow ──


def main():
    state = build_state(sys.stdin.read())

    # Guard checks — exit if preconditions not met
    #   env.is_inside_recursion → block recursive invocation
    #   env.is_disabled → plugin disabled

    # Advance round
    #   current_round += 1, persist to state file
    #   current_round > limit → terminate

    # Analysis (separate claude -p process)
    #   prompt + turn.user_input + turn.agent_actions → build prompt
    #   inherit turn.agent_model, --effort max
    #   parse response JSON → Decision(ok, reason)

    # Apply decision (Stop hook protocol)
    #   parse failure → allow stop (exit 0)
    #   ok=True  → allow stop (exit 0)
    #   ok=False → stderr reason + exit 2 (inject direction)
    ...


if __name__ == "__main__":
    main()
