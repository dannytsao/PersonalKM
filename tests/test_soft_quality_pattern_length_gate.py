"""Soft low-quality patterns must not condemn substantial legitimate content.

Regression test: a Copilot conversation about connecting NotebookLM to
Claude was marked low-quality and left stuck in raw/ forever (status
'failed', never archived, retried every hour) because it mentioned
"If you subscribe to Claude Pro..." as one bullet among many — "subscribe
to" is meant to catch a genuine short paywall block, not a passing mention
inside a real, substantial conversation.
"""

from personalkm.ingest.ingestion_v2 import is_low_quality

REAL_CONVERSATION = """# Connecting NotebookLM to Claude

## Conversation
**user**: is there a way to connect notebooklm to claude

**ai**: Officially, no. Google's NotebookLM is a proprietary Google
product tightly integrated with Google's Gemini models.

However, depending on what you are trying to achieve, there are several
effective workarounds and alternatives:

- Use Claude's native "Projects" feature (Direct Alternative)
  - If you subscribe to Claude Pro or Team, Claude Projects offers
    functionality very similar to NotebookLM.
  - You can upload documents, code, or notes into a Project knowledge
    base and chat exclusively with those sources.
"""

GENUINE_PAYWALL_BLOCK = (
    "Please subscribe to continue reading this article. "
    "Sign in to your account or subscribe to unlock full access."
)


def test_substantial_content_mentioning_subscribe_to_is_not_low_quality():
    low, reason = is_low_quality(REAL_CONVERSATION)
    assert not low, reason


def test_short_genuine_paywall_block_is_still_caught():
    low, reason = is_low_quality(GENUINE_PAYWALL_BLOCK)
    assert low
    assert "Matched low-quality pattern" in reason


def test_hard_patterns_still_caught_regardless_of_length():
    long_but_broken = (
        "just a moment while we check your browser before proceeding. " * 20
    )
    low, reason = is_low_quality(long_but_broken)
    assert low
    assert "just a moment" in reason
