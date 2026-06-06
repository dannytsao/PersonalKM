# Knowledge Decay Detection System - Implementation Guide

## 📋 Overview

A fully automated system that **detects outdated tech knowledge**, **flags aging notes**, and **generates monthly reports** to keep your wiki current.

**For:** DevOps & AI topics  
**Freshness threshold:** 3 months (current)  
**Handling:** Flag but keep with deprecation notices  
**Reporting:** Monthly digest (1st of month, 9 AM)

---

## 🎯 What It Does

### 1. **Automatic Decay Detection**

Every note gets analyzed for:
- ✅ **Age** — How old is this information?
- ✅ **Versions** — What versions does it reference?
- ✅ **Patterns** — Are the practices still recommended?
- ✅ **Conflicts** — Does it contradict newer information?

### 2. **Freshness Scoring**

```
CRITICAL    🔴  6+ months old         (Update immediately)
HIGH        🟠  4-6 months old        (Update this month)
MEDIUM      🟡  3-4 months old        (Review next quarter)
EVERGREEN   🟢  0-3 months old        (Current & relevant)
```

### 3. **Deprecation Notices**

Outdated notes get automatic notices:
```markdown
🔴 **DECAY NOTICE**
- Status: CRITICAL
- Detected: 2026-06-06
- Issues: Python 3.8 references, old Django ORM
- Action: Update to Python 3.11, new ORM syntax
---
```

### 4. **Monthly Reports**

Generated on **1st of month at 9 AM**:
- Summary of all notes by freshness level
- Top 10 critical notes that need updating
- Suggested updates for each
- Related topics to link

---

## 🏗️ Architecture

```
PersonalKM Bot
    ↓
Note Captured via LINE
    ↓
✨ Enrich (tags + summary)
    ↓
🔍 Analyze (decay detection)
    ├─ Is this DevOps/AI?
    ├─ Extract versions
    ├─ Check against current best practices
    ├─ Add deprecation notice if outdated
    └─ Flag for monthly review
    ↓
Commit to GitHub
    ↓
[Monthly: 1st at 9 AM]
    ├─ Scan entire vault
    ├─ Categorize by freshness
    ├─ Generate report
    └─ Commit to GitHub
```

---

## 📁 Files Created

### `bot/knowledge_decay.py` (12,037 bytes)

**Key functions:**

```python
calculate_freshness_level(days_old: int)
  → Returns freshness level (CRITICAL/HIGH/MEDIUM/EVERGREEN)

detect_version_references(content: str)
  → Finds Docker, Node, Python, Terraform, GPT versions etc.

analyze_with_ai(note_path, metadata)
  → Uses OpenAI to determine if note is outdated
  → Returns severity + suggested updates

add_deprecation_notice(note_path, analysis)
  → Adds 🔴/🟠 notice if outdated

scan_vault(vault_path)
  → Monthly scan of entire vault
  → Categorizes all notes by freshness

generate_report(vault_path, report_path)
  → Creates .decay-report-monthly.md
  → Commits to GitHub
```

### `bot/app.py` (Modified)

Added:
```python
from bot.knowledge_decay import analyze_on_capture
# ... in capture_urls():
await asyncio.to_thread(analyze_on_capture, note_path)
```

Real-time decay checking on every captured note.

### `~/.hermes/scripts/knowledge-decay-monthly.py`

Monthly cron job script. Can be run manually:
```bash
python3 ~/.hermes/scripts/knowledge-decay-monthly.py
```

---

## 📊 Example Report Output

```markdown
# Monthly Knowledge Decay Report
Generated: 2026-07-01 09:00

## Summary
- Total notes scanned: 157
- Critical (needs update): 4
- High (update soon): 12
- Medium (review): 28
- Evergreen (current): 113

## 🔴 CRITICAL (Update within 1-2 weeks)

### Python 3.8 Migration Guide
- Age: 195 days old
- Status: CRITICAL
- Issues: Python 3.8 EOL, old asyncio patterns
- Suggested: Update to Python 3.11, new async/await

### Kubernetes 1.22 Setup
- Age: 210 days old
- Status: CRITICAL
- Issues: K8s 1.22 deprecated, v1.28 current
- Suggested: Update manifests to latest API versions

### React Hooks Patterns
- Age: 189 days old
- Status: CRITICAL
- Issues: React 18/19 changes, old patterns
- Suggested: Update examples to latest React

### Docker Build Best Practices
- Age: 198 days old
- Status: CRITICAL
- Issues: Old Dockerfile optimization patterns
- Suggested: Modernize with BuildKit, new best practices

## 🟠 HIGH (Update within 1 month)

[12 notes listed]

## 🟡 MEDIUM (Review next quarter)

Count: 28 notes

## ✅ EVERGREEN (Current & relevant)

Count: 113 notes

---

Recommendations:
1. Immediate: Fix 4 critical notes
2. This month: Plan updates for 12 high-priority notes
3. Next quarter: Review 28 medium notes
4. Maintain: 113 evergreen notes are healthy
```

