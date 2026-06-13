#!/usr/bin/env python3
"""
Weekly Ingestion Job - Runs Sunday 9 AM via Render Cron
Processes raw/ → wiki/ with LLM-Wiki integration
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add bot to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from bot.ingestion import ingest_raw_to_wiki, generate_ingestion_report
except ImportError as e:
    logger.error(f"Failed to import ingestion module: {e}")
    sys.exit(1)


def get_vault_path() -> Path:
    """Get vault path from environment or use default."""
    vault_path_str = os.getenv("VAULT_PATH")
    if not vault_path_str:
        logger.error("VAULT_PATH environment variable not set")
        sys.exit(1)
    
    vault_path = Path(vault_path_str)
    if not vault_path.exists():
        logger.error(f"Vault path does not exist: {vault_path}")
        sys.exit(1)
    
    return vault_path


def save_ingestion_report(vault_path: Path, result: dict) -> Path:
    """Save ingestion report to outputs/ingestion-reports/."""
    reports_dir = vault_path / "outputs" / "ingestion-reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d")
    report_path = reports_dir / f"ingestion-{timestamp}.md"
    
    report_content = generate_ingestion_report(vault_path, result)
    report_path.write_text(report_content)
    
    logger.info(f"✅ Ingestion report saved: {report_path}")
    return report_path


def main():
    """Main ingestion job entry point."""
    logger.info("=" * 80)
    logger.info("WEEKLY INGESTION JOB STARTED (Render Cron - Sunday 9 AM)")
    logger.info("=" * 80)
    
    try:
        vault_path = get_vault_path()
        logger.info(f"Vault path: {vault_path}")
        
        # Run ingestion
        logger.info("Starting ingestion: raw/ → wiki/")
        result = ingest_raw_to_wiki(vault_path)
        
        # Log results
        logger.info(f"Ingestion result: {json.dumps(result, indent=2)}")
        
        # Save report
        report_path = save_ingestion_report(vault_path, result)
        
        # Check status
        if result.get("status") == "success":
            logger.info("=" * 80)
            logger.info("✅ INGESTION JOB COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info(f"Processed: {result.get('processed', 0)}")
            logger.info(f"Failed: {result.get('failed', 0)}")
            logger.info(f"Report: {report_path}")
            return 0
        else:
            logger.error("=" * 80)
            logger.error("❌ INGESTION JOB FAILED")
            logger.error("=" * 80)
            logger.error(f"Error: {result.get('message', 'Unknown error')}")
            return 1
    
    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ INGESTION JOB CRASHED")
        logger.error("=" * 80)
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
