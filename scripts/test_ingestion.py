#!/usr/bin/env python3
"""
Test ingestion on a small subset of files.
"""
import json
import logging
import os
import sys
from pathlib import Path
from shutil import rmtree

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)-8s] %(message)s'
)
logger = logging.getLogger(__name__)

# Add bot to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.ingestion import ingest_raw_to_wiki

def test_ingestion():
    """Run ingestion and report results."""
    vault_path = Path(os.getenv("VAULT_PATH", "/Users/dannytsao/Documents/PersonalKM"))
    
    logger.info("=" * 80)
    logger.info("TEST INGESTION")
    logger.info(f"Vault: {vault_path}")
    logger.info("=" * 80)
    
    # Backup existing wiki entities/concepts
    wiki_path = vault_path / "wiki"
    entities_backup = vault_path / "wiki_entities_backup"
    concepts_backup = vault_path / "wiki_concepts_backup"
    
    logger.info("\n[1] Backing up existing wiki entries...")
    if (wiki_path / "entities").exists():
        if entities_backup.exists():
            rmtree(entities_backup)
        (wiki_path / "entities").rename(entities_backup)
        logger.info(f"    ✅ Backed up entities/ → {entities_backup.name}/")
    
    if (wiki_path / "concepts").exists():
        if concepts_backup.exists():
            rmtree(concepts_backup)
        (wiki_path / "concepts").rename(concepts_backup)
        logger.info(f"    ✅ Backed up concepts/ → {concepts_backup.name}/")
    
    # Run ingestion
    logger.info("\n[2] Running ingestion...")
    try:
        result = ingest_raw_to_wiki(vault_path)
        
        logger.info(f"\n[3] Ingestion result:")
        logger.info(f"    Status: {result.get('status', 'unknown')}")
        logger.info(f"    Processed: {result.get('processed', 0)}")
        logger.info(f"    Failed: {result.get('failed', 0)}")
        logger.info(f"    Trashed: {result.get('trashed', 0)}")
        logger.info(f"    Total: {result.get('total', 0)}")
        
        # Count created files
        logger.info(f"\n[4] Checking created wiki files...")
        entities_dir = wiki_path / "entities"
        concepts_dir = wiki_path / "concepts"
        
        entities_files = list(entities_dir.glob("*.md")) if entities_dir.exists() else []
        concepts_files = list(concepts_dir.glob("*.md")) if concepts_dir.exists() else []
        
        logger.info(f"    Entities: {len(entities_files)} files")
        if entities_files:
            logger.info(f"        Sample: {[f.name for f in entities_files[:3]]}")
        
        logger.info(f"    Concepts: {len(concepts_files)} files")
        if concepts_files:
            logger.info(f"        Sample: {[f.name for f in concepts_files[:3]]}")
        
        total_created = len(entities_files) + len(concepts_files)
        logger.info(f"    Total: {total_created} wiki files")
        
        if total_created == 0:
            logger.error("\n❌ PROBLEM: No wiki files were created!")
            logger.error("   Check: bot/ingestion.py organize_note_to_wiki() function")
        else:
            logger.info(f"\n✅ SUCCESS: Created {total_created} wiki files")
        
        # Show running log
        if "log_file" in result:
            logger.info(f"\n[5] Running log: {result['log_file']}")
        
    except Exception as e:
        logger.error(f"\n❌ Ingestion crashed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return
    
    logger.info("\n" + "=" * 80)
    logger.info("TEST COMPLETE")
    logger.info("=" * 80)

if __name__ == "__main__":
    test_ingestion()
