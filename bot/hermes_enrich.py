"""Enrich captured notes using OpenAI directly (no Hermes CLI needed)."""
import json
import logging
import os
from pathlib import Path
from openai import OpenAI
import re

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


async def enrich_note(note_path: Path) -> bool:
    """
    Enrich a note with tags, summary, and concepts.
    For YouTube videos: create structured bullet-point summary.
    For regular content: create one-line summary.
    
    Args:
        note_path: Path to the note file
    
    Returns:
        True if successful, False otherwise
    """
    
    try:
        content = note_path.read_text()
        
        # Detect if this is a YouTube video
        is_youtube = "YouTube 影片逐字稿" in content or "YouTube video transcript" in content
        
        if is_youtube:
            metadata = await _enrich_youtube(content)
        else:
            metadata = await _enrich_regular(content)
        
        if not metadata:
            logger.warning(f"Failed to enrich {note_path.name}")
            return False
        
        # Build frontmatter
        frontmatter = _build_frontmatter(metadata)
        
        # Add frontmatter to note
        enhanced = frontmatter + content
        note_path.write_text(enhanced)
        
        logger.info(f"✅ Enriched {note_path.name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Enrichment failed: {e}")
        return False


async def _enrich_youtube(content: str) -> dict:
    """Extract structured summary from YouTube transcript."""
    try:
        # Extract transcript
        match = re.search(r"YouTube 影片逐字稿[:：]\s*(.+?)(?=---|\Z)", content, re.DOTALL)
        if not match:
            return None
        
        transcript = match.group(1).strip()[:3000]  # First 3000 chars
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": f"""分析這個 YouTube 影片逐字稿，提供結構化的摘要。只返回 JSON，不返回其他文字。

JSON 格式：
{{
    "title": "影片標題",
    "tags": ["標籤1", "標籤2", "標籤3"],
    "key_points": [
        "重點1 - 簡短說明",
        "重點2 - 簡短說明",
        "重點3 - 簡短說明"
    ],
    "main_topics": ["主題1", "主題2"],
    "summary": "一句話摘要"
}}

逐字稿：
{transcript}"""
                }
            ],
            temperature=0.5,
            max_tokens=500
        )
        
        output = response.choices[0].message.content.strip()
        start = output.find('{')
        end = output.rfind('}') + 1
        
        if start < 0 or end <= start:
            logger.warning("No JSON found in YouTube enrichment")
            return None
        
        metadata = json.loads(output[start:end])
        
        # Format key_points as markdown
        key_points = metadata.get('key_points', [])
        if key_points:
            formatted_points = "\n".join([f"- {point}" for point in key_points])
            metadata['summary'] = f"**重點摘要：**\n{formatted_points}"
        
        return metadata
        
    except Exception as e:
        logger.error(f"YouTube enrichment error: {e}")
        return None


async def _enrich_regular(content: str) -> dict:
    """Extract summary from regular web content."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": f"""分析這個網頁內容，只返回 JSON，不返回其他文字。

JSON 格式：
{{
    "tags": ["標籤1", "標籤2"],
    "summary": "一句話摘要",
    "concepts": ["概念1", "概念2"]
}}

內容：
{content[:500]}"""
                }
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        output = response.choices[0].message.content.strip()
        start = output.find('{')
        end = output.rfind('}') + 1
        
        if start < 0 or end <= start:
            logger.warning("No JSON found in regular enrichment")
            return None
        
        return json.loads(output[start:end])
        
    except Exception as e:
        logger.error(f"Regular enrichment error: {e}")
        return None


def _build_frontmatter(metadata: dict) -> str:
    """Build YAML frontmatter from metadata."""
    tags = ', '.join(metadata.get('tags', []))
    summary = metadata.get('summary', '').replace('"', '\\"')
    
    return f"""---
tags: {tags}
summary: "{summary}"
---

"""
