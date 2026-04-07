"""Tests for prompt construction (pure formatting, no subprocess)."""

from src.prompt import (
    INSTRUCTION_PROMPT,
    ROLE_PROMPT,
    build_analysis_prompt,
    format_conversion_prompt,
    format_region_history,
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


# ── format_region_history ──


class TestFormatRegionHistory:
    def test_empty_history(self):
        assert format_region_history([]) == "No prior regions."

    def test_single_region(self):
        result = format_region_history(["Add error handling"])
        assert result == "<region-1>\n\nAdd error handling\n\n</region-1>"

    def test_multiple_regions(self):
        result = format_region_history(["Add tests", "Handle edge cases"])
        assert result == (
            "<region-1>\n\nAdd tests\n\n</region-1>"
            "\n\n"
            "<region-2>\n\nHandle edge cases\n\n</region-2>"
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
    def test_includes_file_path(self):
        prompt = format_conversion_prompt("/tmp/actions.json")
        assert "/tmp/actions.json" in prompt

    def test_includes_instruction_text(self):
        prompt = format_conversion_prompt("/tmp/actions.json")
        assert "Produce a markdown document" in prompt

    def test_references_file_not_inline_json(self):
        prompt = format_conversion_prompt("/tmp/actions.json")
        assert "Action record file:" in prompt
        assert "<action-record>" not in prompt


# ── build_analysis_prompt ──


class TestBuildAnalysisPrompt:
    def test_assembles_all_five_sections(self):
        prompt = build_analysis_prompt(
            user_input="implement auth",
            action_history="The agent implemented auth.",
            region_history=["Add validation"],
        )

        assert "<role>" in prompt
        assert "</role>" in prompt
        assert "<original-mission>" in prompt
        assert "implement auth" in prompt
        assert "<action-history>" in prompt
        assert "The agent implemented auth." in prompt
        assert "<parallax-region-history>" in prompt
        assert "<region-1>" in prompt
        assert "Add validation" in prompt
        assert "<instructions>" in prompt
        assert "Find and surface regions" in prompt

    def test_sections_are_in_correct_order(self):
        prompt = build_analysis_prompt("input", "actions", [])

        role_pos = prompt.index("<role>")
        mission_pos = prompt.index("<original-mission>")
        action_pos = prompt.index("<action-history>")
        history_pos = prompt.index("<parallax-region-history>")
        instr_pos = prompt.index("<instructions>")

        assert role_pos < mission_pos < action_pos < history_pos < instr_pos

    def test_empty_region_history(self):
        prompt = build_analysis_prompt("input", "actions", [])
        assert "No prior regions." in prompt
