"""Pure prompt construction — no subprocess calls.

Assembles prompt strings from data. Reads prompt template files from the
prompts/ directory but performs no other I/O.
"""

import json
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

CONVERSION_PROMPT = """\
다음은 AI 에이전트가 사용자의 요청에 대해 수행한 작업 기록(JSON)입니다.
이 작업 기록을 설명하는 마크다운 문서를 작성하세요.
에이전트가 어떤 도구를 사용했고, 어떤 결과를 얻었으며, 어떤 판단을 내렸는지 서술하세요.

{actions_json}"""


def load_prompt_file(name: str) -> str:
    """Load a markdown prompt file from the prompts directory."""
    return (PROMPTS_DIR / name).read_text().strip()


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
    return CONVERSION_PROMPT.format(actions_json=actions_json)


def build_analysis_prompt(
    user_input: str,
    action_history_markdown: str,
    direction_history: list[str],
) -> str:
    """Assemble the 5-section analysis prompt. Pure string assembly."""
    sections = [
        wrap_section("role", load_prompt_file("role.md")),
        wrap_section("original-mission", user_input),
        wrap_section("action-history", action_history_markdown),
        wrap_section(
            "parallax-direction-history",
            format_direction_history(direction_history),
        ),
        wrap_section("instructions", load_prompt_file("instruction.md")),
    ]
    return "\n\n".join(sections)
