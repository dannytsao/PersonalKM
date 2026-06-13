"""
Enhanced Ingestion System with LLM-Wiki Integration
Processes raw/ → wiki/ with index.md and log.md maintenance
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List

# Import helper classes
try:
    from bot.ingestion_wiki_helpers import (
        WikiSchema, WikiIndex, WikiLog, WikiPage, 
        find_related_pages, integrate_wikilinks, ContentQualityChecker
    )
except ImportError:
    from ingestion_wiki_helpers import (
        WikiSchema, WikiIndex, WikiLog, WikiPage,
        find_related_pages, integrate_wikilinks, ContentQualityChecker
    )

# Only import OpenAI if needed
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)

# Initialize OpenAI with API key from environment
if OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key) if api_key else None
else:
    client = None

MODEL = "gpt-4o-mini"

# Configuration
DEVOPS_KEYWORDS = [
    "docker", "kubernetes", "k8s", "container", "helm",
    "terraform", "cloudformation", "ansible", "vagrant",
    "github actions", "gitlab ci", "jenkins", "circleci",
    "prometheus", "grafana", "elk", "datadog", "newrelic",
    "aws", "gcp", "azure", "digitalocean", "heroku",
    "nginx", "apache", "load balancer", "cdn", "vpc",
    "ci/cd", "devops", "infrastructure", "deployment",
]

AI_KEYWORDS = [
    "gpt", "claude", "llm", "large language model",
    "transformer", "bert", "rag", "retrieval",
    "pytorch", "tensorflow", "keras", "huggingface",
    "openai", "anthropic", "mistral", "llama",
    "fine-tune", "quantization", "qlora", "lora",
    "embeddings", "vector", "semantic search",
    "prompt", "chain of thought", "reasoning",
    "agent", "tool use", "function calling",
]


def categorize_note(content: str) -> Tuple[str, List[str]]:
    """Determine if note is DevOps/AI and return category."""
    content_lower = content.lower()
    
    is_devops = any(kw in content_lower for kw in DEVOPS_KEYWORDS)
    is_ai = any(kw in content_lower for kw in AI_KEYWORDS)
    
    categories = []
    if is_devops:
        categories.append("devops")
    if is_ai:
        categories.append("ai")
    
    if not categories:
        categories.append("general")
    
    return "concepts" if categories == ["general"] else "entities", categories


def extract_entities_ai(content: str, categories: List[str]) -> dict:
    """Use AI to extract entities from note."""
    if not client:
        logger.warning("OpenAI client not available, using basic extraction")
        return {"entities": [], "relationships": [], "wiki_path": "concepts/general"}
    
    try:
        prompt = f"""Extract key entities from this {', '.join(categories)} note.

Return JSON with:
- entities: [list of frameworks, tools, versions, concepts]
- relationships: [list of related concepts]
- summary: brief summary (one line)
- wiki_path: suggested path like "entities/docker" or "entities/kubernetes"

Content:
{content[:1000]}

