"""Enrich captured notes using OpenAI directly (no Hermes CLI needed)."""
import json
import logging
import os
from pathlib import Path
from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


async def enrich_note(note_path: Path) -> bool:
    """
    Enrich a note with tags, summary, and concepts.
    
    Args:
        note_path: Path to the note file
    
    Returns:
        True if successful, False otherwise
    """
    
    try:
        content = note_path.read_text()
        
        # Ask OpenAI to analyze the note
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": f"""Analyze this note and provide ONLY a JSON object (no other text):
{{
    "tags": ["tag1", "tag2"],
    "summary": "One-line summary",
    "concepts": ["concept1", "concept2"]
}}

Note content:
{content[:500]}"""
                }
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        output = response.choices[0].message.content.strip()
        
        # Parse JSON response
        start = output.find('{')
        end = output.rfind('}') + 1
        
        if start < 0 or end <= start:
            logger.warning("No JSON found in response")
            return False
        
        metadata = json.loads(output[start:end])
        
        # Build frontmatter
        tags = ', '.join(metadata.get('tags', []))
        summary = metadata.get('summary', '')
        
        frontmatter = f"""---
tags: {tags}
summary: "{summary}"
---

"""
        
        # Add frontmatter to note
        enhanced = frontmatter + content
        note_path.write_text(enhanced)
        
        logger.info(f"✅ Enriched {note_path.name}: tags={tags[:50]}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Enrichment failed: {e}")
        return False
