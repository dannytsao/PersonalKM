"""
Knowledge Decay Detection System
Identifies outdated tech notes and generates monthly decay reports.
Focus: DevOps & AI topics
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"


def openai_client() -> OpenAI:
    return OpenAI()

# Configuration
CURRENT_THRESHOLD_DAYS = 90  # 3 months = current
FRESHNESS_LEVELS = {
    "CRITICAL": 180,    # 6+ months = critical
    "HIGH": 120,        # 4-6 months = high
    "MEDIUM": 90,       # 3-4 months = medium
    "EVERGREEN": 0,     # Always fresh
}

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


def calculate_freshness_level(days_old: int) -> tuple[str, int]:
    """Calculate freshness level (0-100, where 100 is fresh)."""
    if days_old <= CURRENT_THRESHOLD_DAYS:
        return "EVERGREEN", 100
    elif days_old <= FRESHNESS_LEVELS["MEDIUM"]:
        score = 100 - int((days_old / FRESHNESS_LEVELS["MEDIUM"]) * 50)
        return "MEDIUM", score
    elif days_old <= FRESHNESS_LEVELS["HIGH"]:
        score = 50 - int(((days_old - FRESHNESS_LEVELS["MEDIUM"]) / FRESHNESS_LEVELS["HIGH"]) * 40)
        return "HIGH", score
    else:
        return "CRITICAL", max(0, 10 - int((days_old - FRESHNESS_LEVELS["HIGH"]) / 30))


def get_note_metadata(note_path: Path) -> dict:
    """Extract metadata from note."""
    try:
        content = note_path.read_text()
        
        # Get file creation/modification time
        mtime = note_path.stat().st_mtime
        created_date = datetime.fromtimestamp(mtime)
        days_old = (datetime.now() - created_date).days
        
        # Extract title
        title = note_path.stem
        if content.startswith("---"):
            # Has frontmatter
            parts = content.split("---")
            if len(parts) >= 3:
                body = parts[2]
            else:
                body = content
        else:
            body = content
        
        # Detect topic
        content_lower = content.lower()
        is_devops = any(kw in content_lower for kw in DEVOPS_KEYWORDS)
        is_ai = any(kw in content_lower for kw in AI_KEYWORDS)
        
        freshness_level, score = calculate_freshness_level(days_old)
        
        return {
            "path": str(note_path),
            "title": title,
            "created_date": created_date.isoformat(),
            "days_old": days_old,
            "freshness_level": freshness_level,
            "freshness_score": score,
            "is_devops": is_devops,
            "is_ai": is_ai,
            "content_preview": content[:200],
        }
    except Exception as e:
        logger.error(f"Error extracting metadata from {note_path}: {e}")
        return None


def detect_version_references(content: str) -> list[str]:
    """Detect version numbers and framework references."""
    versions = []
    
    # DevOps versions
    import re
    patterns = {
        "Docker": r"docker[:\s]+v?(\d+\.\d+\.\d+)",
        "Kubernetes": r"k8s|kubernetes[:\s]+v?(\d+\.\d+)",
        "Node.js": r"node[:\s]+v?(\d+\.\d+)",
        "Python": r"python[:\s]+(\d+\.\d+)",
        "Go": r"go[:\s]+(\d+\.\d+)",
        "Terraform": r"terraform[:\s]+v?(\d+\.\d+)",
        "PostgreSQL": r"postgres[:\s]+(\d+)",
        "GPT": r"gpt[:\s]*(4|3\.5|turbo)",
        "Claude": r"claude[:\s]*(3\.5|3|2)",
        "PyTorch": r"torch[:\s]+(\d+\.\d+)",
    }
    
    for framework, pattern in patterns.items():
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            versions.append(f"{framework}: {', '.join(matches)}")
    
    return versions


def analyze_with_ai(note_path: Path, metadata: dict) -> dict:
    """Use AI to analyze if note is outdated."""
    try:
        content = note_path.read_text()
        
        analysis_topics = []
        if metadata["is_devops"]:
            analysis_topics.append("DevOps practices, tools, versions")
        if metadata["is_ai"]:
            analysis_topics.append("AI/LLM frameworks, models, best practices")
        
        if not analysis_topics:
            return {"is_outdated": False, "reason": "Not a DevOps/AI note"}
        
        prompt = f"""Analyze this {', '.join(analysis_topics)} note and determine if it's outdated.
        
Note Age: {metadata['days_old']} days old
Title: {metadata['title']}

Content (first 500 chars):
{content[:500]}