---

## 🔄 How It Works - Step by Step

### **On Note Capture (Real-time)**

```
1. User sends LINE message with URL
2. Bot captures URL → creates note
3. ✨ Enrich: Add tags + summary
4. 🔍 Analyze: Check if DevOps/AI + decay
5. Commit to GitHub
```

**What "Analyze" does:**
- Checks if note mentions DevOps/AI keywords
- If yes: Extract versions (Python 3.8, Docker 20.10, etc.)
- Call AI to assess if outdated
- If outdated: Add deprecation notice
- Log for monthly review

### **Monthly Scan (1st at 9 AM)**

```
1. Render cron triggers script
2. Python script scans entire vault
3. For each DevOps/AI note:
   - Calculate age
   - Detect version numbers
   - AI analysis: Is it outdated?
   - Assign freshness level
4. Generate report with categories
5. Git commit + push to GitHub
6. Report appears in `.decay-report-monthly.md`
```

---

## 📈 Freshness Thresholds

Based on your requirement: **"Current" = 3 months**

| Level | Age | Action |
|-------|-----|--------|
| EVERGREEN | 0-3 months | Keep as-is ✅ |
| MEDIUM | 3-4 months | Review soon 🟡 |
| HIGH | 4-6 months | Update this month 🟠 |
| CRITICAL | 6+ months | Update ASAP 🔴 |

---

## 🎯 DevOps Topics Monitored

### Infrastructure
- Docker, Kubernetes, Terraform, Ansible
- AWS, GCP, Azure, DigitalOcean
- Load balancers, CDN, VPC

### CI/CD
- GitHub Actions, GitLab CI, Jenkins
- CircleCI, deployment strategies

### Monitoring
- Prometheus, Grafana, ELK
- Datadog, New Relic, alerting

### Platforms
- Nginx, Apache, reverse proxies

---

## 🤖 AI Topics Monitored

### Models & Frameworks
- GPT, Claude, Mistral, Llama
- Transformers, BERT, RAG
- PyTorch, TensorFlow, Keras, HuggingFace

### Techniques
- Fine-tuning, Quantization, LoRA
- Embeddings, Vector search
- Agents, Tool use, Function calling

---

## 💡 Cost

**Per capture:** ~$0.001 (real-time decay check)  
**Per monthly scan:** ~$0.01-0.02  
**Monthly estimate:** $0.05-0.10 (for decay system alone)

---

## 🚀 Deployment Status

✅ Code: `bot/knowledge_decay.py`  
✅ Integration: `bot/app.py` updated  
✅ Git: Commit `4eb7c4c` pushed  
✅ Auto-deploy: Enabled  
✅ Status: **LIVE on Render**

---

## 📝 Manual Testing

Generate a test report:
```bash
cd ~/Documents/PersonalKM
python3 test_knowledge_decay.py
```

This will create `TEST-decay-report.md` showing what the system detects.

---

## 🔧 Configuration

To adjust thresholds, edit `bot/knowledge_decay.py`:

```python
# Line 22-26
CURRENT_THRESHOLD_DAYS = 90  # Change to 60 for 2 months, 120 for 4 months
FRESHNESS_LEVELS = {
    "CRITICAL": 180,    # 6 months
    "HIGH": 120,        # 4 months
    "MEDIUM": 90,       # 3 months
}
```

---

## 📅 What You'll Get

### **Each capture:**
- ✅ Note created
- ✅ Tags + summary added
- ✅ Decay check (flags if outdated)
- ✅ Deprecation notice added (if needed)

### **Every month (1st at 9 AM):**
- 📊 `.decay-report-monthly.md` generated
- 📋 Lists all notes by freshness
- 💡 Suggests 10 most critical updates
- 🔗 Shows related topics
- 📤 Auto-committed to GitHub

### **You get:**
- 🎯 Clear view of what's stale
- 📌 Prioritized update list
- 🔔 Automated notifications
- 🧠 Knowledge stays current

---

## ✨ The Impact

**Before:**
- Notes age silently
- You forget what's outdated
- Decisions based on stale info

**After:**
- 🔴 Sees exactly what needs updating
- 🔄 Gets monthly reminder
- ✅ Knowledge stays fresh and trustworthy
- 🚀 Wiki evolves with technology

---

## 🎊 Summary

**System:** Fully automated knowledge decay detection  
**Scope:** DevOps & AI topics  
**Freshness:** 3-month threshold (you decide updates)  
**Reports:** Monthly digest (1st of month)  
**Cost:** ~$0.05-0.10/month  
**Status:** ✅ LIVE and auto-deployed

Your personal wiki now **self-maintains** and keeps you updated on what's aging! 🚀
