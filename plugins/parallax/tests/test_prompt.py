"""Tests for prompt construction (pure formatting, no subprocess)."""

import json

from src.prompt import (
    build_analysis_prompt,
    format_conversion_prompt,
    format_direction_history,
    load_prompt_file,
    wrap_section,
)


# ── wrap_section ──


class TestWrapSection:
    def test_wraps_content_in_xml_tags(self):
        result = wrap_section("role", "# Title\n\nContent here.")
        assert result == "<role>\n\n# Title\n\nContent here.\n\n</role>"

    def test_empty_content(self):
        result = wrap_section("tag", "")
        assert result == "<tag>\n\n\n\n</tag>"


# ── format_direction_history ──


class TestFormatDirectionHistory:
    def test_empty_history(self):
        result = format_direction_history([])
        assert "이전에 제시한 방향 없음" in result

    def test_single_direction(self):
        result = format_direction_history(["Add error handling"])
        assert "라운드 1: Add error handling" in result

    def test_multiple_directions(self):
        result = format_direction_history(["Add tests", "Handle edge cases"])
        assert "라운드 1: Add tests" in result
        assert "라운드 2: Handle edge cases" in result


# ── load_prompt_file ──


class TestLoadPromptFile:
    def test_loads_role_md(self):
        content = load_prompt_file("role.md")
        assert "parallax" in content
        assert "# 역할" in content

    def test_loads_instruction_md(self):
        content = load_prompt_file("instruction.md")
        assert "# 지시사항" in content
        assert "`null`" in content


# ── format_conversion_prompt ──


class TestFormatConversionPrompt:
    def test_includes_raw_json(self):
        actions = [{"role": "assistant", "content": "done"}]
        prompt = format_conversion_prompt(actions)
        assert json.dumps(actions, ensure_ascii=False, indent=2) in prompt

    def test_includes_instruction_text(self):
        prompt = format_conversion_prompt([])
        assert "마크다운 문서를 작성하세요" in prompt


# ── build_analysis_prompt ──


class TestBuildAnalysisPrompt:
    def test_assembles_all_five_sections(self):
        prompt = build_analysis_prompt(
            user_input="implement auth",
            action_history="The agent implemented auth.",
            direction_history=["Add validation"],
        )

        assert "<role>" in prompt
        assert "</role>" in prompt
        assert "<original-mission>" in prompt
        assert "implement auth" in prompt
        assert "<action-history>" in prompt
        assert "The agent implemented auth." in prompt
        assert "<parallax-direction-history>" in prompt
        assert "라운드 1: Add validation" in prompt
        assert "<instructions>" in prompt
        assert "지시사항" in prompt

    def test_sections_are_in_correct_order(self):
        prompt = build_analysis_prompt("input", "actions", [])

        role_pos = prompt.index("<role>")
        mission_pos = prompt.index("<original-mission>")
        action_pos = prompt.index("<action-history>")
        history_pos = prompt.index("<parallax-direction-history>")
        instr_pos = prompt.index("<instructions>")

        assert role_pos < mission_pos < action_pos < history_pos < instr_pos

    def test_empty_direction_history(self):
        prompt = build_analysis_prompt("input", "actions", [])
        assert "이전에 제시한 방향 없음" in prompt
