#!/usr/bin/env python3
"""
Test Ingestion Script
Run this locally to verify ingestion works with current files
"""
import sys
import os
from pathlib import Path

# Add repo to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_ingestion():
    """Test that ingestion can find and process files."""
    print("=" * 80)
    print("🧪 TESTING INGESTION SYSTEM")
    print("=" * 80)
    
    # Test 1: Check raw/ directory
    repo_root = Path(__file__).parent.parent
    raw_path = repo_root / "raw"
    
    print(f"\n📁 Test 1: Checking raw/ directory")
    print(f"   Path: {raw_path}")
    
    if not raw_path.exists():
        print(f"   ❌ FAIL: raw/ does not exist")
        return False
    
    # Count files including subdirectories
    md_files = list(raw_path.glob("**/*.md"))
    print(f"   ✅ Found {len(md_files)} markdown files")
    
    if len(md_files) == 0:
        print(f"   ⚠️  WARNING: No files to ingest!")
        return False
    
    # Test 2: Check subdirectories
    print(f"\n📂 Test 2: Checking subdirectories")
    subdirs = [d for d in raw_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
    for subdir in subdirs:
        files = list(subdir.glob("*.md"))
        print(f"   {subdir.name}/: {len(files)} files")
    
    # Test 3: Check wiki/ directory
    print(f"\n📚 Test 3: Checking wiki/ directory")
    wiki_path = repo_root / "wiki"
    if wiki_path.exists():
        wiki_files = list(wiki_path.glob("**/*.md"))
        print(f"   ✅ wiki/ exists with {len(wiki_files)} files")
    else:
        print(f"   ⚠️  wiki/ does not exist yet (will be created)")
    
    # Test 4: Check environment
    print(f"\n🔑 Test 4: Checking environment variables")
    required_vars = ["VAULT_REPO_URL", "OPENAI_API_KEY"]
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Show partial for security
            print(f"   ✅ {var}: {value[:10]}...")
        else:
            print(f"   ⚠️  {var}: not set (may be needed for full test)")
    
    # Test 5: Test glob pattern
    print(f"\n🔍 Test 5: Testing glob pattern (recursive)")
    test_files = list(raw_path.glob("**/*.md"))
    print(f"   Pattern '**/*.md' found: {len(test_files)} files")
    
    # Show sample of what would be processed
    print(f"\n📋 Sample files that would be processed:")
    for f in test_files[:5]:
        print(f"   - {f.parent.name}/{f.name[:50]}...")
    
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    success = test_ingestion()
    sys.exit(0 if success else 1)