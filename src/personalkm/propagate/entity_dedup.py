"""
Entity Deduplication for PersonalKM LLM-Wiki v2 (Phase 6)

Phase 6 adds canonical entity support. Instead of only indexing filename stems
(which produces entries like "hermes-agent-learn-ai"), we now define a set of
canonical entity names. When a new capture arrives about a canonical entity,
it merges into the canonical page (e.g., entities/hermes-agent.md) instead of
creating another date-prefixed page.

Usage:
    from personalkm.propagate.entity_dedup import EntityRegistry, CANONICAL_ENTITIES

    registry = EntityRegistry(Path('wiki'))
    match = registry.find_entity_match('Hermes Agent')
    # → Path('wiki/entities/hermes-agent.md') if canonical page exists

    result = registry.update_or_create(
        entity_name='Hermes Agent',
        new_content='...',
    )
    # → merges into entities/hermes-agent.md
"""

import logging
import re
import unicodedata
from pathlib import Path
from typing import Optional

from tools.omnichannel_md.frontmatter import parse_yaml_list

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Phase 6: Canonical Entity Definitions
#
# When a capture's title matches one of these (via normalized comparison),
# the pipeline writes TO the canonical page (no date prefix) instead of
# creating a date-prefixed page. Subsequent captures about the same entity
# merge into the canonical page.
# ---------------------------------------------------------------------------

CANONICAL_ENTITIES: dict[str, str] = {
    # slug → display name
    "hermes-agent": "Hermes Agent",
    "hermes-os": "Hermes OS",
    "claude-code": "Claude Code",
    "codex": "Codex",
    "cursor": "Cursor",
    "chatgpt": "ChatGPT",
    "gemini": "Gemini",
    "cloudflare": "Cloudflare",
    "anthropic": "Anthropic",
    "sakana-ai": "Sakana AI",
    "sakana-fugu": "Sakana Fugu",
    "glm-5-2": "GLM 5.2",
    "z-ai": "Z.AI",
    "cometapi": "CometAPI",
    "deepseek": "DeepSeek",
    "kimi-k3": "Kimi K3",
    "qwen": "Qwen",
    "minimax-m3": "MiniMax M3",
    "siliconflow": "SiliconFlow",
    "openrouter": "OpenRouter",
    "antigravity": "Antigravity",
    "harness": "Harness",
    "rc-astro": "RC Astro",
    "mistral-ai": "Mistral AI",
    "openclaw": "OpenClaw",
    "anges-ai": "Anges AI",
    "lushbinary": "LushBinary",
    "apple-silicon": "Apple Silicon",
    "motioner": "Motioner",
    "github": "GitHub",
    "poyin-chen": "PoYin Chen",
    "paul-kuo": "Paul Kuo",
    "newmobilelife": "newmobilelife",
    "inside": "Inside",
    "nous-research": "Nous Research",
}


def is_canonical_slug(slug: str) -> bool:
    """Check if a slug is a known canonical entity name."""
    return slug in CANONICAL_ENTITIES


def set_updated_timestamp(text: str, date_str: str) -> str:
    """
    Set the `updated:` frontmatter field to date_str, inserting it after
    `created:` if the field is missing (a bare re.sub silently no-ops when
    there is nothing to replace, which is how merged pages have been going
    stale without any error surfacing).
    """
    new_text, count = re.subn(r'^updated: .+$', f'updated: {date_str}', text, flags=re.MULTILINE)
    if count > 0:
        return new_text
    new_text, count = re.subn(
        r'(^created: .+$)', rf'\1\nupdated: {date_str}', text, count=1, flags=re.MULTILINE
    )
    if count > 0:
        return new_text
    # No created: field either — insert right after the opening frontmatter delimiter.
    return re.sub(r'^(---\s*\n)', rf'\1updated: {date_str}\n', text, count=1, flags=re.MULTILINE)


