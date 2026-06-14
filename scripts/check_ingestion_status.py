"""
Independent status check tool for PersonalKM.
Provides deep insight into ingestion state without assumptions.
"""
import json
import logging
from pathlib import Path
from datetime import datetime
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def get_ingestion_status(vault_path: Path):
    """Get current ingestion status by inspecting actual state."""
    raw_path = vault_path / "raw"
    wiki_path = vault_path / "wiki"
    archive_path = vault_path / "archive"
    
    status = {
        "timestamp": datetime.now().isoformat(),
        "vault_path": str(vault_path),
    }
    
    # Check raw/ folder
    if raw_path.exists():
        raw_files = list(raw_path.glob("**/*.md"))
        status["raw_files_pending"] = len(raw_files)
        status["raw_status"] = "has_pending_files" if raw_files else "empty"
    else:
        status["raw_files_pending"] = 0
        status["raw_status"] = "folder_missing"
    
    # Check wiki/ structure
    wiki_entities = []
    wiki_concepts = []
    wiki_sources = []
    
    if wiki_path.exists():
        entities_path = wiki_path / "entities"
        concepts_path = wiki_path / "concepts"
        sources_path = wiki_path / "sources"
        
        if entities_path.exists():
            wiki_entities = list(entities_path.glob("*.md"))
        if concepts_path.exists():
            wiki_concepts = list(concepts_path.glob("*.md"))
        if sources_path.exists():
            wiki_sources = list(sources_path.glob("*.md"))
    
    status["wiki_entities"] = len(wiki_entities)
    status["wiki_concepts"] = len(wiki_concepts)
    status["wiki_sources"] = len(wiki_sources)
    status["wiki_total_pages"] = len(wiki_entities) + len(wiki_concepts)
    
    # Check archive
    archived_count = 0
    if archive_path.exists():
        archived_count = len(list(archive_path.glob("**/*.md")))
    status["archived_trashed_files"] = archived_count
    
    # Check key wiki files
    index_exists = (wiki_path / "index.md").exists()
    log_exists = (wiki_path / "log.md").exists()
    schema_exists = (wiki_path / "SCHEMA.md").exists()
    kg_exists = (wiki_path / "knowledge-graph.md").exists()
    
    status["index_exists"] = index_exists
    status["log_exists"] = log_exists
    status["schema_exists"] = schema_exists
    status["knowledge_graph_exists"] = kg_exists
    
    # Read index.md to get reported page count
    if index_exists:
        try:
            content = (wiki_path / "index.md").read_text()
            import re
            match = re.search(r"Total pages: (\d+)", content)
            if match:
                status["index_reports_page_count"] = int(match.group(1))
        except:
            pass
    
    # Read latest ingestion log if exists
    logs_path = vault_path / "outputs" / "ingestion-logs"
    latest_log = None
    if logs_path.exists():
        logs = sorted(logs_path.glob("ingestion-*.log"))
        if logs:
            latest_log = logs[-1]
            status["latest_ingestion_log"] = latest_log.name
            
            try:
                content = latest_log.read_text()
                # Extract result from last line before footer
                if "Result:" in content:
                    lines = content.split("\n")
                    for line in reversed(lines):
                        if line.startswith("Result:"):
                            status["last_log_result"] = line.replace("Result:", "").strip()
                            break
            except:
                pass
    
    return status


def print_status_report(status):
    """Pretty print status report."""
    print("\n" + "=" * 80)
    print("PERSONALKM INGESTION STATUS REPORT")
    print("=" * 80)
    print(f"\nTimestamp: {status.get('timestamp')}")
    print(f"Vault: {status.get('vault_path')}")
    
    print("\n[RAW/ FOLDER STATUS]")
    print(f"  Pending files: {status.get('raw_files_pending', 0)}")
    print(f"  Status: {status.get('raw_status', 'unknown')}")
    
    print("\n[WIKI/ STRUCTURE]")
    print(f"  Entities: {status.get('wiki_entities', 0)} files")
    print(f"  Concepts: {status.get('wiki_concepts', 0)} files")
    print(f"  Sources: {status.get('wiki_sources', 0)} files")
    print(f"  Total wiki pages: {status.get('wiki_total_pages', 0)}")
    
    if status.get('index_reports_page_count'):
        actual = status.get('wiki_total_pages', 0)
        reported = status.get('index_reports_page_count', 0)
        match = "✅" if actual == reported else "❌"
        print(f"  Index reports: {reported} (actual: {actual}) {match}")
    
    print("\n[WIKI FILES]")
    print(f"  index.md: {'✅' if status.get('index_exists') else '❌'}")
    print(f"  log.md: {'✅' if status.get('log_exists') else '❌'}")
    print(f"  SCHEMA.md: {'✅' if status.get('schema_exists') else '❌'}")
    print(f"  knowledge-graph.md: {'✅' if status.get('knowledge_graph_exists') else '❌'}")
    
    print("\n[ARCHIVE]")
    print(f"  Trashed (archived) files: {status.get('archived_trashed_files', 0)}")
    
    print("\n[LATEST INGESTION LOG]")
    if status.get('latest_ingestion_log'):
        print(f"  Log file: {status.get('latest_ingestion_log')}")
        if status.get('last_log_result'):
            print(f"  Result: {status.get('last_log_result')}")
    else:
        print("  No ingestion logs found")
    
    print("\n" + "=" * 80)
    
    # Overall assessment
    print("\n[ASSESSMENT]")
    has_pending = status.get('raw_files_pending', 0) > 0
    has_wiki_pages = status.get('wiki_total_pages', 0) > 0
    
    if has_pending:
        print("⚠️  PENDING: raw/ has unprocessed files")
    elif has_wiki_pages:
        print("✅ HEALTHY: All raw files processed, wiki pages created")
    else:
        print("🔴 ERROR: No wiki pages exist")
    
    print("\n" + "=" * 80 + "\n")


def check_health(vault_path: Path):
    """Run full health check using IngestionHealthCheck class."""
    import sys
    sys.path.insert(0, str(vault_path / "bot"))
    sys.path.insert(0, str(vault_path / "scripts"))
    
    try:
        from ingestion_health_check import IngestionHealthCheck
    except ImportError:
        try:
            from bot.ingestion_health_check import IngestionHealthCheck
        except ImportError:
            logger.error("Cannot import IngestionHealthCheck")
            return {}
    
    health_check = IngestionHealthCheck(vault_path)
    return health_check.run_all_checks()


if __name__ == "__main__":
    vault_path = Path("/Users/dannytsao/Documents/PersonalKM")
    
    # Get basic status
    status = get_ingestion_status(vault_path)
    print_status_report(status)
    
    # Run deep health check if requested
    if len(sys.argv) > 1 and sys.argv[1] == "--deep":
        print("\n[RUNNING DEEP HEALTH CHECK]")
        health = check_health(vault_path)
        print(json.dumps(health, indent=2))
