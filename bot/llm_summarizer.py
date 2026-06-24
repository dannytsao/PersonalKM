"""
AI Summarizer for PersonalKM LLM-Wiki v2

Distills raw captures into concise, structured wiki summaries using MiniMax.

Usage:
    from bot.llm_summarizer import summarize_content, distill_to_markdown

    result = summarize_content(raw_text, page_type="entity")
    markdown = distill_to_markdown(result)
"""

import logging
import re
import json
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Prompt Templates
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a knowledge curator for a personal wiki.
Your task is to distill raw notes into concise, structured wiki entries.

RULES:
- Classify the PRIMARY topic of this note from the 5 options ONLY:
  AI-Agent-&-Tools | Automation-Workflows | PKM-&-System-Design | Tech-Trends-&-Insights | Personal-Interests
- topic: choose EXACTLY ONE that best represents the core subject
- tags: capture CROSS-TOPIC attributes — tools, techniques, technologies, years, personal action states
  (e.g. docker, claude, llm, 2025, to-read, recall — NOT a second topic label)
  A note can have 0 tags if nothing cross-topic applies.
- Extract key facts only — no fluff, no repetition
- Use English for entity names (e.g., "Claude Code" not "克勞德代碼")
- Normalize entity names to plain English identifiers (lowercase, hyphens)
- Keep summaries to 3-5 sentences max
- Key facts should be specific (versions, commands, configurations — not generic)
- Always cite the source file

OUTPUT JSON ONLY — no markdown code fences, no explanations."""

ENTITY_USER_PROMPT = """Distill this {page_type} note into a wiki entry.

SOURCE FILE: {source_path}

CONTENT:
{content}

Respond ONLY with this JSON (no markdown, no code fences):
{{
  "topic": "AI-Agent-&-Tools | Automation-Workflows | PKM-&-System-Design | Tech-Trends-&-Insights | Personal-Interests",
  "summary": "3-5 sentence summary in English",
  "key_facts": [
    "{{fact 1 — specific and concrete}}",
    "{{fact 2 — specific and concrete}}",
    "{{fact 3}}"
  ],
  "entities_mentioned": ["entity-name-1", "entity-name-2"],
  "related_concepts": ["concept-name-1"],
  "confidence": "high|medium|low",
  "tags": ["relevant", "cross-topic", "tags"]
}}"""

CONCEPT_USER_PROMPT = """Distill this concept/guide note into a wiki entry.

SOURCE FILE: {source_path}

CONTENT:
{content}

