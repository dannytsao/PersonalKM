"""
LLM-Wiki Integration Helpers
Maintains index.md, log.md, and wiki navigation for PersonalKM bot ingestion.
"""
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Dict

logger = logging.getLogger(__name__)


class ContentQualityChecker:
    """Check if raw content meets minimum quality thresholds."""
    
    # Minimum content requirements
    MIN_BODY_LINES = 3  # At least 3 lines of actual content (not frontmatter)
    MIN_BODY_CHARS = 100  # At least 100 characters of meaningful content
    MIN_SUMMARY_CHARS = 30  # Summary should be meaningful (not stub placeholders)
    
    # Patterns that indicate low-quality stubs
    LOW_QUALITY_PATTERNS = [
        r'等待驗證',  # waiting for verification
        r'please wait for verification',
        r'正在加載',  # loading
        r'loading',
        r'no content',
        r'empty page',
        r'error loading',
        r'page not found',
        r'not found',
        r'404',
        r'access denied',
        r'このページは',  # this page (placeholder JP)
    ]
    
    LOW_QUALITY_SUMMARIES = [
        'placeholder',
        'stub',
        'incomplete',
        '沒有提供具體',  # no concrete info provided
        '沒有具體',  # no concrete
        '無法獲取',  # unable to fetch
        '暫時無法',  # temporarily unable
    ]
    
    @staticmethod
    def get_body_content(file_path: Path) -> tuple:
        """Extract body content (excluding frontmatter)."""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Split frontmatter and body
            lines = content.split('\n')
            in_frontmatter = False
            body_lines = []
            
            for line in lines:
                if line.strip() == '---':
                    in_frontmatter = not in_frontmatter
                    continue
                if not in_frontmatter:
                    body_lines.append(line)
            
            body = '\n'.join(body_lines).strip()
            return body, len(body)
        except Exception as e:
            return '', 0
    
    @staticmethod
    def get_summary(file_path: Path) -> str:
        """Extract summary field from frontmatter."""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Parse YAML frontmatter
            if not content.startswith('---'):
                return ''
            
            lines = content.split('\n')
            in_frontmatter = True
            
            for line in lines[1:]:
                if line.strip() == '---':
                    break
                if line.startswith('summary:'):
                    # Extract summary value
                    summary = line.replace('summary:', '').strip().strip('"\'')
                    return summary
            
            return ''
        except Exception:
            return ''
    
    @classmethod
    def is_low_quality(cls, file_path: Path) -> tuple:
        """
        Check if file is low quality (stub/placeholder).
        Returns: (is_low_quality: bool, reason: str)
        """
        try:
            body, body_chars = cls.get_body_content(file_path)
            
            # Check minimum body length
            if body_chars < cls.MIN_BODY_CHARS:
                return True, f"Body too short ({body_chars} chars, min {cls.MIN_BODY_CHARS})"
            
            # Check body line count
            body_lines = [l for l in body.split('\n') if l.strip()]
            if len(body_lines) < cls.MIN_BODY_LINES:
                return True, f"Body too sparse ({len(body_lines)} lines, min {cls.MIN_BODY_LINES})"
            
            # Check for low-quality patterns in body
            body_lower = body.lower()
            for pattern in cls.LOW_QUALITY_PATTERNS:
                if re.search(pattern, body_lower):
                    return True, f"Contains low-quality pattern: '{pattern}'"
            
            # Check summary
            summary = cls.get_summary(file_path)
            
            if len(summary) < cls.MIN_SUMMARY_CHARS:
                return True, f"Summary too short ({len(summary)} chars, min {cls.MIN_SUMMARY_CHARS})"
            
            # Check for low-quality summary patterns
            summary_lower = summary.lower()
            for pattern in cls.LOW_QUALITY_SUMMARIES:
                if pattern.lower() in summary_lower:
                    return True, f"Summary indicates stub: '{pattern}'"
            
            return False, ""
        
        except Exception as e:
            return True, f"Error checking quality: {str(e)}"


