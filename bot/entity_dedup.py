"""
Entity Deduplication for PersonalKM LLM-Wiki v2

Prevents duplicate wiki pages: when a new capture arrives about an entity
that already has a wiki page, merge into the existing page instead of
creating a new file.

Usage:
    from bot.entity_dedup import EntityRegistry

    registry = EntityRegistry(Path('wiki'))
    print(f'Indexed {registry.count()} entities')

    result = registry.update_or_create(
        entity_name='Claude Code',
        new_content='...',
        source_path='/path/to/raw/file.md',
    )
    print(f'Action: {result["action"]} → {result["path"]}')

Exit Condition:
    from bot.entity_dedup import EntityRegistry
    from pathlib import Path
    registry = EntityRegistry(Path('wiki'))
    print(f'Indexed: {registry.count()} entities')
    match = registry.find_entity_match('claude-code')
    print(f'claude-code → {match}')
    # Should find existing file even with different naming
"""

import logging
import re
import unicodedata
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

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

    # Remove all non-alphanumeric and non-hyphen chars
    name = re.sub(r'[^a-z0-9\-]', '', name)

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
                # Inline list: ["a", "b"] or [tag1, tag2]
                fm[key] = val
            elif val:
                fm[key] = val
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
    
    # Write back with updated sources
    lines = filepath.read_text(encoding='utf-8').split('\n')
    
    # Find and replace sources: line
    for i, line in enumerate(lines):
        if line.strip().startswith('sources:'):
            lines[i] = f'sources: {new_sources}'
            break
    
    filepath.write_text('\n'.join(lines), encoding='utf-8')


# ---------------------------------------------------------------------------
# Entity registry
# ---------------------------------------------------------------------------

class EntityRegistry:
    """
    Index of all existing entities in the wiki.
    
    Built once per ingestion run. Provides O(1) lookup for entity names.
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

        # Map: normalized_name → file path
        self._name_to_path: dict[str, Path] = {}
        
        # Map: file path → normalized name
        self._path_to_name: dict[Path, str] = {}

        self._scan()

    def _scan(self) -> None:
        """Scan wiki directories and build the name index."""
        count = 0
        for directory in [self.entities_dir, self.concepts_dir]:
            if not directory.exists():
                continue
            for filepath in directory.glob('*.md'):
                name = extract_entity_name_from_path(filepath)
                if name:
                    self._name_to_path[name] = filepath
                    self._path_to_name[filepath] = name
                    count += 1

        logger.info(f'EntityRegistry: indexed {count} entities from {self.wiki_root}')

    def count(self) -> int:
        """Return number of indexed entities."""
        return len(self._name_to_path)

    def find_entity_match(self, name: str) -> Optional[Path]:
        """
        Find if an entity already exists in the wiki.
        
        Args:
            name: Entity name (raw, from filename, or LLM-extracted)
        
        Returns:
            Path to existing wiki file, or None if not found.
        """
        normalized = normalize_entity_name(name)
        
        # Direct match
        if normalized in self._name_to_path:
            return self._name_to_path[normalized]
        
        # Partial match: check if any indexed name contains this name or vice versa
        # e.g., "claude-code" matches "claude-code-ai" via fuzzy match
        name_parts = set(normalized.split('-'))
        
        for indexed_name, path in self._name_to_path.items():
            indexed_parts = set(indexed_name.split('-'))
            # High overlap suggests same entity
            if len(name_parts) >= 2 and len(indexed_parts) >= 2:
                overlap = len(name_parts & indexed_parts)
                if overlap >= min(len(name_parts), len(indexed_parts)) * 0.6:
                    logger.debug(f'Fuzzy match: {name} → {indexed_name} ({path.name})')
                    return path
        
        return None

    def get_all_entity_names(self) -> list[str]:
        """Return all indexed entity names (normalized)."""
        return list(self._name_to_path.keys())

    def entity_exists(self, name: str) -> bool:
        """Return True if entity with this name exists."""
        return self.find_entity_match(name) is not None

    def update_or_create(
        self,
        entity_name: str,
        new_content: str,
        source_path: str,
        page_type: str = 'entity',
    ) -> dict:
        """
        Merge new content into existing entity page, or create a new one.
        
        Args:
            entity_name: Canonical name for the entity (from LLM or filename)
            new_content: Distilled wiki body content to add
            source_path: Path to the original raw source file
            page_type: 'entity' or 'concept'
        
        Returns:
            dict with keys: action ('updated'|'created'|'noop'), path, entity_name
        """
        import hashlib
        from datetime import datetime
        
        # Find existing match
        existing_path = self.find_entity_match(entity_name)
        
        if existing_path:
            # --- MERGE: update existing page ---
            logger.info(f'Entity deduplication: merge {entity_name} → {existing_path.name}')
            
            # Add source to frontmatter
            add_source_to_frontmatter(existing_path, source_path)
            
            # Add timestamped section to body
            today = datetime.now().strftime('%Y-%m-%d')
            section = f'Update from {today}\n\n{new_content}'
            append_to_body(existing_path, f'Update {today}', new_content)
            
            return {
                'action': 'updated',
                'path': existing_path,
                'entity_name': entity_name,
                'source': source_path,
            }
        
        # --- CREATE: new entity page ---
        target_dir = self.entities_dir if page_type == 'entity' else self.concepts_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename from entity name
        slug = normalize_entity_name(entity_name)
        today = datetime.now().strftime('%Y-%m-%d')
        filename = f'{today}-{slug}.md'
        new_path = target_dir / filename
        
        # Handle collision
        if new_path.exists():
            filename = f'{today}-{slug}-{hashlib.md5(entity_name.encode()).hexdigest()[:6]}.md'
            new_path = target_dir / filename
        
        # Create frontmatter + body
        content_lines = [
            '---',
            f'title: {entity_name}',
            f'created: {today}',
            f'updated: {today}',
            f'type: {page_type}',
            f'sources: ["{source_path}"]',
            'confidence: medium',
            '---',
            '',
            new_content,
        ]
        
        new_path.write_text('\n'.join(content_lines), encoding='utf-8')
        
        # Register in memory
        self._name_to_path[slug] = new_path
        self._path_to_name[new_path] = slug
        
        logger.info(f'Entity deduplication: created {new_path.name}')
        
        return {
            'action': 'created',
            'path': new_path,
            'entity_name': entity_name,
            'source': source_path,
        }

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
