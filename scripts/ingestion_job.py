#!/usr/bin/env python3
"""
Weekly Ingestion Job - Runs Sunday 7 AM UTC+8 via Render Cron
Processes raw/ → wiki/ with LLM-Wiki integration
Includes automatic retry when OpenAI client is unavailable
"""
import json
import logging
import os
import sys
import time
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


# Retry configuration
MAX_RETRIES = 10  # Try for up to 100 minutes (10 retries * 10 min)
RETRY_WAIT = 600  # 10 minutes in seconds
MIN_WAIT = 300    # 5 minutes minimum before first retry


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


def can_connect_to_client() -> bool:
    """Check if OpenAI client is available."""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set, will retry")
            return False
        
        # Quick check - can we import the client?
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        # Try a simple call to verify
        # For now, just check if client initialization succeeds
        logger.info("✅ OpenAI client is available")
        return True
    except Exception as e:
        logger.warning(f"OpenAI client check failed: {e}")
        return False


def main_with_retry():
    """Main ingestion job with automatic retry."""
    logger.info("=" * 80)
    logger.info("WEEKLY INGESTION JOB STARTED (Render Cron - Sunday 7 AM UTC+8)")
    logger.info("=" * 80)
    
    vault_path = get_vault_path()
    logger.info(f"Vault path: {vault_path}")
    
    # Check for client availability and retry if needed
    attempt = 0
    while attempt <= MAX_RETRIES:
        logger.info(f"\n📡 Checking OpenAI client connectivity (attempt {attempt + 1}/{MAX_RETRIES + 1})")
        
        if can_connect_to_client():
            logger.info("✅ Client available, starting ingestion...")
            break
        
        if attempt < MAX_RETRIES:
            # Calculate wait time with initial delay
            wait_time = MIN_WAIT if attempt == 0 else RETRY_WAIT
            logger.warning(f"⏳ Client not available, retrying in {wait_time // 60} minutes...")
            time.sleep(wait_time)
            attempt += 1
        else:
            logger.error("=" * 80)
            logger.error("❌ INGESTION JOB FAILED")
            logger.error("=" * 80)
            logger.error(f"Could not connect to OpenAI after {MAX_RETRIES} retries")
            return 1
    
    # Run ingestion
    logger.info("Starting ingestion: raw/ → wiki/")
    try:
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
            logger.info(f"Trashed (low-quality): {result.get('trashed', 0)}")
            logger.info(f"Failed: {result.get('failed', 0)}")
            logger.info(f"Report: {report_path}")
            if "log_file" in result:
                logger.info(f"Running log: {result['log_file']}")
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
    sys.exit(main_with_retry())