Respond ONLY with this JSON (no markdown, no code fences):
{{
  "topic": "AI-Agent-&-Tools | Automation-Workflows | PKM-&-System-Design | Tech-Trends-&-Insights | Personal-Interests",
  "summary": "3-5 sentence summary explaining this concept",
  "key_facts": [
    "{{practical fact 1 — how to apply it}}",
    "{{practical fact 2 — concrete steps}}",
    "{{practical fact 3}}"
  ],
  "prerequisites": ["prereq-concept-1"],
  "related_tools": ["tool-name-1"],
  "confidence": "high|medium|low",
  "tags": ["relevant", "cross-topic", "tags"]
}}"""


# ─────────────────────────────────────────────────────────────────────────────
# Main API
# ─────────────────────────────────────────────────────────────────────────────

def summarize_content(
    content: str,
    page_type: str = "entity",
    source_path: Optional[str] = None,
    client=None,
) -> Dict[str, Any]:
    """
    Summarize raw content into wiki-ready structured data.

    Args:
        content: Raw markdown content (with or without frontmatter)
        page_type: "entity" or "concept"
        source_path: Optional path to source file (for provenance)
        client: LLM client (defaults to get_llm_client())

    Returns:
        Dict with keys: summary, key_facts, entities_mentioned, related_concepts,
                        confidence, tags, raw_content
    """
    # Strip frontmatter for processing
    body_content = _strip_frontmatter(content)
    
    # Truncate if too long (API token limit)
    MAX_CHARS = 8000
    if len(body_content) > MAX_CHARS:
        body_content = body_content[:MAX_CHARS]
        logger.warning(f"Content truncated to {MAX_CHARS} chars for summarization")

    # Get LLM client
    if client is None:
        from bot.llm_clients import get_llm_client
        client = get_llm_client()

    if not client.is_available():
        logger.warning("No LLM client available, using fallback summarization")
        return _fallback_summarize(body_content, page_type, source_path)

    # Build prompt
    source_display = source_path or "unknown"
    if page_type == "entity":
        prompt = ENTITY_USER_PROMPT.format(
            page_type=page_type,
            source_path=source_display,
            content=body_content,
        )
    else:
        prompt = CONCEPT_USER_PROMPT.format(
            source_path=source_display,
            content=body_content,
        )

    try:
        response = client.chat_completions_create(
            model=client.default_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=600,
        )

        # Extract response
        if hasattr(response, 'choices'):
            text = response.choices[0].message.content or ""
        elif isinstance(response, dict):
            choices = response.get('choices', [{}])
            text = choices[0].get('message', {}).get('content', '') if choices else ''
        else:
            text = str(response)

        # Parse JSON from response
        result = _parse_json_response(text, body_content, page_type, source_path or "")
        result['raw_content'] = body_content
        return result

    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        fallback = _fallback_summarize(body_content, page_type, source_path)
        fallback['raw_content'] = body_content
        fallback['error'] = str(e)
        return fallback


def distill_to_markdown(result: Dict[str, Any], page_type: str = "entity") -> str:
    """
    Convert summarization result into wiki markdown body.

    Args:
        result: Output from summarize_content()
        page_type: "entity" or "concept"

    Returns:
        Markdown string ready to write to wiki page
    """
    lines = []

    # Summary section
    lines.append("## Summary\n")
    summary = result.get("summary", "No summary available.")
    lines.append(f"{summary}\n")

    # Key Facts section
    key_facts = result.get("key_facts", [])
    if key_facts:
        lines.append("## Key Facts\n")
        for fact in key_facts:
            # Ensure fact is a clean string line
            fact_clean = str(fact).strip()
            if fact_clean:
                lines.append(f"- {fact_clean}")
        lines.append("")

    # Entities Mentioned (for entities)
    if page_type == "entity":
        entities = result.get("entities_mentioned", [])
        if entities:
            lines.append("## Related Entities\n")
            for entity in entities[:10]:  # Cap at 10
                slug = _slugify(entity)
                lines.append(f"- [[{entity}]]")
            lines.append("")

    # Related Concepts (for concepts)
    if page_type == "concept":
        concepts = result.get("related_concepts", [])
        prerequisites = result.get("prerequisites", [])
        tools = result.get("related_tools", [])

        if concepts:
            lines.append("## Related Concepts\n")
            for c in concepts[:10]:
                lines.append(f"- [[{c}]]")
            lines.append("")

        if prerequisites:
            lines.append("## Prerequisites\n")
            for p in prerequisites[:5]:
                lines.append(f"- [[{p}]]")
            lines.append("")

        if tools:
            lines.append("## Tools\n")
            for t in tools[:10]:
                lines.append(f"- [[{t}]]")
            lines.append("")

    # Source provenance
    raw = result.get("raw_content", "")
    if raw:
        # Truncate raw content for source citation
        preview = raw[:200].replace("\n", " ").strip()
        if len(raw) > 200:
            preview += "..."
        lines.append(f"**Source:** ^{preview}\n")

    return "\n".join(lines)


def detect_entity_mentions(content: str) -> List[str]:
    """
    Detect entity mentions in content using simple pattern matching.

    Returns list of normalized entity names (English, lowercase, hyphens).
    """
    # Strip frontmatter
    body = _strip_frontmatter(content)

    # Common patterns for entity names
    # 1. CamelCase → camel-case
    # 2. Acronyms like "GPT-4", "Claude 3.5", "K8s"
    # 3. Tool names: "Docker", "Kubernetes", "Terraform"

    entities = set()

    # Pattern: CamelCase words (but not all-caps like GPT-4)
    camel = re.findall(r'(?<![A-Z])([A-Z][a-z]+(?:[A-Z][a-z]+)+)', body)
    for word in camel:
        entities.add(_slugify(word))

    # Pattern: Acronyms with versions (GPT-4, Claude 3.5, K8s)
    acronyms = re.findall(r'\b(GPT-\d+(?:\.\d+)?|Claude-\d+(?:\.\d+)?|K8s|LLaMA-\d+|Mistral-\d+|Lora|QLoRA|RLHF|AgentOps|RAG)\b', body, re.IGNORECASE)
    for a in acronyms:
        entities.add(a.lower().replace('.', '-'))

    # Pattern: Common tools (lowercase)
    common_tools = [
        'docker', 'kubernetes', 'terraform', 'ansible', 'helm',
        'github-actions', 'gitlab-ci', 'jenkins', 'nginx',
        'postgresql', 'mysql', 'redis', 'mongodb',
        'fastapi', 'flask', 'django', 'nextjs', 'react',
        'vscode', 'cursor', 'claude-code', 'openai', 'anthropic',
        'huggingface', 'pytorch', 'tensorflow', 'langchain',
    ]
    body_lower = body.lower()
    for tool in common_tools:
        if tool in body_lower:
            entities.add(tool)

    # Pattern: Chinese entity mentions like "克劳德·德雷克" or "Claude"
    # Extract quoted or bracket-enclosed names
    chinese_names = re.findall(r'[\'""]?([\u4e00-\u9fff][\u4e00-\u9fff]{1,10})[\'""]?', body)
    for name in chinese_names:
        if len(name) >= 2:
            entities.add(f"topic-{name}")

    return sorted(list(entities))


# ─────────────────────────────────────────────────────────────────────────────
# Internal Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _strip_frontmatter(content: str) -> str:
    """Remove ALL YAML frontmatter blocks from markdown content.
    
    Handles:
    - Standard frontmatter: --- ... --- (on their own lines)
    - Merged closers: ---# Heading (--- on same line as content)
    - Orphaned frontmatter: file starts with --- but no closer
    - Multiple consecutive blocks
    
    Returns only the actual body content.
    """
    lines = content.split('\n')
    n = len(lines)
    
    # Strategy: find ALL frontmatter regions (--- ... --- pairs)
    # and mark all lines within them for skipping.
    skip_indices = set()
    i = 0
    while i < n:
        stripped = lines[i].strip()
        
        if stripped == '---':
            # Found start of a frontmatter block — find its closing ---
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                next_stripped = lines[j].strip()
                if next_stripped == '---':
                    # Properly closed on own line
                    depth -= 1
                    j += 1
                elif next_stripped.startswith('---'):
                    # Merged closer: "---# Heading" or "--- [next]"
                    depth -= 1
                    j += 1
                elif depth == 1 and lines[j].startswith('---'):
                    # Partial merge: "---# content" — the line starts with ---
                    # but has content after; treat as closer
                    depth -= 1
                    j += 1
                else:
                    j += 1
            
            # Mark all lines from i to j (exclusive) as skip
            for k in range(i, j):
                skip_indices.add(k)
            i = j
        else:
            i += 1
    
    # Build cleaned content
    cleaned = []
    for i, line in enumerate(lines):
        if i in skip_indices:
            continue
        s = line.strip()
        # Skip orphaned frontmatter key: value lines (metadata outside blocks)
        if _is_frontmatter_line(s):
            continue
        cleaned.append(line)
    
    return '\n'.join(cleaned).strip()


def _is_frontmatter_line(line: str) -> bool:
    """Check if a line looks like a YAML frontmatter key: value pair."""
    # Metadata patterns: key: value (short, no special chars except : - _)
    line = line.strip()
    if not line:
        return False
    # Has exactly one colon, short value, no markdown chars
    if ':' in line and not line.startswith('#'):
        key = line.split(':', 1)[0].strip()
        val = line.split(':', 1)[1].strip()
        # Key should be alphanumeric + underscore
        import re
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key) and len(key) < 30:
            return True
    return False


def _parse_json_response(text: str, fallback_content: str, page_type: str, source: str) -> Dict[str, Any]:
    """Parse JSON from LLM response, with fallback on failure."""
    try:
        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])  # Remove first and last line

        # Find JSON boundaries
        start = text.find("{")
        end = text.rfind("}") + 1

        if start < 0 or end <= start:
            raise ValueError("No JSON found in response")

        json_str = text[start:end]
        parsed = json.loads(json_str)

        # Validate and sanitize
        return {
            "topic": str(parsed.get("topic", "Tech-Trends-&-Insights")),
            "summary": str(parsed.get("summary", ""))[:300],
            "key_facts": [str(f) for f in parsed.get("key_facts", [])[:10]],
            "entities_mentioned": [str(e) for e in parsed.get("entities_mentioned", [])[:10]],
            "related_concepts": [str(c) for c in parsed.get("related_concepts", [])[:10]],
            "confidence": str(parsed.get("confidence", "medium")),
            "tags": [str(t) for t in parsed.get("tags", [])[:5]],
        }

    except Exception as e:
        logger.warning(f"Failed to parse LLM JSON response: {e}, using fallback")
        return _fallback_summarize(fallback_content, page_type, source)


def _fallback_summarize(content: str, page_type: str, source: Optional[str]) -> Dict[str, Any]:
    """
    Fallback summarization when LLM is unavailable.
    Extracts a rough summary from content using simple text processing.
    """
    body = _strip_frontmatter(content)

    # Get first meaningful paragraph (skip headers, metadata lines)
    paragraphs = body.split("\n\n")
    summary_text = ""
    for para in paragraphs:
        para = para.strip()
        # Skip: too short, is a header, is metadata
        if len(para) < 30:
            continue
        if para.startswith("# ") or para.startswith("## "):
            continue
        if para.startswith("- ") or para.startswith("* "):
            continue
        if re.match(r'^[\u4e00-\u9fff]+', para):  # Skip pure Chinese without context
            continue
        if "：" in para and len(para) < 50:  # Skip short metadata lines like "平台：web"
            continue
        # Clean markdown
        para = re.sub(r'[#*`_[\]()>|]', '', para)
        para = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', para)  # [text](url) → text
        para = re.sub(r'---+', '', para)
        para = para.strip()
        if para:
            summary_text = para
            break

    if not summary_text:
        # Last resort: use first non-header line
        for line in body.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                summary_text = re.sub(r'[#*`]', '', line)[:200]
                break

    summary_text = summary_text[:300] if summary_text else "Summary unavailable."

    return {
        "topic": "Tech-Trends-&-Insights",
        "summary": summary_text,
        "key_facts": [
            "Full content preserved in wiki page",
            "Source file archived in raw/ directory",
        ],
        "entities_mentioned": detect_entity_mentions(body),
        "related_concepts": [],
        "confidence": "low",
        "tags": ["auto-generated"] if page_type == "concept" else [],
    }


def _slugify(text: str) -> str:
    """Convert text to a slug identifier."""
    if not text:
        return ""

    # Lowercase, replace spaces/special chars with hyphens
    slug = text.lower()
    slug = re.sub(r'[\s\-–—]+', '-', slug)
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    slug = re.sub(r'-+', '-', slug)  # Collapse multiple hyphens
    slug = slug.strip('-')

    return slug


# ─────────────────────────────────────────────────────────────────────────────
# Test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from pathlib import Path
    from bot.llm_clients import get_default_client, get_llm_client

    print("=" * 60)
    print("LLM Summarizer Test")
    print("=" * 60)

    # Test content
    sample_content = """# Claude Code