Respond ONLY with JSON:"""
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,
        )
        
        msg_content = response.choices[0].message.content
        output = msg_content.strip() if msg_content else ""
        start = output.find('{')
        end = output.rfind('}') + 1
        
        if start < 0 or end <= start:
            return {"entities": [], "relationships": [], "wiki_path": "concepts/general"}
        
        return json.loads(output[start:end])
    except Exception as e:
        logger.error(f"AI extraction failed: {e}")
        return {"entities": [], "relationships": [], "wiki_path": "concepts/general"}


def build_llmwiki_frontmatter(
    title: str,
    page_type: str,
    categories: List[str],
    entities: List[str],
    summary: str,
    source_path: Path,
    schema: WikiSchema
) -> dict:
    """Build LLM-Wiki compliant frontmatter."""
    
    # Map categories to tags
    tags = []
    
    # Add domain tags (always include primary domain)
    if "devops" in categories:
        tags.append("tech")
        tags.append("container")
    if "ai" in categories:
        tags.append("tech")
        tags.append("ai-llm")
    if not tags:
        tags.append("general")
    
    # Validate tags against schema
    valid_tags, _ = schema.validate_tags(tags)
    if not valid_tags:
        valid_tags = ["tech"]
    
    return {
        "title": title,
        "created": datetime.now().strftime("%Y-%m-%d"),
        "updated": datetime.now().strftime("%Y-%m-%d"),
        "type": page_type,
        "tags": valid_tags,
        "sources": [str(source_path)],
        "confidence": "medium",
        "contested": False,
        "contradictions": [],
    }


def organize_note_to_wiki(
    raw_path: Path,
    wiki_path: Path,
    schema: WikiSchema,
    wiki_index: WikiIndex,
    wiki_log: WikiLog
) -> Tuple[bool, Optional[str]]:
    """Move note from raw/ to wiki/ with LLM-Wiki organization."""
    try:
        content = raw_path.read_text()
        
        # Categorize
        subfolder, categories = categorize_note(content)
        
        # Extract entities and metadata
        extraction = extract_entities_ai(content, categories)
        entities = extraction.get("entities", [])
        summary = extraction.get("summary", WikiPage.extract_body_summary(content))
        
        # Create title from filename
        title = raw_path.stem
        
        # Determine destination
        wiki_category_path = wiki_path / subfolder
        wiki_category_path.mkdir(parents=True, exist_ok=True)
        
        dest_name = f"{title}.md"
        dest_path = wiki_category_path / dest_name
        
        # Build llm-wiki frontmatter
        fm = build_llmwiki_frontmatter(title, subfolder.rstrip('s'), categories, entities, summary, raw_path, schema)
        
        # Add frontmatter to content
        fm_str = WikiPage.build_frontmatter(fm)
        full_content = f"{fm_str}\n\n{content}\n"
        
        # Write to wiki
        dest_path.write_text(full_content)
        logger.info(f"✅ Organized {raw_path.name} → {subfolder}/{title}")
        
        # Update index.md
        rel_path = f"{subfolder}/{title}"
        wiki_index.add_entry(subfolder.capitalize(), rel_path, summary, overwrite=True)
        
        # Add wikilinks to related pages
        if entities:
            integrate_wikilinks(wiki_path, subfolder, title, entities[:5])
        
        # Log the action
        wiki_log.append("ingest", title, [f"Type: {subfolder}", f"Categories: {', '.join(categories)}"])
        
        # Remove from raw
        raw_path.unlink()
        
        return True, rel_path
        
    except Exception as e:
        logger.error(f"Failed to organize {raw_path}: {e}")
        return False, None


def build_knowledge_graph(wiki_path: Path) -> str:
    """Generate knowledge graph markdown (backward compatible)."""
    try:
        graph_md = f"""# 📊 Knowledge Graph

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}

"""
        
        # Index entities
        entities_path = wiki_path / "entities"
        if entities_path.exists():
            files = list(entities_path.glob("*.md"))
            
            graph_md += f"""## 🔗 Entities ({len(files)} files)

"""
            for f in sorted(files):
                name = f.stem
                graph_md += f"- **{name}**\n"
            
            graph_md += "\n"
        
        # Index concepts
        concepts_path = wiki_path / "concepts"
        if concepts_path.exists():
            files = list(concepts_path.glob("*.md"))
            
            graph_md += f"""## 💡 Concepts ({len(files)} files)

"""
            for f in sorted(files):
                name = f.stem
                graph_md += f"- {name}\n"
            
            graph_md += "\n"
        
        graph_md += f"""---
