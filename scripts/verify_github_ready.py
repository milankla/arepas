#!/usr/bin/env python3
"""
GitHub readiness verification script for Arepas project.
Checks that all necessary files are in place and functioning.
"""

import sys
from pathlib import Path
import importlib.util


def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists and report status."""
    path = Path(filepath)
    exists = path.exists()
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {filepath}")
    if exists and filepath.endswith('.md'):
        # Check if markdown files have content
        content = path.read_text(encoding='utf-8')
        if len(content.strip()) < 100:
            print(f"   ⚠️  Warning: {filepath} appears to be very short")
    return exists


def check_import(module_name: str, description: str) -> bool:
    """Check if a module can be imported."""
    try:
        # Add src to path for imports
        import sys
        from pathlib import Path
        src_path = Path(__file__).parent.parent / 'src'
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        __import__(module_name.replace('src.', ''))
        print(f"✅ {description}: {module_name}")
        return True
    except Exception as e:
        print(f"❌ {description}: {module_name} - {str(e)}")
        return False


def main():
    """Run all verification checks."""
    print("🔍 Verifying Arepas GitHub Readiness")
    print("=" * 50)
    
    # Essential files
    essential_files = [
        ("README.md", "Main documentation"),
        ("LICENSE", "License file"),
        ("requirements.txt", "Python dependencies"),
        (".gitignore", "Git ignore rules"),
        ("CONTRIBUTING.md", "Contribution guidelines"),
        ("CHANGELOG.md", "Change log"),
    ]
    
    # Documentation files
    docs = [
        ("docs/PROJECT_STRUCTURE.md", "Architecture documentation"),
        (".github/workflows/ci.yml", "CI workflow"),
        (".github/ISSUE_TEMPLATE/bug_report.md", "Bug report template"),
        (".github/ISSUE_TEMPLATE/feature_request.md", "Feature request template"),
        (".github/pull_request_template.md", "Pull request template"),
        ("scripts/README.md", "Scripts documentation"),
    ]
    
    # Source code structure
    source_files = [
        ("src/__init__.py", "Main package init"),
        ("src/loader/__init__.py", "Loader package init"),
        ("src/loader/configurable_loader.py", "Configurable data loader"),
        ("src/loader/csv_parser.py", "CSV parser"),
        ("src/loader/image_index.py", "Image indexer"),
        ("src/fine_tune.py", "Main pipeline"),
    ]
    
    print("\n📋 Essential Files")
    print("-" * 20)
    essential_ok = all(check_file_exists(f, desc) for f, desc in essential_files)
    
    print("\n📚 Documentation")
    print("-" * 20)
    docs_ok = all(check_file_exists(f, desc) for f, desc in docs)
    
    print("\n🎯 Source Code Structure") 
    print("-" * 20)
    source_ok = all(check_file_exists(f, desc) for f, desc in source_files)
    
    # Check for sensitive files BEFORE importing modules (which creates __pycache__)
    print("\n📊 Project Statistics")
    print("-" * 20)
    
    # Count Python files
    py_files = list(Path('src').rglob('*.py'))
    print(f"✅ Python source files: {len(py_files)}")
    
    # Check for sensitive files that shouldn't be committed
    sensitive_patterns = ['*.log', '*.pyc', '__pycache__', '.DS_Store', '.env']
    sensitive_found = []
    for pattern in sensitive_patterns:
        matches = list(Path('.').rglob(pattern))
        # Filter out .venv directory
        matches = [m for m in matches if not str(m).startswith('.venv/')]
        if matches:
            sensitive_found.extend(matches)
    
    if sensitive_found:
        # Categorize by type
        cache_files = [f for f in sensitive_found if '__pycache__' in str(f) or str(f).endswith('.pyc')]
        other_files = [f for f in sensitive_found if f not in cache_files]
        
        if cache_files:
            print(f"ℹ️  Python cache files found: {len(cache_files)} (normal, will be ignored by git)")
        
        if other_files:
            print(f"⚠️  Sensitive files found: {len(other_files)}")
            for f in other_files[:5]:  # Show first 5
                print(f"   - {f}")
            print(f"\n💡 Run this to clean: find . -name '.DS_Store' -not -path './.venv/*' -delete")
        elif not cache_files:
            print("✅ No sensitive files found in repository")
    else:
        print("✅ No sensitive files found in repository")
    
    # Import tests AFTER checking for cache files
    print("\n🔧 Module Imports")
    print("-" * 20)
    imports_to_test = [
        ("src.loader", "Loader package"),
        ("src.loader.configurable_loader", "ConfigurableDataLoader"),
        ("src.loader.csv_parser", "CSV Parser"),
        ("src.loader.image_index", "Image Index"),
    ]
    
    imports_ok = all(check_import(module, desc) for module, desc in imports_to_test)
    
    print("\n🎉 Overall Status")
    print("=" * 20)
    
    all_checks = [essential_ok, docs_ok, source_ok, imports_ok]
    overall_ok = all(all_checks)
    
    if overall_ok:
        print("🚀 Project is ready for GitHub!")
        print("\nNext steps:")
        print("1. Initialize git repository: git init")
        print("2. Add files: git add .")
        print("3. Create initial commit: git commit -m 'Initial commit'")
        print("4. Create GitHub repository")
        print("5. Add remote: git remote add origin <your-repo-url>")
        print("6. Push: git push -u origin main")
        return 0
    else:
        print("❌ Some issues need to be resolved before GitHub publication")
        return 1


if __name__ == "__main__":
    sys.exit(main())
