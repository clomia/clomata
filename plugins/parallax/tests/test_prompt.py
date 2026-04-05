"""Tests for prompt construction (pure formatting, no subprocess)."""

import json

from src.prompt import (
    INSTRUCTION_PROMPT,
    ROLE_PROMPT,
    build_analysis_prompt,
    format_conversion_prompt,
    format_direction_history,
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
        assert format_direction_history([]) == "No prior directions."

    def test_single_direction(self):
        result = format_direction_history(["Add error handling"])
        assert result == "<direction-1>\n\nAdd error handling\n\n</direction-1>"

    def test_multiple_directions(self):
        result = format_direction_history(["Add tests", "Handle edge cases"])
        assert result == (
            "<direction-1>\n\nAdd tests\n\n</direction-1>"
            "\n\n"
            "<direction-2>\n\nHandle edge cases\n\n</direction-2>"
        )


# ── Prompt constants ──


class TestPromptConstants:
    def test_role_prompt_loaded(self):
        assert "advisory agent" in ROLE_PROMPT
        assert "# Background" in ROLE_PROMPT

    def test_instruction_prompt_loaded(self):
        assert "`null`" in INSTRUCTION_PROMPT


# ── format_conversion_prompt ──


class TestFormatConversionPrompt:
    def test_includes_raw_json(self):
        actions = [{"role": "assistant", "content": "done"}]
        prompt = format_conversion_prompt(actions)
        assert json.dumps(actions, ensure_ascii=False, indent=2) in prompt

    def test_includes_instruction_text(self):
        prompt = format_conversion_prompt([])
        assert "Produce a markdown document" in prompt

    def test_wraps_json_in_action_record_tag(self):
        prompt = format_conversion_prompt([])
        assert "<action-record>" in prompt
        assert "</action-record>" in prompt


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
        assert "<direction-1>" in prompt
        assert "Add validation" in prompt
        assert "<instructions>" in prompt
        assert "Explore thought regions" in prompt

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
        assert "No prior directions." in prompt