def _append_source_to_frontmatter(fm: str, source: str) -> str:
    """
    Append *source* to the frontmatter's `sources:` list, after any existing
    entries — never in the middle of the list.

    The previous version matched only the `sources:` line itself (`.*$` with
    MULTILINE doesn't cross into the following indented `  - "..."` lines),
    so `re.sub` replaced just that one line with `sources:\\n  - "new"`,
    inserting the new entry directly under the header and pushing every
    pre-existing entry down by one line — i.e. the new source landed
    *before* older ones instead of after. On a page whose `sources:` list
    was formatted with unusual spacing this also produced non-YAML-parsable
    frontmatter, which is a distinct (and worse) bug: every downstream
    frontmatter reader used elsewhere in this codebase splits content on the
    first two `---` occurrences, so once the frontmatter block itself is
    malformed, `title`/`canonical`/`tags`/etc. silently stop being visible
    as metadata to any of them.
    """
    lines = fm.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == 'sources: []':
            lines[i] = f'sources:\n  - "{source}"'
            return '\n'.join(lines)
        if stripped.startswith('sources:'):
            j = i + 1
            while j < len(lines) and lines[j].startswith(' '):
                if source in lines[j]:
                    return fm  # already present
                j += 1
            lines.insert(j, f'  - "{source}"')
            return '\n'.join(lines)
    return fm.rstrip('\n') + f'\nsources:\n  - "{source}"'


def canonical_slug_from_name(name: str) -> Optional[str]:
    """
    Given a raw entity name, return the canonical slug if it matches.

    Examples:
        "Hermes Agent"          → "hermes-agent"
        "hermes-agent-learn-ai"  → "hermes-agent" (contains canonical slug)
        "Claude Code"           → "claude-code"
        "random topic"          → None

    2026-07-19 fix: when a long title mentions several canonical entities,
    prefer whichever occurs EARLIEST in the normalized name, not whichever
    happens to be enumerated first in CANONICAL_ENTITIES. Titles conventionally
    lead with their primary subject — e.g. a capture titled "Kimi K3 ...
    tested inside Claude Code" is primarily about Kimi, with Claude Code only
    the incidental test harness mentioned later. The old first-in-dict
    behavior merged that capture straight into claude-code.md instead of a
    Kimi page, because "claude-code" happened to be enumerated before
    whichever entity actually led the title.
    """
    normalized = normalize_entity_name(name)
    if not normalized:
        return None

    # Direct match
    if normalized in CANONICAL_ENTITIES:
        return normalized

    # Prefer the canonical slug that appears earliest in the title.
    best_slug, best_pos = None, None
    for slug in CANONICAL_ENTITIES:
        pos = normalized.find(slug)
        if pos != -1 and (best_pos is None or pos < best_pos):
            best_slug, best_pos = slug, pos
    if best_slug:
        return best_slug

    # Fallback: the normalized name itself is a substring of a longer
    # canonical slug (e.g. a short/partial name close to the canonical spelling).
    for slug in CANONICAL_ENTITIES:
        if normalized in slug:
            return slug

    return None

# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------

# Patterns to strip from entity names
_STRIP_PREFIXES = [
    re.compile(r'^\d{4}-\d{2}-\d{2}[-_]'),          # 2026-06-14 date prefix
    re.compile(r'^\d{10,}[-_]'),                      # Unix timestamp prefix: 202606081207_
    re.compile(r'^\d{8,9}[-_]'),                      # YYYYMMDD or shorter: 20260608_
    re.compile(r'^\d{6,}[-_]'),                       # Any 6+ digit prefix: 00001_
    re.compile(r'-on-[a-z]+$', re.I),                # -on-youtube, -on-instagram suffix
    re.compile(r'-\d{6,}$'),                           # trailing timestamp: -20260614
    re.compile(r'^re:?\s+', re.I),                   # re: reply prefix
    re.compile(r'^(post|thread|tweet|video|article)[:\s]', re.I),
]

