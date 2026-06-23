"""
Bidirectional Wikilinks for PersonalKM LLM-Wiki v2

When a new page mentions existing entities, links go BOTH ways:
- New page → existing entities (outbound links)
- Existing entities → new page (backlinks)

Usage:
    from bot.wikilinks import WikilinkManager

    wm = WikilinkManager(Path('wiki'), registry)
    wm.add_bidirectional_links(new_page_path, ['claude-code', 'docker'])
    
    # Or scan an existing page for entities and add links
    wm.link_page_entities(page_path)

Exit Condition:
    # After linking a new page about "claude-code":
    grep -c '\\[\\[' wiki/entities/claude-code.md    # Should be > 0 (has wikilinks)
    grep 'new-page' wiki/entities/*.md | wc -l        # Should be > 0 (got backlinks)
"""

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Valid wiki link pattern: [[slug]] or [[slug|display text]]
_WIKILINK_RE = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')

# Entities that are too generic to link
_IGNORE_ENTITIES = {
    'topic', 'post', 'video', 'article', 'thread', 'page',
    'source', 'summary', 'key-facts', 'related', 'update',
    'today', 'note', 'file', 'content', 'title', 'type',
}


class WikilinkManager:
    """
    Manages bidirectional wikilinks between wiki pages.
    
    Outbound links: When a new page mentions existing entities,
                    those mentions become [[wikilinks]] pointing to the entity pages.
    
    Backlinks:      When a new page is created/updated, all existing pages
                    that mention this new entity get a backlink added.
    """

    def __init__(self, wiki_root: Path, entity_registry=None):
        """
        Args:
            wiki_root: Path to wiki/ directory (contains entities/ and concepts/)
            entity_registry: Optional EntityRegistry for entity-aware linking.
                           If None, uses filename-based matching.
        """
        self.wiki_root = wiki_root
        self.entities_dir = wiki_root / 'entities'
        self.concepts_dir = wiki_root / 'concepts'
        self.entity_registry = entity_registry

    # -------------------------------------------------------------------------
    # Core bidirectional linking
    # -------------------------------------------------------------------------

    def add_bidirectional_links(
        self,
        new_page_path: Path,
        mentioned_entities: list[str],
    ) -> dict:
        """
        Add links in both directions for a newly created/updated page.
        
        Args:
            new_page_path: Path to the new or updated wiki page
            mentioned_entities: List of entity names mentioned in this page
        
        Returns:
            dict with outbound_links and backlinks counts
        """
        if not mentioned_entities:
            return {'outbound': 0, 'backlinks': 0}

        # Normalize entity names
        entity_slugs = []
        for e in mentioned_entities:
            slug = self._normalize(e)
            if slug and slug not in _IGNORE_ENTITIES and len(slug) > 1:
                entity_slugs.append(slug)

        outbound = self._add_outbound_links(new_page_path, entity_slugs)
        backlinks = self._add_backlinks_to_mentioned_entities(new_page_path, entity_slugs)

        logger.info(f'Bidirectional links: {outbound} outbound, {backlinks} backlinks')
        return {'outbound': outbound, 'backlinks': backlinks}

    def _normalize(self, name: str) -> str:
        """Normalize an entity name to a wikilink slug."""
        if not name:
            return ""
        name = name.lower().strip()
        # Remove wikilink brackets if present
        name = re.sub(r'^\[\[+|\]+\$', '', name)
        name = name.replace(' ', '-')
        name = re.sub(r'[^a-z0-9\-_]', '', name)
        name = re.sub(r'-+', '-', name)
        return name.strip('-')

    def _resolve_entity_path(self, slug: str) -> Optional[Path]:
        """
        Resolve a normalized entity slug to an existing wiki file path.
        Checks both entities/ and concepts/ directories.
        """
        # Direct match
        for directory in [self.entities_dir, self.concepts_dir]:
            if not directory.exists():
                continue
            # Try exact slug match
            for f in directory.glob(f'*-{slug}.md'):
                return f
            for f in directory.glob(f'{slug}.md'):
                return f
            # Try without date prefix
            for f in directory.glob('*.md'):
                if self._normalize(f.stem).endswith(slug) or slug in self._normalize(f.stem):
                    return f

        # Fuzzy match via registry
        if self.entity_registry:
            return self.entity_registry.find_entity_match(slug)

        return None

    def _add_outbound_links(self, page_path: Path, entity_slugs: list[str]) -> int:
        """
        Ensure the page has wikilinks to all mentioned entities.
        Adds [[slug]] syntax where missing.
        """
        if not page_path.exists():
            return 0

        content = page_path.read_text(encoding='utf-8')
        original = content

        added = 0
        for slug in entity_slugs:
            # Skip if already linked
            if f'[[{slug}]]' in content or f'[[{slug}|' in content:
                continue

            # Check if entity page exists
            entity_path = self._resolve_entity_path(slug)
            if entity_path is None:
                logger.debug(f'No wiki page for entity: {slug}')
                continue

            # Find a good place to insert the link
            # Pattern: look for entity name mention in text and wrap with wikilink
            content = self._link_entity_mentions(content, slug)

            if content != original:
                added += 1
                original = content

        if content != original:
            page_path.write_text(content, encoding='utf-8')

        return added

    def _link_entity_mentions(self, content: str, slug: str) -> str:
        """
        Find plain-text mentions of an entity in content and convert to wikilinks.
        
        Smart replacement — only converts mentions that aren't already links.
        """
        # Skip body section detection — just find standalone word mentions
        # Look for the slug words appearing as words (not inside [[ ]])
        pattern = re.compile(
            r'(?<!\[\[)(?<!\w)(?<!-)(' + re.escape(slug).replace(r'\-', r'[- ]') + r')(?!\|])(?!\]\})(?!-)(?<!\w)',
            re.IGNORECASE
        )

        def make_link(match):
            original = match.group(0)
            # Already in a wikilink?
            before = content[:match.start()]
            if before.rstrip().endswith('[['):
                return original
            return f'[[{slug}]]'

        new_content = pattern.sub(make_link, content)
        return new_content

    def _add_backlinks_to_mentioned_entities(
        self,
        new_page_path: Path,
        entity_slugs: list[str],
    ) -> int:
        """
        Add backlinks from existing entity pages TO the new page.
        
        When page P mentions entity E, E's page gets a "See also: [[P]]" link.
        """
        if not new_page_path.exists():
            return 0

        new_page_name = new_page_path.stem
        new_page_link = f'[[{new_page_name}]]'
        new_page_dir = new_page_path.parent.name  # 'entities' or 'concepts'

        backlinks_added = 0

        for slug in entity_slugs:
            entity_path = self._resolve_entity_path(slug)
            if entity_path is None:
                continue

            # Don't backlink to self
            if entity_path.resolve() == new_page_path.resolve():
                continue

            content = entity_path.read_text(encoding='utf-8')

            # Skip if already has this backlink
            if new_page_name in content and f'[[{new_page_name}' in content:
                continue

            # Add backlink in "See also" section at end of body
            content = self._append_backlink(content, new_page_link, new_page_name)

            if content != entity_path.read_text(encoding='utf-8'):
                entity_path.write_text(content, encoding='utf-8')
                backlinks_added += 1
                logger.debug(f'Added backlink in {entity_path.name} → {new_page_name}')

        return backlinks_added

    def _append_backlink(self, content: str, link: str, page_name: str) -> str:
        """
        Append a backlink to a page's body.
        
        Looks for a "See also" section, or creates one at the end of body.
        """
        # Split frontmatter
        parts = content.split('---', 2)
        if len(parts) < 3:
            return content

        fm = parts[1]
        body = parts[2]

        # Check if already linked
        if link in body or f'[[{page_name}]]' in body:
            return content

        # Find or create "See also" section
        see_also_marker = '## See also'
        if see_also_marker in body:
            # Append to existing section
            lines = body.split('\n')
            for i in reversed(range(len(lines))):
                if lines[i].strip() and not lines[i].startswith('#'):
                    lines.insert(i + 1, f'- {link}')
                    body = '\n'.join(lines)
                    return fm + '---' + body
            # Fallback: add at end
            body = body.rstrip() + f'\n- {link}\n'
        else:
            # Create new section
            body = body.rstrip()
            if body:
                body += f'\n\n{see_also_marker}\n\n- {link}\n'
            else:
                body = f'\n{see_also_marker}\n\n- {link}\n'

        return fm + '---' + body

    # -------------------------------------------------------------------------
    # Entity extraction and auto-linking
    # -------------------------------------------------------------------------

    def extract_entities_from_page(self, page_path: Path) -> list[str]:
        """
        Extract all wikilink entities from a page's content.
        
        Returns list of entity slugs (without brackets).
        """
        if not page_path.exists():
            return []

        content = page_path.read_text(encoding='utf-8')
        # Strip frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2]

        matches = _WIKILINK_RE.findall(content)
        return [self._normalize(m) for m in matches]

    def link_page_entities(self, page_path: Path) -> dict:
        """
        Find all entity mentions in a page and ensure they're wikilinked.
        
        Also adds backlinks from those entity pages to this page.
        """
        entities = self.extract_entities_from_page(page_path)
        if not entities:
            return {'outbound': 0, 'backlinks': 0}

        return self.add_bidirectional_links(page_path, entities)

    def scan_and_link_page(self, page_path: Path, page_text: str) -> list[str]:
        """
        Extract potential entity names from raw page text (before wiki format)
        and add bidirectional links.
        
        Returns list of entities that were linked.
        """
        # Find CamelCase words (likely entity names)
        camel_entities = re.findall(r'[A-Z][a-z]+(?:[A-Z][a-z]+)+', page_text)
        
        # Find existing wikilinks
        existing = _WIKILINK_RE.findall(page_text)
        
        # Combine and dedupe
        all_entities = list(set(camel_entities + existing))
        
        # Filter
        all_entities = [e for e in all_entities if len(e) > 2 and e.lower() not in _IGNORE_ENTITIES]
        
        if all_entities:
            return self.add_bidirectional_links(page_path, all_entities)['outbound']
        
        return []

    # -------------------------------------------------------------------------
    # Link validation
    # -------------------------------------------------------------------------

    def validate_links(self, page_path: Optional[Path] = None) -> dict:
        """
        Check for broken wikilinks in wiki pages.
        
        Returns dict of {path: [broken_link_slugs]}.
        """
        broken = {}
        all_slugs = set()

        # Build set of all valid slugs
        for directory in [self.entities_dir, self.concepts_dir]:
            if not directory.exists():
                continue
            for f in directory.glob('*.md'):
                slug = self._normalize(f.stem)
                all_slugs.add(slug)
                # Also add date-prefixed slug
                date_match = re.match(r'^\d{4}-\d{2}-\d{2}-(.+)', f.stem)
                if date_match:
                    all_slugs.add(date_match.group(1))

        # Check pages
        if page_path:
            paths_to_check = [page_path]
        else:
            paths_to_check = list(self.entities_dir.glob('*.md')) + list(self.concepts_dir.glob('*.md'))

        for path in paths_to_check:
            if not path.exists():
                continue
            content = path.read_text(encoding='utf-8')
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    content = parts[2]

            links_in_page = _WIKILINK_RE.findall(content)
            page_broken = []
            for link in links_in_page:
                normalized = self._normalize(link)
                if normalized and normalized not in all_slugs:
                    page_broken.append(link)

            if page_broken:
                broken[str(path)] = page_broken

        return broken

    def get_backlinks(self, page_path: Path) -> list[str]:
        """
        Find all pages that link to a given page.
        
        Returns list of paths that have [[page_name]] links.
        """
        if not page_path.exists():
            return []

        page_name = page_path.stem
        backlinks = []

        for directory in [self.entities_dir, self.concepts_dir]:
            if not directory.exists():
                continue
            for f in directory.glob('*.md'):
                if f.resolve() == page_path.resolve():
                    continue
                content = f.read_text(encoding='utf-8')
                if f'[[{page_name}]]' in content or f'[[{page_name}|' in content:
                    backlinks.append(str(f))

        return backlinks

    def get_all_outbound_links(self, page_path: Path) -> list[str]:
        """Get all outbound wikilinks from a page."""
        if not page_path.exists():
            return []

        content = page_path.read_text(encoding='utf-8')
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2]

        return _WIKILINK_RE.findall(content)
