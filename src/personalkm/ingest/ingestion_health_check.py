"""
Post-ingestion health check and validation system.
Ensures data integrity and detects silent failures.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Tuple, List
import re

logger = logging.getLogger(__name__)


class IngestionHealthCheck:
    """Comprehensive validation of ingestion results."""
    
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.raw_path = vault_path / "raw"
        self.wiki_path = vault_path / "wiki"
        self.archive_path = vault_path / "archive"
        self.checks_passed = []
        self.checks_failed = []
        self.warnings = []
    
    def run_all_checks(self) -> Dict:
        """Execute all health checks and return comprehensive report."""
        logger.info("=" * 80)
        logger.info("INGESTION HEALTH CHECK")
        logger.info("=" * 80)
        
        # Core checks
        self.check_raw_folder_empty()
        self.check_wiki_structure()
        self.check_file_counts()
        self.check_frontmatter_samples()
        self.check_index_integrity()
        self.check_log_integrity()
        self.check_knowledge_graph()
        self.check_cross_references()
        
        # Generate report
        report = self._generate_report()
        
        logger.info("\n" + "=" * 80)
        logger.info("HEALTH CHECK COMPLETE")
        logger.info("=" * 80)
        
        return report
    
    def check_raw_folder_empty(self) -> bool:
        """Raw folder should be empty after successful ingestion."""
        raw_md_files = list(self.raw_path.glob("**/*.md"))
        
        if len(raw_md_files) == 0:
            self.checks_passed.append("Raw folder empty ✅")
            return True
        else:
            self.checks_failed.append(
                f"Raw folder NOT empty: {len(raw_md_files)} files remain"
            )
            for f in raw_md_files[:5]:
                self.checks_failed.append(f"  - {f.relative_to(self.raw_path)}")
            if len(raw_md_files) > 5:
                self.checks_failed.append(f"  ... and {len(raw_md_files)-5} more")
            return False
    
    def check_wiki_structure(self) -> bool:
        """Check wiki/ has required subdirectories."""
        required_dirs = ["entities", "concepts"]
        all_exist = True
        
        for dir_name in required_dirs:
            dir_path = self.wiki_path / dir_name
            if dir_path.exists() and dir_path.is_dir():
                self.checks_passed.append(f"Wiki/{dir_name}/ exists ✅")
            else:
                self.checks_failed.append(f"Wiki/{dir_name}/ MISSING ❌")
                all_exist = False
        
        # Check required files
        required_files = ["index.md", "log.md", "knowledge-graph.md", "SCHEMA.md", "QUICKREF.md"]
        for file_name in required_files:
            file_path = self.wiki_path / file_name
            if file_path.exists():
                self.checks_passed.append(f"Wiki/{file_name} exists ✅")
            else:
                self.warnings.append(f"Wiki/{file_name} MISSING (optional)")
        
        return all_exist
    
    def check_file_counts(self) -> Tuple[int, int]:
        """Check entity and concept file counts."""
        entities = list((self.wiki_path / "entities").glob("*.md"))
        concepts = list((self.wiki_path / "concepts").glob("*.md"))
        archived = list(self.archive_path.glob("**/*.md")) if self.archive_path.exists() else []
        
        total_wiki = len(entities) + len(concepts)
        
        logger.info(f"\n[FILE COUNTS]")
        logger.info(f"  Entities: {len(entities)}")
        logger.info(f"  Concepts: {len(concepts)}")
        logger.info(f"  Total wiki: {total_wiki}")
        logger.info(f"  Archived (trashed): {len(archived)}")
        
        # Validate counts
        if total_wiki > 0:
            self.checks_passed.append(f"Wiki files created: {total_wiki} ✅")
        else:
            self.checks_failed.append("NO wiki files created ❌")
        
        if len(entities) > 0:
            self.checks_passed.append(f"Entities: {len(entities)} ✅")
        else:
            self.warnings.append(f"No entities created (only concepts)")
        
        if len(concepts) > 0:
            self.checks_passed.append(f"Concepts: {len(concepts)} ✅")
        else:
            self.warnings.append(f"No concepts created (only entities)")
        
        return len(entities), len(concepts)
    
    def check_frontmatter_samples(self) -> bool:
        """Validate frontmatter on 5 random wiki files."""
        entities = list((self.wiki_path / "entities").glob("*.md"))
        concepts = list((self.wiki_path / "concepts").glob("*.md"))
        all_files = entities[:3] + concepts[:2]  # 3 entities, 2 concepts
        
        if not all_files:
            self.warnings.append("No wiki files to validate")
            return False
        
        valid_count = 0
        for file_path in all_files:
            content = file_path.read_text()
            
            # Check frontmatter exists
            if not content.startswith("---"):
                self.checks_failed.append(f"No frontmatter: {file_path.name}")
                continue
            
            # Extract frontmatter block
            try:
                fm_end = content.find("---", 3)
                if fm_end == -1:
                    self.checks_failed.append(f"Incomplete frontmatter: {file_path.name}")
                    continue
                
                fm_block = content[3:fm_end]
                
                # Validate required fields (per SCHEMA.md: contested/confidence are optional quality signals)
                required_fields = ["title:", "created:", "updated:", "type:", "tags:", "sources:"]
                optional_quality_fields = ["confidence:", "contested:"]
                missing = [f for f in required_fields if f not in fm_block]
                missing_quality = [f for f in optional_quality_fields if f not in fm_block]

                if missing:
                    self.warnings.append(f"Missing fields in {file_path.name}: {missing}")
                elif missing_quality:
                    self.warnings.append(f"Missing optional quality signals in {file_path.name}: {missing_quality}")

                if not missing:
                    valid_count += 1
            except Exception as e:
                self.checks_failed.append(f"Frontmatter parse error in {file_path.name}: {e}")
        
        if valid_count == len(all_files):
            self.checks_passed.append(f"Frontmatter valid: {valid_count}/{len(all_files)} samples ✅")
            return True
        else:
            self.checks_failed.append(f"Frontmatter issues in {len(all_files)-valid_count}/{len(all_files)} samples")
            return False
    
    def check_index_integrity(self) -> bool:
        """Validate index.md structure and content."""
        index_path = self.wiki_path / "index.md"
        
        if not index_path.exists():
            self.checks_failed.append("index.md does not exist ❌")
            return False
        
        content = index_path.read_text()
        
        # Check required sections
        has_header = "# Wiki Index" in content
        has_entities = "## Entities" in content
        has_concepts = "## Concepts" in content
        has_last_updated = "Last updated:" in content
        has_page_count = "Total pages:" in content
        
        checks = {
            "Header": has_header,
            "Entities section": has_entities,
            "Concepts section": has_concepts,
            "Last updated": has_last_updated,
            "Page count": has_page_count,
        }
        
        all_valid = all(checks.values())
        
        if all_valid:
            self.checks_passed.append("index.md structure valid ✅")
            
            # Extract and log page count
            match = re.search(r"Total pages: (\d+)", content)
            if match:
                page_count = int(match.group(1))
                logger.info(f"  Index reports {page_count} total pages")
        else:
            missing = [k for k, v in checks.items() if not v]
            self.checks_failed.append(f"index.md missing: {missing}")
        
        return all_valid
    
    def check_log_integrity(self) -> bool:
        """Validate log.md structure."""
        log_path = self.wiki_path / "log.md"
        
        if not log_path.exists():
            self.checks_failed.append("log.md does not exist ❌")
            return False
        
        content = log_path.read_text()
        lines = content.split("\n")
        
        # Check header
        if "# Wiki Log" not in content:
            self.checks_failed.append("log.md missing header ❌")
            return False
        
        # Count entries (lines starting with "##")
        entries = [l for l in lines if l.startswith("## [")]
        
        if len(entries) > 0:
            self.checks_passed.append(f"log.md has {len(entries)} entries ✅")
            return True
        else:
            self.warnings.append("log.md has no date-stamped entries")
            return True  # Still valid, just empty
    
    def check_knowledge_graph(self) -> bool:
        """Validate knowledge-graph.md (optional).

        2026-07-20: this used to check for emoji-decorated headers
        ("# 📊 Knowledge Graph" / "## 🔗 Entities" / "## 💡 Concepts") that
        personalkm.propagate.knowledge_graph.build_knowledge_graph() has never
        produced — it emits a plain "# Knowledge Graph" title, and its
        "## Canonical Entities" / "## Other Entity Pages" / "## Concepts"
        index sections are each conditional on that category having any
        pages at all, so none of them are safe to require unconditionally.
        This silently failed on every single Phase A run without anyone
        investigating why. Rewritten to check the markers the generator
        actually, unconditionally emits: the title, timestamp, and the
        Mermaid flowchart's two subgraph blocks (always present even when
        empty of nodes).
        """
        kg_path = self.wiki_path / "knowledge-graph.md"

        if not kg_path.exists():
            self.warnings.append("Wiki/knowledge-graph.md MISSING (optional)")
            return True  # Optional, don't fail

        content = kg_path.read_text()

        # Check structure
        has_header = "# Knowledge Graph" in content
        has_mermaid = "```mermaid" in content
        has_subgraphs = "subgraph Entities" in content and "subgraph Concepts" in content
        has_timestamp = "Last updated:" in content

        all_valid = has_header and has_mermaid and has_subgraphs and has_timestamp

        if all_valid:
            self.checks_passed.append("knowledge-graph.md valid ✅")
        else:
            self.checks_failed.append("knowledge-graph.md structure invalid ❌")

        return all_valid
    
    def check_cross_references(self) -> bool:
        """Spot-check wikilinks are properly formatted."""
        entities = list((self.wiki_path / "entities").glob("*.md"))[:3]
        wikilink_pattern = r"\[\[.*?\]\]"
        wikilink_count = 0
        
        for file_path in entities:
            content = file_path.read_text()
            matches = re.findall(wikilink_pattern, content)
            wikilink_count += len(matches)
        
        if wikilink_count > 0:
            self.checks_passed.append(f"Wikilinks found in samples: {wikilink_count} ✅")
            return True
        else:
            self.warnings.append("No wikilinks detected in sample files")
            return False
    
    def _generate_report(self) -> Dict:
        """Compile health check into structured report."""
        passed_count = len(self.checks_passed)
        failed_count = len(self.checks_failed)
        warning_count = len(self.warnings)
        
        overall_status = "healthy" if failed_count == 0 else "degraded"
        
        logger.info(f"\n[SUMMARY]")
        logger.info(f"  ✅ Passed: {passed_count}")
        logger.info(f"  ❌ Failed: {failed_count}")
        logger.info(f"  ⚠️  Warnings: {warning_count}")
        logger.info(f"  Status: {overall_status}")
        
        if self.checks_failed:
            logger.info(f"\n[FAILURES]")
            for check in self.checks_failed:
                logger.error(f"  {check}")
        
        if self.warnings:
            logger.info(f"\n[WARNINGS]")
            for warning in self.warnings:
                logger.warning(f"  {warning}")
        
        return {
            "status": overall_status,
            "checks_passed": passed_count,
            "checks_failed": failed_count,
            "warnings": warning_count,
            "details": {
                "passed": self.checks_passed,
                "failed": self.checks_failed,
                "warnings": self.warnings,
            }
        }
