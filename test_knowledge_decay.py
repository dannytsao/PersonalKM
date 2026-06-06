#!/usr/bin/env python3
"""Test knowledge decay report generation (local)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bot.knowledge_decay import generate_report
import tempfile

# Create a test report
repo_root = Path(__file__).parent
report_path = repo_root / "TEST-decay-report.md"

print("🔍 Generating test decay report...")
print(f"📁 Vault: {repo_root}")
print(f"📝 Report: {report_path}")
print()

success = generate_report(repo_root, report_path)

if success and report_path.exists():
    print("✅ Test report generated!")
    print("\n" + "="*70)
    print(report_path.read_text()[:1500])
    print("...\n(truncated for display)")
    print("="*70)
else:
    print("❌ Failed to generate test report")
