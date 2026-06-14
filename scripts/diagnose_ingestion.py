#!/usr/bin/env python3
"""
Diagnostic ingestion script with verbose logging at every step.
Tests a small sample of files to identify where failures happen.
"""
import json
import logging
import os
import sys
from pathlib import Path

# Setup VERY verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)-8s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Add bot to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from bot.ingestion import (
        ingest_raw_to_wiki, organize_note_to_wiki, extract_entities_ai,
        categorize_note, build_llmwiki_frontmatter
    )
    from bot.ingestion_wiki_helpers import (
        WikiSchema, WikiIndex, WikiLog, WikiPage,
        ContentQualityChecker, RunningLog
    )
except ImportError as e:
    logger.error(f"Failed to import: {e}")
    sys.exit(1)

from openai import OpenAI

def diagnose_sample():
    """Test ingestion on a small sample of files."""
    vault_path = Path(os.getenv("VAULT_PATH", "/Users/dannytsao/Documents/PersonalKM"))
    
    logger.info("=" * 80)
    logger.info("DIAGNOSTIC INGESTION - VERBOSE MODE")
    logger.info(f"Vault path: {vault_path}")
    logger.info("=" * 80)
    
    raw_path = vault_path / "raw"
    wiki_path = vault_path / "wiki"
    
    # 1. Check folders exist
    logger.info(f"\n[1] Checking folders...")
    logger.info(f"    raw/ exists: {raw_path.exists()}")
    logger.info(f"    wiki/ exists: {wiki_path.exists()}")
    
    # 2. List raw files
    logger.info(f"\n[2] Scanning raw/...")
    raw_files = list(raw_path.glob("*.md"))
    logger.info(f"    Found {len(raw_files)} .md files")
    if raw_files:
        logger.info(f"    First 3: {[f.name for f in raw_files[:3]]}")
    
    # 3. Test quality check
    logger.info(f"\n[3] Testing quality checker on first 3 files...")
    sample_files = raw_files[:3]
    for f in sample_files:
        is_low_quality, reason = ContentQualityChecker.is_low_quality(f)
        logger.info(f"    {f.name}")
        logger.info(f"        Low quality: {is_low_quality} (reason: {reason})")
        if not is_low_quality:
            logger.info(f"        Size: {f.stat().st_size} bytes")
            logger.info(f"        First 100 chars: {f.read_text()[:100]}")
    
    # 4. Test categorization
    logger.info(f"\n[4] Testing categorization...")
    for f in sample_files:
        is_low_quality, _ = ContentQualityChecker.is_low_quality(f)
        if not is_low_quality:
            content = f.read_text()
            subfolder, categories = categorize_note(content)
            logger.info(f"    {f.name}")
            logger.info(f"        Subfolder: {subfolder}")
            logger.info(f"        Categories: {categories}")
    
    # 5. Test entity extraction
    logger.info(f"\n[5] Testing AI entity extraction...")
    api_key = os.getenv("OPENAI_API_KEY")
    logger.info(f"    OpenAI API key available: {bool(api_key)}")
    
    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            logger.info(f"    ✅ OpenAI client initialized")
        except Exception as e:
            logger.error(f"    ❌ Failed to init OpenAI: {e}")
            return
    else:
        logger.error(f"    ⚠️  OPENAI_API_KEY not set!")
        return
    
    for f in sample_files[:1]:  # Just test first one
        is_low_quality, _ = ContentQualityChecker.is_low_quality(f)
        if not is_low_quality:
            content = f.read_text()
            subfolder, categories = categorize_note(content)
            logger.info(f"    Extracting from: {f.name}")
            try:
                extraction = extract_entities_ai(content, categories)
                logger.info(f"        ✅ Extraction succeeded")
                logger.info(f"        Result: {json.dumps(extraction, indent=12)}")
            except Exception as e:
                logger.error(f"        ❌ Extraction failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
    
    # 6. Test wiki initialization
    logger.info(f"\n[6] Testing wiki initialization...")
    try:
        schema = WikiSchema(wiki_path / "SCHEMA.md")
        logger.info(f"    ✅ Schema loaded")
    except Exception as e:
        logger.error(f"    ❌ Schema failed: {e}")
        return
    
    try:
        wiki_index = WikiIndex(wiki_path / "index.md")
        logger.info(f"    ✅ Index loaded")
    except Exception as e:
        logger.error(f"    ❌ Index failed: {e}")
        return
    
    try:
        wiki_log = WikiLog(wiki_path / "log.md")
        logger.info(f"    ✅ Log loaded")
    except Exception as e:
        logger.error(f"    ❌ Log failed: {e}")
        return
    
    # 7. Test full organization on one file (NO WRITE, just check path)
    logger.info(f"\n[7] Testing organize_note_to_wiki (dry run)...")
    test_file = None
    for f in sample_files:
        is_low_quality, _ = ContentQualityChecker.is_low_quality(f)
        if not is_low_quality:
            test_file = f
            break
    
    if test_file:
        logger.info(f"    Test file: {test_file.name}")
        logger.info(f"    File exists before: {test_file.exists()}")
        
        # Dry run - just see what would happen
        content = test_file.read_text()
        subfolder, categories = categorize_note(content)
        extraction = extract_entities_ai(content, categories)
        
        title = test_file.stem
        wiki_category_path = wiki_path / subfolder
        dest_path = wiki_category_path / f"{title}.md"
        
        logger.info(f"    Would write to: {dest_path}")
        logger.info(f"    Destination dir exists: {wiki_category_path.exists()}")
        
        # Check if we can write
        try:
            wiki_category_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"    ✅ Can create destination dir")
        except Exception as e:
            logger.error(f"    ❌ Cannot create destination dir: {e}")
            return
        
        # Check frontmatter building
        try:
            fm = build_llmwiki_frontmatter(
                title, subfolder.rstrip('s'), categories,
                extraction.get("entities", []),
                extraction.get("summary", ""),
                test_file, schema
            )
            logger.info(f"    ✅ Frontmatter built:")
            logger.info(f"        {json.dumps(fm, indent=12)}")
        except Exception as e:
            logger.error(f"    ❌ Frontmatter failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return
    
    logger.info(f"\n" + "=" * 80)
    logger.info("DIAGNOSTIC COMPLETE")
    logger.info("=" * 80)

if __name__ == "__main__":
    diagnose_sample()