class WikiSchema:
    """Parse and manage wiki/SCHEMA.md tag taxonomy."""
    
    def __init__(self, schema_path: Path):
        self.schema_path = schema_path
        self.taxonomy = self._parse_taxonomy()
    
    def _parse_taxonomy(self) -> Dict[str, List[str]]:
        """Parse SCHEMA.md to extract tag taxonomy."""
        if not self.schema_path.exists():
            logger.warning(f"SCHEMA.md not found at {self.schema_path}")
            return self._default_taxonomy()
        
        try:
            content = self.schema_path.read_text()
            taxonomy = {}
            
            # Split by sections and parse tags
            lines = content.split('\n')
            current_category = None
            tags_buffer = []
            
            for line in lines:
                # Detect category headers (### Name)
                if line.startswith('###'):
                    # Save previous category if exists
                    if current_category and tags_buffer:
                        taxonomy[current_category] = tags_buffer
                    
                    current_category = line.replace('###', '').strip()
                    tags_buffer = []
                
                # Detect tag lines (- tag or - `tag` with optional description)
                elif line.strip().startswith('-') and current_category:
                    # Extract tag name from "- tag" or "- `tag`" or "- tag — description"
                    line = line.strip()[1:].strip()  # Remove leading dash
                    
                    # Remove description if present (text after —)
                    if ' —' in line or ' -' in line:
                        line = line.split(' —')[0].split(' -')[0].strip()
                    
                    # Remove backticks if present
                    tag = line.strip('`').strip()
                    
                    if tag and tag.isidentifier():
                        tags_buffer.append(tag)
            
            # Don't forget last category
            if current_category and tags_buffer:
                taxonomy[current_category] = tags_buffer
            
            return taxonomy if taxonomy else self._default_taxonomy()
        
        except Exception as e:
            logger.error(f"Failed to parse SCHEMA.md: {e}")
            return self._default_taxonomy()
    
    def _default_taxonomy(self) -> Dict[str, List[str]]:
        """Fallback taxonomy from SCHEMA.md defaults."""
        return {
            "Domain": ["tech", "food", "photography", "general"],
            "Topic": ["hermes-agent", "ai-llm", "container", "web-dev", "travel", "productivity", "learning"],
            "Quality": ["decay-flagged", "needs-verification", "wip", "controversial", "evergreen"],
            "Processing": ["from-line", "from-youtube", "from-article", "ai-summarized", "auto-tagged", "manual-curated"]
        }
    
    def get_all_tags(self) -> List[str]:
        """Return flat list of all valid tags."""
        tags = []
        for category_tags in self.taxonomy.values():
            tags.extend(category_tags)
        return tags
    
    def validate_tags(self, tags: List[str]) -> Tuple[List[str], List[str]]:
        """Validate tags against taxonomy. Return (valid, invalid)."""
        all_valid = self.get_all_tags()
        valid = [t for t in tags if t in all_valid]
        invalid = [t for t in tags if t not in all_valid]
        return valid, invalid


