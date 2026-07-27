"""Tests for the P6#22 wikilink analyzer → llm.router migration.

Verifies that:
1. analyze_page() calls router.route() with the correct stage
2. XML parser correctly extracts forward/backward links from raw output
3. Backward-compatibility alias (OllamaWikilinkAnalyzer) works
4. Empty entity list short-circuits without calling the router
5. LLMError from the router propagates (no silent fallback)
6. parse_wikilink_output handles edge cases
"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from personalkm.propagate.ollama_wikilink import (
    WikilinkAnalyzer,
    OllamaWikilinkAnalyzer,
    parse_wikilink_output,
)
from personalkm.llm.base import Completion, LLMError


# ─── Parser tests ────────────────────────────────────────────────────────

def test_parse_wikilink_output_extracts_forward_and_backward():
    raw = """<FORWARD_LINKS>
- [[claude-code]]
- [[docker]]
</FORWARD_LINKS>

<BACKWARD_LINKS>
- [[anthropic]]
</BACKWARD_LINKS>"""
    forward, backward = parse_wikilink_output(raw)
    assert forward == ["claude-code", "docker"]
    assert backward == ["anthropic"]


def test_parse_wikilink_output_handles_empty_sections():
    raw = """<FORWARD_LINKS>
</FORWARD_LINKS>

<BACKWARD_LINKS>
</BACKWARD_LINKS>"""
    forward, backward = parse_wikilink_output(raw)
    assert forward == []
    assert backward == []


def test_parse_wikilink_output_strips_trailing_comments():
    raw = """<FORWARD_LINKS>
- [[claude-code]]  # this is a comment
</FORWARD_LINKS>

<BACKWARD_LINKS>
</BACKWARD_LINKS>"""
    forward, backward = parse_wikilink_output(raw)
    assert forward == ["claude-code"]
    assert backward == []


def test_parse_wikilink_output_handles_alias_syntax():
    raw = """<FORWARD_LINKS>
- [[kimi-k3|KIMI K3]]
</FORWARD_LINKS>

<BACKWARD_LINKS>
</BACKWARD_LINKS>"""
    forward, backward = parse_wikilink_output(raw)
    assert forward == ["kimi-k3"]


def test_parse_wikilink_output_lowercases_slugs():
    raw = """<FORWARD_LINKS>
- [[Claude-Code]]
- [[Docker]]
</FORWARD_LINKS>

<BACKWARD_LINKS>
</BACKWARD_LINKS>"""
    forward, backward = parse_wikilink_output(raw)
    assert forward == ["claude-code", "docker"]


def test_parse_wikilink_output_no_tags_returns_empty():
    forward, backward = parse_wikilink_output("no tags here")
    assert forward == []
    assert backward == []


# ─── Analyzer tests ──────────────────────────────────────────────────────

def test_backward_compat_alias_is_same_class():
    assert WikilinkAnalyzer is OllamaWikilinkAnalyzer


def test_analyze_page_calls_router_with_correct_stage():
    analyzer = WikilinkAnalyzer()
    fake_completion = Completion(
        text="<FORWARD_LINKS>\n- [[docker]]\n</FORWARD_LINKS>\n<BACKWARD_LINKS>\n</BACKWARD_LINKS>",
        model="ollama/qwen2.5:latest",
        input_tokens=100,
        output_tokens=20,
    )
    with patch("personalkm.llm.router.route", return_value=fake_completion) as mock_route:
        result = analyzer.analyze_page(
            page_title="Test Page",
            page_body="Some body text about docker containers.",
            existing_entity_names=["docker", "claude-code"],
        )

    mock_route.assert_called_once()
    call_args = mock_route.call_args
    assert call_args[0][0] == "wikilink_analysis"  # stage name
    assert call_args[1]["system"]  # system prompt passed
    assert "docker" in call_args[0][1]  # prompt includes entity list

    assert result["forward_links"] == ["docker"]
    assert result["backward_links"] == []
    assert result["parse_success"] is True


def test_analyze_page_empty_entities_skips_router():
    analyzer = WikilinkAnalyzer()
    with patch("personalkm.llm.router.route") as mock_route:
        result = analyzer.analyze_page(
            page_title="Test Page",
            page_body="Some body text.",
            existing_entity_names=[],
        )

    mock_route.assert_not_called()
    assert result["forward_links"] == []
    assert result["parse_success"] is True


def test_analyze_page_llm_error_propagates():
    """P6#22: router raises LLMError when all models exhausted — must propagate."""
    analyzer = WikilinkAnalyzer()
    with patch("personalkm.llm.router.route", side_effect=LLMError("All models exhausted")):
        try:
            analyzer.analyze_page(
                page_title="Test Page",
                page_body="Some body text.",
                existing_entity_names=["docker"],
            )
            assert False, "Should have raised LLMError"
        except LLMError:
            pass  # Expected — no silent fallback


def test_analyze_page_custom_stage():
    """Analyzer can use a custom stage name for testing or alternative configs."""
    analyzer = WikilinkAnalyzer(stage="propagation_distill")
    fake_completion = Completion(
        text="<FORWARD_LINKS>\n</FORWARD_LINKS>\n<BACKWARD_LINKS>\n</BACKWARD_LINKS>",
        model="ollama/qwen2.5:latest",
        input_tokens=50,
        output_tokens=10,
    )
    with patch("personalkm.llm.router.route", return_value=fake_completion) as mock_route:
        analyzer.analyze_page(
            page_title="Test",
            page_body="body",
            existing_entity_names=["x"],
        )
    assert mock_route.call_args[0][0] == "propagation_distill"
