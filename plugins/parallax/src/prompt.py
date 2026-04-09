"""Prompt — assembles the 5-section XML+Markdown analysis prompt.

Pure string formatting. Reads prompt templates from prompts/ but performs
no subprocess calls or other I/O.
"""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

ROLE_PROMPT = (PROMPTS_DIR / "role.md").read_text().strip()
INSTRUCTION_PROMPT = (PROMPTS_DIR / "instruction.md").read_text().strip()

CONVERSION_PROMPT_TEMPLATE = """\
Read the JSON file below. This is the main agent's task execution record.
Produce a markdown document describing this record.
Enumerate the agent's thoughts, attempts, and results systematically, leaving nothing out.

Ignore metadata outside the agent's own awareness, such as token usage, API turn counts, or signatures.

Action record file: {file_path}"""

CAUTION_TEXT = """\
NEVER end your task by asking the user a question or making a request in plain text.
If you need to ask the user anything, YOU ALWAYS MUST USE THE `AskUserQuestion` TOOL.
"""


def wrap_section(tag: str, content: str) -> str:
    """Wrap content in an XML tag."""
    return f"<{tag}>\n\n{content}\n\n</{tag}>"


def format_region_history(region_history: list[str]) -> str:
    """Format previous parallax regions for the <parallax-region-history> section."""
    if not region_history:
        return "No prior regions."
    return "\n\n".join(
        f"<region-{i + 1}>\n\n{region}\n\n</region-{i + 1}>"
        for i, region in enumerate(region_history)
    )


def format_conversion_prompt(file_path: str) -> str:
    """Build the prompt string for the action-to-markdown conversion call."""
    return CONVERSION_PROMPT_TEMPLATE.format(file_path=file_path)


def build_analysis_prompt(
    user_input: str,
    action_history: str,
    region_history: list[str],
) -> str:
    """Assemble the 5-section analysis prompt. Pure string assembly."""
    sections = [
        wrap_section("role", ROLE_PROMPT),
        wrap_section("original-mission", user_input),
        wrap_section("action-history", action_history),
        wrap_section(
            "parallax-region-history",
            format_region_history(region_history),
        ),
        wrap_section("instructions", INSTRUCTION_PROMPT),
    ]
    return "\n\n".join(sections)


def format_injection(content: str, *, mission: str | None = None) -> str:
    """Assemble the stop-hook feedback injected into Main Context."""
    sections = []
    if mission:
        sections.append(f"# Original Mission\n\n{mission}")
    sections.append(f"# Advice\n\n{content}")
    sections.append(f"# Caution\n\n{CAUTION_TEXT}")
    return "\n\n".join(sections)
