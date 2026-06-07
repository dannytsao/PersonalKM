#!/usr/bin/env python3
"""Test the enrichment module locally."""
import asyncio
import os
import tempfile
from pathlib import Path

# Add repo to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from bot.hermes_enrich import enrich_note

async def test_enrichment():
    """Test enrichment on a sample note."""
    
    # Check OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set!")
        return False
    
    # Create a test note
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""# Artificial Intelligence in 2024

Artificial intelligence has become increasingly powerful, with models like GPT-4 and Claude 
demonstrating remarkable capabilities in code generation, analysis, and reasoning. The field 
is moving towards multi-modal AI with text, image, and audio processing.

Key trends: transformer models, retrieval-augmented generation (RAG), fine-tuning, and 
autonomous agents. Companies are racing to integrate AI into products and services.
""")
        test_file = Path(f.name)
    
    try:
        print(f"📝 Test file: {test_file}")
        print("⏳ Running enrichment...")
        
        result = await enrich_note(test_file)
        
        if result:
            print("✅ Enrichment successful!")
            print("\n📄 Enriched content:\n")
            print(test_file.read_text())
            return True
        else:
            print("❌ Enrichment failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        test_file.unlink()

if __name__ == "__main__":
    success = asyncio.run(test_enrichment())
    exit(0 if success else 1)