class WikiIndex:
    """Maintain wiki/index.md."""
    
    def __init__(self, index_path: Path):
        self.index_path = index_path
        self.entries = self._parse_index()
    
    def _parse_index(self) -> Dict[str, List[Tuple[str, str]]]:
        """Parse index.md into sections."""
        sections = {}
        
        if not self.index_path.exists():
            return {"Entities": [], "Concepts": [], "Comparisons": [], "Queries": []}
        
        try:
            content = self.index_path.read_text()
            current_section = None
            
            for line in content.split('\n'):
                if line.startswith('## '):
                    current_section = line[3:].strip()
                    if current_section not in sections:
                        sections[current_section] = []
                elif current_section and line.startswith('- [['):
                    # Parse "- [[path/slug]] — summary"
                    match = re.match(r'- \[\[([^\]]+)\]\] — (.+)', line)
                    if match:
                        path = match.group(1)
                        summary = match.group(2).strip()
                        sections[current_section].append((path, summary))
            
            return sections if sections else {"Entities": [], "Concepts": [], "Comparisons": [], "Queries": []}
        
        except Exception as e:
            logger.error(f"Failed to parse index.md: {e}")
            return {"Entities": [], "Concepts": [], "Comparisons": [], "Queries": []}
    
    def add_entry(self, section: str, path: str, summary: str, overwrite: bool = False) -> bool:
        """Add entry to index. Return True if added/updated, False if duplicate."""
        if section not in self.entries:
            self.entries[section] = []
        
        # Check if already exists
        for i, (existing_path, existing_summary) in enumerate(self.entries[section]):
            if existing_path == path:
                if overwrite:
                    self.entries[section][i] = (path, summary)
                    logger.info(f"Updated index entry: {path}")
                    return True
                else:
                    logger.debug(f"Entry already exists: {path}")
                    return False
        
        
        # Add new entry (keep alphabetical within section)
        self.entries[section].append((path, summary))
        self.entries[section].sort(key=lambda x: x[0].lower())
        logger.info(f"Added index entry: {path}")
        return True
    
    def remove_entry(self, path: str) -> bool:
        """Remove entry from index."""
        for section in self.entries:
            original_len = len(self.entries[section])
            self.entries[section] = [(p, s) for p, s in self.entries[section] if p != path]
            if len(self.entries[section]) < original_len:
                logger.info(f"Removed index entry: {path}")
                return True
        return False
    
    def save(self):
        """Write index.md to disk."""
        try:
            content = "# Wiki Index\n\n"
            content += "> Content catalog. Every wiki page listed under its type with a one-line summary.\n"
            content += f"> Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
            
            total_pages = sum(len(entries) for entries in self.entries.values())
            content += f"Total pages: {total_pages}\n\n"
            
            for section in ["Entities", "Concepts", "Comparisons", "Queries"]:
                content += f"## {section}\n\n"
                
                if self.entries.get(section):
                    for path, summary in self.entries[section]:
                        content += f"- [[{path}]] — {summary}\n"
                else:
                    content += "(None yet)\n"
                
                content += "\n"
            
            self.index_path.write_text(content)
            logger.info(f"Saved index.md ({total_pages} pages)")
        
        except Exception as e:
            logger.error(f"Failed to save index.md: {e}")


class WikiLog:
    """Maintain wiki/log.md append-only action log."""
    
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.max_entries = 500
    
    def append(self, action: str, subject: str, details: Optional[List[str]] = None):
        """Append action to log."""
        try:
            # Ensure log exists
            if not self.log_path.exists():
                self.log_path.write_text("# Wiki Log\n\n> Append-only action log.\n\n")
            
            content = self.log_path.read_text()
            
            # Count existing entries
            entry_count = content.count("## [")
            
            # Rotate if needed
            if entry_count >= self.max_entries:
                self._rotate_log()
                content = self.log_path.read_text()
            
            # Build new entry
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = f"\n## [{timestamp}] {action} | {subject}\n"
            
            if details:
                for detail in details:
                    entry += f"- {detail}\n"
            
            # Append
            content += entry
            self.log_path.write_text(content)
            logger.info(f"Logged: {action} | {subject}")
        
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
    
    def _rotate_log(self):
        """Rotate log when it exceeds max_entries."""
        try:
            year = datetime.now().strftime("%Y")
            rotated_name = f"log-{year}.md"
            rotated_path = self.log_path.parent / rotated_name
            
            # Move current log
            if self.log_path.exists():
                current = self.log_path.read_text()
                
                # Append to rotated version if it exists
                if rotated_path.exists():
                    rotated = rotated_path.read_text()
                    rotated_path.write_text(rotated + current)
                else:
                    rotated_path.write_text(current)
            
            # Start fresh log
            header = "# Wiki Log\n\n> Append-only action log. Rotated after 500 entries.\n\n"
            self.log_path.write_text(header)
            logger.info(f"Rotated log to {rotated_name}")
        
        except Exception as e:
            logger.error(f"Failed to rotate log: {e}")