Claude Code is an AI coding assistant by Anthropic that runs in your terminal.

## Key Features
- Natural language code generation
- Multi-file project understanding
- Git integration
- Terminal command execution

## Usage
Just type `claude` in any project directory to start.

## Version
Current version is Claude 3.5 (Sonnet/Opus/Haiku variants).

Claude can help with:
- Writing Python, JavaScript, Go, Rust code
- Debugging and code review
- Explaining complex algorithms
- Refactoring legacy code
"""

    print("\n1. Testing with NO LLM (fallback mode)...")
    result = summarize_content(sample_content, page_type="entity", source_path="raw/test/claude-code.md")
    print(f"   Summary: {result['summary'][:100]}...")
    print(f"   Key facts: {len(result['key_facts'])} items")
    print(f"   Entities: {result['entities_mentioned']}")
    print(f"   Confidence: {result['confidence']}")

    md = distill_to_markdown(result, page_type="entity")
    print(f"\n   Distilled markdown ({len(md)} chars):")
    print("   " + "\n   ".join(md.split("\n")[:10]))

    # Test with LLM if available
    client = get_llm_client()
    if client.is_available():
        print("\n2. Testing with MiniMax API...")
        result2 = summarize_content(sample_content, page_type="entity", source_path="raw/test/claude-code.md", client=client)
        print(f"   Summary: {result2['summary'][:100]}...")
        print(f"   Key facts: {len(result2['key_facts'])} items")
        print(f"   Confidence: {result2['confidence']}")

        md2 = distill_to_markdown(result2, page_type="entity")
        print(f"\n   Distilled markdown ({len(md2)} chars):")
        print("   " + "\n   ".join(md2.split("\n")[:15]))
        print("\n   ✅ LLM summarization works!")
    else:
        print("\n   ⚠️  No LLM API key — using fallback summarization")
        print("   Set MINIMAX_API_KEY to enable AI summarization")

    print("\n" + "=" * 60)
