"""Prompt — assembles the 5-section XML+Markdown analysis prompt.

Pure string formatting. Reads prompt templates from prompts/ but performs
no subprocess calls or other I/O.
"""

import json
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

ROLE_PROMPT = (PROMPTS_DIR / "role.md").read_text().strip()
INSTRUCTION_PROMPT = (PROMPTS_DIR / "instruction.md").read_text().strip()

CONVERSION_PROMPT_TEMPLATE = """\
This is the main agent's task execution record.
Produce a markdown document describing this record.
Enumerate the agent's thoughts, attempts, and results systematically, leaving nothing out.

Ignore metadata outside the agent's own awareness, such as token usage or API turn counts.

<action-record>
{actions_json}
</action-record>"""


def wrap_section(tag: str, content: str) -> str:
    """Wrap content in an XML tag."""
    return f"<{tag}>\n\n{content}\n\n</{tag}>"


def format_direction_history(direction_history: list[str]) -> str:
    """Format previous parallax directions for the <parallax-direction-history> section."""
    if not direction_history:
        return "이번 턴에서 이전에 제시한 방향 없음."
    return "\n".join(
        f"- 라운드 {i + 1}: {direction}"
        for i, direction in enumerate(direction_history)
    )


def format_conversion_prompt(actions: list[dict]) -> str:
    """Build the prompt string for the action-to-markdown conversion call."""
    actions_json = json.dumps(actions, ensure_ascii=False, indent=2)
    return CONVERSION_PROMPT_TEMPLATE.format(actions_json=actions_json)


def build_analysis_prompt(
    user_input: str,
    action_history: str,
    direction_history: list[str],
) -> str:
    """Assemble the 5-section analysis prompt. Pure string assembly."""
    sections = [
        wrap_section("role", ROLE_PROMPT),
        wrap_section("original-mission", user_input),
        wrap_section("action-history", action_history),
        wrap_section(
            "parallax-direction-history",
            format_direction_history(direction_history),
        ),
        wrap_section("instructions", INSTRUCTION_PROMPT),
    ]
    return "\n\n".join(sections)