class WikiPage:
    """Represent a wiki page with frontmatter."""
    
    @staticmethod
    def extract_frontmatter(content: str) -> Tuple[Dict, str]:
        """Extract YAML frontmatter and body."""
        if not content.startswith("---"):
            return {}, content
        
        try:
            parts = content.split("---", 2)
            if len(parts) < 3:
                return {}, content
            
            fm_text = parts[1]
            body = parts[2].lstrip('\n')
            
            fm = {}
            for line in fm_text.split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    key = key.strip()
                    val = val.strip()
                    
                    # Parse JSON values
                    if val.startswith('['):
                        try:
                            fm[key] = json.loads(val)
                        except:
                            fm[key] = val
                    else:
                        fm[key] = val
            
            return fm, body
        
        except Exception as e:
            logger.error(f"Failed to extract frontmatter: {e}")
            return {}, content
    
    @staticmethod
    def build_frontmatter(fm: Dict) -> str:
        """Build YAML frontmatter string."""
        lines = ["---"]
        
        # Order keys for consistency
        key_order = ["title", "created", "updated", "type", "tags", "sources", "confidence", "contested", "contradictions"]
        
        for key in key_order:
            if key in fm and fm[key]:
                val = fm[key]
                if isinstance(val, list):
                    lines.append(f"{key}: {json.dumps(val)}")
                elif isinstance(val, bool):
                    lines.append(f"{key}: {str(val).lower()}")
                else:
                    lines.append(f"{key}: {val}")
        
        lines.append("---")
        return '\n'.join(lines)
    
    @staticmethod
    def extract_body_summary(content: str, max_length: int = 80) -> str:
        """Extract one-line summary from page body."""
        _, body = WikiPage.extract_frontmatter(content)
        
        # Remove markdown formatting
        body = re.sub(r'^#+\s+', '', body, flags=re.MULTILINE)
        body = re.sub(r'[*_`\[\]()]', '', body)
        
        # Get first non-empty line
        for line in body.split('\n'):
            line = line.strip()
            if line and not line.startswith('>'):
                return line[:max_length]
        
        return "(No summary)"
    
    @staticmethod
    def extract_wikilinks(content: str) -> List[str]:
        """Extract all [[wikilinks]] from content."""
        matches = re.findall(r'\[\[([^\]]+)\]\]', content)
        return matches
    
    @staticmethod
    def add_wikilink(content: str, target: str) -> str:
        """Add a wikilink to content if not already present."""
        existing_links = WikiPage.extract_wikilinks(content)
        
        if target in existing_links:
            return content
        
        # Add to end of body (after frontmatter)
        _, body = WikiPage.extract_frontmatter(content)
        
        if not body.rstrip().endswith('\n'):
            body += "\n"
        
        body += f"\nSee also: [[{target}]]\n"
        
        return content.replace(body.lstrip('\n'), body.lstrip('\n'), 1)


def find_related_pages(wiki_path: Path, keywords: List[str], page_type: Optional[str] = None) -> List[Tuple[str, str]]:
    """Find pages that mention given keywords. Return [(path, title)]."""
    related = []
    
    if page_type:
        search_path = wiki_path / page_type
    else:
        search_path = wiki_path
    
    if not search_path.exists():
        return []
    
    try:
        for md_file in search_path.glob("*.md"):
            if md_file.name in ["SCHEMA.md", "index.md", "log.md", "knowledge-graph.md", "QUICKREF.md"]:
                continue
            
            content = md_file.read_text().lower()
            
            for kw in keywords:
                if kw.lower() in content:
                    rel_path = f"{page_type}/{md_file.stem}" if page_type else md_file.stem
                    title = WikiPage.extract_body_summary(md_file.read_text())
                    related.append((rel_path, title))
                    break
        
        return list(set(related))  # Deduplicate
    
    except Exception as e:
        logger.error(f"Failed to find related pages: {e}")
        return []


def integrate_wikilinks(wiki_path: Path, page_type: str, page_title: str, keywords: List[str]):
    """Add wikilinks between related pages."""
    try:
        page_path = wiki_path / page_type / f"{page_title}.md"
        if not page_path.exists():
            return
        
        content = page_path.read_text()
        
        # Find related pages
        for keyword in keywords[:5]:  # Limit to 5 keywords
            related = find_related_pages(wiki_path, [keyword], None)
            
            for rel_path, rel_title in related[:2]:  # Link to 2 related pages max
                if rel_path != f"{page_type}/{page_title}":
                    content = WikiPage.add_wikilink(content, rel_path)
        
        page_path.write_text(content)
        logger.info(f"Added wikilinks to {page_type}/{page_title}md")
    
    except Exception as e:
        logger.error(f"Failed to integrate wikilinks: {e}")
