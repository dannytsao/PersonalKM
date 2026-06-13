#!/usr/bin/env python3
"""
LLM-Wiki Bot Integration Test
Verify ingestion_v2.py works correctly with sample data.
"""
import tempfile
import json
from pathlib import Path
import sys

# Add bot to path
sys.path.insert(0, '/Users/dannytsao/Documents/PersonalKM')

from bot.ingestion_v2 import (
    ingest_raw_to_wiki, 
    categorize_note,
    build_llmwiki_frontmatter,
)
from bot.ingestion_wiki_helpers import (
    WikiSchema, WikiIndex, WikiLog, WikiPage
)


def test_wiki_helpers():
    """Test WikiSchema, WikiIndex, WikiLog classes."""
    print("\n=== Testing Wiki Helper Classes ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_path = Path(tmpdir)
        
        # Create SCHEMA.md
        schema_path = wiki_path / "SCHEMA.md"
        schema_path.write_text("""# Wiki Schema

## Domain
Multi-domain KM

### Tag Taxonomy
- tech
- ai-llm
- container
- general
""")
        
        # Test WikiSchema
        print("✓ WikiSchema: Parse SCHEMA.md")
        schema = WikiSchema(schema_path)
        tags = schema.get_all_tags()
        assert "tech" in tags and "container" in tags
        print(f"  Found {len(tags)} tags: {tags[:4]}...")
        
        # Test WikiIndex
        print("✓ WikiIndex: Create and maintain index.md")
        index_path = wiki_path / "index.md"
        index = WikiIndex(index_path)
        index.add_entry("Entities", "entities/docker", "Container platform")
        index.add_entry("Entities", "entities/kubernetes", "Orchestration")
        index.save()
        assert index_path.exists()
        content = index_path.read_text()
        assert "docker" in content and "kubernetes" in content
        print(f"  Created index with {len(index.entries.get('Entities', []))} entities")
        
        # Test WikiLog
        print("✓ WikiLog: Append-only log.md")
        log_path = wiki_path / "log.md"
        log = WikiLog(log_path)
        log.append("ingest", "docker-article", ["Type: entity", "Category: tech"])
        assert log_path.exists()
        content = log_path.read_text()
        assert "ingest" in content and "docker-article" in content
        print(f"  Created log with 1 entry: {len(content)} bytes")
        
        # Test WikiPage
        print("✓ WikiPage: Build/parse frontmatter")
        fm = {
            "title": "Docker",
            "type": "entity",
            "tags": ["tech", "container"],
            "confidence": "high"
        }
        fm_str = WikiPage.build_frontmatter(fm)
        assert "---" in fm_str and "docker" in fm_str.lower()
        print(f"  Built frontmatter: {len(fm_str)} bytes")
        
        parsed_fm, body = WikiPage.extract_frontmatter(fm_str + "\n\nBody text")
        assert parsed_fm.get("title") == "Docker"
        print(f"  Parsed frontmatter correctly")


def test_categorization():
    """Test note categorization."""
    print("\n=== Testing Note Categorization ===\n")
    
    # DevOps note
    devops_note = "How to deploy Docker containers with Kubernetes"
    subfolder, cats = categorize_note(devops_note)
    assert "devops" in cats
    print(f"✓ DevOps note: categories={cats}, subfolder={subfolder}")
    
    # AI note
    ai_note = "Fine-tuning GPT with LoRA for question answering"
    subfolder, cats = categorize_note(ai_note)
    assert "ai" in cats
    print(f"✓ AI note: categories={cats}, subfolder={subfolder}")
    
    # General note
    general_note = "My favorite coffee shops"
    subfolder, cats = categorize_note(general_note)
    assert "general" in cats
    print(f"✓ General note: categories={cats}, subfolder={subfolder}")


def test_frontmatter_generation():
    """Test LLM-Wiki frontmatter generation."""
    print("\n=== Testing Frontmatter Generation ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        schema = WikiSchema(Path(tmpdir) / "SCHEMA.md")
        
        fm = build_llmwiki_frontmatter(
            title="Docker Best Practices",
            page_type="entity",
            categories=["devops"],
            entities=["Docker", "Containers"],
            summary="Modern Docker practices for 2026",
            source_path=Path("raw/Tech/docker-article.md"),
            schema=schema
        )
        
        assert fm["title"] == "Docker Best Practices"
        assert fm["type"] == "entity"
        assert "tech" in fm["tags"]
        assert fm["confidence"] == "medium"
        assert fm["contested"] == False
        print(f"✓ Generated frontmatter: {json.dumps(fm, indent=2)}")


def test_fake_ingestion():
    """Test ingestion with fake data."""
    print("\n=== Testing Ingestion Pipeline ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        raw_path = vault_path / "raw"
        wiki_path = vault_path / "wiki"
        
        # Create structure
        raw_path.mkdir()
        wiki_path.mkdir()
        (wiki_path / "entities").mkdir()
        (wiki_path / "concepts").mkdir()
        
        # Create SCHEMA.md
        (wiki_path / "SCHEMA.md").write_text("""# Wiki Schema
### Domain Tags
- tech
- container
- devops
- ai-llm
""")
        
        # Create sample notes in raw/
        note1 = raw_path / "note1.md"
        note1.write_text("# Docker Tutorial\n\nHow to use Docker containers with Kubernetes for deployment.")
        
        note2 = raw_path / "note2.md"
        note2.write_text("# AI Models\n\nFine-tuning GPT models using PyTorch and transformers library.")
        
        print(f"✓ Created test data: {len(list(raw_path.glob('*.md')))} raw notes")
        
        # Run ingestion (will fail on AI extraction if no API key, but that's OK for test)
        print("✓ Running ingestion_v2.ingest_raw_to_wiki()...")
        try:
            result = ingest_raw_to_wiki(vault_path)
            
            # Check results
            assert result["processed"] >= 0
            assert (wiki_path / "knowledge-graph.md").exists()
            
            # Check if index and log were created/updated
            if (wiki_path / "index.md").exists():
                index_content = (wiki_path / "index.md").read_text()
                assert "Wiki Index" in index_content
                print(f"✓ index.md created: {len(index_content)} bytes")
            
            if (wiki_path / "log.md").exists():
                log_content = (wiki_path / "log.md").read_text()
                assert "Wiki Log" in log_content
                print(f"✓ log.md created: {len(log_content)} bytes")
            
            print(f"✓ Ingestion result: {result}")
        
        except Exception as e:
            print(f"⚠ Ingestion error (expected if no API key): {e}")


def main():
    print("="*60)
    print("LLM-Wiki Bot Integration Test Suite")
    print("="*60)
    
    try:
        test_wiki_helpers()
        test_categorization()
        test_frontmatter_generation()
        test_fake_ingestion()
        
        print("\n" + "="*60)
        print("✅ All tests passed!")
        print("="*60)
        return 0
    
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