# Platform/topic junk to remove
_JUNK_PATTERNS = [
    re.compile(r'\bgithub\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+', re.I),  # GitHub URLs
    re.compile(r'\b[a-z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),      # email addresses
    re.compile(r'[\U0001F300-\U0001F9FF]'),                             # emoji
    re.compile(r'#\w+'),                                                # hashtags
    re.compile(r'@\w+'),                                                # @mentions
]


def normalize_entity_name(name: str) -> str:
    """
    Normalize an entity name to a consistent slug.
    
    Examples:
        "Claude Code"           → "claude-code"
        "claude-code"           → "claude-code"
        "2026-06-14-Claude-Code" → "claude-code"
        "202606081207_00001-claude-code" → "claude-code"
        "claude-code-on-youtube" → "claude-code"
        "零基礎GitHub教學"       → "ji-chu-gitg-jiao-xue"
    
    Rules applied in order:
    1. Unicode normalization (NFKC)
    2. Strip known prefixes (dates, timestamps, "re:", platform suffixes)
    3. Convert to lowercase
    4. Replace non-alphanumeric runs with single hyphen
    5. Strip leading/trailing hyphens
    """
    if not name:
        return ""

    # NFKC normalization — expands CJK compatibility chars
    name = unicodedata.normalize('NFKC', name)

    # Remove junk patterns first
    for pattern in _JUNK_PATTERNS:
        name = pattern.sub('', name)

    # Strip prefixes
    for pattern in _STRIP_PREFIXES:
        name = pattern.sub('', name)

    # Remove anything in parentheses (e.g., "(step-by-step)")
    name = re.sub(r'\([^)]*\)', '', name)

    # Lowercase
    name = name.lower().strip()

    # Replace Chinese/punctuation runs with hyphen
    # CJK characters → treat as word boundaries
    name = re.sub(r'[\s_]+', '-', name)  # spaces/underscores → hyphen
    name = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', name)  # CamelCase → hyphen
    name = re.sub(r'([a-zA-Z0-9])([\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af])', r'\1-\2', name)  # latin → CJK boundary
    name = re.sub(r'([\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af])([a-zA-Z0-9])', r'\1-\2', name)  # CJK → latin boundary

    # Remove all non-alphanumeric and non-hyphen chars EXCEPT CJK
    # (preserve CJK so slugs like 五星飯店南洋吃到飽 remain meaningful)
    name = re.sub(r'[^a-z0-9\-\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]', '', name)

    # Collapse multiple hyphens
    name = re.sub(r'-+', '-', name)

    # Strip leading/trailing hyphens
    name = name.strip('-')

    return name


def extract_entity_name_from_path(filepath: Path) -> str:
    """
    Extract a meaningful entity name from a wiki file path.
    
    Examples:
        wiki/entities/2026-06-14-claude-code.md → "claude-code"
        wiki/entities/my-obsidian-vault.md     → "my-obsidian-vault"
        wiki/concepts/docker-best-practices.md  → "docker-best-practices"
    """
    name = filepath.stem  # filename without extension
    return normalize_entity_name(name)


def extract_entity_name_from_title(frontmatter_title: str) -> str:
    """Extract entity name from the title: field in frontmatter."""
    return normalize_entity_name(frontmatter_title)


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

def read_frontmatter(filepath: Path) -> tuple[dict, str]:
    """
    Read frontmatter from a wiki file.
    
    Returns (fm_dict, body_content).
    fm_dict: keys are str, values may be str or list
    body_content: everything after the closing ---
    """
    content = filepath.read_text(encoding='utf-8')
    return parse_frontmatter(content)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Parse frontmatter from markdown content string.
    
    Returns (fm_dict, body_content).
    """
    fm = {}
    lines = content.split('\n')
    n = len(lines)

    if not lines or lines[0].strip() != '---':
        return fm, content

    # Find closing ---
    i = 1
    while i < n:
        stripped = lines[i].strip()
        if stripped == '---' or stripped.startswith('---#') or stripped.startswith('--- '):
            break
        # Parse key: value
        if ':' in stripped:
            key, _, val = stripped.partition(':')
            key = key.strip()
            val = val.strip()
            if val.startswith('['):
                # Inline list: ["a", "b"] or ['a', 'b'] or [tag1, tag2]
                fm[key] = parse_yaml_list(val)
            elif val:
                fm[key] = parse_yaml_list(val)
            else:
                fm[key] = ""
        i += 1

    body = '\n'.join(lines[i+1:]) if i < n else ''
    return fm, body.strip()


def update_frontmatter_field(filepath: Path, key: str, value: str, list_mode: bool = False) -> None:
    """
    Update or add a field in a wiki file's frontmatter.
    
    If list_mode=True, appends to existing list or creates new list.
    Otherwise replaces the value.
    """
    content = filepath.read_text(encoding='utf-8')
    lines = content.split('\n')
    n = len(lines)

    if not lines or lines[0].strip() != '---':
        # No frontmatter — prepend
        new_lines = ['---', f'{key}: {value}', '---', ''] + lines
        filepath.write_text('\n'.join(new_lines), encoding='utf-8')
        return

    # Find frontmatter boundaries
    fm_end = None
    for i in range(1, n):
        stripped = lines[i].strip()
        if stripped == '---' or stripped.startswith('---#') or stripped.startswith('--- '):
            fm_end = i
            break

    if fm_end is None:
        return

    # Look for existing key
    key_line = None
    for i in range(1, fm_end):
        stripped = lines[i].strip()
        if stripped.startswith(f'{key}:'):
            key_line = i
            break

    if key_line is not None:
        if list_mode:
            # Append to existing inline list
            old_val = lines[key_line].strip()
            if old_val.rstrip(',').endswith(']'):
                # Already a list — append
                lines[key_line] = old_val.rstrip(']') + f', {value}]'
            else:
                lines[key_line] = f'{key}: [{value}]'
        else:
            lines[key_line] = f'{key}: {value}'
    else:
        # Insert before closing ---
        lines.insert(fm_end, f'{key}: {value}')

    filepath.write_text('\n'.join(lines), encoding='utf-8')


def append_to_body(filepath: Path, section_title: str, content: str) -> None:
    """
    Append a new section to the body of a wiki file.
    
    Adds a heading and content, separated by blank lines.
    """
    existing = filepath.read_text(encoding='utf-8')
    if existing and not existing.endswith('\n'):
        existing += '\n'
    existing += f'\n\n## {section_title}\n\n{content}\n'
    filepath.write_text(existing, encoding='utf-8')


def add_source_to_frontmatter(filepath: Path, source_path: str) -> None:
    """Add a source path to the sources: list in frontmatter."""
    if not source_path:
        return
    # Read existing frontmatter
    fm, body = read_frontmatter(filepath)
    
    existing_sources = fm.get('sources', '[]')
    
    # Parse existing list
    if existing_sources.startswith('['):
        # Inline YAML list — append to it
        # Remove trailing ]
        sources_content = existing_sources.rstrip(']').strip()
        if sources_content.endswith('['):
            new_sources = sources_content + f'"{source_path}"]'
        else:
            new_sources = sources_content + f', "{source_path}"]'
    else:
        new_sources = f'["{source_path}"]'
    
    # Write back with updated sources — remove all duplicates, keep one
    lines = filepath.read_text(encoding='utf-8').split('\n')
    new_lines: list[str] = []
    sources_written = False
    for line in lines:
        if line.strip().startswith('sources:'):
            if not sources_written:
                new_lines.append(f'sources: {new_sources}')
                sources_written = True
        else:
            new_lines.append(line)
    filepath.write_text('\n'.join(new_lines), encoding='utf-8')


# ---------------------------------------------------------------------------
# Entity registry
# ---------------------------------------------------------------------------

class EntityRegistry:
    """
    Index of all existing entities in the wiki.
    
    Phase 6: now supports canonical entity pages (no date prefix).
    Canonical pages (e.g., entities/hermes-agent.md) are indexed by their
    canonical slug AND by their filename. Date-prefixed pages are still
    indexed for backward compatibility but will be merged into canonical
    pages over time.
    """

    def __init__(self, wiki_root: Path):
        """
        Initialize registry by scanning all wiki/entities/ and wiki/concepts/ files.
        
        Args:
            wiki_root: Path to the wiki/ directory (contains entities/ and concepts/)
        """
        self.wiki_root = wiki_root
        self.entities_dir = wiki_root / 'entities'
        self.concepts_dir = wiki_root / 'concepts'

        # Map: normalized_name → file path (includes both canonical + filename-based)
        self._name_to_path: dict[str, Path] = {}
        
        # Map: file path → normalized name
        self._path_to_name: dict[Path, str] = {}
        
        # Phase 6: canonical slug → canonical page path
        self._canonical_to_path: dict[str, Path] = {}

        self._scan()

    def _scan(self) -> None:
        """Scan wiki directories and build the name index + canonical index."""
        count = 0
        canonical_count = 0
        for directory in [self.entities_dir, self.concepts_dir]:
            if not directory.exists():
                continue
            for filepath in directory.glob('*.md'):
                # Phase 6: detect canonical pages (no date prefix)
                stem = filepath.stem
                if is_canonical_slug(stem):
                    self._canonical_to_path[stem] = filepath
                    self._name_to_path[stem] = filepath
                    self._path_to_name[filepath] = stem
                    canonical_count += 1
                else:
                    # Legacy: index by filename stem (with normalization)
                    name = extract_entity_name_from_path(filepath)
                    if name:
                        self._name_to_path[name] = filepath
                        self._path_to_name[filepath] = name
                count += 1

        logger.info(
            f'EntityRegistry: indexed {count} total, '
            f'{canonical_count} canonical from {self.wiki_root}'
        )

    def count(self) -> int:
        """Return number of indexed entities."""
        return len(self._name_to_path)

    def canonical_count(self) -> int:
        """Return number of canonical entity pages."""
        return len(self._canonical_to_path)

    def find_entity_match(self, name: str) -> Optional[Path]:
        """
        Find if an entity already exists in the wiki.
        
        Phase 6: checks in this order:
        1. Canonical entities first (by slug match)
        2. Direct filename-stem match
        3. Fuzzy match on overlapping word parts
        
        Args:
            name: Entity name (raw, from filename, or LLM-extracted)
        
        Returns:
            Path to existing wiki file, or None if not found.
        """
        normalized = normalize_entity_name(name)
        if not normalized:
            return None

        # 1. Check canonical entities first (Phase 6)
        canonical_slug = canonical_slug_from_name(name)
        if canonical_slug and canonical_slug in self._canonical_to_path:
            logger.debug(f'Canonical match: {name} → {canonical_slug}')
            return self._canonical_to_path[canonical_slug]

        # 2. Direct filename-stem match
        if normalized in self._name_to_path:
            return self._name_to_path[normalized]
        
        # 3. Partial match (fuzzy): check overlapping word parts
        name_parts = set(normalized.split('-'))
        
        for indexed_name, path in self._name_to_path.items():
            indexed_parts = set(indexed_name.split('-'))
            if len(name_parts) >= 2 and len(indexed_parts) >= 2:
                overlap = len(name_parts & indexed_parts)
                if overlap >= min(len(name_parts), len(indexed_parts)) * 0.6:
                    logger.debug(f'Fuzzy match: {name} → {indexed_name} ({path.name})')
                    return path
        
        return None

    def get_all_entity_names(self) -> list[str]:
        """Return all indexed entity names (normalized)."""
        return list(self._name_to_path.keys())

    def get_canonical_names(self) -> list[str]:
        """Return all canonical entity slugs."""
        return list(self._canonical_to_path.keys())

    def entity_exists(self, name: str) -> bool:
        """Return True if entity with this name exists."""
        return self.find_entity_match(name) is not None

    def get_or_create_canonical_path(self, slug: str, page_type: str = 'entity') -> Path:
        """
        Get the path for a canonical entity page, creating it if it doesn't exist.
        
        This is the key Phase 6 method: instead of creating date-prefixed pages,
        we create/reuse {canonical-slug}.md in the appropriate directory.
        """
        if slug in self._canonical_to_path:
            return self._canonical_to_path[slug]

        target_dir = self.entities_dir if page_type == 'entity' else self.concepts_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        canonical_path = target_dir / f'{slug}.md'
        self._canonical_to_path[slug] = canonical_path
        self._name_to_path[slug] = canonical_path
        self._path_to_name[canonical_path] = slug

        return canonical_path

    def update_or_create(
        self,
        entity_name: str,
        new_content: str,
        source_path: str = '',
        page_type: str = 'entity',
        use_canonical: bool = True,
    ) -> dict:
        """
        Merge new content into existing entity page, or create a new one.
        
        Phase 6: if use_canonical=True and the entity name matches a canonical
        entity, writes to the canonical page (no date prefix) instead of
        creating a date-prefixed page.
        
        Args:
            entity_name: Canonical name for the entity (from LLM or filename)
            new_content: Distilled wiki body content to add
            source_path: Path to the original raw source file
            page_type: 'entity' or 'concept'
            use_canonical: If True, use canonical page when name matches
        
        Returns:
            dict with keys: action ('updated'|'created'|'noop'), path, entity_name
        """
        from datetime import datetime
        
        slug = normalize_entity_name(entity_name)
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Phase 6: Check for canonical match
        canonical_slug = canonical_slug_from_name(entity_name) if use_canonical else None
        
        if canonical_slug and canonical_slug in self._canonical_to_path:
            # --- MERGE into existing canonical page ---
            existing_path = self._canonical_to_path[canonical_slug]
            logger.info(f'Canonical merge: {entity_name} → {existing_path.name}')
            
            self._append_capture(existing_path, entity_name, new_content, source_path, today)
            
            return {
                'action': 'updated',
                'path': existing_path,
                'entity_name': canonical_slug,
                'source': source_path,
            }

        # Find existing match (non-canonical or canonical page to create)
        existing_path = self.find_entity_match(entity_name)
        
        if existing_path:
            # --- MERGE: update existing page ---
            logger.info(f'Entity deduplication: merge {entity_name} → {existing_path.name}')
            
            if source_path:
                add_source_to_frontmatter(existing_path, source_path)
            self._append_capture(existing_path, entity_name, new_content, source_path, today)
            
            return {
                'action': 'updated',
                'path': existing_path,
                'entity_name': entity_name,
                'source': source_path,
            }
        
        # Phase 6: Create canonical page if name matches
        if canonical_slug:
            canonical_path = self.get_or_create_canonical_path(canonical_slug, page_type)
            self._write_canonical_page(canonical_path, entity_name, new_content, source_path, today, page_type)
            logger.info(f'Canonical create: {entity_name} → {canonical_path.name}')
            return {
                'action': 'created',
                'path': canonical_path,
                'entity_name': canonical_slug,
                'source': source_path,
            }
        
        # --- CREATE: new page (date-prefixed, legacy behavior) ---
        target_dir = self.entities_dir if page_type == 'entity' else self.concepts_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f'{today}-{slug}.md'
        new_path = target_dir / filename
        if new_path.exists():
            import hashlib
            filename = f'{today}-{slug}-{hashlib.md5(entity_name.encode()).hexdigest()[:6]}.md'
            new_path = target_dir / filename
        
        content_lines = [
            '---',
            f'title: {entity_name}',
            f'created: {today}',
            f'updated: {today}',
            f'type: {page_type}',
            f'sources: ["{source_path}"]' if source_path else 'sources: []',
            'confidence: medium',
            '---',
            '',
            new_content,
        ]
        new_path.write_text('\n'.join(content_lines), encoding='utf-8')
        self._name_to_path[slug] = new_path
        self._path_to_name[new_path] = slug
        
        return {
            'action': 'created',
            'path': new_path,
            'entity_name': slug,
            'source': source_path,
        }

    def _append_capture(self, path: Path, title: str, content: str, source: str, date_str: str) -> None:
        """Append a capture entry to an existing wiki page body."""
        from personalkm.frontmatter import join_frontmatter, split_frontmatter

        existing = path.read_text(encoding='utf-8')
        fm, body = split_frontmatter(existing)
        if fm is not None:
            # Update updated date
            fm = set_updated_timestamp(fm, date_str)

            # Add source if provided and not already present
            if source and source not in existing:
                fm = _append_source_to_frontmatter(fm, source)

            # No "---" divider here (unlike the old behavior): a literal
            # "---" inside the body is indistinguishable from a
            # frontmatter delimiter to every reader in this codebase
            # that splits content on the first two "---" occurrences —
            # one stray body divider is enough to permanently orphan
            # this page's real frontmatter as unparsed text the next
            # time anything re-parses it.
            body = body.rstrip() + f'\n\n### {title} ({date_str})\n\n{content}\n'
            path.write_text(join_frontmatter(fm, body), encoding='utf-8')
            return

        # No frontmatter — append directly (no "---" divider, same reason)
        with path.open('a', encoding='utf-8') as f:
            f.write(f'\n\n### {title} ({date_str})\n\n{content}\n')

    def _write_canonical_page(self, path: Path, title: str, content: str, source: str, date_str: str, page_type: str) -> None:
        """Write initial content to a new canonical entity page."""
        source_line = f'  - "{source}"' if source else '  - "initial"'
        text = f"""---
title: {title}
canonical: true
created: {date_str}
updated: {date_str}
type: {page_type}
sources:
{source_line}
confidence: medium
---

{content}
"""
        path.write_text(text, encoding='utf-8')

    def suggest_entity_name(self, content_snippet: str, existing_names: list[str]) -> str:
        """
        Given content and list of existing entity names, suggest a name for this content.
        
        Uses simple heuristics: prefer the longest meaningful phrase that doesn't
        overlap significantly with existing names.
        """
        # Strip markdown formatting
        text = re.sub(r'#+ ', '', content_snippet)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        text = re.sub(r'[*_`]', '', text)
        
        # Look for CamelCase words (likely proper nouns)
        camel = re.findall(r'[A-Z][a-z]+(?:[A-Z][a-z]+)+', text)
        
        # Look for hashtags (without the #)
        tags = re.findall(r'#([a-zA-Z0-9_-]+)', text)
        
        candidates = []
        
        for word in camel + tags:
            norm = normalize_entity_name(word)
            # Skip if too short or too generic
            if len(norm) < 3:
                continue
            if norm in ('topic', 'post', 'video', 'article', 'thread'):
                continue
            candidates.append((len(norm), norm, word))
        
        # Sort by length descending (prefer longer, more specific names)
        candidates.sort(reverse=True)
        
        for _, norm, original in candidates:
            # Check it's not already heavily overlapping
            existing_norms = [normalize_entity_name(n) for n in existing_names]
            overlaps = sum(1 for en in existing_norms if norm in en or en in norm)
            if overlaps == 0:
                return original
        
        # Fallback: first CamelCase or first tag
        return camel[0] if camel else (tags[0] if tags else 'unknown')