Last updated: {datetime.now().isoformat()}
"""
        
        return graph_md
        
    except Exception as e:
        logger.error(f"Graph generation failed: {e}")
        return "# Knowledge Graph\n\n(generation failed)"


def ingest_raw_to_wiki(vault_path: Path) -> dict:
    """Main ingestion: process raw/ and organize to wiki/."""
    try:
        raw_path = vault_path / "raw"
        wiki_path = vault_path / "wiki"
        
        if not raw_path.exists():
            logger.warning("raw/ folder does not exist")
            return {"status": "error", "message": "raw/ folder not found", "processed": 0}
        
        # Initialize wiki helpers
        schema = WikiSchema(wiki_path / "SCHEMA.md")
        wiki_index = WikiIndex(wiki_path / "index.md")
        wiki_log = WikiLog(wiki_path / "log.md")
        
        # Process all files in raw/
        raw_files = list(raw_path.glob("*.md"))
        processed = 0
        failed = 0
        trashed = 0
        created_pages = []
        trashed_files = []
        
        logger.info(f"Starting ingestion: {len(raw_files)} files in raw/")
        
        for note_file in raw_files:
            # Check content quality
            is_low_quality, reason = ContentQualityChecker.is_low_quality(note_file)
            
            if is_low_quality:
                logger.warning(f"Trashing low-quality note: {note_file.name} - {reason}")
                # Move to archive instead of deleting
                archive_path = vault_path / "archive" / note_file.name
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                note_file.rename(archive_path)
                trashed += 1
                trashed_files.append(note_file.name)
                continue
            
            success, page_path = organize_note_to_wiki(note_file, wiki_path, schema, wiki_index, wiki_log)
            if success:
                processed += 1
                if page_path:
                    created_pages.append(page_path)
            else:
                failed += 1
        
        # Save updated index
        wiki_index.save()
        
        # Log batch operation
        if created_pages or trashed_files:
            msg_parts = []
            if processed > 0:
                msg_parts.append(f"Processed: {processed} notes")
            if trashed > 0:
                msg_parts.append(f"Trashed (low-quality): {trashed} notes")
            
            created_msg = [f"Created: {', '.join(created_pages[:5])}" + 
                          (f" (+{len(created_pages)-5} more)" if len(created_pages) > 5 else "")]
            
            trashed_msg = [f"Trashed: {', '.join(trashed_files[:10])}" + 
                          (f" (+{len(trashed_files)-10} more)" if len(trashed_files) > 10 else "")] if trashed_files else []
            
            wiki_log.append("ingest_batch", "; ".join(msg_parts), created_msg + trashed_msg)
        
        # Build knowledge graph (backward compatible)
        graph_content = build_knowledge_graph(wiki_path)
        graph_path = wiki_path / "knowledge-graph.md"
        graph_path.write_text(graph_content)
        
        result = {
            "status": "success",
            "processed": processed,
            "failed": failed,
            "trashed": trashed,
            "total": len(raw_files),
            "created_pages": created_pages,
            "trashed_files": trashed_files,
            "timestamp": datetime.now().isoformat(),
            "graph_updated": True,
            "index_updated": True,
            "log_updated": True,
        }
        
        logger.info(f"✅ Ingestion complete: {processed} processed, {trashed} trashed, {failed} failed")
        return result
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        return {"status": "error", "message": str(e), "processed": 0}


def generate_ingestion_report(vault_path: Path, result: dict) -> str:
    """Generate markdown report of ingestion."""
    report = f"""# Weekly Ingestion Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Summary
- Status: {result.get('status', 'unknown')}
- Processed: {result.get('processed', 0)}
- Failed: {result.get('failed', 0)}
- Total: {result.get('total', 0)}

## Pages Created
"""
    
    created = result.get('created_pages', [])
    if created:
        for page in created[:10]:
            report += f"- `{page}`\n"
        if len(created) > 10:
            report += f"- ... and {len(created) - 10} more\n"
    else:
        report += "(None)\n"
    
    report += f"""
## Infrastructure Updates
- index.md: Updated ✅
- log.md: Updated ✅
- knowledge-graph.md: Updated ✅

## Details
```json
{json.dumps(result, indent=2)}
```

## What Happened
1. Scanned raw/ folder
2. Extracted entities from each note using AI
3. Built LLM-Wiki frontmatter (tags, sources, confidence)
4. Categorized and moved to wiki/ (entities/ or concepts/)
5. Added wikilinks between related pages
6. Updated index.md with page catalog
7. Appended to log.md audit trail
8. Built knowledge-graph.md
9. Committed changes to Git

Next ingestion: 1 week

---
*Integrated with Karpathy LLM-Wiki pattern for knowledge compilation and cross-referencing.*
"""
    return report