Respond ONLY with JSON (no other text):
{{
    "is_outdated": true/false,
    "severity": "CRITICAL|HIGH|MEDIUM|LOW",
    "outdated_aspects": ["aspect1", "aspect2"],
    "suggested_updates": ["update1", "update2"],
    "related_topics": ["topic1", "topic2"]
}}"""
        
        response = openai_client().chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=300,
        )
        
        output = response.choices[0].message.content.strip()
        
        # Extract JSON
        start = output.find('{')
        end = output.rfind('}') + 1
        
        if start < 0 or end <= start:
            return {"is_outdated": False, "reason": "Could not parse AI response"}
        
        analysis = json.loads(output[start:end])
        return analysis
        
    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        return {"is_outdated": False, "reason": str(e)}


def add_deprecation_notice(note_path: Path, analysis: dict) -> bool:
    """Add deprecation notice to note if outdated."""
    try:
        content = note_path.read_text()
        
        # Check if already has notice
        if "⚠️ DEPRECATED" in content or "🔴 OUTDATED" in content:
            return True
        
        severity_icon = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢",
        }
        
        icon = severity_icon.get(analysis.get("severity", "MEDIUM"), "🟡")
        
        notice = f"""{icon} **DECAY NOTICE**
- Status: {analysis.get("severity", "UNKNOWN")}
- Detected: {datetime.now().strftime('%Y-%m-%d')}
- Issues: {', '.join(analysis.get('outdated_aspects', ['unknown']))}
- Action: {', '.join(analysis.get('suggested_updates', ['review']))}
---

"""
        
        # Insert after frontmatter if exists
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                updated = parts[0] + "---" + parts[1] + "---\n" + notice + parts[2]
            else:
                updated = notice + content
        else:
            updated = notice + content
        
        note_path.write_text(updated)
        logger.info(f"✅ Added decay notice to {note_path.name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add deprecation notice: {e}")
        return False


def scan_vault(vault_path: Path) -> dict:
    """Scan entire vault for decay analysis."""
    results = {
        "critical": [],
        "high": [],
        "medium": [],
        "evergreen": [],
        "total_notes": 0,
        "scan_date": datetime.now().isoformat(),
    }
    
    # Find all markdown files
    note_files = list(vault_path.rglob("*.md"))
    
    for note_path in note_files:
        # Skip special files
        if note_path.name.startswith(".") or "Trash" in str(note_path):
            continue
        
        results["total_notes"] += 1
        
        # Get metadata
        metadata = get_note_metadata(note_path)
        if not metadata:
            continue
        
        # Only analyze DevOps/AI notes
        if not (metadata["is_devops"] or metadata["is_ai"]):
            continue
        
        # AI analysis
        analysis = analyze_with_ai(note_path, metadata)
        metadata.update(analysis)
        
        # Add to appropriate level
        level = metadata["freshness_level"]
        if level == "CRITICAL":
            results["critical"].append(metadata)
        elif level == "HIGH":
            results["high"].append(metadata)
        elif level == "MEDIUM":
            results["medium"].append(metadata)
        else:
            results["evergreen"].append(metadata)
        
        # Add deprecation notice if outdated
        if analysis.get("is_outdated"):
            add_deprecation_notice(note_path, analysis)
    
    return results


def generate_report(vault_path: Path, report_path: Path) -> bool:
    """Generate monthly decay report."""
    try:
        logger.info("Scanning vault for knowledge decay...")
        results = scan_vault(vault_path)
        
        report = f"""# Monthly Knowledge Decay Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 📊 Summary
- Total notes scanned: {results['total_notes']}
- Critical (needs update): {len(results['critical'])}
- High (update soon): {len(results['high'])}
- Medium (review): {len(results['medium'])}
- Evergreen (current): {len(results['evergreen'])}

---

## 🔴 CRITICAL (Update within 1-2 weeks)

"""
        
        for note in results["critical"][:10]:  # Top 10
            report += f"""
### {note['title']}
- Age: {note['days_old']} days
- Path: `{note['path']}`
- Status: {note.get('severity', 'UNKNOWN')}
- Issues: {', '.join(note.get('outdated_aspects', ['review needed']))}
- Suggested: {', '.join(note.get('suggested_updates', ['update content']))}

"""
        
        report += f"""
---

## 🟠 HIGH (Update within 1 month)

"""
        
        for note in results["high"][:10]:
            report += f"""
### {note['title']}
- Age: {note['days_old']} days
- Status: {note.get('severity', 'UNKNOWN')}

"""
        
        report += f"""
---

## 🟡 MEDIUM (Review next quarter)

Count: {len(results['medium'])} notes

"""
        
        report += f"""
---

## ✅ EVERGREEN (Current & relevant)

Count: {len(results['evergreen'])} notes

These notes cover timeless concepts that remain relevant.

---

## 💡 Recommendations

1. **Immediate**: Address {len(results['critical'])} critical notes
2. **This month**: Plan updates for {len(results['high'])} high-priority notes
3. **Next quarter**: Review {len(results['medium'])} medium-priority notes
4. **Maintain**: {len(results['evergreen'])} evergreen notes are healthy

---

Generated by PersonalKM Knowledge Decay System
"""
        
        report_path.write_text(report)
        logger.info(f"✅ Report generated: {report_path}")
        return True
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return False


# analyze_on_capture was removed — it wrote decay notices to raw/ files
# but these were stripped during ingestion. Decay detection now runs
# on wiki content directly (generate_monthly_report reads wiki frontmatter).
# kept for future use.
